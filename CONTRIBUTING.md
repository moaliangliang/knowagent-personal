# 🤝 贡献指南

感谢你对 Mac Agent Personal 的兴趣！任何形式的贡献都欢迎。

## 目录

- [报告 Bug](#报告-bug)
- [提交功能请求](#提交功能请求)
- [开发环境搭建](#开发环境搭建)
- [代码风格](#代码风格)
- [提交 PR](#提交-pr)
- [插件开发](#插件开发)

## 报告 Bug

在 [Issues](https://github.com/knowagent/knowagent-personal/issues) 中提交，请包含：

- macOS 版本
- Python 版本
- 完整的错误输出（不要截图，粘贴文字）
- 复现步骤

## 提交功能请求

在 [Issues](https://github.com/knowagent/knowagent-personal/issues) 中提交，请描述：

- 你想要什么功能
- 为什么需要它（使用场景）
- 你愿意帮忙实现吗？

## 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/knowagent/knowagent-personal.git
cd knowagent-personal

# 安装开发依赖
pip install -e ".[openai,voice,menubar]"

# 运行测试
python -m pytest tests/ -v

# 运行完整测试
python tests/run_all.py
```

## 代码风格

- Python 代码遵循 PEP 8
- 使用 `ruff` 或 `flake8` 检查代码质量
- 所有函数必须有类型注解
- `cmd_*` 函数签名必须是 `def cmd_xxx(params: dict) -> str:`
- docstring 用中文（面向国内用户）或英文

## 提交 PR

1. Fork 本仓库
2. 创建功能分支: `git checkout -b feature/your-feature`
3. 提交更改: `git commit -m "feat: add your feature"`
4. 推送到分支: `git push origin feature/your-feature`
5. 创建 Pull Request

PR 合并前需要：
- ✅ 所有测试通过
- ✅ 代码风格检查通过
- ✅ 有测试覆盖新功能
- ✅ 相关的 README / 文档已更新

## 插件开发

参考 `knowagent_personal/plugins/examples/` 目录下的示例插件。

基本模板：

```python
from knowagent_personal.plugins import Plugin


class MyPlugin(Plugin):
    name = "我的插件"
    description = "插件的功能描述"
    version = "0.1.0"
    author = "your-name"

    def get_commands(self) -> dict:
        return {"my_command": self.cmd_my_command}

    def cmd_my_command(self, params: dict) -> str:
        return f"✅ 插件执行成功"
```

将插件文件放入 `~/.knowagent/plugins/` 目录，下次启动 `ka` 时自动加载。
