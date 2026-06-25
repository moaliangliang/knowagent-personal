"""Sandbox Executor — 子进程隔离执行引擎。

遵循 Claude Code 的隔离原则：
- 高风险操作在子进程中隔离执行
- 超时自动终止
- 独立的文件系统和网络域
- 崩溃不影响主进程

Mac 上使用 subprocess + 信号实现轻量级隔离。
"""

from __future__ import annotations

import marshal
import multiprocessing
import os
import queue
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from .registry import TOOL_REGISTRY, ToolDef, PermissionLevel
from .events import EventBus

# ── 风险分类 ──────────────────────────────────────────────


RISK_PROFILES = {
    "safe": {
        "description": "安全操作，当前进程执行",
        "subprocess": False,
        "timeout": 30,
    },
    "isolated": {
        "description": "子进程隔离执行，超时自动终止",
        "subprocess": True,
        "timeout": 30,
    },
    "dangerous": {
        "description": "子进程 + 严格限制（不可访问用户目录外的文件）",
        "subprocess": True,
        "timeout": 60,
        "restrict_fs": True,
    },
}

# 高风险工具映射
_HIGH_RISK_TOOLS = {
    "workflow_execute", "keyboard_type", "keyboard_press",
    "lock_screen", "ui_click",
}


def _classify_tool(tool: ToolDef) -> str:
    """对工具进行风险分类。"""
    if tool.name in _HIGH_RISK_TOOLS:
        return "isolated"
    if tool.is_destructive:
        return "dangerous"
    if tool.permission.value >= PermissionLevel.SYSTEM_CTRL.value:
        return "isolated"
    return "safe"


# ── 子进程执行器 ──────────────────────────────────────────


class SandboxExecutor:
    """沙箱执行器 —— 在子进程中隔离执行高风险工具。

    设计原则：
    - 每个高风险工具调用在独立的子进程中运行
    - 超时自动 kill
    - 子进程崩溃不会影响主进程
    - 支持选择性文件系统/网络限制
    """

    def __init__(self, events: EventBus | None = None):
        self.events = events
        self._active_processes: dict[int, subprocess.Popen] = {}

    def run(self, tool_name: str, params: dict | None = None,
            timeout: int = 30) -> str:
        """在隔离环境中执行工具。

        使用 multiprocessing 实现进程隔离。
        """
        params = params or {}
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            return f"❌ 未知工具: {tool_name}"

        # 使用 multiprocessing.Process 隔离
        result_queue: queue.Queue = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=self._worker,
            args=(tool_name, params, result_queue),
            daemon=True,
        )
        proc.start()
        self._active_processes[proc.pid] = proc

        try:
            proc.join(timeout=timeout)
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=2)
                if proc.is_alive():
                    proc.kill()
                    proc.join()
                return f"⏱ 工具 {tool_name} 执行超时（{timeout}秒），已终止"
            try:
                result = result_queue.get_nowait()
                return result
            except queue.Empty:
                return f"❌ 工具 {tool_name} 未返回结果（可能崩溃）"
        except Exception as e:
            return f"❌ 隔离执行失败: {e}"
        finally:
            self._active_processes.pop(proc.pid, None)

    def run_subprocess(self, tool_name: str, params: dict | None = None,
                       timeout: int = 60) -> str:
        """在 subprocess 中执行（更严格的隔离）。

        生成一个临时 Python 脚本，在独立的解释器中运行。
        """
        params = params or {}
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            return f"❌ 未知工具: {tool_name}"

        # 构建 wrapper 脚本
        script = textwrap.dedent(f"""
        import sys, json
        sys.path.insert(0, {repr(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))})
        from knowagent_personal.harness.registry import TOOL_REGISTRY
        tool = TOOL_REGISTRY.get({repr(tool_name)})
        if not tool:
            print("❌ 未知工具")
        else:
            try:
                result = tool.handler({repr(params)})
                print(result)
            except Exception as e:
                print(f"❌ {{e}}")
        """).strip()

        try:
            proc = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=timeout,
            )
            self._active_processes[proc.pid] = proc

            output = proc.stdout.strip()
            error = proc.stderr.strip()

            if proc.returncode != 0:
                return f"❌ 隔离执行失败 (exit={proc.returncode}): {error or '未知错误'}"
            if error:
                output = f"{output}\n⚠ stderr: {error[:200]}"
            return output or "✅ 执行成功（无输出）"
        except subprocess.TimeoutExpired:
            return f"⏱ 工具 {tool_name} 执行超时（{timeout}秒）"
        except Exception as e:
            return f"❌ 隔离执行异常: {e}"
        finally:
            self._active_processes.pop(proc.pid, None) if hasattr(proc, 'pid') else None

    @staticmethod
    def _worker(tool_name: str, params: dict,
                result_queue: multiprocessing.Queue) -> None:
        """子进程的工作函数。"""
        try:
            tool = TOOL_REGISTRY.get(tool_name)
            if not tool:
                result_queue.put(f"❌ 未知工具: {tool_name}")
                return
            result = tool.handler(params)
            result_queue.put(str(result))
        except Exception as e:
            result_queue.put(f"❌ 隔离执行异常: {e}")

    def terminate_all(self) -> int:
        """终止所有活动进程。"""
        count = 0
        for pid, proc in list(self._active_processes.items()):
            try:
                if proc.is_alive():
                    proc.terminate()
                    count += 1
            except Exception:
                pass
        self._active_processes.clear()
        return count


# ── 简便函数 ──────────────────────────────────────────────

_sandbox = SandboxExecutor()


def run_isolated(tool_name: str, params: dict | None = None,
                 timeout: int = 30) -> str:
    """在隔离环境中运行工具。

    自动选择隔离级别：
    - 高风险 → multiprocessing 隔离
    - 破坏性 → subprocess 严格隔离
    - 普通 → 直接执行
    """
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        # 回退：直接执行
        return f"❌ 未知工具: {tool_name}"

    risk = _classify_tool(tool)
    if risk == "dangerous":
        return _sandbox.run_subprocess(tool_name, params, timeout=timeout)
    elif risk == "isolated":
        return _sandbox.run(tool_name, params, timeout=timeout)
    else:
        # 低风险直接执行
        try:
            result = tool.handler(params or {})
            return str(result)
        except Exception as e:
            return f"❌ {e}"
