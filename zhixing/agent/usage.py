"""知行用量限制器 — 按月统计对话次数。

逻辑：
  免费用户: 每月 50 次对话上限
  Plus 用户: 不限次（通过 license_key 或本地标记识别）

存储:
  ~/.zhixing/usage.db — SQLite，按月统计
"""

import json
import os
import sqlite3
import time
from datetime import datetime

from zhixing.config import Config

USAGE_DB = os.path.expanduser("~/.zhixing/usage.db")
FREE_MONTHLY_LIMIT = 50


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(USAGE_DB), exist_ok=True)
    conn = sqlite3.connect(USAGE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            user_id TEXT NOT NULL,
            year_month TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, year_month)
        )
    """)
    conn.commit()
    return conn


def _current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def _is_plus() -> bool:
    """检查当前用户是否为 Plus 会员。"""
    env_pro = os.environ.get("ZHIXING_PRO", "")
    if env_pro == "1":
        return True
    try:
        cfg = Config()
        key = cfg.get("pro.license_key", "")
        if key and key.startswith("KA-PRO-"):
            return True
    except Exception:
        pass
    return False


def get_usage(user_id: str = "default") -> int:
    """查询本月已用次数。"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT count FROM usage WHERE user_id = ? AND year_month = ?",
        (user_id, _current_month()),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def add_usage(user_id: str = "default") -> int:
    """增加一次使用计数，返回本月累计次数。"""
    conn = _get_conn()
    month = _current_month()
    conn.execute("""
        INSERT INTO usage (user_id, year_month, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, year_month)
        DO UPDATE SET count = count + 1
    """, (user_id, month))
    conn.commit()
    row = conn.execute(
        "SELECT count FROM usage WHERE user_id = ? AND year_month = ?",
        (user_id, month),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def check_limit(user_id: str = "default") -> dict:
    """检查是否达到用量限制。

    Returns:
        {"ok": True} 或
        {"ok": False, "used": int, "limit": int, "message": str}
    """
    if _is_plus():
        return {"ok": True}

    used = get_usage(user_id)
    if used >= FREE_MONTHLY_LIMIT:
        return {
            "ok": False,
            "used": used,
            "limit": FREE_MONTHLY_LIMIT,
            "message": (
                f"本月 {FREE_MONTHLY_LIMIT} 次对话已用完 🫙\n\n"
                f"升级 Plus 可享不限次对话 + 全部场景\n"
                f"定价: ¥59/年 · ¥149 终身\n"
                f"购买: https://afdian.com/a/moaliangliang\n\n"
                f"输入 activation 您的LicenseKey 激活"
            ),
        }

    remaining = FREE_MONTHLY_LIMIT - used
    if remaining <= 5:
        return {
            "ok": True,
            "used": used,
            "limit": FREE_MONTHLY_LIMIT,
            "remaining": remaining,
            "message": f"💡 本月还剩 {remaining} 次免费对话，用完可升级 Plus 不限次",
        }

    return {"ok": True, "used": used, "limit": FREE_MONTHLY_LIMIT, "remaining": remaining}
