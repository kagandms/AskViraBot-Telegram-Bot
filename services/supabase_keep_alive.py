from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEFAULT_KEEP_ALIVE_TABLE = "users"
DEFAULT_KEEP_ALIVE_SELECT = "user_id"
DEFAULT_TIMEOUT_SECONDS = 20
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SELECT_PATTERN = re.compile(r"^[A-Za-z0-9_,*]+$")


class SupabaseKeepAliveError(RuntimeError):
    """Raised when the scheduled Supabase keep-alive check cannot complete."""


@dataclass(frozen=True, slots=True)
class SupabaseKeepAliveConfig:
    """Runtime configuration for a low-impact Supabase REST keep-alive request."""

    url: str
    key: str = field(repr=False)
    table: str = DEFAULT_KEEP_ALIVE_TABLE
    select: str = DEFAULT_KEEP_ALIVE_SELECT
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        validate_supabase_url(self.url)
        validate_table_name(self.table)
        validate_select_clause(self.select)
        validate_timeout(self.timeout_seconds)


def load_keep_alive_config(env: Mapping[str, str] | None = None) -> SupabaseKeepAliveConfig:
    """Build keep-alive config from environment variables.

    Args:
        env: Optional environment mapping, mainly for tests.

    Returns:
        Validated Supabase keep-alive configuration.

    Raises:
        SupabaseKeepAliveError: If required settings are missing or invalid.
    """
    source = env if env is not None else os.environ
    return SupabaseKeepAliveConfig(
        url=get_required_env(source, "SUPABASE_URL"),
        key=get_required_env(source, "SUPABASE_KEY"),
        table=get_optional_env(source, "SUPABASE_KEEP_ALIVE_TABLE", DEFAULT_KEEP_ALIVE_TABLE),
        select=get_optional_env(source, "SUPABASE_KEEP_ALIVE_SELECT", DEFAULT_KEEP_ALIVE_SELECT),
        timeout_seconds=parse_timeout_seconds(source.get("SUPABASE_KEEP_ALIVE_TIMEOUT_SECONDS")),
    )


def ping_supabase(config: SupabaseKeepAliveConfig) -> int:
    """Execute one authenticated Supabase REST read to prevent inactivity pausing.

    Args:
        config: Validated keep-alive configuration.

    Returns:
        HTTP status code returned by Supabase.

    Raises:
        SupabaseKeepAliveError: If Supabase cannot be reached or returns a non-2xx response.
    """
    request = Request(
        build_keep_alive_url(config),
        headers=build_keep_alive_headers(config),
        method="GET",
    )

    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            response.read()
            status_code = response.status
    except HTTPError as error:
        raise build_http_error(error) from error
    except URLError as error:
        raise SupabaseKeepAliveError(f"Supabase keep-alive network error: {error.reason}") from error

    if not 200 <= status_code < 300:
        raise SupabaseKeepAliveError(f"Supabase keep-alive returned unexpected HTTP {status_code}")

    logger.info("Supabase keep-alive succeeded with HTTP %s", status_code)
    return status_code


def build_keep_alive_url(config: SupabaseKeepAliveConfig) -> str:
    """Build the Supabase REST endpoint URL for the keep-alive read."""
    query = urlencode({"select": config.select, "limit": "1"})
    return f"{config.url.rstrip('/')}/rest/v1/{config.table}?{query}"


def build_keep_alive_headers(config: SupabaseKeepAliveConfig) -> dict[str, str]:
    """Build authenticated Supabase REST headers without exposing secrets in logs."""
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.key}",
        "apikey": config.key,
    }


def get_required_env(env: Mapping[str, str], name: str) -> str:
    """Read a required environment variable."""
    value = env.get(name, "").strip()
    if value:
        return value
    raise SupabaseKeepAliveError(f"Missing required environment variable: {name}")


def get_optional_env(env: Mapping[str, str], name: str, default: str) -> str:
    """Read an optional environment variable with empty values treated as unset."""
    value = env.get(name, "").strip()
    if value:
        return value
    return default


def parse_timeout_seconds(raw_value: str | None) -> int:
    """Parse the request timeout from environment input."""
    if not raw_value:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        timeout_seconds = int(raw_value)
    except ValueError as error:
        raise SupabaseKeepAliveError("SUPABASE_KEEP_ALIVE_TIMEOUT_SECONDS must be an integer") from error

    validate_timeout(timeout_seconds)
    return timeout_seconds


def validate_supabase_url(url: str) -> None:
    """Validate Supabase project URL format."""
    if url.startswith(("https://", "http://")):
        return
    raise SupabaseKeepAliveError("SUPABASE_URL must start with http:// or https://")


def validate_table_name(table: str) -> None:
    """Validate the REST table path segment."""
    if IDENTIFIER_PATTERN.fullmatch(table):
        return
    raise SupabaseKeepAliveError("SUPABASE_KEEP_ALIVE_TABLE must be a simple table identifier")


def validate_select_clause(select: str) -> None:
    """Validate a constrained PostgREST select clause for scheduled keep-alive reads."""
    if SELECT_PATTERN.fullmatch(select):
        return
    raise SupabaseKeepAliveError("SUPABASE_KEEP_ALIVE_SELECT contains unsupported characters")


def validate_timeout(timeout_seconds: int) -> None:
    """Validate network timeout boundaries."""
    if 1 <= timeout_seconds <= 120:
        return
    raise SupabaseKeepAliveError("SUPABASE_KEEP_ALIVE_TIMEOUT_SECONDS must be between 1 and 120")


def build_http_error(error: HTTPError) -> SupabaseKeepAliveError:
    """Convert an HTTPError into a sanitized keep-alive error."""
    response_body = error.read().decode("utf-8", errors="replace")[:500]
    return SupabaseKeepAliveError(f"Supabase keep-alive failed with HTTP {error.code}: {response_body}")
