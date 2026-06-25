"""Harness — Agent 确定性框架层。

遵循 Claude Code 架构原则：
1. 框架与模型分离 — 98.4% 确定性基础设施
2. 拒绝优先安全 — deny > ask > allow
3. 隔离即原语 — 子进程、权限域
4. 渐进扩展 — Plugins/Skills/Hooks 分级
5. 恢复为设计目标 — 重试、回滚、状态恢复
"""

from .registry import (
    ToolDef,
    ToolCategory,
    PermissionLevel,
    register_tool,
    unregister_tool,
    get_tool,
    list_tools,
    get_tool_definitions,
    TOOL_REGISTRY,
)
from .permissions import (
    PermissionManager,
    DenyFirstPolicy,
    allow_for_user,
    deny_for_user,
)
from .executor import (
    Executor,
    ExecutionResult,
    ExecutionStrategy,
)
from .events import (
    EventBus,
    on_event,
    emit,
    EVENT_CATEGORIES,
)
from .context import (
    TieredMemory,
    ContextManager,
    MemoryTier,
)
from .sandbox import (
    SandboxExecutor,
    run_isolated,
)
from .threat_detection import (
    ThreatScanner,
    ThreatMatch,
    ScanResult,
    ScanScope,
    ScanAction,
    scan_input,
    scan_memory,
    scan_strict,
)
from .gateway import (
    Gateway,
    PlatformAdapter,
    WebSocketAdapter,
    WebSocketClientAdapter,
    CLIAdapter,
    AgentMessage,
    AgentResponse,
)
from .sandbox_whitelist import (
    CodeSandbox,
    SandboxResult,
    SANDBOX_ALLOWED_TOOLS,
)

__all__ = [
    # registry
    "ToolDef", "ToolCategory", "PermissionLevel",
    "register_tool", "unregister_tool", "get_tool", "list_tools",
    "get_tool_definitions", "TOOL_REGISTRY",
    # permissions
    "PermissionManager", "DenyFirstPolicy", "allow_for_user", "deny_for_user",
    # executor
    "Executor", "ExecutionResult", "ExecutionStrategy",
    # events
    "EventBus", "on_event", "emit", "EVENT_CATEGORIES",
    # context
    "TieredMemory", "ContextManager", "MemoryTier",
    # sandbox
    "SandboxExecutor", "run_isolated",
]
