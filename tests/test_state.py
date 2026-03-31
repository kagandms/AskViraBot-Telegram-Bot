"""
State Module Unit Tests
Tests for state transitions: set_state, check_state, get_state,
get_data, clear_user_states (all async, mocked DB layer).

Run with: python -m pytest tests/test_state.py -v
"""

from unittest.mock import patch

import pytest


class TestStateConstants:
    """Verify all required state constants are defined and valid."""

    def test_all_handler_states_defined(self):
        """All states used by handlers must be defined."""
        import state

        expected_states = [
            "PLAYING_XOX",
            "PLAYING_TKM",
            "NOTES_IN_MENU",
            "DELETING_NOTES",
            "WAITING_FOR_QR_DATA",
            "WAITING_FOR_REMINDER_INPUT",
            "WAITING_FOR_PDF_CONVERSION_INPUT",
            "WAITING_FOR_WEATHER_CITY",
            "REMINDER_MENU_ACTIVE",
            "WAITING_FOR_REMINDER_DELETE",
            "WAITING_FOR_NEW_NOTE_INPUT",
            "WAITING_FOR_EDIT_NOTE_INPUT",
            "EDITING_NOTES",
            "GAMES_MENU_ACTIVE",
            "WAITING_FOR_SHAZAM",
            "WAITING_FOR_VIDEO_LINK",
            "WAITING_FOR_FORMAT_SELECTION",
            "AI_CHAT_ACTIVE",
            "METRO_BROWSING",
            "TOOLS_MENU_ACTIVE",
            "DEVELOPER_MENU_ACTIVE",
            "METRO_SELECTION",
            "ADMIN_MENU_ACTIVE",
            "AI_MENU_ACTIVE",
        ]
        for state_name in expected_states:
            assert hasattr(state, state_name), f"Missing state: {state_name}"

    def test_states_are_unique_strings(self):
        """All state constants must be unique string values."""
        import state

        state_values = []
        for attr in dir(state):
            val = getattr(state, attr)
            if isinstance(val, str) and not attr.startswith("_") and attr.isupper():
                state_values.append(val)
        # Check uniqueness
        assert len(state_values) == len(set(state_values)), "Duplicate state values found!"

    def test_state_values_are_lowercase(self):
        """State values should be lowercase snake_case."""
        import state

        for attr in dir(state):
            val = getattr(state, attr)
            if isinstance(val, str) and not attr.startswith("_") and attr.isupper():
                assert val == val.lower(), f"State {attr} = '{val}' is not lowercase"


class TestSetState:
    """Test state.set_state async function."""

    @pytest.mark.asyncio
    async def test_set_state_calls_db(self):
        """set_state should call db.set_user_state via asyncio.to_thread."""
        import state

        with patch("state.db.set_user_state") as mock_db:
            await state.set_state(123, "playing_xox", {"board": []})
            mock_db.assert_called_once_with(123, "playing_xox", {"board": []})

    @pytest.mark.asyncio
    async def test_set_state_without_data(self):
        """set_state with no data should pass None."""
        import state

        with patch("state.db.set_user_state") as mock_db:
            await state.set_state(123, "ai_chat_active")
            mock_db.assert_called_once_with(123, "ai_chat_active", None)


class TestCheckState:
    """Test state.check_state async function."""

    @pytest.mark.asyncio
    async def test_matching_state_returns_true(self):
        """Should return True when user is in the specified state."""
        import state

        with patch("state.db.get_user_state", return_value={"state_name": "playing_xox", "state_data": {}}):
            result = await state.check_state(123, "playing_xox")
            assert result is True

    @pytest.mark.asyncio
    async def test_different_state_returns_false(self):
        """Should return False when user is in a different state."""
        import state

        with patch("state.db.get_user_state", return_value={"state_name": "ai_chat_active", "state_data": {}}):
            result = await state.check_state(123, "playing_xox")
            assert result is False

    @pytest.mark.asyncio
    async def test_no_state_returns_false(self):
        """Should return False when user has no active state."""
        import state

        with patch("state.db.get_user_state", return_value=None):
            result = await state.check_state(123, "playing_xox")
            assert result is False


class TestGetState:
    """Test state.get_state async function."""

    @pytest.mark.asyncio
    async def test_returns_state_name(self):
        """Should return the state name string."""
        import state

        with patch("state.db.get_user_state", return_value={"state_name": "metro_browsing", "state_data": {}}):
            result = await state.get_state(456)
            assert result == "metro_browsing"

    @pytest.mark.asyncio
    async def test_no_state_returns_none(self):
        """Should return None when user has no active state."""
        import state

        with patch("state.db.get_user_state", return_value=None):
            result = await state.get_state(456)
            assert result is None


class TestGetData:
    """Test state.get_data async function."""

    @pytest.mark.asyncio
    async def test_returns_state_data(self):
        """Should return the state data dict."""
        import state

        data = {"platform": "tiktok", "format": "video"}
        with patch(
            "state.db.get_user_state", return_value={"state_name": "waiting_for_video_link", "state_data": data}
        ):
            result = await state.get_data(789)
            assert result == data

    @pytest.mark.asyncio
    async def test_no_state_returns_empty_dict(self):
        """Should return empty dict when user has no state."""
        import state

        with patch("state.db.get_user_state", return_value=None):
            result = await state.get_data(789)
            assert result == {}

    @pytest.mark.asyncio
    async def test_missing_data_key_returns_empty_dict(self):
        """Should return empty dict when state_data key is missing."""
        import state

        with patch("state.db.get_user_state", return_value={"state_name": "ai_chat_active"}):
            result = await state.get_data(789)
            assert result == {}


class TestUpdateData:
    """Test state.update_data async function."""

    @pytest.mark.asyncio
    async def test_merges_partial_state_data(self):
        """Should merge partial state data into the active state."""
        import state

        existing_state = {"state_name": "waiting_for_new_note_input", "state_data": {"message_id": 10, "page": 1}}

        with patch("state.db.get_user_state", return_value=existing_state), patch("state.db.set_user_state") as mock_db:
            await state.update_data(123, {"message_id": None, "extra": True})

            mock_db.assert_called_once_with(
                123,
                "waiting_for_new_note_input",
                {"message_id": None, "page": 1, "extra": True},
            )

    @pytest.mark.asyncio
    async def test_update_data_without_active_state_noops(self):
        """Should do nothing when there is no active state."""
        import state

        with patch("state.db.get_user_state", return_value=None), patch("state.db.set_user_state") as mock_db:
            await state.update_data(123, {"message_id": None})
            mock_db.assert_not_called()


class TestClearUserStates:
    """Test state.clear_user_states async function."""

    @pytest.mark.asyncio
    async def test_calls_db_clear(self):
        """Should call db.clear_user_state."""
        import state

        with patch("state.db.clear_user_state") as mock_db:
            await state.clear_user_states(321)
            mock_db.assert_called_once_with(321)
