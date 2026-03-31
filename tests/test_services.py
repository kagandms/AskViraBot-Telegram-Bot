"""
Service Layer & Handler Utility Tests
Tests for cache_service, weather cache eviction, video URL validation,
and admin_only decorator.

Run with: python -m pytest tests/test_services.py -v
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# CACHE SERVICE TESTS
# =============================================================================


class TestCacheServiceNoRedis:
    """Test cache service behavior when Redis is not available."""

    @pytest.mark.asyncio
    async def test_get_cache_without_redis_returns_none(self):
        """get_cache should return None when redis_client is None."""
        from services.cache_service import get_cache

        with patch("services.cache_service.redis_client", None):
            result = await get_cache("test_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_set_cache_without_redis_no_error(self):
        """set_cache should silently do nothing when redis_client is None."""
        from services.cache_service import set_cache

        with patch("services.cache_service.redis_client", None):
            await set_cache("key", "value")  # Should not raise

    @pytest.mark.asyncio
    async def test_delete_cache_without_redis_no_error(self):
        """delete_cache should silently do nothing when redis_client is None."""
        from services.cache_service import delete_cache

        with patch("services.cache_service.redis_client", None):
            await delete_cache("key")  # Should not raise


class TestCacheServiceWithRedis:
    """Test cache service behavior with mocked Redis."""

    @pytest.mark.asyncio
    async def test_get_cache_returns_parsed_json(self):
        """get_cache should parse JSON values from Redis."""
        from services.cache_service import get_cache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"lang": "tr"})
        with patch("services.cache_service.redis_client", mock_redis):
            result = await get_cache("user:123:lang")
            assert result == {"lang": "tr"}

    @pytest.mark.asyncio
    async def test_get_cache_returns_raw_for_non_json(self):
        """get_cache should return raw string when JSON parse fails."""
        from services.cache_service import get_cache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = "plain_string"
        with patch("services.cache_service.redis_client", mock_redis):
            result = await get_cache("user:123:lang")
            assert result == "plain_string"

    @pytest.mark.asyncio
    async def test_get_cache_returns_none_for_missing_key(self):
        """get_cache should return None for a key that doesn't exist."""
        from services.cache_service import get_cache

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        with patch("services.cache_service.redis_client", mock_redis):
            result = await get_cache("nonexistent_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_set_cache_serializes_and_sets(self):
        """set_cache should JSON-serialize and call setex with TTL."""
        from services.cache_service import set_cache

        mock_redis = AsyncMock()
        with patch("services.cache_service.redis_client", mock_redis):
            await set_cache("key", {"data": 1}, ttl=600)
            mock_redis.setex.assert_called_once_with("key", 600, json.dumps({"data": 1}))

    @pytest.mark.asyncio
    async def test_set_cache_default_ttl_3600(self):
        """set_cache should use 3600 as default TTL."""
        from services.cache_service import set_cache

        mock_redis = AsyncMock()
        with patch("services.cache_service.redis_client", mock_redis):
            await set_cache("key", "value")
            args = mock_redis.setex.call_args[0]
            assert args[1] == 3600  # Default TTL

    @pytest.mark.asyncio
    async def test_delete_cache_calls_redis_delete(self):
        """delete_cache should call Redis delete."""
        from services.cache_service import delete_cache

        mock_redis = AsyncMock()
        with patch("services.cache_service.redis_client", mock_redis):
            await delete_cache("key_to_delete")
            mock_redis.delete.assert_called_once_with("key_to_delete")


# =============================================================================
# WEATHER CACHE EVICTION TESTS
# =============================================================================


class TestWeatherCacheEviction:
    """Test the weather cache eviction logic."""

    def test_evict_removes_expired_entries(self):
        """Expired entries should be removed."""
        from handlers.weather import _evict_expired_cache, _weather_cache

        _weather_cache.clear()
        now = datetime.now()
        # Add an expired entry
        _weather_cache["expired_city"] = {"data": {}, "expires": now - timedelta(minutes=1), "lang": "tr"}
        # Add a valid entry
        _weather_cache["valid_city"] = {"data": {}, "expires": now + timedelta(minutes=5), "lang": "en"}
        _evict_expired_cache()
        assert "expired_city" not in _weather_cache
        assert "valid_city" in _weather_cache

    def test_evict_respects_max_size(self):
        """Cache should not exceed MAX_WEATHER_CACHE_SIZE after eviction."""
        from handlers.weather import MAX_WEATHER_CACHE_SIZE, _evict_expired_cache, _weather_cache

        _weather_cache.clear()
        now = datetime.now()
        # Add more entries than MAX_CACHE_SIZE (all valid)
        for i in range(MAX_WEATHER_CACHE_SIZE + 20):
            _weather_cache[f"city_{i}"] = {"data": {}, "expires": now + timedelta(minutes=i + 1), "lang": "tr"}
        _evict_expired_cache()
        assert len(_weather_cache) <= MAX_WEATHER_CACHE_SIZE

    def test_evict_empty_cache_no_error(self):
        """Eviction on empty cache should not raise."""
        from handlers.weather import _evict_expired_cache, _weather_cache

        _weather_cache.clear()
        _evict_expired_cache()  # Should not raise
        assert len(_weather_cache) == 0


# =============================================================================
# VIDEO URL VALIDATION TESTS
# =============================================================================


class TestVideoUrlValidation:
    """Test video URL validation function."""

    def test_valid_tiktok_url(self):
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://www.tiktok.com/@user/video/123", "tiktok") is True
        assert is_valid_video_url("https://vm.tiktok.com/abc123", "tiktok") is True

    def test_valid_twitter_url(self):
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://twitter.com/user/status/123", "twitter") is True
        assert is_valid_video_url("https://x.com/user/status/123", "twitter") is True

    def test_valid_instagram_url(self):
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://www.instagram.com/reel/abc123", "instagram") is True

    def test_rejects_wrong_platform(self):
        """TikTok URL should fail on twitter platform check."""
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://tiktok.com/video/123", "twitter") is False

    def test_rejects_phishing_url(self):
        """Phishing URLs with legit domain in path/query should fail."""
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://evil.com?redirect=tiktok.com", "tiktok") is False
        assert is_valid_video_url("https://evil.com/tiktok.com/video", "tiktok") is False

    def test_rejects_non_http(self):
        """Non-HTTP schemes should be rejected."""
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("ftp://tiktok.com/video", "tiktok") is False
        assert is_valid_video_url("javascript:alert(1)", "tiktok") is False

    def test_empty_and_invalid_input(self):
        """Empty/invalid strings should be rejected."""
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("", "tiktok") is False
        assert is_valid_video_url("not a url", "tiktok") is False

    def test_unknown_platform_rejects(self):
        """Unknown platform should reject all URLs."""
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://example.com", "unknown") is False

    def test_subdomain_accepted(self):
        """Subdomains of valid domains should be accepted."""
        from handlers.video import is_valid_video_url

        assert is_valid_video_url("https://m.tiktok.com/video/123", "tiktok") is True

    def test_download_workspaces_are_unique(self):
        """Each download request should get its own temp workspace."""
        from handlers.video import create_download_workspace

        first = create_download_workspace(123)
        second = create_download_workspace(123)

        try:
            assert first != second
        finally:
            first.rmdir()
            second.rmdir()


# =============================================================================
# ADMIN_ONLY DECORATOR TESTS
# =============================================================================


class TestAdminOnlyDecorator:
    """Test the admin_only decorator."""

    @pytest.mark.asyncio
    async def test_admin_user_passes(self):
        """Admin user should be allowed through."""
        from utils.decorators import admin_only

        @admin_only
        async def my_handler(update, context):
            return "success"

        mock_update = MagicMock()
        mock_update.effective_user.id = 12345
        mock_context = MagicMock()

        with patch("utils.decorators.settings") as mock_settings:
            mock_settings.get_admin_ids = [12345]
            result = await my_handler(mock_update, mock_context)
            assert result == "success"

    @pytest.mark.asyncio
    async def test_non_admin_user_blocked(self):
        """Non-admin user should be blocked with error message."""
        from utils.decorators import admin_only

        @admin_only
        async def my_handler(update, context):
            return "success"

        mock_update = MagicMock()
        mock_update.effective_user.id = 99999
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()

        with patch("utils.decorators.settings") as mock_settings:
            mock_settings.get_admin_ids = [12345]
            result = await my_handler(mock_update, mock_context)
            assert result is None
            mock_update.message.reply_text.assert_called_once()
            call_text = mock_update.message.reply_text.call_args[0][0]
            assert "⛔" in call_text
