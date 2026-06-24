# 🚀 Mac Agent Personal — 推广素材包

项目地址：https://github.com/moaliangliang/knowagent-personal

---

## 一、Twitter/X 帖子

### 帖 1：发布公告（推荐置顶）

> 🧠 I built an open-source AI agent for macOS that can actually DO things on your Mac.
>
> Features:
> 🎵 Play Apple Music by voice
> 📸 Screenshot + OCR
> ✉️ Read/send emails
> 🖱️ Automate UI clicks
> 📚 Local RAG knowledge base
>
> 100% local. No data leaves your Mac.
>
> ⭐ GitHub: https://github.com/moaliangliang/knowagent-personal

### 帖 2：演示动图

> "Play 周杰伦's music" — and it just works. 🎵
>
> Mac Agent Personal understands natural language and controls your Mac:
>
> 30+ system commands, all local, no cloud.
>
> Try it: https://github.com/moaliangliang/knowagent-personal

### 帖 3：技术分享

> How I built a local AI agent for macOS:
>
> • Python + Swift for system integration
> • Ollama for local LLM (tool calling)
> • ChromaDB for personal RAG
> • macOS Accessibility API for UI automation
> • Vision Framework for OCR
>
> Everything runs offline. Full source:
> https://github.com/moaliangliang/knowagent-personal

---

## 二、Hacker News - Show HN

**标题：** Show HN: I built an open-source AI agent that controls macOS (music, email, UI, OCR)

**正文：**

> Hi HN! I built Mac Agent Personal — an open-source, local-first AI assistant for macOS.
>
> Unlike cloud assistants that can only chat, this one can actually control your Mac:
>
> - 🎵 Apple Music: search, play, volume control
> - 📧 Mail: read/send via Mail.app + MailMaster
> - 📸 Screenshot + OCR (macOS Vision framework, Chinese + English)
> - 🖱️ UI automation via Accessibility API (inspect, find, click elements)
> - ⌨️ Keyboard simulation (type text, press keys, shortcuts)
> - 📋 System: CPU/RAM/disk/network/battery/WiFi
> - 📚 Personal RAG knowledge base (ChromaDB, local embeddings)
> - 🎤 Voice input
> - 🔄 Multi-step workflows
>
> It uses Ollama for local LLM (tool calling), so everything runs 100% offline — no data leaves your machine.
>
> Quick start:
> ```bash
> pip install knowagent-personal
> ka
> ```
>
> Stack: Python + Swift (AX API, Vision) + Ollama + ChromaDB + SQLite
>
> GitHub: https://github.com/moaliangliang/knowagent-personal
>
> Would love your feedback! 🙏

---

## 三、Reddit

### r/macapps

**标题：** I built an open-source AI agent for macOS that can control Music, Mail, UI, and more

**正文：**

> Hey everyone! I've been working on an open-source AI assistant for macOS that's different from the usual chat bots — it can actually DO things on your Mac.
>
> Demo: ask it to "play Jay Chou's music" and it'll search Apple Music, play a preview, and open the full track. Ask it "what's on my screen" and it'll take a screenshot and OCR the text.
>
> Key features:
> - 33 built-in commands (music, mail, screenshot/OCR, UI automation, system, clipboard, calendar, etc.)
> - Local LLM via Ollama (qwen2.5:7b) — no cloud dependency
> - Personal RAG: index your Documents and ask questions about them
> - Plugin system: write your own commands in Python
> - Menu bar app for quick access
>
> Tech stack: Python + Swift (native Accessibility API + Vision OCR) + Ollama + ChromaDB
>
> Would love to hear what you think!
>
> https://github.com/moaliangliang/knowagent-personal

### r/programming

**标题：** Show HN: Open-source AI agent for macOS with 33 system commands, local RAG, UI automation

**正文：**

> Built an open-source macOS agent that combines LLM tool calling with deep system integration:
>
> The architecture:
> - User input → parse_natural() fast path (keyword matching, ~100ms)
> - Or → Agent loop (Ollama local LLM, tool calling)
> - Tools execute via: AppleScript, Swift AX API, Vision Framework, shell commands
>
> The plugin system lets anyone add new commands:
> ```python
> class MyPlugin(Plugin):
>     def get_commands(self):
>         return {"my_cmd": self.handler}
> ```
>
> https://github.com/moaliangliang/knowagent-personal

---

## 四、知乎 / 掘金

**标题：** 我从零写了一个 Mac AI 助手：30+ 系统命令、本地 RAG、UI 自动化，全部开源

文章中包含 `docs/tech-article-zh.md` 的内容。

**发布地址：**
- 知乎专栏：https://zhuanlan.zhihu.com
- 掘金：https://juejin.cn
- 即刻：发图文短帖

---

## 五、ProductHunt 发布

参考 `docs/producthunt.md` 完整清单。

---

## 六、演示截图建议

在 README 里加截图能大幅提升转化率。建议截图：

| 场景 | 命令 | 效果 |
|---|---|---|
| 系统状态 | `ka 系统状态` | 显示 CPU/内存/磁盘 |
| 播放音乐 | `ka 播放周杰伦的歌` | Music 打开+播放预览 |
| 截图 OCR | `ka 看看屏幕上有什么字` | 识别结果 |
| RAG 搜索 | `ka rag search 机器学习` | 文档搜索结果 |
| 菜单栏 | 点击 KA 图标 | 下拉菜单 |
| REPL | `ka` | 交互式终端界面 |

---

## 七、SEO 关键词

| 语言 | 关键词 |
|---|---|
| 中文 | Mac AI助手, macOS AI Agent, 本地知识库, Mac自动化, 开源Mac助手 |
| 英文 | macos ai agent, local llm mac, open source mac assistant, apple music cli, mac ui automation, personal rag |
