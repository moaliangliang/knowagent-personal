# KnowAgent 架构迁移指南

## 将 Claude Code 架构原则应用到 Mac Agent Personal 项目

---

## 当前架构 vs 目标架构

```
当前架构（Command Dispatcher 模式）:
用户 → [REPL / WebSocket / LLM] → COMMANDS 字典 → cmd_* 函数 → 系统调用

目标架构（Harness 模式）:
用户 → [LLM / REPL] → Executor → Permission Check → Tool Registry → cmd_*
                                ├─ Isolated Subprocess → 高风险工具
                                ├─ Event Bus → 生命周期 Hook
                                └─ Context Manager → 分级记忆
```

## 迁移阶段

### Phase 0：基础设施（已完成 ✅）

已在 `knowagent_personal/harness/` 创建 7 个核心模块：

| 模块 | 文件 | 对应 Claude Code 原则 |
|------|------|----------------------|
| Registry | `registry.py` | buildTool() 工厂、统一 Tool 接口 |
| Permissions | `permissions.py` | Deny-First、7 层纵深防御 |
| Executor | `executor.py` | 执行调度、自动重试、并发控制 |
| Events | `events.py` | 27+ 生命周期事件、Hooks 系统 |
| Context | `context.py` | Tiered Memory、Context Compaction |
| Sandbox | `sandbox.py` | 子进程隔离、风险分级 |
| Integration | `integration.py` | 一键注入现有 Agent |

---

### Phase 1：集成注入（10 分钟）

**目标**: 将 Harness 注入现有 Agent，启用权限检查和事件日志

在 `knowagent_personal/agent/core.py` 的 `Agent.__init__()` 加入一行：

```python
# core.py — 改动点
from knowagent_personal.harness.integration import install_harness

class Agent:
    def __init__(self, llm_client, config):
        # ... 现有代码 ...

        # 新增：注入 Harness
        self._harness = install_harness(
            agent_instance=self,
            config=config,
            migrate_legacy=True,   # 自动迁移旧 COMMANDS
        )

        # 原有 execute_tool 已被自动替换为 Harness 版本
```

**效果**:
- ✅ 所有工具执行经过权限检查
- ✅ 高风险工具自动子进程隔离
- ✅ 执行结果记录到历史
- ✅ 事件触发（可在 hooks 中监听）

---

### Phase 2：权限策略配置（30 分钟）

**目标**: 配置 Deny-First 权限规则，决定哪些工具需要审批

创建 `~/.knowagent/permissions.json`：

```json
{
  "mode": "normal",
  "rules": [
    {"effect": "allow", "tool": "system_status", "reason": "基础只读查询"},
    {"effect": "allow", "tool": "battery_*", "reason": "只读系统信息"},
    {"effect": "allow", "tool": "calendar", "reason": "只读日程"},
    {"effect": "allow", "tool": "clipboard_read", "reason": "只读剪贴板"},
    {"effect": "allow", "tool": "music_*", "reason": "音乐控制"},
    {"effect": "allow", "tool": "notification", "reason": "通知"},
    {"effect": "allow", "tool": "file_list", "reason": "文件浏览"},
    {"effect": "allow", "tool": "screenshot*", "reason": "截图"},
    {"effect": "deny", "tool": "lock_screen", "reason": "锁屏需确认"},
    {"effect": "deny", "tool": "keyboard_*", "reason": "键盘模拟需确认"},
    {"effect": "deny", "tool": "workflow_execute", "reason": "工作流需审批"}
  ]
}
```

在 `Agent.__init__()` 加载：

```python
harness = self._harness
harness.permissions.set_mode("normal")  # 从 config 读取
harness.permissions.load_rules("~/.knowagent/permissions.json")
```

**权限模式速查**:

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| `plan` | 所有操作需审批 | 调试/演示 |
| `normal` | 只读自动允许，写操作需确认 | 日常使用 |
| `accept_edits` | 文件编辑自动批准，系统控制需确认 | 开发工作流 |
| `elevated` | 仅破坏性操作需确认 | 信任环境 |
| `trusted` | 几乎不提示（deny 规则仍生效） | 主人模式 |

---

### Phase 3：Hooks 系统（20 分钟）

**目标**: 添加生命周期 Hook，实现审计日志、通知等

```python
# hooks/setup.py — 运行一次即生效
from knowagent_personal.harness.events import Hook, get_bus

bus = get_bus()

# 1. 审计日志 —— 记录每次工具执行
@bus.on("tool.after")
def audit_log(tool_name, result, duration, **kw):
    with open("~/.knowagent/logs/audit.csv", "a") as f:
        f.write(f"{time.time()},{tool_name},{result.success},{duration:.2f}\n")

# 2. 通知 —— 高风险操作发通知
@bus.on("tool.before")
def notify_high_risk(tool_name, **kw):
    from knowagent_personal.agent.tools import cmd_notification
    if tool_name in ("lock_screen", "workflow_execute"):
        cmd_notification({"text": f"即将执行: {tool_name}", "title": "⚠ 安全提醒"})

# 3. 工作流进度 —— 进度条更新
@bus.on("workflow.step")
def workflow_progress(step, total, desc, **kw):
    print(f"📊 工作流进度: [{step}/{total}] {desc}")
```

**事件类型全览**:

| 事件 | 触发时机 | 数据 |
|------|---------|------|
| `session.start` | Agent 启动 | - |
| `session.end` | Agent 关闭 | - |
| `tool.before` | 工具执行前 | tool_name, params |
| `tool.after` | 工具执行后 | tool_name, result, duration |
| `tool.error` | 工具异常 | tool_name, error, duration |
| `tool.denied` | 权限拒绝 | tool_name, reason |
| `permission.grant` | 授权通过 | tool_name, mode |
| `permission.deny` | 授权拒绝 | tool_name, rule |
| `workflow.start` | 工作流开始 | steps |
| `workflow.step` | 工作流每步 | step, total, desc |
| `workflow.end` | 工作流结束 | results |
| `plugin.load` | 插件加载 | name, version |
| `plugin.unload` | 插件卸载 | name |
| `context.compact` | 上下文压缩 | freed_chars |
| `context.reset` | 上下文重置 | - |

---

### Phase 4：逐步迁移工具（可选，推荐但非必须）

**目标**: 将 `cmd_*` 函数逐个改为装饰器注册，获得完整的元数据

**迁移示例**（以 `mail_send` 为例）：

```python
# 旧写法（现在仍能工作）
def cmd_mail_send(params: dict) -> str:
    """通过 Mac Mail.app 发送邮件"""
    ...

COMMANDS["mail_send"] = cmd_mail_send  # 手动注册

# 新写法 — 装饰器注册
from knowagent_personal.harness.registry import register_tool, ToolCategory, PermissionLevel

@register_tool(
    "mail_send",
    category=ToolCategory.MAIL,
    permission=PermissionLevel.FILE_WRITE,
    timeout=30,
)
def cmd_mail_send(params: dict) -> str:
    """通过 Mac Mail.app 发送邮件"""
    ...
```

**可同时存在的两种注册方式**（渐进迁移）:

```
旧: COMMANDS["name"] = handler  →  自动迁移到 TOOL_REGISTRY
新: @register_tool("name")       →  直接注册到 TOOL_REGISTRY
```

建议按**风险等级**逐步迁移:
1. 第一波：高风险工具（`keyboard_*`, `ui_click`, `lock_screen`）→ 获得隔离执行
2. 第二波：系统控制工具（`vpn_status`, `workflow_execute`）→ 获得权限检查
3. 第三波：全部工具 → 统一的 ToolDef 元数据

---

### Phase 5：使用 Tiered Memory（30 分钟）

**目标**: 让 Agent 记住用户偏好和习惯

```python
# 在 Agent 中集成记忆
harness = self._harness

# 用户偏好（T2 — 跨会话持久）
harness.context.add_fact(
    "user.preferred_music", "周杰伦",
    tier=MemoryTier.USER,
)

# 会话事实（T1 — 仅当前会话）
harness.context.add_fact(
    "current_project", "KnowAgent",
)

# 搜索记忆
results = harness.context.remember("周杰伦")
```

持久化记忆到 `~/.knowagent/personal.db`：

```python
# 使用已有 RAG（knowagent_personal/memory/rag.py）
from knowagent_personal.memory.rag import PersonalRAG

rag = PersonalRAG(self.config)
if rag.init():
    # 将 TieredMemory 的内容持久化
    for item in harness.context.memory.get_tier(MemoryTier.USER):
        rag.index_text(
            text=item.content,
            source=f"memory:{item.key}",
        )
```

---

### Phase 6：完整架构展示

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent (LLM Loop)                          │
│  core.py                                                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Harness（确定性层）                      │    │
│  │                                                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │ Registry  │  │Executor  │  │ ContextManager   │   │    │
│  │  │ ToolDef[] │→ │调度/重试  │  │ T0 AXIOM         │   │    │
│  │  │ 元数据    │  │并行/隔离  │  │ T1 SESSION       │   │    │
│  │  └──────────┘  └────┬─────┘  │ T2 USER           │   │    │
│  │                      │        │ T3 ARCHIVE        │   │    │
│  │  ┌──────────┐  ┌────▼─────┐  └──────────────────┘   │    │
│  │  │Permissions│  │ Sandbox   │                          │    │
│  │  │Deny-First │  │子进程隔离  │  ┌──────────┐           │    │
│  │  │ 7层防御   │  │超时终止   │  │ Events   │           │    │
│  │  └──────────┘  └──────────┘  │ Hooks    │           │    │
│  │                              │ 27+事件   │           │    │
│  │                              └──────────┘           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              工具层（概率性层）                        │    │
│  │  tools.py / *_tools.py / plugins/ / skills/           │    │
│  │  50+ cmd_* 函数 → 系统调用/Swift/AppleScript          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 验证清单

完成每个阶段后，运行验证：

```python
# Phase 1 验证
python3 -c "
from knowagent_personal.harness.integration import install_harness
h = install_harness()
print(f'✅ 工具: {h.status_report()[\"tools\"][\"total\"]} 个已注册')
print(f'✅ 权限模式: {h.status_report()[\"permissions\"][\"mode\"]}')
print(f'✅ 工具列表:')
for t in h.list_tools()[:5]:
    print(f'  - {t[\"name\"]} ({t[\"category\"]}) read_only={t[\"readonly\"]}')
"

# Phase 2 验证
python3 -c "
from knowagent_personal.harness.integration import install_harness
h = install_harness()

# 只读工具应通过
result = h.execute('system_status')
print(f'system_status: {\"✅\" if result.success else \"❌\"} {result.output[:80]}')

# 检查所有工具可访问
forbidden = h.execute('lock_screen')
print(f'lock_screen: {\"🔒\" if not forbidden.success else \"⚠️未受限\"} (需要确认)')
"
```

---

## 快速启动

```bash
# 1. 安装 harness 模块
cd knowagent-personal
pip install -e .

# 2. 一键注入 Agent
python3 -c "
from knowagent_personal.harness.integration import install_harness
h = install_harness(migrate_legacy=True)
print('🚀 Harness 就绪!')
print(f'   已注册 {h.status_report()[\"tools\"][\"total\"]} 个工具')
"

# 3. 试运行
python3 -c "
h = install_harness()
result = h.execute('system_status')
if result.success:
    print(result.output)
else:
    print('需要先安装 psutil: pip install psutil')
"
```

---

## 原则映射

| # | Claude Code 原则 | KnowAgent 实现 | 迁移阶段 |
|---|-----------------|----------------|---------|
| 1 | 框架/模型分离 | `Harness` 类 vs `Agent` 类 | Phase 1 |
| 2 | 拒绝优先安全 | `DenyFirstPolicy` + 7 层检查 | Phase 2 |
| 3 | 上下文即资源 | `TieredMemory` + `ContextManager` | Phase 5 |
| 4 | 渐进度任 | `PermissionMode` (plan→trusted) | Phase 2 |
| 5 | 隔离即原语 | `SandboxExecutor` 子进程隔离 | Phase 1 |
| 6 | 确定性>概率性 | `PermissionRule` 确定规则 vs LLM 概率 | Phase 2 |
| 7 | 渐进扩展 | `EventBus.on()` 注册 Hook | Phase 3 |
| 8 | 统一工具接口 | `ToolDef` 数据类 + `TOOL_REGISTRY` | Phase 4 |
| 9 | 恢复为设计目标 | `Executor` 重试 + 执行记录 | Phase 1 |
| 10 | 模型不变，框架变精 | 工具迁移 + Hooks 扩展 | Phase 3-4 |
