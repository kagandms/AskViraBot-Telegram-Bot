from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.supabase_keep_alive import SupabaseKeepAliveError, load_keep_alive_config, ping_supabase


def main() -> int:
    """Run one Supabase keep-alive ping for scheduled jobs.

    Returns:
        Process exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        status_code = ping_supabase(load_keep_alive_config())
    except SupabaseKeepAliveError as error:
        logging.getLogger(__name__).error("%s", error)
        return 1

    logging.getLogger(__name__).info("Supabase keep-alive completed with HTTP %s", status_code)
    return 0


if __name__ == "__main__":
    sys.exit(main())
