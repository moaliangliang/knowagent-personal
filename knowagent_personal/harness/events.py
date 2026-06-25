"""Event System — 生命周期事件总线。

遵循 Claude Code 的 Hooks 系统设计：
- 27+ 生命周期事件覆盖执行全过程
- 支持 command/http/mcp_tool/prompt/agent 五种模式
- 零上下文成本 — 事件配置存在于主上下文之外
"""

from __future__ import annotations

import enum
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

# ── 事件分类 ──────────────────────────────────────────────


class EVENT_CATEGORIES:
    """事件分类常量。"""
    # 会话生命周期
    SESSION_START = "session.start"
    SESSION_END = "session.end"

    # 工具执行
    TOOL_BEFORE = "tool.before"
    TOOL_AFTER = "tool.after"
    TOOL_ERROR = "tool.error"
    TOOL_DENIED = "tool.denied"

    # 权限
    PERMISSION_CHECK = "permission.check"
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_DENY = "permission.deny"

    # 上下文
    CONTEXT_COMPACT = "context.compact"
    CONTEXT_RESET = "context.reset"

    # 工作流
    WORKFLOW_START = "workflow.start"
    WORKFLOW_STEP = "workflow.step"
    WORKFLOW_END = "workflow.end"

    # 用户交互
    USER_INPUT = "user.input"
    USER_OUTPUT = "user.output"
    USER_CONFIRM = "user.confirm"

    # 系统
    ERROR = "system.error"
    WARNING = "system.warning"
    STARTUP = "system.startup"
    SHUTDOWN = "system.shutdown"

    # 插件/技能
    PLUGIN_LOAD = "plugin.load"
    PLUGIN_UNLOAD = "plugin.unload"
    SKILL_INSTALL = "skill.install"
    SKILL_REMOVE = "skill.remove"


# ── Hook 定义 ─────────────────────────────────────────────


@dataclass
class Hook:
    """Hook 定义 — 对应 Claude Code 的 5 种执行模式。"""
    event: str
    mode: str                       # command | http | log | callback
    handler: Callable | None = None
    command: str = ""               # mode=command 时使用
    url: str = ""                   # mode=http 时使用
    blocking: bool = False          # 是否阻塞执行
    timeout: int = 10
    description: str = ""

    def __hash__(self):
        return hash((self.event, self.mode, self.command or self.url or id(self.handler)))


# ── 事件总线 ──────────────────────────────────────────────


class EventBus:
    """同步事件总线 — 注册、触发、取消事件。

    用法:
        bus = EventBus()

        # 注册监听器
        @bus.on("tool.before")
        def log_tool_call(tool_name: str, **data):
            logger.info(f"执行工具: {tool_name}")

        # 触发事件
        bus.emit("tool.before", tool_name="screenshot")
    """

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)
        self._hooks: dict[str, list[Hook]] = defaultdict(list)
        self._history: list[dict] = []
        self._max_history = 1000
        self._enabled = True

    def on(self, event: str, priority: int = 0):
        """装饰器：注册事件监听器。

        支持可选优先级（数值小优先执行）。
        """
        def decorator(fn: Callable) -> Callable:
            self._listeners[event].append(fn)
            # 按优先级排序：priority 属性值小的先执行
            fn._event_priority = priority
            self._listeners[event].sort(key=lambda f: getattr(f, "_event_priority", 0))
            return fn
        return decorator

    def off(self, event: str, fn: Callable | None = None) -> None:
        """取消注册。fn=None 则移除该事件所有监听器。"""
        if fn is None:
            self._listeners.pop(event, None)
        else:
            self._listeners[event] = [
                f for f in self._listeners[event] if f is not fn
            ]

    def emit(self, event: str, **data) -> list[Any]:
        """触发事件，通知所有监听器。

        返回所有监听器的返回值列表。
        异常不会中断其他监听器的执行。
        """
        if not self._enabled:
            return []

        results: list[Any] = []
        errors: list[Exception] = []

        # 执行监听器
        for listener in self._listeners.get(event, []):
            try:
                result = listener(**data)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 执行 Hook
        for hook in self._hooks.get(event, []):
            try:
                if hook.mode == "callback" and hook.handler:
                    result = hook.handler(**data)
                    results.append(result)
                elif hook.mode == "log":
                    self._log_hook(hook, event, data)
            except Exception as e:
                errors.append(e)

        # 记录到历史
        self._history.append({
            "event": event,
            "data": _summarize(data),
            "time": time.time(),
            "errors": [str(e) for e in errors],
        })
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return results

    def add_hook(self, hook: Hook) -> None:
        """注册一个 Hook。"""
        self._hooks[hook.event].append(hook)

    def remove_hook(self, hook: Hook) -> None:
        """移除一个 Hook。"""
        hooks = self._hooks.get(hook.event, [])
        if hook in hooks:
            hooks.remove(hook)

    def get_hooks(self, event: str | None = None) -> list[Hook]:
        """获取所有已注册的 Hook。"""
        if event:
            return list(self._hooks.get(event, []))
        return [h for hooks in self._hooks.values() for h in hooks]

    def enable(self) -> None:
        """启用事件总线。"""
        self._enabled = True

    def disable(self) -> None:
        """禁用事件总线（临时关闭，不清除注册）。"""
        self._enabled = False

    @property
    def history(self) -> list[dict]:
        """获取事件历史。"""
        return list(self._history)

    def clear_history(self) -> None:
        """清空事件历史。"""
        self._history.clear()

    def _log_hook(self, hook: Hook, event: str, data: dict) -> None:
        """执行 log 模式的 Hook。"""
        msg = f"[{event}] {hook.description or hook.command}"
        detail = _summarize(data)
        if detail:
            msg += f": {detail}"
        print(msg)


# ── 全局默认事件总线 ──────────────────────────────────────

_default_bus = EventBus()


def on_event(event: str, priority: int = 0):
    """装饰器：在默认总线上注册事件监听器。

    用法:
        @on_event("tool.before")
        def my_hook(tool_name: str, **data):
            print(f"即将执行: {tool_name}")
    """
    return _default_bus.on(event, priority)


def emit(event: str, **data) -> list[Any]:
    """在默认总线上触发事件。"""
    return _default_bus.emit(event, **data)


def get_bus() -> EventBus:
    """获取默认事件总线。"""
    return _default_bus


# ── 辅助 ──────────────────────────────────────────────────


def _summarize(data: dict) -> str:
    """将事件数据转为可读摘要（避免日志过于冗长）。"""
    parts = []
    for k, v in data.items():
        if isinstance(v, str) and len(v) > 80:
            parts.append(f"{k}={v[:80]}...")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)
