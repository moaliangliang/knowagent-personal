<p align="center">
  <img src="https://img.shields.io/badge/macOS-11.0+-blue?logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/Python-3.10+-green?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/github/stars/knowagent/knowagent-personal?style=social" alt="Stars">
</p>

<h1 align="center">🧠 Mac Agent Personal</h1>
<p align="center">
  <b>本地 Mac 桌面 AI 助手</b><br>
  30+ 系统命令 · 本地 LLM · 完全离线 · 开源免费
</p>

<p align="center">
  <i>能控制音乐、读邮件、截图 OCR、UI 自动化、搜索个人知识库</i>
</p>

---

## ✨ 功能

| 类别 | 命令 | 说明 |
|------|------|------|
| 🖥️ **系统** | `system_status` `battery_status` `wifi_status` `lock_screen` | CPU/内存/磁盘/网络/电池/WiFi |
| 🎵 **音乐** | `music_play` `music_search_online` `music_next` `music_volume` | Apple Music 搜索/播放/音量 |
| 📧 **邮件** | `mail_read` `mail_master` `mail_send` | Mail.app + 邮箱大师收发 |
| 📸 **截屏 OCR** | `screenshot` `screenshot_analyze` | 截图 + Vision 原生 OCR |
| 🖱️ **UI 自动化** | `ui_tree` `ui_find` `ui_click` | 查看/搜索/点击界面元素 |
| ⌨️ **键盘** | `keyboard_type` `keyboard_press` | 模拟输入、快捷键 |
| 📋 **系统工具** | `clipboard_read/write` `calendar` `notification` | 剪贴板、日历、通知 |
| 📚 **知识库** | `rag search` `rag index` | 本地 RAG 文档搜索 |
| 🎤 **语音** | `voice_input` | 语音识别输入 |
| 🔄 **工作流** | `workflow_execute` | 多步自动化 |
| 📂 **文件** | `file_list` `open_app` `open_url` | 文件浏览、启动应用 |
| 👤 **个人信息** | `contacts_search` `reminder_add` `notes_list` `speak` | 联系人、提醒、备忘录 |
| 🧠 **AI 对话** | 自然语言 → 工具调用 | Ollama 本地 LLM 驱动 |

---

## 🚀 快速开始

### 前提条件

```bash
# 1. 安装 Ollama（用于本地 AI）
brew install ollama
ollama serve
ollama pull qwen2.5:7b   # 或 deepseek-r1:8b
```

### 安装

```bash
pip install knowagent-personal
```

### 使用

```bash
# 交互式 REPL（推荐）
ka

# 单命令模式
ka 系统状态
ka 播放周杰伦的歌
ka 截图
```

**第一次启动后**，菜单栏会出现 `KA` 图标，点击可快捷操作。

---

## 📖 使用示例

```bash
# 🖥️ 系统状态
$ ka 系统状态
📋 系统状态 —— MacBook-Pro.local (macOS 26.5.1)
  🖥 CPU: 23%
  🧠 内存: 10.2/32.0 GB (76.6%)
  💾 磁盘: 514.9/994.6 GB 空闲

# 🎵 播放音乐
$ ka 播放周杰伦的歌
🎵 Apple Music 找到 10 首「周杰伦」
▶️ 正在播放: 晴天 — 周杰伦（预览30秒）

# 📸 截图+识别文字
$ ka 看看屏幕上有什么字
📸 识别到 12 行文字:
  欢迎使用 Mac Agent Personal
  ...

# 📧 读邮件
$ ka 读邮件
📋 邮箱大师 收件箱（最近5封）:
  📩 张三 <zhangs@example.com>
      周报会议邀请
      06-24 09:30

# 📚 搜索个人知识库（先索引）
$ ka rag index ~/Documents
📋 索引结果: {'added': 42, 'skipped': 3, ...}

$ ka 我的笔记里关于机器学习的
📋 [来源: Documents/ML/notes.md]
机器学习是人工智能的一个分支...
```

---

## ⚙️ 配置

配置文件 `~/.knowagent/config.yaml` 首次启动自动生成：

```yaml
llm:
  provider: ollama              # ollama 或 openai
  model: qwen2.5:7b             # Ollama 模型名
  ollama_url: http://localhost:11434
rag:
  enabled: true                 # 启用个人知识库
  index_dirs:
    - ~/Documents
    - ~/Desktop
```

---

## 🔌 插件系统

插件是放在 `~/.knowagent/plugins/` 下的 Python 文件，启动时自动加载。

创建插件只需 5 行：

```python
from knowagent_personal.plugins import Plugin

class HelloPlugin(Plugin):
    name = "Hello"
    def get_commands(self):
        return {"hello": lambda p: "👋 Hello from plugin!"}
```

---

## 🧠 AI 集成

需要 Ollama 本地运行。支持两种模式：

| 模式 | LLM | 特点 |
|------|-----|------|
| **本地** (默认) | Ollama + qwen2.5:7b | 免费、离线、隐私 |
| **云端** | OpenAI 兼容 API | 更强大、需自备 Key |

配置方式：

```bash
# 方式 1: Ollama 本地（推荐）
ollama pull qwen2.5:7b

# 方式 2: OpenAI 兼容 API
ka --provider openai --model gpt-4o --ollama-url https://api.openai.com/v1
```

无需 AI 也能用——所有命令都可以直接通过自然语言匹配执行。

---

## 🖥️ 菜单栏应用

启动后在菜单栏显示 `KA` 图标：

```bash
# 启动菜单栏
bash scripts/menubar.sh start

# 关闭
bash scripts/menubar.sh stop
```

菜单功能：打开 REPL 终端 / 索引知识库 / 打开配置

---

## 🏗 项目架构

```
你输入 "播放周杰伦的歌"
      │
      ├─ parse_natural() ── 关键词匹配 ──▶ music_search_online() (0.1s)
      │
      └─ 未匹配 → Agent.process()
               │
               ├─ [Ollama 可用] ──▶ LLM 工具调用循环
               │                      ├─ 返回 system_status 等命令
               │                      └─ 返回文本回复
               │
               └─ [离线] ──▶ local_chat() 内置对话
```

```
knowagent-personal/
├── knowagent_personal/
│   ├── agent/
│   │   ├── tools.py      # 33 个系统命令（核心）
│   │   ├── llm.py        # Ollama/OpenAI 客户端
│   │   └── core.py       # Agent 工具调用循环
│   ├── memory/
│   │   ├── db.py         # SQLite 对话持久化
│   │   └── rag.py        # ChromaDB 个人知识库
│   ├── plugins/          # 插件系统
│   ├── ui/
│   │   ├── cli.py        # REPL 交互终端
│   │   └── menubar.py    # 菜单栏应用
│   ├── config.py         # 配置管理
│   └── app.py            # 菜单栏入口
├── swift/
│   ├── ax_inspector.swift   # UI 自动化
│   ├── screen_ocr.swift     # 屏幕 OCR
│   └── menubar.swift        # 菜单栏
└── tests/
```

---

## 📊 路线图

- [x] **Phase 0**: 代码分离、项目骨架、31 个命令
- [x] **Phase 1**: RAG 知识库、对话记忆、语音输入、菜单栏
- [ ] **Phase 2**: 插件系统、开源发布、社区增长 ← **当前**
- [ ] **Phase 3**: Pro 版变现、Windows 移植、企业版

---

## 🤝 贡献

欢迎各种形式的贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

- 报告 Bug → [New Issue](https://github.com/knowagent/knowagent-personal/issues/new?labels=bug)
- 提功能请求 → [New Issue](https://github.com/knowagent/knowagent-personal/issues/new?labels=enhancement)
- 开发插件 → 参考 `plugins/examples/` 目录

---

## 📄 许可证

[MIT License](LICENSE) © 2026 KnowAgent
