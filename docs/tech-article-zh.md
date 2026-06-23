# 我从零写了一个 Mac AI 助手：30+ 系统命令、本地 RAG、UI 自动化，全部开源

> 一个能控制音乐、读邮件、截图 OCR、操作 UI 的本地 AI 助手，完全离线运行。

## 为什么做这个

每天早上我坐到电脑前，会重复做这几件事：

1. 打开 Music 放首歌
2. 检查邮件
3. 看看今天的日程
4. 搜一下之前的笔记

每件事都要手动操作，就算用 Alfred/Raycast 也得敲不同的快捷键。我想要一个**能听懂人话**的助手——说一句"放周杰伦的歌"就能播，说一句"今天有什么安排"就显示日程。

市面上的方案都不够理想：
- **Siri**：能力有限，不支持自定义操作
- **Copilot**：Windows 专属，云端运行
- **Claude Desktop**：不能控制本地系统
- **Raycast AI**：有 API 但扩展性受限

所以我决定自己写一个。

## 能做什么

放几个实际使用场景：

### 🎵 放音乐

```bash
$ ka 播放周杰伦的歌
🎵 Apple Music 找到 10 首「周杰伦」
▶️ 正在播放: 晴天 — 周杰伦（预览30秒）
```

背后做了三件事：搜索 iTunes API、下载 30 秒预览播放、在 Music App 中打开完整版。

### 📧 读邮件

```bash
$ ka 读邮件
📋 邮箱大师 收件箱（最近5封）:
  📩 张三 <zhangs@example.com>
      周报会议邀请
      06-24 09:30
```

直接读取邮箱大师的 SQLite 数据库，不需要配置 IMAP。

### 📸 截图+识别文字

```bash
$ ka 看看屏幕上有什么字
📸 识别到 12 行文字:
  欢迎使用 Mac Agent Personal
  ...
```

用 macOS 原生的 Vision 框架做 OCR，中英文混合识别，准确率比 Tesseract 高很多。

### 🖱️ 操作 UI

```bash
$ ka 打开 Music 的界面结构
$ ka 点击播放按钮
```

通过 macOS Accessibility API 获取界面元素树，然后模拟点击。可以用在自动化测试、重复操作等场景。

### 📚 搜索个人知识库

```bash
$ ka rag index ~/Documents
📋 索引结果: 42 个文件已索引

$ ka 我的笔记里关于机器学习的内容
📋 [来源: Documents/ML/notes.md]
机器学习是人工智能的一个分支...
```

所有数据都在本地，不经过任何云端。

## 技术架构

```
用户输入 → parse_natural() 快速匹配 → 直接执行命令 (0.1s)
         ↕ (没匹配到)
         Agent 引擎
           ├─ → Ollama (本地 LLM) → 工具调用 → 执行命令
           └─ → 离线回退 → 内置对话
```

技术栈：

| 组件 | 选型 | 原因 |
|---|---|---|
| 语言 | Python + Swift | Python 快速开发，Swift 调用原生 API |
| 本地 LLM | Ollama + qwen2.5:7b | 免费、离线、中文好 |
| 向量库 | ChromaDB | 零配置嵌入 |
| 持久化 | SQLite | 零依赖 |
| UI 自动化 | Swift AX API | macOS 原生，比 pyautogui 快 |
| OCR | Vision Framework | 原生中英文，比 Tesseract 准 |

## 遇到的坑

### 1. AppleScript 的限制

AppleScript 是 macOS 自动化的核心，但语法极其古老。写一个读邮件的脚本：

```applescript
tell application "Mail"
    set msgs to messages of inbox
    repeat with m in msgs
        log subject of m
    end repeat
end tell
```

看起来简单，但实际调试中发现不同 macOS 版本的 AppleScript 行为不一致，有些属性名在不同语言环境下不一样。

### 2. macOS 权限

截屏需要授权、读邮件需要授权、UI 自动化需要授权（而且每次重启可能失效）。最坑的是 Accessibility 权限——系统偏好设置里打开了也没用，得重启应用才生效。

### 3. Swift 编译兼容性

用了两个 Swift 工具（UI 检查器和 OCR），编译参数因 macOS 版本和 Xcode 版本不同而不同。解决方案是每次运行时自动检测并重新编译。

### 4. 本地 LLM 的工具调用

让本地模型理解"什么时候该用什么工具"是最难的部分。同样的问题，有的模型能正确调用工具，有的就直接胡诌。实测 qwen2.5:7b 在工具调用上表现最好。

## 开源

项目完全开源：https://github.com/knowagent/knowagent-personal

你可以通过 pip 安装：

```bash
pip install knowagent-personal
ka
```

几步就能上手：
1. 安装 Ollama：`brew install ollama`
2. 拉取模型：`ollama pull qwen2.5:7b`
3. 启动：`ka`

不用 AI 也能用——所有命令都可以通过自然语言直接匹配。

## 下一步

- **插件系统** 🔜 — 任何人都可以写插件扩展功能
- **Windows 移植** — 让更多平台能用
- **Pro 版** — 高级自动化工作流、跨设备同步

如果你对这类工具感兴趣，欢迎来 GitHub 点个 Star，也欢迎提交 PR 和 Issue。
