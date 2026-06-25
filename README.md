<p align="center">
  <img src="https://img.shields.io/badge/macOS-11.0+-blue?logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/Python-3.10+-green?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/commands-83-brightgreen" alt="Commands">
  <img src="https://img.shields.io/github/stars/knowagent/knowagent-personal?style=social" alt="Stars">
</p>

<h1 align="center">🧠 Mac Agent Personal</h1>
<p align="center">
  <b>本地 Mac 桌面 AI 助手</b><br>
  83 个系统命令 · 中文自然语言 · Ollama/OpenAI · 开源免费
</p>

<p align="center">
  <i>调亮度、翻译、搜索文件、截图、控制音乐、读邮件、VPN、录屏……</i>
</p>

---

## ✨ 功能一览

| 类别 | 命令数 | 说明 |
|------|:------:|------|
| 🔧 **系统控制** | 11 | 亮度/音量/睡眠/关机/重启/屏保/专注模式/系统状态/电池/WiFi/锁屏 |
| 🌐 **网络工具** | 7 | 公网IP/测速/HTTP请求/下载/whois/ping/端口检测 |
| 📁 **文件管理** | 8 | 搜索/内容搜索/压缩/解压/废纸篓/重复文件/图片转换/浏览 |
| 💻 **开发工具** | 3 | Homebrew/进程管理/Docker |
| 🎬 **媒体处理** | 6 | 录屏/录音/视频信息/图片OCR/截图/截图分析 |
| 📅 **日常效率** | 7 | 番茄钟/剪贴板历史/翻译/快捷指令/通知/日历/提醒 |
| 🤖 **AI 增强** | 5 | 对话/摘要/代码审查/图片生成/知识库搜索 |
| 📊 **监控 & VPN** | 4 | 磁盘空间/电池健康/CPU温度/双VPN管理 |
| 🎵 **音乐 & 邮件** | 8 | Apple Music播放/搜索/音量/邮件收/邮件发/邮箱大师 |
| ⌨️ **UI & 键盘** | 14 | UI树/查找/点击/键盘输入/快捷键/剪贴板/朗读/语音/联系人/备忘/工作流/打开应用/打开URL |
| 🔐 **安全 & 工具** | 5 | 凭据管理(Keychain)/剪贴板监控/配置热加载 |
| 💬 **企业通讯** | 4 | 企业微信/飞书/钉钉消息发送、一键群发 |

> **总计 78 个命令**，全部支持中文别名调用（157 条别名映射）。

---

## 🚀 快速开始

### 前提条件

```bash
# 1. 安装 Ollama（本地 AI 对话和工具调用）
brew install ollama
ollama serve
ollama pull qwen3:8b       # 推荐
```

### 安装

```bash
pip install knowagent-personal
```

### 使用

```bash
# 交互式 REPL（推荐）
ka

# 单命令模式——中文直达
ka 系统状态
ka 播放周杰伦的歌
ka 翻译 hello
ka 亮度 level=70
ka 测速
```

---

## 🎯 亮点功能

### 中文自然语言

所有命令支持中文直接调用，无需记英文名：

```bash
ka 温度                     # sensor_temp
ka 搜索文件 query=合同       # file_search
ka 番茄钟 minutes=25         # timer
ka 画图 prompt="一只猫"       # image_gen
ka 电池健康                   # battery_health
```

### VPN 管理

内置深信服 aTrust + FortiGate 双 VPN 管理：

```bash
ka vpn_status                # 查看状态
ka vpn_status action=connect # 一键连接
ka vpn_status action=fortinet # 切换到 Fortinet 并连接
```

### 凭据加密

敏感信息通过 macOS Keychain 安全存储：

```bash
ka credential action=set name=openai   # 存入 Keychain
ka credential action=get name=fortinet # 安全读取
```

### 剪贴板历史后台监控

```bash
ka clipboard_monitor_start   # 启动后台监控
ka clipboard_history limit=20 # 查看最近 20 条
```

### 配置热加载

```bash
ka config action=show        # 查看配置（密码脱敏）
ka config action=reload      # 热重载 config.yaml
ka config action=set key=llm.model value=qwen3:8b
```

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

# 🔍 搜索文件
$ ka 搜索文件 query=合同 limit=10
📋 搜索到 3 个结果:
  /Users/me/Documents/合同/2026采购合同.pdf
  ...

# 🌐 翻译
$ ka 翻译 hello
📋 翻译 en→zh:
  原文: hello
  译文: 你好

# 📸 截图+识别文字
$ ka 看看屏幕上有什么字
📸 识别到 12 行文字:
  欢迎使用 Mac Agent Personal

# 📧 读邮件
$ ka 读邮件
📋 邮箱大师 收件箱（最近5封）:
  📩 张三 <zhangs@example.com>
      周报会议邀请

# 📚 搜索个人知识库
$ ka rag index ~/Documents
📋 索引结果: {'added': 42, 'skipped': 3, ...}
```

---

## ⚙️ 配置

配置文件 `~/.knowagent/config.yaml` 首次启动自动生成：

```yaml
llm:
  provider: ollama              # ollama 或 openai
  model: qwen3:8b              # 推荐模型
  ollama_url: http://localhost:11434

proxy:
  enabled: false               # VPN 代理
  vpn_type: atrust             # 或 fortinet

rag:
  enabled: true
  index_dirs:
    - ~/Documents
    - ~/Desktop
```

安全提示：敏感信息（API Key、VPN 密码）建议通过 `ka credential` 存入 Keychain，不在配置文件中明文存储。

---

## 🔌 插件系统

插件是放在 `~/.knowagent/plugins/` 下的 Python 文件，启动时自动加载：

```python
from knowagent_personal.plugins import Plugin

class HelloPlugin(Plugin):
    name = "Hello"
    def get_commands(self):
        return {"hello": lambda p: "👋 Hello from plugin!"}
```

---

## 🧠 AI 集成

支持三种运行模式：

| 模式 | LLM | 工具调用 | 特点 |
|------|-----|---------|------|
| **离线** | 无 | ✅ NL 规则匹配 | 0 依赖，0.1s 启动 |
| **本地** | Ollama + qwen3:8b | ✅ ~70% 准确率 | 免费、离线、隐私 |
| **云端** | OpenAI/Claude | ✅ ~90%+ 准确率 | 更强大、需 API Key |

无需 AI 也能用——所有 78 个命令都可以通过中文别名直接执行。

---

## 🏗 项目架构

```
你输入 "播放周杰伦的歌"
      │
      ├─ parse_natural() ── 中文别名匹配 ──▶ music_search_online() (0.1s)
      │
      └─ 未匹配 → Agent.process()
               │
               ├─ [Ollama 可用] ──▶ LLM 工具调用循环
               │                      ├─ 选工具
               │                      ├─ 填参数
               │                      └─ 解释结果
               │
               └─ [离线] ──▶ local_chat() 内置对话
```

```
knowagent-personal/
├── knowagent_personal/
│   ├── agent/
│   │   ├── tools.py          # 核心 34 个命令 + 注册中心
│   │   ├── system_tools.py   # 系统控制（7 命令）
│   │   ├── network_tools.py  # 网络工具（7 命令）
│   │   ├── file_tools.py     # 文件管理（7 命令）
│   │   ├── dev_tools.py      # 开发工具（3 命令）
│   │   ├── media_tools.py    # 媒体处理（4 命令）
│   │   ├── daily_tools.py    # 日常效率（5 命令）
│   │   ├── ai_tools.py       # AI 增强（4 命令）
│   │   ├── monitor_tools.py  # 监控（3 命令）
│   │   ├── vpn.py            # 双 VPN 管理
│   │   ├── clipboard_daemon.py # 剪贴板历史后台
│   │   ├── keychain.py       # macOS Keychain 凭据加密
│   │   ├── llm.py            # Ollama/OpenAI 客户端
│   │   ├── core.py           # Agent 工具调用循环
│   │   ├── aliases.py        # 157 条中文别名映射
│   │   ├── help_text.py      # 中/英多语言帮助
│   │   └── __tools_init__.py # 统一注册入口
│   ├── memory/
│   │   ├── db.py             # SQLite 对话持久化
│   │   └── rag.py            # ChromaDB 个人知识库
│   ├── plugins/              # 插件系统
│   ├── ui/
│   │   ├── cli.py            # REPL 交互终端 + 中文路由
│   │   └── menubar.py        # 菜单栏应用
│   ├── config.py             # 配置管理
│   └── app.py                # 菜单栏入口
├── swift/
│   ├── ax_inspector.swift    # UI 自动化
│   ├── screen_ocr.swift      # 屏幕 OCR
│   └── menubar.swift         # 菜单栏
└── tests/
    ├── test_tools.py         # 核心命令测试
    └── test_new_tools.py     # 14 个模块测试（全部通过）
```

---

## 📊 路线图

- [x] **Phase 0**: 项目骨架、34 个命令
- [x] **Phase 1**: RAG 知识库、对话记忆、语音输入、菜单栏
- [x] **Phase 2**: 78 命令、中文别名、双 VPN、剪贴板历史、Keychain 加密
- [ ] **Phase 3**: 插件生态、云同步、Windows 移植

---

## 🤝 贡献

欢迎各种形式的贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

- 报告 Bug → [New Issue](https://github.com/knowagent/knowagent-personal/issues/new?labels=bug)
- 提功能请求 → [New Issue](https://github.com/knowagent/knowagent-personal/issues/new?labels=enhancement)
- 开发插件 → 参考 `plugins/examples/` 目录

---

## 📄 许可证

[MIT License](LICENSE) © 2026 KnowAgent
