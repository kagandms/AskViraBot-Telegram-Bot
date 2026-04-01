from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from dataclasses import asdict, dataclass
from threading import Lock, Thread
from typing import Any
from urllib.parse import unquote

from flask import Flask, jsonify, request, send_from_directory
from telegram import Update

from config import ALLOW_LOCAL_WEBAPP_BYPASS, BOT_TOKEN
from services.game_service import get_web_game_high_score, save_web_game_score

# Configure Flask to serve static files from 'web' directory
app = Flask(__name__, static_folder="web", static_url_path="/web")
logger = logging.getLogger(__name__)
ALLOWED_GAME_TYPES = {"snake", "2048", "flappy", "runner", "sudoku", "xox"}


@dataclass(slots=True)
class BotRuntimeStatus:
    ready: bool = False
    mode: str = "not-started"
    webhook_path: str | None = None
    webhook_url: str | None = None
    last_error: str | None = None


@dataclass(slots=True)
class BotRuntimeContext:
    application: Any | None = None
    loop: asyncio.AbstractEventLoop | None = None
    secret_token: str | None = None


_bot_status = BotRuntimeStatus()
_bot_runtime = BotRuntimeContext()
_bot_runtime_lock = Lock()


def mark_bot_starting(*, mode: str, webhook_path: str | None = None, webhook_url: str | None = None) -> None:
    with _bot_runtime_lock:
        _bot_status.ready = False
        _bot_status.mode = mode
        _bot_status.webhook_path = webhook_path
        _bot_status.webhook_url = webhook_url
        _bot_status.last_error = None


def mark_bot_ready() -> None:
    with _bot_runtime_lock:
        _bot_status.ready = True
        _bot_status.last_error = None


def mark_bot_failed(error_message: str) -> None:
    with _bot_runtime_lock:
        _bot_status.ready = False
        _bot_status.last_error = error_message


def register_bot_runtime(
    *,
    application: Any,
    loop: asyncio.AbstractEventLoop,
    secret_token: str | None = None,
) -> None:
    with _bot_runtime_lock:
        _bot_runtime.application = application
        _bot_runtime.loop = loop
        _bot_runtime.secret_token = secret_token


def clear_bot_runtime() -> None:
    with _bot_runtime_lock:
        _bot_runtime.application = None
        _bot_runtime.loop = None
        _bot_runtime.secret_token = None
        _bot_status.ready = False


def get_bot_status() -> dict[str, object]:
    with _bot_runtime_lock:
        return asdict(_bot_status)


@app.route("/")
def home():
    status = get_bot_status()
    status_code = 200 if status["ready"] else 503
    return jsonify(status), status_code


@app.route("/healthz")
def healthz():
    return home()


# --- STATIC FILE SERVING ---
@app.route("/web/<path:path>")
def serve_web_files(path):
    return send_from_directory("web", path)


# --- API HELPER: VALIDATE TELEGRAM WEBAPP DATA ---
def validate_telegram_data(init_data: str | None) -> dict[str, Any] | None:
    """
    Validates the data received from the Telegram Web App.
    Returns the user data if valid, None otherwise.
    """
    if not init_data:
        return None

    try:
        parsed_data = {}
        for key_value in init_data.split("&"):
            key, value = key_value.split("=", 1)
            parsed_data[unquote(key)] = unquote(value)

        hash_value = parsed_data.pop("hash", None)
        if not hash_value:
            return None

        # Sort keys alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # Calculate HMAC-SHA256 signature
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash == hash_value:
            # Data is valid, parse 'user' JSON
            user_json = parsed_data.get("user")
            if user_json:
                return json.loads(user_json)
    except Exception as e:
        logger.warning(f"Telegram WebApp validation failed: {e}")
    return None


@app.route("/api/test", methods=["GET"])
def test_api():
    return jsonify({"status": "ok", "message": "API is reachable"})


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid update payload"}), 400

    with _bot_runtime_lock:
        application = _bot_runtime.application
        loop = _bot_runtime.loop
        secret_token = _bot_runtime.secret_token

    if not application or not loop:
        return jsonify({"error": "Bot runtime unavailable"}), 503

    if secret_token:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_token != secret_token:
            return jsonify({"error": "Forbidden"}), 403

    update = Update.de_json(payload, application.bot)
    if update is None:
        return jsonify({"error": "Invalid update payload"}), 400

    try:
        future = asyncio.run_coroutine_threadsafe(application.update_queue.put(update), loop)
        future.result(timeout=5)
    except Exception as e:
        logger.error(f"Webhook update enqueue failed: {e}", exc_info=True)
        return jsonify({"error": "Unable to enqueue update"}), 500

    return jsonify({"ok": True})


@app.route("/api/save_score", methods=["POST"])
def save_score():
    """
    Saves game score from Web App.
    Expects JSON: { "initData": "...", "game": "snake", "score": 100, "difficulty": "easy" }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No data provided"}), 400

        init_data = data.get("initData")
        user_data = validate_telegram_data(init_data)

        # Local development override is disabled by default and must be explicit.
        if not user_data and ALLOW_LOCAL_WEBAPP_BYPASS and request.host.startswith("localhost"):
            # Mock user for testing
            user_data = {"id": 123456789, "first_name": "TestUser"}

        if not user_data:
            return jsonify({"error": "Invalid authentication"}), 401

        user_id = str(user_data["id"])
        game_type = data.get("game")
        difficulty = data.get("difficulty")

        if not game_type or game_type not in ALLOWED_GAME_TYPES:
            return jsonify({"error": "Game type required"}), 400

        try:
            score = int(data.get("score", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid score"}), 400

        # Save via service
        success = save_web_game_score(user_id, game_type, score, difficulty)

        if success:
            best_score = get_web_game_high_score(user_id, game_type)
            return jsonify({"success": True, "best_score": best_score, "new_high_score": score >= best_score})
        else:
            return jsonify({"error": "Unable to save score"}), 500

    except Exception as e:
        logger.error(f"Score API error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


def run_http_server() -> None:
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, use_reloader=False)


def keep_alive() -> Thread:
    t = Thread(target=run_http_server, name="keep-alive-server", daemon=True)
    t.start()
    return t
