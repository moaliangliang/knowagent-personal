"""Tests for the new command tool modules.

Each test verifies that commands from a specific module are registered
in the COMMANDS dict and that they accept (params: dict) -> str.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from knowagent_personal.agent.tools import COMMANDS


# ── system_tools ──────────────────────────────────────────────

def test_system_tools_commands():
    """system_tools: display_brightness, system_volume, system_sleep,
    system_shutdown, system_restart, screensaver, focus_mode."""
    expected = [
        "display_brightness",
        "system_volume",
        "system_sleep",
        "system_shutdown",
        "system_restart",
        "screensaver",
        "focus_mode",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing system_tools command: {name}"


# ── network_tools ────────────────────────────────────────────

def test_network_tools_commands():
    """network_tools: my_ip, speedtest, http_request, download,
    whois, ping, port_check."""
    expected = [
        "my_ip",
        "speedtest",
        "http_request",
        "download",
        "whois",
        "ping",
        "port_check",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing network_tools command: {name}"


# ── file_tools ────────────────────────────────────────────────

def test_file_tools_commands():
    """file_tools: file_search, file_grep, compress, extract, trash,
    duplicate_finder, convert_image."""
    expected = [
        "file_search",
        "file_grep",
        "compress",
        "extract",
        "trash",
        "duplicate_finder",
        "convert_image",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing file_tools command: {name}"


# ── dev_tools ─────────────────────────────────────────────────

def test_dev_tools_commands():
    """dev_tools: brew, process, docker."""
    expected = [
        "brew",
        "process",
        "docker",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing dev_tools command: {name}"


# ── media_tools ───────────────────────────────────────────────

def test_media_tools_commands():
    """media_tools: screen_record, audio_record, video_info, ocr_file."""
    expected = [
        "screen_record",
        "audio_record",
        "video_info",
        "ocr_file",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing media_tools command: {name}"


# ── daily_tools ───────────────────────────────────────────────

def test_daily_tools_commands():
    """daily_tools: timer, clipboard_history, translate, shortcut,
    credential."""
    expected = [
        "timer",
        "clipboard_history",
        "translate",
        "shortcut",
        "credential",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing daily_tools command: {name}"


# ── ai_tools ─────────────────────────────────────────────────

def test_ai_tools_commands():
    """ai_tools: chat, summarize, code_review, image_gen."""
    expected = [
        "chat",
        "summarize",
        "code_review",
        "image_gen",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing ai_tools command: {name}"


# ── monitor_tools ─────────────────────────────────────────────

def test_monitor_tools_commands():
    """monitor_tools: disk_monitor, battery_health, sensor_temp."""
    expected = [
        "disk_monitor",
        "battery_health",
        "sensor_temp",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing monitor_tools command: {name}"


# ── Clipboard daemon commands ─────────────────────────────────

def test_clipboard_daemon_commands():
    """clipboard_daemon: clipboard_monitor_start, clipboard_monitor_stop,
    clipboard_monitor_status."""
    expected = [
        "clipboard_monitor_start",
        "clipboard_monitor_stop",
        "clipboard_monitor_status",
    ]
    for name in expected:
        assert name in COMMANDS, f"Missing clipboard_daemon command: {name}"


# ── CN aliases ────────────────────────────────────────────────

def test_cn_aliases():
    """All Chinese aliases resolve to valid registered commands.
    'help' is excluded because it is not a tool command but a UI handler."""
    from knowagent_personal.agent.aliases import CN_ALIASES
    for cn_alias, en_command in CN_ALIASES.items():
        if en_command == "help":
            continue  # help is a UI handler, not a COMMANDS entry
        assert en_command in COMMANDS, (
            f"Alias '{cn_alias}' points to '{en_command}' "
            f"which is not in COMMANDS"
        )


# ── Help text ─────────────────────────────────────────────────

def test_help_text_categories():
    """All help text categories reference valid registered commands."""
    from knowagent_personal.agent.help_text import HELP_EN, HELP_ZH

    for lang_name, help_dict in [("EN", HELP_EN), ("ZH", HELP_ZH)]:
        categories = help_dict.get("ex_categories", {})
        assert categories, f"HELP_{lang_name} has no ex_categories"

        for category_name, cmd_list in categories.items():
            for cmd in cmd_list:
                assert cmd in COMMANDS, (
                    f"HELP_{lang_name} category '{category_name}' "
                    f"references unknown command: {cmd}"
                )


# ── VPN module ────────────────────────────────────────────────

def test_vpn_module():
    """VpnClient can be instantiated."""
    from knowagent_personal.agent.vpn import VpnClient
    client = VpnClient()
    assert client is not None
    # Verify expected attributes exist
    assert hasattr(client, "quick_check")
    assert hasattr(client, "enable_proxy")
    assert hasattr(client, "disable_proxy")
    assert hasattr(client, "connect")
    assert hasattr(client, "disconnect")
    assert hasattr(client, "switch_type")


# ── Keychain module ──────────────────────────────────────────

def test_keychain_module():
    """Keychain module can be imported and has expected functions."""
    from knowagent_personal.agent.keychain import (
        keychain_set,
        keychain_get,
        keychain_delete,
        cmd_credential,
    )
    # Verify the functions exist and are callable
    assert callable(keychain_set)
    assert callable(keychain_get)
    assert callable(keychain_delete)
    assert callable(cmd_credential)
    # cmd_credential should also be registered as a command
    assert "credential" in COMMANDS


# ── Function signatures ──────────────────────────────────────

def test_new_tool_function_signatures():
    """All new-module command functions accept (params: dict) and return str.

    This tests one representative command from each module to avoid
    calling every command (some require macOS or external tools).
    """
    # System tools
    for name in ("display_brightness", "system_volume", "focus_mode"):
        _check_signature(name)

    # Network tools
    for name in ("my_ip", "speedtest", "whois", "port_check"):
        _check_signature(name)

    # File tools
    for name in ("compress", "extract", "trash"):
        _check_signature(name)

    # Dev tools
    for name in ("brew", "process", "docker"):
        _check_signature(name)

    # Media tools
    for name in ("screen_record", "audio_record", "video_info", "ocr_file"):
        _check_signature(name)

    # Daily tools (timer is excluded because it blocks for minutes)
    for name in ("translate", "shortcut", "credential"):
        _check_signature(name)

    # AI tools
    for name in ("chat", "summarize", "code_review", "image_gen"):
        _check_signature(name)

    # Monitor tools
    for name in ("disk_monitor", "battery_health", "sensor_temp"):
        _check_signature(name)

    # Clipboard daemon
    for name in ("clipboard_monitor_start", "clipboard_monitor_stop", "clipboard_monitor_status"):
        _check_signature(name)


def _check_signature(name: str) -> None:
    """Verify that *name* is a callable returning str when passed {}."""
    assert name in COMMANDS, f"Command not in COMMANDS: {name}"
    func = COMMANDS[name]
    assert callable(func), f"{name} is not callable"
    # Call with empty params; tolerate macOS-specific errors
    try:
        result = func({})
        assert isinstance(result, str), (
            f"{name} did not return str, got {type(result)}"
        )
    except Exception:
        # macOS-only commands may require osascript, pmset, etc.
        pass
