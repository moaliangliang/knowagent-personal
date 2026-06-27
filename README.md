<p align="center">
  <img src="https://img.shields.io/badge/macOS-11.0+-blue?logo=apple" alt="macOS">
  <img src="https://img.shields.io/badge/Python-3.10+-green?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="License">
  <img src="https://img.shields.io/badge/commands-101-brightgreen" alt="Commands">
  <img src="https://img.shields.io/badge/workflow-37%20templates-orange" alt="Templates">
  <img src="https://img.shields.io/badge/security-deny--first-red" alt="Security">
  <img src="https://img.shields.io/badge/tests-150-passing-green" alt="Tests">
</p>

<h1 align="center">⬡ 知行 (ZhiXing)</h1>
<p align="center">
  <b>AI 驱动的 macOS 桌面自动化助手</b><br>
  <a href="https://github.com/zhixing-ai/zhixing/releases"><img src="https://img.shields.io/github/v/release/zhixing-ai/zhixing?label=version" alt="Version"></a>
  <a href="https://github.com/zhixing-ai/zhixing/releases"><img src="https://img.shields.io/github/downloads/zhixing-ai/zhixing/total" alt="Downloads"></a>
  101 个系统命令 · 可视化工作流 · 自然语言配置 · Ollama/OpenAI · 开源免费
</p>

<p align="center">
  <a href="#-快速安装"><b>快速安装</b></a> ·
  <a href="#-工作流"><b>工作流</b></a> ·
  <a href="#-使用示例"><b>使用示例</b></a> ·
  <a href="tests/WORKFLOW_SOP.md"><b>完整手册</b></a>
</p>

<p align="center">
  <i>调亮度 · 翻译 · 搜索文件 · 截图 · 控制音乐 · 读邮件 · VPN · 录屏 · UI 自动化 · 工作流编排</i>
</p>

---

## 📸 截图

> ![](docs/screenshots/01-system-status.png) | ![](docs/screenshots/02-terminal.png) | ![](docs/screenshots/03-music.png)

---

## 🚀 快速安装

### 方式 1：从 PyPI 安装（推荐，CLI 模式）

```bash
pip install zhixing

# 启动交互式终端
zhi
```

### 方式 2：从源码安装（完整功能，含 Electron 桌面）

```bash
# 1. Python 后端
git clone https://github.com/zhixing-ai/zhixing.git
cd zhixing
pip install -e ".[openai,voice,menubar]"

# 2. Electron 桌面
cd electron-app
npm install

# 3. 启动
npx electron .          # 桌面应用
zhi                     # 或纯 CLI 模式
```

### 方式 3：DMG 安装包（macOS，推荐）

从 [GitHub Releases](https://github.com/zhixing-ai/zhixing/releases) 下载最新的 `ZhiXing-{version}-{arch}.dmg`，拖入 Applications 即可。

> 已签名 + 公证，Gatekeeper 友好。

### 前提条件（可选，用于 AI 对话）

```bash
brew install ollama
ollama serve
ollama pull qwen3:8b    # 推荐模型
```

---

## 🎯 核心功能

### 101 个系统命令

| 类别 | 数量 | 包含 |
|:----|:----:|:-----|
| 🔧 系统控制 | 11 | 亮度/音量/睡眠/锁屏/专注模式/系统状态/电池/WiFi |
| 🌐 网络工具 | 8 | 公网IP/测速/HTTP请求/下载/whois/ping/端口检测/**新闻** |
| 📁 文件管理 | 8 | 搜索/压缩/解压/废纸篓/重复文件/图片转换 |
| 💻 开发工具 | 3 | Homebrew/进程管理/Docker |
| 🎬 媒体处理 | 6 | 录屏/录音/OCR/截图+分析/视频信息 |
| 📅 日常效率 | 7 | 番茄钟/剪贴板历史/翻译/快捷指令/通知/日历/待办 |
| 🤖 AI 增强 | 5 | 对话/摘要/代码审查/图片生成/**图片分析** |
| 🎵 音乐&邮件 | 8 | 播放/搜索/邮件收/邮件发/邮箱大师 |
| ⌨️ UI & 键盘 | 14 | UI树/点击/键盘输入/朗读/语音/联系/备忘/工作流 |
| 🔐 安全&工具 | 5 | Keychain/凭据管理/剪贴板监控/配置热加载 |

> 全部命令支持中文别名（157 条别名映射）

### 🧩 可视化工作流

将多个命令编排为自动化流水线：

```
🚀 三种配置方式:
  ① 自然语言:  "每天9点检查系统然后发通知"
  ② 交互引导:  zhi create_wf（问答式）
  ③ 预设模板:  zhi workflow（37 个内置模板）
```

**工作流引擎高级特性**：

| 特性 | 说明 | 示例 |
|:----|:-----|:-----|
| 🔁 循环 | 步骤重复执行 N 次 | `loop: 5` |
| 🔂 重试 | 失败自动重试 | `retry: 2` |
| ⏱ 超时 | 单步超时控制 | `timeout: 30` |
| 🧩 子工作流 | 调用其他模板 | `sub_workflow: "系统报告"` |
| 📦 变量传递 | 步骤间传递结果 | `${result_system_status}` |
| 🏃 后台执行 | 不阻塞终端 | `bg: true` |
| ✅ 参数验证 | 前端实时校验 | Cron/URL/数字 |

> 详见 [工作流完整手册](tests/WORKFLOW_SOP.md)

### 🛡️ Harness 安全层

拒绝优先的权限系统，7 层纵深防御：

| 防御层 | 说明 |
|:------|:-----|
| 工具预过滤 | 未注册工具不可见 |
| Deny-First | 拒绝始终覆盖允许 |
| 权限模式 | 5 级放行策略（plan/normal/accept_edits/elevated/trusted） |
| 会话授权 | 一次性授权，重启恢复 |
| 提示注入检测 | 输入+输出层扫描 |
| 隔离执行 | 子进程 + 白名单沙箱 |
| 审计日志 | 每次执行记录 JSONL |

### 🔄 macOS 提醒事项同步

知行待办与 macOS 提醒事项双向同步：

```bash
zhi todo_add title=买牛奶        # 自动同步到提醒事项
zhi todo_import                   # 导入提醒事项到知行
zhi todo_list                     # 同时显示两边
```

### 🤖 AI 图片理解

```bash
zhi 看图                          # 截屏分析（场景/物体/氛围/文字）
zhi image_analyze path=photo.jpg  # 分析指定图片
```

需要 Ollama（`ollama pull llava`）或 OpenAI gpt-4o。

---

## 📖 使用示例

### CLI 模式

```bash
# 系统状态
$ zhi 系统状态
📋 系统状态
  🖥 CPU: 23%
  🧠 内存: 10.2/32.0 GB

# 一句话创建工作流
$ zhi workflow_create text="每天9点检查系统然后发通知" run=true
🧠 从描述: 「每天9点检查系统然后发通知」
  解析出 3 步工作流

# 查看 37 个模板
$ zhi workflow
📋 预设工作流:
  1. 📊 系统报告: 检查系统 → 检查电池 → 检查网络 → 今日日程
  2. ☀️ 晨间检查: 系统状态 → 今日日程 → 待办事项 → 问候
  ...

# 引导式创建
$ zhi create_wf

# 高级工作流（循环5次，间隔1小时）
$ zhi workflow_execute bg=true steps='[{"cmd":"system_status","loop":5,"wait":3600}]'
```

### 桌面模式

```bash
cd electron-app && npx electron .
```

- 📋 **预设** → 一键加载 37 个模板
- ▶️ **运行** → 实时高亮当前步骤
- 📋 **导出 YAML** → 分享工作流
- 💾 **保存** → 本地持久化

---

## ⚙️ 配置

`~/.zhixing/config.yaml` 首次启动自动生成：

```yaml
llm:
  provider: ollama
  model: qwen3:8b
  ollama_url: http://localhost:11434
  vision_model: llava          # 图片分析模型

harness:
  permission_mode: normal
  audit_log: true
```

---

## 📁 项目结构

```
zhixing/
├── zhishing/          # Python 后端
│   ├── agent/         # Agent 核心 + 101 个命令
│   ├── harness/       # 安全层（权限/隔离/事件/威胁检测）
│   ├── memory/        # RAG 知识库 + 对话记忆
│   └── ui/            # CLI REPL
├── electron-app/      # Electron 桌面应用
└── swift/             # macOS 原生桥接
```

---

## 🧪 测试

```bash
pytest tests/ -v
# 150 个测试，覆盖全部模块
```

---

## 🗺️ 路线图

| 阶段 | 状态 | 内容 |
|:----|:----:|:------|
| v1.0 命令系统 | ✅ | 101 命令 + Harness 安全层 |
| v1.1 工作流 | ✅ | 可视化编辑器 + 37 模板 + 自然语言创建 |
| v1.2 同步 | ✅ | macOS 提醒事项同步 + 待办管理 |
| v2.0 App Store | 🚧 | Electron 打包 + 签名 + 公证 |
| v2.1 云同步 | 📅 | iCloud 工作流同步 + 配置备份 |
| v2.2 Windows | 📅 | 平台适配器 + 核心命令移植 |

---

## 🤝 贡献

欢迎 Issue 和 PR！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

### 贡献方向

- **新增命令**: 在 `zhixing/agent/` 下创建 `*_tools.py`
- **工作流模板**: 在 `cli.py` 的 `WORKFLOW_PRESETS` 中添加
- **平台适配**: 为 Windows/Linux 实现 `PlatformAdapter`
- **安全加固**: 完善威胁检测模式库

---

## 📄 许可证

[MIT License](LICENSE) © 2026 ZhiXing Team
