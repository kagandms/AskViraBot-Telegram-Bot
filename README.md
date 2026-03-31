# ViraBot

Multilingual Telegram bot with notes, reminders, AI chat, weather, media tools, metro helpers, and web mini-games.

## Repository Status

This repository is prepared for public visibility with placeholder environment
configuration, CI validation, and deployment documentation.

The source is currently published under a source-available proprietary license.
See `LICENSE` before reusing code or assets.

## Stack

- Python 3.11+
- `python-telegram-bot`
- Supabase/PostgreSQL
- Redis (optional cache)
- Flask health-check and WebApp score endpoint
- `aiohttp`, `yt-dlp`, OpenRouter-compatible `openai` client

## Setup

1. Create and activate a Python environment.
2. Install runtime dependencies:

```bash
pip install -r requirements.txt
```

3. Install development tools when needed:

```bash
pip install -r requirements-dev.txt
```

4. Copy `.env.example` to `.env` and fill the required values.
5. Apply `database_schema.sql` to the target Supabase/PostgreSQL database.
6. Ensure `ffmpeg` is installed if you use media download or conversion flows.

## Required Environment Variables

- `TELEGRAM_BOT_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_KEY`

## Optional Environment Variables

- `OPENWEATHERMAP_API_KEY`
- `OPENROUTER_API_KEY`
- `REDIS_URL`
- `ADMIN_IDS`
- `TIMEZONE`
- `BOT_NAME`
- `NOTES_PER_PAGE`
- `AI_DAILY_LIMIT`
- `WEB_APP_BASE_URL`
- `ALLOW_LOCAL_WEBAPP_BYPASS`
- `LOG_LEVEL`
- `LOG_TO_FILE`
- `LOG_FILE_PATH`

`ALLOW_LOCAL_WEBAPP_BYPASS` defaults to `false` and should stay disabled outside explicit local development.

## Running

Local polling mode:

```bash
python main.py
```

The app also starts a Flask server for health checks and Telegram WebApp assets.

## Verification

Run the full test suite:

```bash
pytest
```

Run lint checks:

```bash
ruff check .
```

## Security

Report security issues through GitHub private vulnerability reporting when it is
enabled for the repository. Do not post vulnerabilities in public issues.

## Deployment Notes

- `render.yaml` installs runtime dependencies only.
- `Dockerfile` uses the same runtime dependency set.
- If `WEB_APP_BASE_URL` is unset, web game URLs fall back to `RENDER_EXTERNAL_URL`, then local `http://127.0.0.1:8080`.

## Public Release Notes

The working tree is public-ready, but the historical git metadata from the
private repository should not be exposed unchanged. The recommended release flow
is documented in `docs/public-release.md`.
