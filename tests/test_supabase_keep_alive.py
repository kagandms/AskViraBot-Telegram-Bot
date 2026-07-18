from __future__ import annotations

from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from services.supabase_keep_alive import (
    SupabaseKeepAliveConfig,
    SupabaseKeepAliveError,
    build_keep_alive_url,
    load_keep_alive_config,
    ping_supabase,
)


class FakeResponse:
    def __init__(self, status: int, body: bytes = b"[]") -> None:
        self.status = status
        self._body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        return None


def test_load_keep_alive_config_reads_required_and_optional_env() -> None:
    env = {
        "SUPABASE_URL": "https://project.supabase.co",
        "SUPABASE_KEY": "secret-key",
        "SUPABASE_KEEP_ALIVE_TABLE": "notes",
        "SUPABASE_KEEP_ALIVE_SELECT": "id,user_id",
        "SUPABASE_KEEP_ALIVE_TIMEOUT_SECONDS": "7",
    }

    config = load_keep_alive_config(env)

    assert config.url == "https://project.supabase.co"
    assert config.key == "secret-key"
    assert config.table == "notes"
    assert config.select == "id,user_id"
    assert config.timeout_seconds == 7


def test_load_keep_alive_config_raises_for_missing_key() -> None:
    env = {"SUPABASE_URL": "https://project.supabase.co"}

    with pytest.raises(SupabaseKeepAliveError, match="SUPABASE_KEY"):
        load_keep_alive_config(env)


def test_build_keep_alive_url_uses_limit_one_read() -> None:
    config = SupabaseKeepAliveConfig(
        url="https://project.supabase.co/",
        key="secret-key",
        table="users",
        select="user_id",
    )

    url = build_keep_alive_url(config)

    assert url == "https://project.supabase.co/rest/v1/users?select=user_id&limit=1"


def test_ping_supabase_sends_authenticated_get_request() -> None:
    captured = {}
    config = SupabaseKeepAliveConfig(
        url="https://project.supabase.co",
        key="secret-key",
        timeout_seconds=5,
    )

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(status=200)

    with patch("services.supabase_keep_alive.urlopen", fake_urlopen):
        status_code = ping_supabase(config)

    request = captured["request"]
    assert status_code == 200
    assert captured["timeout"] == 5
    assert request.get_method() == "GET"
    assert request.get_header("Authorization") == "Bearer secret-key"
    assert request.get_header("Apikey") == "secret-key"


def test_ping_supabase_wraps_http_errors() -> None:
    config = SupabaseKeepAliveConfig(url="https://project.supabase.co", key="secret-key")

    def fake_urlopen(request, timeout):
        raise HTTPError(
            url=request.full_url,
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=FakeResponse(status=401, body=b"invalid token"),
        )

    with patch("services.supabase_keep_alive.urlopen", fake_urlopen):
        with pytest.raises(SupabaseKeepAliveError, match="HTTP 401"):
            ping_supabase(config)
