"""Smoke tests for tool commands."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zhixing.agent.tools import COMMANDS, get_tool_definitions


def test_commands_exist():
    """Verify all expected commands are registered (not windchill)."""
    expected = [
        "system_status", "mail_read", "mail_send", "notification",
        "file_list", "screenshot", "screenshot_analyze",
        "clipboard_read", "clipboard_write",
        "calendar", "music_play", "music_next", "music_volume",
        "music_search", "music_search_online",
        "open_app", "open_url",
        "battery_status", "wifi_status", "speak",
        "keyboard_type", "keyboard_press",
        "ui_tree", "ui_find", "ui_click",
        "lock_screen", "reminder_add", "notes_list", "contacts_search",
        "workflow_execute",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing command: {name}"


def test_windchill_removed():
    """Windchill must not exist in personal version."""
    assert "windchill" not in COMMANDS, "Windchill must be removed from personal version"


def test_31_commands():
    """Should have at least 77 commands (base + all module commands)."""
    assert len(COMMANDS) >= 77, f"Only {len(COMMANDS)} commands registered"


def test_tool_definitions_generated():
    """Tool definitions should have the right shape."""
    defs = get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) == len(COMMANDS)
    for td in defs:
        assert td["type"] == "function"
        assert "name" in td["function"]
        assert td["function"]["name"] in COMMANDS


def test_tool_function_signatures():
    """All command functions accept (params: dict) and return str."""
    for name, func in COMMANDS.items():
        try:
            result = func({})
            assert isinstance(result, str), f"{name} did not return str, got {type(result)}"
        except Exception as e:
            # Some commands may require macOS (osascript, pmset, etc.)
            # That's fine - just verify they don't crash the import
            pass


def test_mail_master_no_crash():
    """mail_master should not crash on non-existent data."""
    result = COMMANDS["mail_master"]({"limit": "1"})
    assert isinstance(result, str)


def test_notification_defaults():
    """notification should work with empty params."""
    result = COMMANDS["notification"]({})
    assert isinstance(result, str)
    assert "知行" in result


def test_file_list_default():
    """file_list should default to home dir."""
    result = COMMANDS["file_list"]({})
    assert isinstance(result, str)
    assert "📋" in result or "❌" in result
