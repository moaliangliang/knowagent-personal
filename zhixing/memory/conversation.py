"""对话历史存储 — SQLite 持久化，支持 session 管理。

存储结构：
  - 每个 session 有自己的消息列表
  - 自动截断到最近 N 轮（默认 20 轮）
  - 按日期自动归档
"""

import json
import os
import sqlite3
import time
from datetime import datetime

CONV_DB = os.path.expanduser("~/.zhixing/conversations.db")
MAX_TURNS = 20  # 保留最近 20 轮


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(CONV_DB), exist_ok=True)
    conn = sqlite3.connect(CONV_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            title TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_calls TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    """)
    conn.commit()
    return conn


def create_session(session_id: str | None = None) -> str:
    """创建一个新会话，返回 session_id。"""
    if session_id is None:
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
    conn = _get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
        (session_id,),
    )
    conn.commit()
    conn.close()
    return session_id


def list_sessions(limit: int = 20) -> list[dict]:
    """列出最近的会话列表。"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT session_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "session_id": r[0],
            "title": r[1] or r[0],
            "created_at": r[2],
            "updated_at": r[3],
        }
        for r in rows
    ]


def add_message(
    session_id: str,
    role: str,
    content: str,
    tool_calls: list | None = None,
) -> int:
    """添加一条消息，返回消息 ID。"""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        (session_id, role, content, json.dumps(tool_calls or [], ensure_ascii=False)),
    )
    conn.execute(
        "UPDATE sessions SET updated_at = datetime('now') WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()

    # 截断超出轮数的旧消息
    _trim_history(conn, session_id)

    row = conn.execute("SELECT last_insert_rowid()").fetchone()
    conn.close()
    return row[0] if row else 0


def get_history(
    session_id: str,
    max_turns: int | None = None,
    include_tool_calls: bool = False,
) -> list[dict]:
    """获取会话历史。"""
    max_turns = max_turns or MAX_TURNS
    conn = _get_conn()
    rows = conn.execute(
        "SELECT role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, max_turns * 2),  # user + assistant = 1 turn
    ).fetchall()
    conn.close()

    msgs = []
    for r in reversed(rows):
        msg = {"role": r[0], "content": r[1]}
        if include_tool_calls and r[2] and r[2] != "[]":
            msg["tool_calls_data"] = json.loads(r[2])
        msgs.append(msg)
    return msgs


def get_openai_history(session_id: str, max_turns: int | None = None) -> list[dict]:
    """获取 OpenAI 格式的对话历史（用于 API 调用上下文）。"""
    max_turns = max_turns or MAX_TURNS
    history = get_history(session_id, max_turns)
    # 只保留 role 和 content（去掉工具数据，避免上下文过大）
    return [{"role": m["role"], "content": m["content"]} for m in history]


def delete_session(session_id: str):
    """删除会话及其所有消息。"""
    conn = _get_conn()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def _trim_history(conn: sqlite3.Connection, session_id: str):
    """保留最近 N 条消息，删除更早的。"""
    total = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()[0]

    if total > MAX_TURNS * 2:
        conn.execute("""
            DELETE FROM messages WHERE session_id = ? AND id NOT IN (
                SELECT id FROM messages WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
            )
        """, (session_id, session_id, MAX_TURNS * 2))
        conn.commit()
