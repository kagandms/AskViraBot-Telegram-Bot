"""Web API regression tests for the Flask keep-alive app."""

from unittest.mock import patch


class TestHealthApi:
    """Test bot health endpoints reflect runtime status."""

    def test_home_returns_service_unavailable_until_bot_is_ready(self):
        from keep_alive import app, clear_bot_runtime, mark_bot_starting

        client = app.test_client()
        clear_bot_runtime()
        mark_bot_starting(mode="polling")

        response = client.get("/")

        assert response.status_code == 503
        payload = response.get_json()
        assert payload["ready"] is False
        assert payload["mode"] == "polling"


class TestTelegramWebhookApi:
    """Test webhook endpoint fails fast when bot runtime is unavailable."""

    def test_webhook_returns_service_unavailable_without_runtime(self):
        from keep_alive import app, clear_bot_runtime, mark_bot_starting

        client = app.test_client()
        clear_bot_runtime()
        mark_bot_starting(mode="webhook", webhook_path="/telegram-webhook")

        response = client.post("/telegram-webhook", json={"update_id": 1})

        assert response.status_code == 503
        assert response.get_json()["error"] == "Bot runtime unavailable"


class TestScoreApi:
    """Test WebApp score API auth and validation behavior."""

    def test_rejects_invalid_auth_when_bypass_disabled(self):
        from keep_alive import app

        client = app.test_client()

        with (
            patch("keep_alive.ALLOW_LOCAL_WEBAPP_BYPASS", False),
            patch("keep_alive.validate_telegram_data", return_value=None),
        ):
            response = client.post(
                "/api/save_score",
                json={"initData": "invalid", "game": "snake", "score": 10},
            )

        assert response.status_code == 401
        assert response.get_json()["error"] == "Invalid authentication"

    def test_localhost_bypass_requires_explicit_flag(self):
        from keep_alive import app

        client = app.test_client()

        with (
            patch("keep_alive.ALLOW_LOCAL_WEBAPP_BYPASS", True),
            patch("keep_alive.validate_telegram_data", return_value=None),
            patch("keep_alive.save_web_game_score", return_value=True),
            patch("keep_alive.get_web_game_high_score", return_value=10),
        ):
            response = client.post(
                "/api/save_score",
                base_url="http://localhost",
                json={"game": "snake", "score": 10},
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["best_score"] == 10

    def test_invalid_score_returns_bad_request(self):
        from keep_alive import app

        client = app.test_client()

        with patch("keep_alive.validate_telegram_data", return_value={"id": 1}):
            response = client.post(
                "/api/save_score",
                json={"initData": "valid", "game": "snake", "score": "oops"},
            )

        assert response.status_code == 400
        assert response.get_json()["error"] == "Invalid score"
