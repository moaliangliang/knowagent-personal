# 🤝 贡献指南

感谢你对 Mac Agent Personal 的兴趣！任何形式的贡献都欢迎。

---

## 📋 目录

- [架构概览](#架构概览)
- [开发环境搭建](#开发环境搭建)
- [代码风格](#代码风格)
- [添加新工具](#添加新工具)
- [开发 Harness 模块](#开发-harness-模块)
- [新增平台适配器](#新增平台适配器)
- [测试](#测试)
- [提交 PR](#提交-pr)
- [报告 Bug](#报告-bug)
- [提交功能请求](#提交功能请求)

---

## 🏗 架构概览

```
Agent (LLM Loop)
  └─ Harness (确定性层)
       ├─ Registry     — 工具注册与元数据
       ├─ Permissions  — Deny-First 权限策略
       ├─ Executor     — 执行调度与重试
       ├─ Events       — 生命周期事件总线
       ├─ Context      — TieredMemory 分级上下文
       ├─ Sandbox      — 子进程隔离执行
       ├─ ThreatDetect — 提示注入扫描
       └─ Gateway      — 平台适配器
  └─ Tools (概率性层)
       └─ *._tools.py — 83 个系统命令
```

**设计原则**:
- 框架与模型分离（~98% 确定性基础设施，~2% AI 决策）
- 拒绝优先安全（Deny > Ask > Allow）
- 隔离即原语（子进程沙箱、权限域）
- 渐进扩展（Plugins/Skills/Hooks 分级）
- 恢复为设计目标（重试、执行记录）

---

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/knowagent/knowagent-personal.git
cd knowagent-personal

# 安装开发依赖
pip install -e ".[openai,voice,menubar]"

# 运行所有测试
python -m pytest tests/ -v

# 运行 Harness 单元测试
python -m tests.test_harness

# 运行集成验证
python -m tests.test_integration
```

---

## 代码风格

- Python 代码遵循 PEP 8
- 使用 `ruff` 检查代码质量
- 所有函数必须有类型注解
- 使用中文 docstring（面向国内用户）
- 引用 Claude Code 架构模式时标注出处

---

## 添加新工具

### 推荐方式：装饰器注册（获得完整元数据）

在 `agent/*_tools.py` 或新文件中：

```python
from knowagent_personal.harness.registry import register_tool, ToolCategory, PermissionLevel

@register_tool(
    "my_command",
    category=ToolCategory.GENERAL,
    permission=PermissionLevel.FILE_READ,
    timeout=30,
)
def cmd_my_command(params: dict) -> str:
    """我的命令。

    参数:
        name: 用户的名字（必填）
        count: 重复次数（可选，默认1）
    """
    name = params.get("name", "World")
    return f"👋 Hello, {name}!"
```

### 传统方式：手动注册（向后兼容）

```python
def cmd_my_command(params: dict) -> str:
    """我的命令。"""
    ...

# 在模块底部手动注册
COMMANDS["my_command"] = cmd_my_command
TOOL_SCHEMAS["my_command"] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "用户的名字"},
    },
    "required": ["name"],
}
```

旧方式会被 `install_harness(migrate_legacy=True)` 自动迁移到 `TOOL_REGISTRY`，
但装饰器方式可以获得更精确的元数据（权限级别、分类、只读标记等）。

---

## 开发 Harness 模块

### 新增模块步骤

1. 在 `harness/` 下创建新文件
2. 在 `harness/__init__.py` 中导出
3. 在 `harness/integration.py` 的 `Harness` 类中集成
4. 编写测试到 `tests/test_harness.py`
5. 在 `tests/test_integration.py` 增加验证项

### 模块设计规范

```python
"""Module docstring — 说明设计和参考来源。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

# 参考 Claude Code xxx 模式
# 参考 Hermes xxx 实现

class MyModule:
    """类 docstring — 包含用法示例。"""

    def __init__(self, ...):
        ...

    def public_method(self) -> Any:
        """公开方法 — 类型注解完整。"""
        ...
```

### 事件命名规范

添加新事件时，遵循 `domain.action` 命名：

```
tool.before      tool.after      tool.error
permission.check permission.grant   permission.deny
workflow.start   workflow.step   workflow.end
session.start    session.end
```

---

## 新增平台适配器

继承 `harness/gateway.py` 的 `PlatformAdapter` 基类：

```python
from knowagent_personal.harness.gateway import PlatformAdapter, AgentMessage, AgentResponse

class TelegramAdapter(PlatformAdapter):
    """Telegram 平台适配器。"""

    def __init__(self, token: str):
        super().__init__(name="telegram")
        self.token = token

    async def start(self):
        """启动长轮询，接收消息。"""
        ...

    async def stop(self):
        """停止适配器。"""
        ...

    async def send(self, response: AgentResponse):
        """发送响应到 Telegram。"""
        ...

# 使用
gateway.register(TelegramAdapter(token="xxx"))
gateway.run()
```

---

## 测试

### 测试分类

| 测试文件 | 覆盖范围 |
|----------|---------|
| `tests/test_harness.py` | 10 个单元测试（registry/permissions/executor/events/context/sandbox） |
| `tests/test_integration.py` | 8 项端到端验证（权限/事件/记忆/持久化/Hooks/Agent集成） |
| `tests/test_tools.py` | 核心工具命令测试 |
| `tests/test_memory.py` | 记忆系统测试 |

### 运行测试

```bash
# 全部测试
python -m pytest tests/ -v

# 仅 Harness 测试
python -m tests.test_harness

# 集成验证
python -m tests.test_integration
```

### 编写 Harness 测试模板

```python
from knowagent_personal.harness.registry import TOOL_REGISTRY, register_tool, ToolCategory, PermissionLevel

def test_my_feature():
    # 1. 注册测试工具
    TOOL_REGISTRY._tools.clear()

    @register_tool("test_tool", permission=PermissionLevel.BASIC)
    def cmd(p): return "ok"

    # 2. 测试逻辑
    tool = TOOL_REGISTRY.get("test_tool")
    assert tool is not None
    assert tool.permission == PermissionLevel.BASIC

    # 3. 验证结果
    result = tool.handler({})
    assert result == "ok"

    print("✅ test_my_feature PASS")
```

---

## 提交 PR

1. Fork 本仓库
2. 创建功能分支: `git checkout -b feature/your-feature`
3. 提交更改: `git commit -m "feat: add your feature"`
4. 推送到分支: `git push origin feature/your-feature`
5. 创建 Pull Request

PR 合并前需要：
- ✅ 所有测试通过
- ✅ `python -m tests.test_harness` 全部通过
- ✅ `python -m tests.test_integration` 全部通过
- ✅ 有测试覆盖新功能
- ✅ 相关的 README / 文档已更新

### Commit 信息规范

```
<type>(<scope>): <subject>

type: feat | fix | docs | style | refactor | test | chore
scope: harness | agent | ui | config | docs | ...

示例:
  feat(harness): add threat detection scanner
  fix(agent): handle empty params in executor
  docs: update README with harness architecture
```

---

## 报告 Bug

在 [Issues](https://github.com/knowagent/knowagent-personal/issues) 中提交，请包含：

- macOS 版本
- Python 版本
- 完整的错误输出（不要截图，粘贴文字）
- 是否有 Harness 权限拦截（检查 `~/.knowagent/logs/audit_*.jsonl`）
- 复现步骤

## 提交功能请求

在 [Issues](https://github.com/knowagent/knowagent-personal/issues) 中提交，请描述：

- 你想要什么功能
- 为什么需要它（使用场景）
- 你愿意帮忙实现吗？
