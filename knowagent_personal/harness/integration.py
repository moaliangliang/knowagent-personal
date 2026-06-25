"""Harness Integration — 将 Harness 层注入现有 Agent。

这是 KnowAgent 的 "Architecture Injection" 入口 ——
把新架构组件注入 Agent，无需修改现有工具代码。

用法:
    from knowagent_personal.harness.integration import install_harness

    # 在 Agent 启动时调用一次
    harness = install_harness(agent_instance)
    # 现在所有工具执行都经过权限检查、隔离、事件通知
    result = harness.execute("screenshot_analyze", {"region": "0,0,800,600"})
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .registry import (
    TOOL_REGISTRY, ToolDef, import_from_legacy,
    get_tool_definitions, list_tools,
)
from .permissions import (
    PermissionManager, PermissionMode, check_permission,
)
from .executor import (
    Executor, ExecutionResult, ExecutionStrategy,
)
from .events import (
    EventBus, get_bus, on_event, emit, EVENT_CATEGORIES,
    Hook,
)
from .context import (
    ContextManager, TieredMemory, MemoryTier,
)
from .sandbox import (
    SandboxExecutor, run_isolated,
)


class Harness:
    """Agent Harness — 为 Agent 提供确定性基础设施层。

    组合所有子组件为统一接口：
    - registry: 工具注册和元数据
    - permissions: 权限策略评估
    - executor: 智能执行（含隔离、重试）
    - events: 生命周期事件
    - context: 分级上下文管理
    - sandbox: 子进程隔离
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.events = get_bus()
        self.permissions = PermissionManager()
        self.executor = Executor(permissions=self.permissions, events=self.events)
        self.context = ContextManager(events=self.events)
        self.sandbox = SandboxExecutor(events=self.events)

        # 注册默认事件
        self._register_default_events()

    def _register_default_events(self) -> None:
        """注册默认生命周期事件。"""

        @self.events.on("tool.before", priority=100)
        def log_tool_call(tool_name: str, params: dict, **kw):
            print(f"🔧 [{tool_name}] 开始执行...")

        @self.events.on("tool.after", priority=100)
        def log_tool_result(tool_name: str, result: ExecutionResult, **kw):
            status = "✅" if result.success else "❌"
            duration = f" ({result.duration:.1f}s)" if result.duration > 0.1 else ""
            print(f"   {status} {tool_name}{duration}")

        @self.events.on("tool.error", priority=100)
        def log_tool_error(tool_name: str, error: str, **kw):
            print(f"   ❌ {tool_name}: {error}")

        @self.events.on("tool.denied", priority=100)
        def log_tool_denied(tool_name: str, reason: str, **kw):
            print(f"   🔒 {tool_name} 被拒绝: {reason}")

        @self.events.on("session.start")
        def on_session_start(**kw):
            print("🚀 Agent 会话已启动")

        @self.events.on("session.end")
        def on_session_end(**kw):
            print("👋 Agent 会话已结束")

    def execute(self, tool_name: str, params: dict | None = None,
                confirm: bool = False) -> ExecutionResult:
        """执行一个工具（首选入口）。"""
        return self.executor.run(tool_name, params, confirm=confirm)

    def check(self, tool_name: str) -> bool:
        """检查工具是否有权限执行。"""
        verdict = self.permissions.check(tool_name)
        return verdict.allowed

    def execute_safe(self, tool_name: str, params: dict | None = None) -> str:
        """安全执行 —— 有权限检查，无确认提示。"""
        result = self.executor.run(tool_name, params)
        return result.output if result.success else result.error

    def set_permission_mode(self, mode: str) -> None:
        """设置权限模式。"""
        self.permissions.set_mode(PermissionMode(mode))

    def tool_definitions(self) -> list[dict]:
        """获取 OpenAI 兼容的 tool definitions。"""
        return get_tool_definitions()

    def list_tools(self, **kwargs) -> list[dict]:
        """列出可用工具及其元数据。"""
        return [
            {
                "name": t.name,
                "category": t.category.value,
                "permission": t.permission.name,
                "readonly": t.is_readonly,
                "destructive": t.is_destructive,
                "description": t.description,
            }
            for t in list_tools(**kwargs)
        ]

    def status_report(self) -> dict:
        """生成系统状态报告。"""
        return {
            "tools": {
                "total": len(TOOL_REGISTRY._tools),
                "by_category": self._count_by_category(),
            },
            "permissions": {
                "mode": self.permissions.mode.value,
                "rules": self.permissions.export_rules(),
            },
            "executor": {
                "history": len(self.executor.recorder._history),
                "success": self.executor.recorder.success_count,
                "failures": self.executor.recorder.failure_count,
            },
            "events": {
                "history": len(self.events.history),
                "hooks": len(self.events.get_hooks()),
            },
            "context": self.context.memory.stats,
        }

    def _count_by_category(self) -> dict[str, int]:
        """按分类统计工具数量。"""
        from collections import Counter
        return dict(Counter(
            t.category.value for t in TOOL_REGISTRY._tools.values()
        ))


def install_harness(agent_instance: Any = None,
                    config: dict | None = None,
                    migrate_legacy: bool = True) -> Harness:
    """将 Harness 注入 Agent。

    这是主要的集成入口。提供两种模式：
    1. attach 到现有 Agent：注入 executor 和 events
    2. 独立运行：完全替代旧的 COMMANDS 调用方式

    参数:
        agent_instance: 现有的 Agent 实例（可选）
        config: 配置字典
        migrate_legacy: 是否将旧版 COMMANDS 迁移到 ToolDef 注册表

    返回:
        Harness 实例
    """
    harness = Harness(config)

    # 迁移旧版命令到 ToolDef 注册表
    if migrate_legacy:
        try:
            from knowagent_personal.agent.tools import COMMANDS, TOOL_SCHEMAS
            import_from_legacy(COMMANDS, TOOL_SCHEMAS)
        except ImportError:
            try:
                from agent_core import COMMANDS
                import_from_legacy(COMMANDS)
            except ImportError:
                pass

    # 如果有关联的 Agent 实例，注入执行器
    if agent_instance is not None:
        agent_instance._harness = harness
        agent_instance._executor = harness.executor
        agent_instance._events = harness.events

        # 替换原 execute_tool 方法
        if hasattr(agent_instance, '_execute_tool'):
            original = agent_instance._execute_tool

            def harnessed_execute(name: str, params: dict) -> str:
                result = harness.executor.run(name, params)
                return result.output if result.success else result.error

            agent_instance._execute_tool = harnessed_execute

    return harness
