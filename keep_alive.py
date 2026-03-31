import hashlib
import hmac
import json
import logging
import os
from threading import Thread
from urllib.parse import unquote

from flask import Flask, jsonify, request, send_from_directory

from config import ALLOW_LOCAL_WEBAPP_BYPASS, BOT_TOKEN
from services.game_service import get_web_game_high_score, save_web_game_score

# Configure Flask to serve static files from 'web' directory
app = Flask(__name__, static_folder="web", static_url_path="/web")
logger = logging.getLogger(__name__)
ALLOWED_GAME_TYPES = {"snake", "2048", "flappy", "runner", "sudoku", "xox"}


@app.route("/")
def home():
    # Keep-alive check - Simple response to satisfy Render health check
    return "ViraBot Web App Server is Running! 🚀"


# --- STATIC FILE SERVING ---
@app.route("/web/<path:path>")
def serve_web_files(path):
    return send_from_directory("web", path)


# --- API HELPER: VALIDATE TELEGRAM WEBAPP DATA ---
def validate_telegram_data(init_data):
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


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    # Threaded=True for better handling in dev
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.start()
