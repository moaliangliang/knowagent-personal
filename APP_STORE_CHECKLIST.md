# 🍎 ZhiXing Mac App Store 提交检查清单

> 最后更新: 2026-06-27
> Apple Developer Team: Y3K9Z836YN (liangliang mao)

---

## 📋 概述

ZhiXing (知行) 是 Electron 桌面应用 + Python 后端架构。Python 后端子进程特性与 Mac App Store 沙箱要求存在根本冲突。本清单提供 **两条路径** 供选择。

---

## 🔀 路径选择

### 路径 A：公证 DMG（推荐 v1.0 首发）

| 项目 | 说明 |
|:----|:------|
| 分发方式 | 官网/GitHub Releases 下载 `.dmg` |
| 限制 | ❌ 不在 Mac App Store 内 |
| 优势 | ✅ 支持子进程（Python 后端 `zhi`）<br>✅ 自动更新（electron-updater）<br>✅ 3 天可完成 |
| 要求 | Apple Distribution 证书 ✅ 已有<br>公证（Notarization）<br>Hardened Runtime |

### 路径 B：Mac App Store（MAS）

| 项目 | 说明 |
|:----|:------|
| 分发方式 | App Store 搜索「知行」或「ZhiXing」|
| 限制 | ⚠️ 沙箱限制（App Sandbox）|
| 瓶颈 | ❌ **Python 后端无法 execSync**<br>❌ 需要 Python.framework 内嵌或 JS 重写 |
| 时间 | 2-4 周 |

**推荐策略**: 先走 **路径 A** 快速上线，路径 B 作为 v2.0 目标。

---

## ✅ 路径 A：公证 DMG 提交清单

### 阶段 1：基础设施

- [ ] **1.1 Apple Developer Program**
  - 已激活（有 iOS App 上架记录，Y3K9Z836YN）
  - App Store Connect 创建应用「ZhiXing」

- [ ] **1.2 证书检查**
  - ✅ Apple Distribution: liangliang mao (Y3K9Z836YN)
  - ⚠️ 需要 Apple ID 专用 App Password（用于 notarytool）

- [ ] **1.3 App Store Connect 记录**
  - Bundle ID: `com.zhixing.desktop`
  - App Name: 知行 (ZhiXing)
  - SKU: ZHIXING_MAC_1

### 阶段 2：代码签名配置

- [ ] **2.1 entitlements.plist**（非沙箱 Hardened Runtime）
- [ ] **2.2 entitlements.mac.inherit.plist**
- [ ] **2.3 更新 electron-builder 配置**
  - `hardenedRuntime: true`
  - `gatekeeperAssess: false`
  - `entitlements` 指向文件
  - 公证配置

### 阶段 3：构建与签名

- [ ] **3.1 执行 `electron-builder --mac`**
- [ ] **3.2 验证签名** `codesign -dv --verbose=4`
- [ ] **3.3 公证** `notarytool submit`
- [ ] **3.4 验证公证** `spctl -a -t install -v`

### 阶段 4：元数据

- [ ] **4.1 截图**（5 张 1280x800 / 1440x900）
- [ ] **4.2 描述文字**
- [ ] **4.3 关键词**
- [ ] **4.4 隐私政策 URL**
- [ ] **4.5 支持 URL**

### 阶段 5：发布

- [ ] **5.1 GitHub Release 创建**
- [ ] **5.2 DMG 上传**
- [ ] **5.3 公证书 stapling**
- [ ] **5.4 验证下载+安装体验**

---

## ⚠️ 路径 B：MAS 核心瓶颈分析

### 核心问题：Python 后端子进程

Electron 通过 `execSync('zhi ...')` 调用 Python 后端。MAS 沙箱下：

```
❌ 不允许: execSync / child_process.spawn（任意路径）
❌ 不允许: 调用 ~/.local/bin/zhi
❌ 不允许: 加载 Python 动态库（无 disable-library-validation）
```

### 解决方案比较

| 方案 | 难度 | 工作量 | 备注 |
|:---|:----:|:------:|:-----|
| **内嵌 Python.framework** | 🔴 高 | 2 周 | 需要在 .app 内嵌完整 Python，50MB+ |
| **PyInstaller 单文件打包** | 🟡 中 | 1 周 | 将 zhixing 打包为独立二进制 |
| **WebSocket 独立服务** | 🟢 低 | 2 天 | Electron 启动时连接本地 Python 服务 |
| **JS 重写后端** | 🔴 高 | 1-2 月 | 全部用 Node.js 重写 |

### 推荐 MAS 方案：PyInstaller 打包

```
ZhiXing.app/
├── Contents/
│   ├── MacOS/
│   │   └── ZhiXing              ← Electron shell
│   ├── Frameworks/
│   │   └── zhixing-backend      ← PyInstaller 打包的独立二进制
│   └── Resources/
│       └── ...
```

Electron 调用方式改为：
```js
// 从 execSync('zhi ...') 改为
const backend = path.join(process.resourcesPath, '..', 'Frameworks', 'zhixing-backend');
execSync(`"${backend}" ${cmd}`, ...);
```

### MAS 时序

| 步骤 | 预计 |
|:----|:----:|
| PyInstaller 打包 zhixing | 3 天 |
| entitlements.mas.plist | 1 天 |
| 测试沙箱兼容性 | 2 天 |
| App Review 审核 | 1-7 天 |
| **合计** | **1-2 周** |

---

## 🔧 环境准备

```bash
# 1. 安装必要工具
npm install -g electron-builder

# 2. App 专用密码（用于 notarytool）
#    访问 appleid.apple.com → App-Specific Passwords → 生成
#    保存到 Keychain:
security add-generic-password -s "zhixing-notary" -a "<你的苹果ID>" -w "<密码>"

# 3. 验证证书
security find-identity -v -p basic

# 4. 构建
cd electron-app
npm run dist:mac
```

---

## 📸 截图要求

| 要求 | 非 MAS | MAS |
|:----|:------|:----|
| 尺寸 | 1280x800 | 1280x800 或 1440x900 |
| 数量 | 1-5 张 | 5 张（必须） |
| 格式 | PNG | PNG |
| 内容 | 显示实际功能 | 显示实际功能 |
| 状态栏 | 可接受 | 隐藏敏感信息 |

建议截图：
1. 主界面 + 工作流列表（37 模板）
2. 工作流编辑器 + 预设弹窗
3. CLI 终端 + 自然语言创建
4. 系统托盘 + 浮动按钮
5. 待办同步 macOS 提醒事项

---

## 📝 描述文案（中/英）

### 中文描述

> 知行 (ZhiXing) 是一个 AI 驱动的 macOS 桌面自动化助手。通过自然语言即可控制你的 Mac——调整系统设置、搜索文件、播放音乐、发送消息、管理待办事项，甚至编排自动化工作流。
>
> 核心特性：
> • 101 个系统命令 — 亮度、音量、网络、文件、截图、OCR 等
> • 可视化工作流 — 37 个预设模板，支持循环/重试/后台/变量传递
> • 自然语言创建 — 「每天9点检查系统然后发通知」一句话搞定
> • macOS 提醒事项同步 — 待办双向同步
> • AI 图片分析 — 截图即理解（需 Ollama/OpenAI）
> • Harness 安全层 — 拒绝优先，7 层纵深防御
>
> 知行无需网络即可运行核心功能（本地 LLM 通过 Ollama）。开源免费，无追踪无广告。

### English Description

> ZhiXing is an AI-powered macOS desktop automation assistant. Control your Mac with natural language — adjust system settings, search files, play music, send messages, manage todos, and orchestrate automated workflows.
>
> Key Features:
> • 101 system commands — brightness, volume, network, files, screenshots, OCR, etc.
> • Visual workflow editor — 37 preset templates, loop/retry/background/variables
> • Natural language creation — say "check system and notify at 9am daily"
> • macOS Reminders sync — bidirectional todo sync
> • AI image analysis — understand screenshots instantly (Ollama/OpenAI)
> • Harness security — deny-first, 7-layer defense
>
> Core functions work offline (local LLM via Ollama). Open source, free, no tracking, no ads.

### 关键词 Keywords（英文）

```
ZhiXing,知行,Mac assistant,desktop automation,AI agent,workflow automation,natural language,productivity,open source,Ollama,Apple Mac,macOS tool
```

---

## 📎 参考资料

- [Electron MAS Build Guide](https://www.electron.build/configuration/mac#mas)
- [Apple Hardened Runtime](https://developer.apple.com/documentation/security/hardened_runtime)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [ZhiXing Workflow SOP](tests/WORKFLOW_SOP.md)
