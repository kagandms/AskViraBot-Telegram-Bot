"""
Rate Limiter Unit Tests
Tests for is_rate_limited, get_remaining_cooldown, clear_user_limits,
get_user_stats, and _cleanup_old_records functions.

Run with: python -m pytest tests/test_rate_limiter.py -v
"""

import time


class TestIsRateLimited:
    """Test the core rate limiting logic."""

    def setup_method(self):
        """Reset rate limiter state before each test."""
        from rate_limiter import user_requests

        user_requests.clear()

    def test_first_request_not_limited(self):
        """First request should never be rate limited."""
        from rate_limiter import is_rate_limited

        assert is_rate_limited(12345, "general") is False

    def test_within_limit_not_limited(self):
        """Requests within the limit should pass."""
        from rate_limiter import RATE_LIMITS, is_rate_limited

        user_id = 99999
        limit = RATE_LIMITS["general"]
        for _i in range(limit - 1):
            assert is_rate_limited(user_id, "general") is False

    def test_exceeds_limit_is_limited(self):
        """Requests exceeding the limit should be blocked."""
        from rate_limiter import RATE_LIMITS, is_rate_limited

        user_id = 88888
        limit = RATE_LIMITS["general"]
        for _ in range(limit):
            is_rate_limited(user_id, "general")
        assert is_rate_limited(user_id, "general") is True

    def test_different_categories_independent(self):
        """Rate limits per category should be independent."""
        from rate_limiter import RATE_LIMITS, is_rate_limited

        user_id = 77777
        # Fill up 'games' category
        for _ in range(RATE_LIMITS["games"]):
            is_rate_limited(user_id, "games")
        # 'general' should still be available
        assert is_rate_limited(user_id, "general") is False

    def test_different_users_independent(self):
        """Rate limits per user should be independent."""
        from rate_limiter import RATE_LIMITS, is_rate_limited

        for _ in range(RATE_LIMITS["general"]):
            is_rate_limited(111, "general")
        assert is_rate_limited(111, "general") is True
        assert is_rate_limited(222, "general") is False

    def test_expired_requests_cleaned(self):
        """Old requests outside the window should be cleaned up."""
        from rate_limiter import WINDOW_SECONDS, is_rate_limited, user_requests

        user_id = 66666
        # Inject old timestamps outside the window
        old_time = time.time() - WINDOW_SECONDS - 10
        user_requests[user_id]["general"] = [old_time] * 50
        # Should not be limited because all old entries are expired
        assert is_rate_limited(user_id, "general") is False

    def test_unknown_category_uses_general_limit(self):
        """Unknown category should fall back to general limit."""
        from rate_limiter import RATE_LIMITS, is_rate_limited

        user_id = 55555
        # Should use general limit for unknown category
        for _ in range(RATE_LIMITS["general"]):
            is_rate_limited(user_id, "unknown_category")
        assert is_rate_limited(user_id, "unknown_category") is True


class TestGetRemainingCooldown:
    """Test cooldown remaining time calculation."""

    def setup_method(self):
        from rate_limiter import user_requests

        user_requests.clear()

    def test_no_requests_returns_zero(self):
        """No requests should return 0 cooldown."""
        from rate_limiter import get_remaining_cooldown

        assert get_remaining_cooldown(12345, "general") == 0

    def test_active_requests_returns_positive(self):
        """Active requests should return positive cooldown."""
        from rate_limiter import get_remaining_cooldown, user_requests

        user_id = 44444
        user_requests[user_id]["general"].append(time.time())
        cooldown = get_remaining_cooldown(user_id, "general")
        assert cooldown > 0
        assert cooldown <= 60

    def test_old_requests_return_zero(self):
        """Expired requests should return 0 cooldown."""
        from rate_limiter import WINDOW_SECONDS, get_remaining_cooldown, user_requests

        user_id = 33333
        user_requests[user_id]["general"].append(time.time() - WINDOW_SECONDS - 5)
        cooldown = get_remaining_cooldown(user_id, "general")
        assert cooldown == 0


class TestClearUserLimits:
    """Test clearing user rate limits."""

    def setup_method(self):
        from rate_limiter import user_requests

        user_requests.clear()

    def test_clear_existing_user(self):
        """Should remove all records for a user."""
        from rate_limiter import clear_user_limits, is_rate_limited, user_requests

        user_id = 22222
        is_rate_limited(user_id, "general")
        assert user_id in user_requests
        clear_user_limits(user_id)
        assert user_id not in user_requests

    def test_clear_nonexistent_user_no_error(self):
        """Clearing a user that doesn't exist should not raise."""
        from rate_limiter import clear_user_limits

        clear_user_limits(99999)  # Should not raise


class TestGetUserStats:
    """Test user rate limit statistics."""

    def setup_method(self):
        from rate_limiter import user_requests

        user_requests.clear()

    def test_fresh_user_all_remaining(self):
        """Fresh user should have full limits remaining."""
        from rate_limiter import RATE_LIMITS, get_user_stats

        stats = get_user_stats(11111)
        for category, limit in RATE_LIMITS.items():
            assert stats[category]["used"] == 0
            assert stats[category]["remaining"] == limit
            assert stats[category]["limit"] == limit

    def test_after_requests_stats_updated(self):
        """Stats should reflect requests made."""
        from rate_limiter import RATE_LIMITS, get_user_stats, is_rate_limited

        user_id = 10101
        is_rate_limited(user_id, "general")
        is_rate_limited(user_id, "general")
        stats = get_user_stats(user_id)
        assert stats["general"]["used"] == 2
        assert stats["general"]["remaining"] == RATE_LIMITS["general"] - 2


class TestCleanupOldRecords:
    """Test periodic memory cleanup."""

    def setup_method(self):
        from rate_limiter import user_requests

        user_requests.clear()

    def test_cleanup_removes_inactive_users(self):
        """Very old entries should be cleaned up."""
        import rate_limiter

        user_requests = rate_limiter.user_requests
        user_id = 10001

        # Add entry well past the inactive threshold
        old_time = time.time() - rate_limiter.INACTIVE_THRESHOLD - 100
        user_requests[user_id]["general"].append(old_time)

        # Force cleanup by setting last cleanup time far in the past
        rate_limiter._last_cleanup_time = 0
        rate_limiter._cleanup_old_records()

        assert user_id not in user_requests
