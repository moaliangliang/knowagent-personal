"""Harness 层集成测试"""

import sys
import os

# Ensure package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from knowagent_personal.harness.registry import (
    TOOL_REGISTRY, ToolDef, ToolCategory, PermissionLevel,
    register_tool, list_tools, import_from_legacy,
)
from knowagent_personal.harness.permissions import (
    PermissionManager, PermissionMode, PermissionVerdict, PermissionRule,
)
from knowagent_personal.harness.executor import (
    Executor, ExecutionResult,
)
from knowagent_personal.harness.events import (
    EventBus, on_event, emit, EVENT_CATEGORIES, Hook,
)
from knowagent_personal.harness.context import (
    TieredMemory, ContextManager, MemoryTier,
)


def test_register_tool():
    """测试装饰器注册"""
    TOOL_REGISTRY._tools.clear()

    @register_tool("hello", category=ToolCategory.GENERAL, permission=PermissionLevel.BASIC)
    def cmd_hello(params: dict) -> str:
        """问候函数"""
        name = params.get("name", "World")
        return f"Hello, {name}!"

    tool = TOOL_REGISTRY.get("hello")
    assert tool is not None, "工具应已注册"
    assert tool.name == "hello"
    assert tool.category == ToolCategory.GENERAL
    assert tool.permission == PermissionLevel.BASIC
    assert not tool.is_destructive
    assert "问候" in tool.description

    result = tool.handler({"name": "测试"})
    assert result == "Hello, 测试!"

    print("✅ test_register_tool PASS")


def test_legacy_import():
    """测试旧版命令迁移"""
    TOOL_REGISTRY._tools.clear()

    legacy_commands = {
        "system_status": lambda p: f"CPU: OK",
        "lock_screen": lambda p: f"屏幕已锁定",
    }
    import_from_legacy(legacy_commands)

    assert TOOL_REGISTRY.get("system_status") is not None
    assert TOOL_REGISTRY.get("lock_screen") is not None

    # lock_screen 应有更高权限
    lock = TOOL_REGISTRY.get("lock_screen")
    assert lock.permission == PermissionLevel.SYSTEM_CTRL, "锁屏应为高风险"
    assert lock.is_destructive, "锁屏应为破坏性操作"

    # system_status 应为低权限只读
    status = TOOL_REGISTRY.get("system_status")
    assert status.permission == PermissionLevel.BASIC, "系统状态应为低权限"
    assert status.is_readonly, "系统状态应只读"

    print("✅ test_legacy_import PASS")


def test_deny_first_permissions():
    """测试拒绝优先权限"""
    TOOL_REGISTRY._tools.clear()

    @register_tool("read_only", permission=PermissionLevel.BASIC)
    def cmd_read(params): return "data"

    @register_tool("dangerous_op", permission=PermissionLevel.DESTRUCTIVE)
    def cmd_dangerous(params): return "done"

    pm = PermissionManager()
    pm.set_mode(PermissionMode.NORMAL)

    # 只读工具应允许
    verdict = pm.check("read_only")
    assert verdict.allowed, "BASIC 权限在 NORMAL 模式下应允许"

    # 破坏性工具应拒绝（需要确认）
    verdict = pm.check("dangerous_op")
    assert not verdict.allowed, "破坏性操作应需要确认"
    assert verdict.require_confirmation, "应标记为需确认"

    # 未注册的工具
    verdict = pm.check("not_exist")
    assert not verdict.allowed, "未注册工具应拒绝"

    print("✅ test_deny_first_permissions PASS")


def test_permission_modes():
    """测试不同权限模式"""
    TOOL_REGISTRY._tools.clear()

    @register_tool("basic_tool", permission=PermissionLevel.BASIC)
    def cmd1(p): return "ok"

    @register_tool("file_tool", permission=PermissionLevel.FILE_WRITE)
    def cmd2(p): return "ok"

    @register_tool("ctrl_tool", permission=PermissionLevel.SYSTEM_CTRL)
    def cmd3(p): return "ok"

    pm = PermissionManager()

    # PLAN 模式：全部拒绝
    pm.set_mode(PermissionMode.PLAN)
    assert not pm.check("basic_tool").allowed, "PLAN 模式应拒绝所有"

    # NORMAL 模式：只 BASIC 允许
    pm.set_mode(PermissionMode.NORMAL)
    assert pm.check("basic_tool").allowed
    assert not pm.check("file_tool").allowed
    assert not pm.check("ctrl_tool").allowed

    # ACCEPT_EDITS 模式：≤ FILE_WRITE 允许
    pm.set_mode(PermissionMode.ACCEPT_EDITS)
    assert pm.check("basic_tool").allowed
    assert pm.check("file_tool").allowed
    assert not pm.check("ctrl_tool").allowed

    # TRUSTED 模式：全部允许
    pm.set_mode(PermissionMode.TRUSTED)
    assert pm.check("basic_tool").allowed
    assert pm.check("file_tool").allowed
    assert pm.check("ctrl_tool").allowed

    print("✅ test_permission_modes PASS")


def test_deny_rules_override():
    """测试 Deny 规则优先于 Allow"""
    TOOL_REGISTRY._tools.clear()

    @register_tool("test_tool", permission=PermissionLevel.BASIC)
    def cmd(p): return "ok"

    pm = PermissionManager()
    pm.set_mode(PermissionMode.TRUSTED)

    # TRUSTED 模式本来全允许
    assert pm.check("test_tool").allowed

    # 添加 deny 规则
    pm.add_deny_rule("test_tool", "策略禁止")
    verdict = pm.check("test_tool")
    assert not verdict.allowed, "Deny 规则应覆盖 Trusted 模式"
    assert "策略禁止" in verdict.reason

    print("✅ test_deny_rules_override PASS")


def test_event_bus():
    """测试事件总线"""
    bus = EventBus()
    received = []

    @bus.on("tool.before")
    def handler(tool_name, **kw):
        received.append(tool_name)

    # 触发事件
    bus.emit("tool.before", tool_name="screenshot")
    assert "screenshot" in received, "事件应被监听"

    # 多次触发
    bus.emit("tool.before", tool_name="music_play")
    assert len(received) == 2

    # 取消注册
    bus.off("tool.before", handler)
    bus.emit("tool.before", tool_name="test")
    assert len(received) == 2, "取消后不应再触发"

    print("✅ test_event_bus PASS")


def test_tiered_memory():
    """测试分级记忆"""
    mem = TieredMemory()

    # T0: 系统定义
    mem.set(MemoryTier.AXIOM, "system_prompt", "你是 Mac Agent")
    assert len(mem.get_tier(MemoryTier.AXIOM)) == 1

    # T1: 会话
    mem.set(MemoryTier.SESSION, "user:hi", "你好")
    mem.set(MemoryTier.SESSION, "assistant:reply", "你好！")
    assert len(mem.get_tier(MemoryTier.SESSION)) == 2

    # T2: 用户偏好
    mem.set(MemoryTier.USER, "pref:music", "周杰伦")
    assert len(mem.get_tier(MemoryTier.USER)) == 1

    # 搜索
    results = mem.search("周杰伦")
    assert len(results) >= 1

    # 压缩
    freed = mem.compact(100)
    assert freed >= 0

    print("✅ test_tiered_memory PASS")


def test_executor_workflow():
    """测试执行引擎工作流"""
    TOOL_REGISTRY._tools.clear()

    @register_tool("step1", permission=PermissionLevel.BASIC)
    def cmd1(p): return "步骤1完成"

    @register_tool("step2", permission=PermissionLevel.READ_ONLY)
    def cmd2(p): return f"步骤2: {p.get('name', '?')}"

    from knowagent_personal.harness.permissions import PermissionManager
    pm = PermissionManager()
    pm.set_mode(PermissionMode.TRUSTED)

    executor = Executor(permissions=pm)

    # 单步执行
    result = executor.run("step1")
    assert result.success
    assert "步骤1" in result.output

    # 带参数
    result = executor.run("step2", {"name": "测试"})
    assert result.success
    assert "测试" in result.output

    # 未知工具
    result = executor.run("not_exist")
    assert not result.success

    # 工作流
    steps = [
        {"cmd": "step1", "desc": "第一步"},
        {"cmd": "step2", "params": {"name": "工作流"}, "desc": "第二步"},
    ]
    result = executor.run_workflow(steps)
    assert result.success
    assert "2/2" in result.output

    print("✅ test_executor_workflow PASS")


def test_run_isolated():
    """测试隔离执行（mock）"""
    TOOL_REGISTRY._tools.clear()

    call_count = 0

    @register_tool("safe_tool", permission=PermissionLevel.BASIC)
    def cmd_safe(p):
        nonlocal call_count
        call_count += 1
        return "安全执行"

    @register_tool("high_risk_tool", permission=PermissionLevel.UI_CTRL)
    def cmd_risk(p):
        nonlocal call_count
        call_count += 1
        return "高风险执行"

    from knowagent_personal.harness.sandbox import run_isolated

    # 安全工具直接执行
    result = run_isolated("safe_tool")
    # Note: safe tools are executed directly
    assert "安全执行" in result

    print("✅ test_run_isolated PASS")


def test_harness_integration():
    """测试 Harness 集成入口"""
    from knowagent_personal.harness.integration import Harness

    # 注册一些测试工具
    TOOL_REGISTRY._tools.clear()

    @register_tool("hello", permission=PermissionLevel.BASIC)
    def cmd_hello(p): return f"你好, {p.get('name', '朋友')}!"

    @register_tool("lock", permission=PermissionLevel.SYSTEM_CTRL)
    def cmd_lock(p): return "已锁定"

    h = Harness()

    # 状态报告
    report = h.status_report()
    assert report["tools"]["total"] >= 2

    # 工具列表
    tools = h.list_tools()
    assert len(tools) >= 2

    # 权限模式设置
    h.set_permission_mode("trusted")

    print("✅ test_harness_integration PASS")


if __name__ == "__main__":
    test_register_tool()
    test_legacy_import()
    test_deny_first_permissions()
    test_permission_modes()
    test_deny_rules_override()
    test_event_bus()
    test_tiered_memory()
    test_executor_workflow()
    test_run_isolated()
    test_harness_integration()
    print(f"\n{'='*40}")
    print("🎉 所有测试通过")
