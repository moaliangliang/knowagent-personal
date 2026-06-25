"""Default Hooks — KnowAgent 默认生命周期钩子。

在 Agent 启动时加载，提供：
1. 审计日志 — 记录每次工具执行到文件
2. 高风险操作通知 — 锁屏/关机/工作流时发通知
3. 工作流进度 — 控制台进度输出
4. 统计摘要 — 会话结束时输出统计

用法:
    from knowagent_personal.harness.default_hooks import install_default_hooks
    install_default_hooks()
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime

from knowagent_personal.harness.events import get_bus

LOG_DIR = os.path.expanduser("~/.knowagent/logs")


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


# ── Hook 1: 审计日志 ─────────────────────────────────────


def _audit_log(tool_name: str, result=None, duration=0.0, error="", **kw):
    """记录工具执行到审计日志文件。"""
    _ensure_log_dir()
    log_file = os.path.join(LOG_DIR, f"audit_{datetime.now().strftime('%Y%m')}.jsonl")
    entry = {
        "ts": time.time(),
        "time": datetime.now().isoformat(),
        "tool": tool_name,
        "success": result.success if hasattr(result, 'success') else (not error),
        "duration": round(duration, 3),
        "error": error[:200] if error else "",
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Hook 2: 高风险操作通知 ────────────────────────────────


def _notify_high_risk(tool_name: str, **kw):
    """高风险操作时发系统通知。"""
    high_risk = {
        "lock_screen": "🔒 锁屏",
        "system_sleep": "💤 睡眠",
        "system_shutdown": "⏻ 关机",
        "system_restart": "🔄 重启",
        "workflow_execute": "📋 工作流",
    }
    label = high_risk.get(tool_name, tool_name)
    title = f"⚠️ {label} 即将执行"

    import subprocess
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "正在执行: {tool_name}" with title "{title}"',
        ], capture_output=True, timeout=5)
    except Exception:
        pass


# ── Hook 3: 工作流进度控制台输出 ──────────────────────────


def _workflow_step(step: int, total: int, desc: str = "", **kw):
    """工作流每步的进度显示。"""
    bar_len = 20
    filled = int(step / total * bar_len) if total else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  📊 [{bar}] {step}/{total}  {desc}")


# ── Hook 4: 会话统计收集（用于 session.end）───────────────


def _session_collector(**kw):
    """收集会话期间的执行统计（暂存在内存中）。"""
    pass  # 数据由 EventBus history 自动记录


# ── Hook 5: session.end 输出摘要 ──────────────────────────


def _session_summary(**kw):
    """会话结束时输出统计摘要。"""
    bus = get_bus()
    if not bus.history:
        return
    tool_events = [h for h in bus.history if h["event"] in (
        "tool.after", "tool.error", "tool.denied")]
    if not tool_events:
        return
    successes = sum(1 for h in tool_events if h["event"] == "tool.after")
    errors = sum(1 for h in tool_events if h["event"] == "tool.error")
    denied = sum(1 for h in tool_events if h["event"] == "tool.denied")
    total = len(tool_events)
    print(f"\n📊 会话摘要: {total} 次工具调用")
    print(f"   ✅ 成功: {successes}  ❌ 失败: {errors}  🔒 拒绝: {denied}")
    if total > 0:
        print(f"   ✅ 成功率: {successes/total*100:.0f}%")


# ── 安装函数 ─────────────────────────────────────────────


def install_default_hooks():
    """注册所有默认 Hook 到事件总线。

    在 Agent 初始化后调用一次即可。
    """
    bus = get_bus()

    # 审计日志（优先级 50，在中性位置）
    bus.on("tool.after", priority=50)(_audit_log)
    bus.on("tool.error", priority=50)(_audit_log)

    # 高风险通知（优先级 10，尽早触发）
    bus.on("tool.before", priority=10)(_notify_high_risk)

    # 工作流进度（优先级 50）
    bus.on("workflow.step", priority=50)(_workflow_step)

    # 会话摘要（优先级 90，最后执行）
    bus.on("session.end", priority=90)(_session_summary)

    return True


# ── 查看日志 ─────────────────────────────────────────────


def tail_audit(n: int = 20) -> list[dict]:
    """查看最近 N 条审计日志。"""
    _ensure_log_dir()
    log_files = sorted(
        f for f in os.listdir(LOG_DIR)
        if f.startswith("audit_") and f.endswith(".jsonl")
    )
    if not log_files:
        return []
    latest = os.path.join(LOG_DIR, log_files[-1])
    entries = []
    try:
        with open(latest, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    return entries[-n:]
