"""Agent 工具函数 — 共享辅助函数。

集中管理跨模块重复代码:
- _run_cmd — 安全执行 shell 命令 (4个模块各有一份副本)
- _osa_escape — AppleScript 转义 (2个模块各有副本)
"""

from __future__ import annotations

import subprocess


def run_cmd(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """安全执行 shell 命令（列表形式，防注入）。"""
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=False,
    )


def osa_escape(s: str) -> str:
    """AppleScript 字符串转义（反斜杠 + 双引号）。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')
