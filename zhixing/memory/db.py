"""SQLite persistence for conversation history and settings."""

import json
import os
import sqlite3
from datetime import datetime

DB_DIR = os.path.expanduser("~/.zhixing")


def get_db_path() -> str:
    return os.path.join(DB_DIR, "personal.db")


def init_db():
    """Initialize SQLite database with required tables."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT,
            tool_calls TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            title TEXT,
            indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_message(role: str, content: str | None = None, tool_calls: list | None = None):
    """Save a conversation message to SQLite."""
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT INTO conversations (role, content, tool_calls) VALUES (?, ?, ?)",
        (role, content, json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None),
    )
    conn.commit()
    conn.close()


def get_recent_messages(limit: int = 50) -> list[dict]:
    """Retrieve recent conversation history."""
    conn = sqlite3.connect(get_db_path())
    rows = conn.execute(
        "SELECT role, content, tool_calls FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    messages = []
    for role, content, tool_calls_json in reversed(rows):
        msg = {"role": role}
        if content:
            msg["content"] = content
        if tool_calls_json:
            try:
                msg["tool_calls"] = json.loads(tool_calls_json)
            except json.JSONDecodeError:
                pass
        messages.append(msg)
    return messages


def get_setting(key: str, default: str | None = None) -> str | None:
    conn = sqlite3.connect(get_db_path())
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def clear_history():
    """Clear all conversation history."""
    conn = sqlite3.connect(get_db_path())
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()


def set_setting(key: str, value: str):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()
