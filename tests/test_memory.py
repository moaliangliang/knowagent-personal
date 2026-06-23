"""Tests for memory persistence module."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from knowagent_personal.memory.db import (
    init_db,
    save_message,
    get_recent_messages,
    clear_history,
    get_setting,
    set_setting,
)


def setup_module():
    init_db()
    clear_history()


def test_save_and_read_messages():
    clear_history()
    save_message("user", "测试消息")
    save_message("assistant", "测试回复")
    msgs = get_recent_messages(limit=10)
    assert len(msgs) >= 2

    roles = [m["role"] for m in msgs]
    assert "user" in roles
    assert "assistant" in roles


def test_settings():
    set_setting("test_key", "test_value")
    assert get_setting("test_key") == "test_value"
    assert get_setting("nonexistent") is None
    assert get_setting("nonexistent", "default") == "default"


def test_clear_history():
    save_message("user", "to_be_cleared")
    clear_history()
    msgs = get_recent_messages(limit=10)
    assert len(msgs) == 0


def test_document_index_table():
    """Verify the document_index table was created by init_db."""
    from knowagent_personal.memory.db import get_db_path
    import sqlite3
    conn = sqlite3.connect(get_db_path())
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t[0] for t in tables]
    assert "document_index" in table_names
    assert "settings" in table_names
    assert "conversations" in table_names
    conn.close()
