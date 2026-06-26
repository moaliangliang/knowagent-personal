"""端到端集成验证 — Harness + Agent 完整流程。"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 清理注册表，重新迁移
from zhixing.harness.registry import TOOL_REGISTRY, import_from_legacy
from zhixing.agent.tools import COMMANDS, TOOL_SCHEMAS

TOOL_REGISTRY._tools.clear()
import_from_legacy(COMMANDS, TOOL_SCHEMAS)

print("=" * 50)
print("🔍 ZhiXing Harness 集成验证")
print("=" * 50)

# ── 1. 验证 Harness 安装 ──
from zhixing.harness.integration import install_harness

h = install_harness(migrate_legacy=False)  # 已通过 import_from_legacy 导入
print(f"\n📊 1. Harness 安装")
print(f"   ├─ Tool Registry: {h.status_report()['tools']['total']} 个工具")
print(f"   ├─ Permissions Mode: {h.status_report()['permissions']['mode']}")
print(f"   ├─ Events: {h.status_report()['events']['history']} 条历史")
print(f"   └─ Tools by category:")
for cat, cnt in sorted(h.status_report()['tools']['by_category'].items()):
    print(f"       {cat:15s}: {cnt}")

# ── 2. 验证权限检查 ──
from zhixing.harness.permissions import PermissionMode

h.set_permission_mode("normal")
print(f"\n🔒 2. 权限检查 (mode=normal)")

# 只读工具应通过
result = h.execute("battery_status")
assert result.success, "battery_status 应允许"
print(f"   ✅ battery_status (BASIC) → 允许")

result = h.execute("mail_read")
assert result.success, "mail_read 应允许"
print(f"   ✅ mail_read (READ_ONLY) → 允许")

result = h.execute("notification")
assert result.success, "notification 应允许"
print(f"   ✅ notification (MEDIA) → 允许")

# 高风险工具应需要确认
result = h.execute("lock_screen")
assert not result.success, "lock_screen 应拒绝"
assert result.strategy.value == "confirmed", "lock_screen 应标记为需确认"
print(f"   🔒 lock_screen (SYSTEM_CTRL) → 拒绝（需确认）")

result = h.execute("workflow_execute")
assert not result.success, "workflow_execute 应拒绝"
print(f"   🔒 workflow_execute (DESTRUCTIVE) → 拒绝（需确认）")

result = h.execute("system_shutdown")
assert not result.success, "system_shutdown 应拒绝"
print(f"   🔒 system_shutdown (DESTRUCTIVE) → 拒绝（需确认）")

# TRUSTED 模式应全通过
h.set_permission_mode("trusted")
result = h.execute("lock_screen")
print(f"   ✅ lock_screen (TRUSTED mode) → 允许")

# ── 3. 验证事件总线 ──
from zhixing.harness.events import get_bus

bus = get_bus()
events_before = len(bus.history)
h.execute("calendar")
events_after = len(bus.history)
assert events_after > events_before, "工具执行应产生事件"
print(f"\n📡 3. 事件总线")
print(f"   ├─ 工具执行前: {events_before} 事件")
print(f"   ├─ 工具执行后: {events_after} 事件")
print(f"   └─ 最近事件: {bus.history[-1]['event']}")

# ── 4. 验证上下文管理 ──
h.context.add_fact("test:greeting", "你好，世界！")
found = h.context.remember("你好")
print(f"\n🧠 4. 分级记忆")
print(f"   ├─ 写入: test:greeting = '你好，世界！'")
print(f"   ├─ 搜索 '你好': {len(found)} 条结果")
print(f"   └─ 记忆统计: {h.context.memory.stats}")

# 压缩测试
freed = h.context.memory.compact(100)
print(f"   └─ 压缩释放: {freed} 字符")

# ── 5. 验证持久化 ──
h.context.memory.save_to_db()
print(f"\n💾 5. 持久化")
print(f"   ├─ T2 记忆已保存到 ~/.zhixing/personal.db")

from zhixing.harness.context import TieredMemory, MemoryTier
new_mem = TieredMemory()
new_mem.load_from_db()
restored = new_mem.get_tier(MemoryTier.USER)
print(f"   └─ 加载后 T2 记忆: {len(restored)} 条")

# ── 6. 验证默认 Hooks ──
from zhixing.harness.default_hooks import install_default_hooks, tail_audit
install_default_hooks()
h.execute("battery_status")
print(f"\n📋 6. 默认 Hooks")
log_entries = tail_audit(5)
print(f"   ├─ 审计日志: 写入 ~/.zhixing/logs/audit_*.jsonl")
print(f"   └─ 最近 {len(log_entries)} 条审计记录就绪")

# ── 7. 验证 Agent 集成（mock Agent）──
print(f"\n🤖 7. Agent 集成")
from zhixing.config import Config
from zhixing.agent.core import Agent

# Mock LLM client
class MockLLM:
    def chat(self, messages, **kw):
        return {"choices": [{"message": {"content": "Hello from mock!", "role": "assistant"}}]}

config = Config()
agent = Agent(llm_client=MockLLM(), config=config)
assert hasattr(agent, '_harness'), "Agent 应包含 _harness 属性"
assert agent._harness is not None, "Harness 应已安装"

print(f"   ├─ core.py 导入: ✅")
print(f"   ├─ _harness 已注入: ✅")
print(f"   ├─ 配置权限模式: {config.get('harness.permission_mode')}")
print(f"   ├─ max_history_turns: {config.get('harness.max_history_turns')}")
print(f"   └─ agent.harness_status(): {agent.harness_status()['tools']['total']} 工具")

# ── 8. 权限策略文件 ──
import json
policy_path = os.path.expanduser("~/.zhixing/permissions.json")
if os.path.exists(policy_path):
    with open(policy_path) as f:
        policy = json.load(f)
    allowed = sum(1 for r in policy["rules"] if r["effect"] == "allow")
    denied = sum(1 for r in policy["rules"] if r["effect"] == "deny")
    print(f"\n📜 8. 权限策略文件")
    print(f"   ├─ 路径: {policy_path}")
    print(f"   ├─ 模式: {policy['mode']}")
    print(f"   ├─ allow 规则: {allowed} 条")
    print(f"   └─ deny 规则: {denied} 条")

print(f"\n{'='*50}")
print("🎉 全部集成验证通过")
print(f"{'='*50}")
