# 隐私政策 · Privacy Policy

**知行 (ZhiXing)** · 最后更新: 2026-06-27

---

## 中文

### 数据收集

知行不会收集您的个人信息。所有数据均在本地处理。

#### 我们收集什么

- **匿名使用统计**：仅在您**主动启用**时（`config.yaml` 中 `telemetry.enabled: true`），我们可能收集匿名的命令使用频率数据，用于改进产品。
- **崩溃报告**：如果应用崩溃，macOS 可能会生成崩溃报告，这些报告由 Apple 系统处理，知行本身不发送任何崩溃数据。

#### 我们不收集什么

- ❌ 您的文件内容
- ❌ 您的系统信息截图
- ❌ 您的邮件内容或通讯录
- ❌ 您的键盘输入
- ❌ 您的浏览器历史
- ❌ 任何个人身份信息

### 数据存储

所有数据存储在您的本地设备上：

| 数据类型 | 存储位置 | 说明 |
|---------|---------|------|
| 配置文件 | `~/.zhixing/config.yaml` | LLM 配置、代理设置等 |
| 待办事项 | `~/.zhixing/personal.db` | 本地 SQLite 数据库 |
| 对话历史 | `~/.zhixing/history` | CLI 交互历史 |
| 知识库索引 | `~/.zhixing/chroma/` | 本地 RAG 向量索引 |

### 网络请求

知行仅在以下情况下发起网络请求：

1. **LLM 调用**：发送对话内容到您配置的 LLM 服务（Ollama 本地 / OpenAI API）
2. **音乐搜索**：请求 iTunes API 搜索歌曲元数据
3. **在线播放**：通过 yt-dlp 从 YouTube/网易云下载音频（需您主动执行）
4. **GitHub 检查更新**：启动时检查新版本

### AI 对话

当您使用 AI 对话功能时：

- 您的消息发送到您配置的 **本地 Ollama** 或 **OpenAI API**
- 如果您使用 Ollama（默认），数据**永远不会离开您的电脑**
- 如果您使用 OpenAI API，请参考 [OpenAI 隐私政策](https://openai.com/privacy)

### 权限说明

知行请求以下 macOS 系统权限：

| 权限 | 用途 |
|------|------|
| 辅助功能 (Accessibility) | 模拟键盘输入、UI 自动化 |
| 屏幕录制 (Screen Recording) | 截图与分析 |
| 麦克风 | 语音输入功能 |
| 通讯录 | 联系人搜索 |
| 日历 | 日程读取 |
| 通知 | 发送桌面通知 |

### 第三方服务

知行使用以下开源组件和服务：

- **Electron** — 桌面框架
- **Ollama** — 本地 LLM（可选）
- **yt-dlp** — 音乐下载（可选）

### 您的权利

- 您可以随时删除 `~/.zhixing/` 目录以清除所有本地数据
- 您可以随时撤销系统权限（系统设置 → 隐私与安全性）

### 联系我们

如有隐私相关问题，请提交 [GitHub Issue](https://github.com/zhixing-ai/zhixing/issues)。

---

## English

### Data Collection

ZhiXing does not collect your personal information. All data is processed locally.

#### What We Collect

- **Anonymous usage statistics**: Only when you **explicitly enable** it (`telemetry.enabled: true` in `config.yaml`), we may collect anonymous command frequency data for product improvement.
- **Crash reports**: If the app crashes, macOS may generate crash reports. These are handled by Apple's system. ZhiXing does not send any crash data itself.

#### What We Don't Collect

- ❌ Your file contents
- ❌ Your system screenshots
- ❌ Your email or contacts
- ❌ Your keyboard input
- ❌ Your browser history
- ❌ Any personally identifiable information

### Data Storage

All data is stored locally on your device:

| Data Type | Location | Description |
|-----------|----------|-------------|
| Configuration | `~/.zhixing/config.yaml` | LLM config, proxy settings |
| Tasks | `~/.zhixing/personal.db` | Local SQLite database |
| Chat History | `~/.zhixing/history` | CLI interaction history |
| Knowledge Index | `~/.zhixing/chroma/` | Local RAG vector index |

### Network Requests

ZhiXing only makes network requests in the following cases:

1. **LLM calls**: Sending conversation to your configured LLM (Ollama local / OpenAI API)
2. **Music search**: Querying iTunes API for song metadata
3. **Online playback**: Downloading audio from YouTube/Netease via yt-dlp (user-initiated)
4. **Update check**: Checking for new versions on startup

### Permissions

ZhiXing requests the following macOS system permissions:

| Permission | Purpose |
|-----------|---------|
| Accessibility | Keyboard simulation, UI automation |
| Screen Recording | Screenshots & analysis |
| Microphone | Voice input |
| Contacts | Contact search |
| Calendar | Schedule reading |
| Notifications | Desktop notifications |

### Contact

For privacy concerns, please submit a [GitHub Issue](https://github.com/zhixing-ai/zhixing/issues).
