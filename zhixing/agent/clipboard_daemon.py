"""Clipboard history background monitor daemon.

Polls ``pbpaste`` every 1 second and appends changes to
``~/.zhixing/clipboard_history.json`` (max 200 entries).

All cmd_* functions accept params: dict and return str.
"""

import json
import os
import subprocess
import threading
import time

# ── Constants ──────────────────────────────────────────

_DATA_DIR = os.path.expanduser("~/.zhixing")
_HISTORY_FILE = os.path.join(_DATA_DIR, "clipboard_history.json")
_PID_FILE = os.path.join(_DATA_DIR, "clipboard_monitor.pid")
_MAX_ENTRIES = 200
_POLL_INTERVAL = 1.0  # seconds

# ── Module-level state ─────────────────────────────────

_monitor_thread: threading.Thread | None = None
_stop_event: threading.Event | None = None


# ── Internal helpers ───────────────────────────────────

def _ensure_data_dir() -> None:
    """Create ~/.zhixing/ if it does not exist."""
    os.makedirs(_DATA_DIR, exist_ok=True)


def _load_history() -> list[dict]:
    """Load clipboard history from JSON file. Returns empty list on error/missing."""
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_history(entries: list[dict]) -> None:
    """Save clipboard history to JSON file (atomic write)."""
    _ensure_data_dir()
    tmp = _HISTORY_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _HISTORY_FILE)


def _read_pbpaste() -> str:
    """Run pbpaste and return the content string. Returns empty on error."""
    try:
        r = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return r.stdout
    except Exception:
        return ""


def _clipboard_poll_loop(stop: threading.Event) -> None:
    """Main polling loop: runs in the daemon thread."""
    last_content = ""
    while not stop.is_set():
        try:
            content = _read_pbpaste()
            if content and content != last_content:
                entries = _load_history()
                now = time.time()
                entries.append({
                    "content": content,
                    "timestamp": now,
                    "timestamp_str": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(now)
                    ),
                })
                # Keep only the last N entries
                if len(entries) > _MAX_ENTRIES:
                    entries = entries[-_MAX_ENTRIES:]
                _save_history(entries)
                last_content = content
        except Exception:
            pass
        stop.wait(_POLL_INTERVAL)


# ── Command handlers ───────────────────────────────────

def cmd_clipboard_monitor_start(params: dict) -> str:
    """Start clipboard monitoring daemon. Polls pbpaste every 1s and
    saves changes to ~/.zhixing/clipboard_history.json (max 200 entries)."""
    global _monitor_thread, _stop_event

    if _monitor_thread is not None and _monitor_thread.is_alive():
        return "⚠️  Clipboard monitor is already running."

    _ensure_data_dir()
    _stop_event = threading.Event()
    _monitor_thread = threading.Thread(
        target=_clipboard_poll_loop,
        args=(_stop_event,),
        daemon=True,
        name="clipboard-monitor",
    )
    _monitor_thread.start()

    # Write PID file
    try:
        with open(_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        return f"❌ Failed to write PID file: {e}"

    return "✅ Clipboard monitor started (polls pbpaste every 1s, max 200 entries)."


def cmd_clipboard_monitor_stop(params: dict) -> str:
    """Stop clipboard monitoring daemon."""
    global _monitor_thread, _stop_event

    if _monitor_thread is None or not _monitor_thread.is_alive():
        # Clean up stale PID file
        if os.path.exists(_PID_FILE):
            try:
                os.remove(_PID_FILE)
            except OSError:
                pass
        return "⚠️  Clipboard monitor is not running."

    if _stop_event is not None:
        _stop_event.set()
    _monitor_thread.join(timeout=3)
    _monitor_thread = None
    _stop_event = None

    # Remove PID file
    try:
        if os.path.exists(_PID_FILE):
            os.remove(_PID_FILE)
    except OSError:
        pass

    return "✅ Clipboard monitor stopped."


def cmd_clipboard_monitor_status(params: dict) -> str:
    """Show clipboard monitor status: running state, history file size, entry count."""
    running = (
        _monitor_thread is not None and _monitor_thread.is_alive()
    )

    # History stats
    entries = _load_history()
    count = len(entries)
    size_bytes = 0
    if os.path.exists(_HISTORY_FILE):
        try:
            size_bytes = os.path.getsize(_HISTORY_FILE)
        except OSError:
            pass

    size_str = (
        f"{size_bytes / 1024:.1f} KB"
        if size_bytes >= 1024
        else f"{size_bytes} bytes"
    )

    pid_exists = os.path.exists(_PID_FILE)

    return (
        f"📋 Clipboard Monitor Status:\n"
        f"  Running: {'🟢 Yes' if running else '🔴 No'}\n"
        f"  PID file: {'✅ Present' if pid_exists else '❌ Not found'}\n"
        f"  History entries: {count} / {_MAX_ENTRIES}\n"
        f"  History file size: {size_str}\n"
        f"  History file: {_HISTORY_FILE}"
    )


def cmd_clipboard_history(params: dict) -> str:
    """Show last N clipboard history entries with timestamps and content preview."""
    n = min(int(params.get("n", 10)), _MAX_ENTRIES)
    entries = _load_history()

    if not entries:
        return "📋 Clipboard history is empty."

    # Show last N (newest first)
    shown = entries[-n:][::-1]

    lines = [f"📋 Clipboard History (last {len(shown)} of {len(entries)} entries):"]
    for i, entry in enumerate(shown, 1):
        content = entry.get("content", "")
        ts = entry.get("timestamp_str", "?")
        preview = content[:100].replace("\n", " ").replace("\r", " ")
        if len(content) > 100:
            preview += "..."
        lines.append(f"  {i}. [{ts}] {preview}")

    return "\n".join(lines)


# ── Command registration ───────────────────────────────

COMMANDS: dict = {
    "clipboard_monitor_start": cmd_clipboard_monitor_start,
    "clipboard_monitor_stop": cmd_clipboard_monitor_stop,
    "clipboard_monitor_status": cmd_clipboard_monitor_status,
    "clipboard_history": cmd_clipboard_history,
}

TOOL_SCHEMAS: dict = {
    "clipboard_monitor_start": {
        "type": "object",
        "properties": {},
    },
    "clipboard_monitor_stop": {
        "type": "object",
        "properties": {},
    },
    "clipboard_monitor_status": {
        "type": "object",
        "properties": {},
    },
    "clipboard_history": {
        "type": "object",
        "properties": {
            "n": {
                "type": "integer",
                "description": "Number of recent entries to show (default 10, max 200)",
            },
        },
    },
}
