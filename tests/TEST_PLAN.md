# 知行 (ZhiXing) 全面测试计划

## 概述

- **项目**: 知行 (ZhiXing) v2.0.0 — 自然语言驱动的 Mac 桌面 AI 自动化助手
- **测试目标**: 全面验证 83+ 系统命令、Harness 安全层、Agent 核心、UI/CLI、Electron 前端、Chrome 扩展的完整性和稳定性
- **测试环境**: macOS (当前), Python 3.13
- **测试日期**: 2026-06-27

---

## 一、测试范围总览

| 模块 | 文件 | 行数 | 现有测试覆盖 | 计划新增覆盖 |
|------|------|:----:|:-----------:|:-----------:|
| **Core 核心模块** |||||
| config.py | 配置管理 | ✓ test_config.py | - |
| main.py | CLI 入口 | 部分 (run_all.py) | - |
| app.py | 应用入口 | 基本导入 | - |
| llm.py | LLM 客户端 | 基本导入 | TODO |
| core.py | Agent 核心 | ✓ 多文件覆盖 | - |
| tools.py | 命令注册 | ✓ 多文件覆盖 | - |
| **Tool 模块 (功能测试)** |||||
| system_tools.py | 系统控制(11个) | ✗ 仅注册测试 | TODO |
| network_tools.py | 网络工具(7个) | ✗ 仅注册测试 | TODO |
| file_tools.py | 文件管理(8个) | ✗ 仅注册测试 | TODO |
| dev_tools.py | 开发工具(3个) | ✗ 仅注册测试 | TODO |
| media_tools.py | 媒体处理(6个) | ✗ 仅注册测试 | TODO |
| daily_tools.py | 日常效率(7个) | ✗ 仅注册测试 | TODO |
| ai_tools.py | AI 增强(5个) | ✗ 仅注册测试 | TODO |
| monitor_tools.py | 监控(3个) | ✗ 仅注册测试 | TODO |
| clipboard_daemon.py | 剪贴板(3个) | ✗ 仅注册测试 | TODO |
| **业务模块 (零测试覆盖)** |||||
| browser_controller.py | 浏览器控制 | ✗ 零覆盖 | TODO |
| funnel.py | 用户转化漏斗 | ✗ 零覆盖 | TODO |
| i18n.py | 国际化 | ✗ 零覆盖 | TODO |
| messaging.py | 企业消息 | ✗ 零覆盖 | TODO |
| plugin_tools.py | 插件管理 | ✗ 零覆盖 | TODO |
| pro.py | Pro 版本 | ✗ 零覆盖 | TODO |
| skill_manager.py | Skill 管理 | ✗ 零覆盖 | TODO |
| todo.py | 待办管理(450行) | ✗ 零覆盖 | TODO |
| auto.py | 自动化脚本 | 部分(test_workflow) | TODO |
| **Harness 安全层** |||||
| gateway.py | 消息网关(414行) | ✗ 零覆盖 | TODO |
| self_improvement.py | 自我改进 | ✗ 零覆盖 | TODO |
| skill_context.py | Skill 上下文 | ✗ 零覆盖 | TODO |
| sandbox.py | 沙箱(基本) | ✓ test_harness | - |
| sandbox_whitelist.py | 沙箱白名单 | ✓ test_audit_fixes | - |
| threat_detection.py | 威胁检测 | ✓ test_audit_fixes | - |
| **UI 模块** |||||
| timer_window.py | 番茄钟窗口 | ✗ 零覆盖 | TODO |
| **Electron 前端** |||||
| workflow.js | 工作流编辑器 | ✓ test_workflow | - |
| app.js | 应用逻辑 | ✗ 零覆盖 | TODO |
| preload.js | 预加载脚本 | ✗ 零覆盖 | TODO |
| **Chrome 扩展** |||||
| background.js | 后台脚本 | ✗ 零覆盖 | TODO |
| content.js | 内容脚本 | ✗ 零覆盖 | TODO |
| server.py | 本地服务器 | ✗ 零覆盖 | TODO |
| **Swift 模块** |||||
| ax_inspector.swift | AX 检查器 | ✗ 零覆盖 | TODO |
| screen_ocr.swift | 屏幕 OCR | ✗ 零覆盖 | TODO |
| hotkey.swift | 热键注册 | ✗ 零覆盖 | TODO |
| timer_window.swift | 番茄钟窗口 | ✗ 零覆盖 | TODO |

---

## 二、测试回合 (Rounds)

### Round 1: 回归测试 (Existing Tests)
运行全部 57 个现有测试，确认基础功能正常。

| 测试文件 | 数量 | 状态 |
|----------|:---:|:----:|
| tests/test_config.py | 4 | ✅ 通过 |
| tests/test_memory.py | 4 | ✅ 通过 |
| tests/test_tools.py | 7 | ✅ 通过 |
| tests/test_new_tools.py | 15 | ✅ 通过 |
| tests/test_harness.py | 10 | ✅ 通过 |
| tests/test_audit_fixes.py | ~20 | ✅ 通过 |
| tests/test_workflow.py | 17 | ✅ 通过 |
| **合计** | **~77** | **✅ 全部通过** |

### Round 2: Tool 模块功能测试
为所有 Tool 模块编写单元测试，验证:
- 每个命令的参数校验
- 边界条件（空参数、无效参数）
- macOS 命令的错误处理（无权限/不可用）
- 关键路径执行

### Round 3: 业务模块零覆盖测试
为以下零覆盖模块编写测试:
1. `browser_controller.py` — 平台检测、AppleScript 调用
2. `funnel.py` — 状态管理、漏斗提示逻辑
3. `i18n.py` — 语言检测、翻译表
4. `messaging.py` — Webhook 构建、平台配置
5. `plugin_tools.py` — 插件生命周期
6. `pro.py` — License 校验、功能开关
7. `skill_manager.py` — Skill 安装、列表、加载
8. `todo.py` — CRUD、优先级、排序、导出
9. `auto.py` — YAML 执行、进度报告

### Round 4: Harness 新增模块测试
- `gateway.py` — 消息协议、WebSocket 适配器
- `self_improvement.py` — 自我改进逻辑
- `skill_context.py` — Skill 上下文管理

### Round 5: Electron + Chrome 扩展集成测试
- 使用 browser 工具测试 Electron 窗口
- Chrome 扩展的 background/content script 逻辑验证
- Server.py API 测试

### Round 6: 端到端工作流测试
- CLI → Agent → Tool → macOS 全链路
- Harness 权限 → 执行 → 事件 → 审计
- Electron 前端 → Node backend → 系统命令

---

## 三、测试执行计划

### 第1步: 回归验证 (已完成)
```bash
python3 -m pytest tests/ -v --tb=short
```
结果: **57/57 通过** ✅

### 第2步: 编写 test_tool_modules.py (功能测试)
覆盖 system_tools, network_tools, file_tools, dev_tools, media_tools, daily_tools, ai_tools, monitor_tools, clipboard_daemon

### 第3步: 编写 test_business_modules.py (业务模块)
覆盖 todo, funnel, i18n, pro, messaging, browser_controller, plugin_tools, skill_manager, auto

### 第4步: 编写 test_harness_extras.py (Harness 扩展)
覆盖 gateway, self_improvement, skill_context

### 第5步: 编写 test_electron.py (Electron 前端)
使用 browser 工具测试 Electron 窗口

### 第6步: 问题记录与修复
每轮测试中发现的问题记录在 tests/ISSUES.md

---

## 四、问题分类标准

| 严重级别 | 标签 | 说明 |
|----------|:----:|------|
| 🔴 P0-Critical | critical | 崩溃、数据丢失、安全漏洞 |
| 🟡 P1-High | high | 主要功能失效、严重逻辑错误 |
| 🟠 P2-Medium | medium | 次要功能异常、边界条件错误 |
| 🔵 P3-Low | low | 文案错误、样式问题、代码异味 |

---

## 五、交付物

1. ✅ **测试计划**: tests/TEST_PLAN.md
2. ⬜ **测试脚本**:
   - tests/test_tool_modules.py  (Tool 功能测试)
   - tests/test_business_modules.py (业务模块测试)  
   - tests/test_harness_extras.py (Harness 扩展测试)
   - tests/test_electron.py (Electron 测试)
3. ⬜ **问题报告**: tests/ISSUES.md
4. ⬜ **问题修复确认**: 每个问题修复后的回归验证记录

---

## 六、测试注意事项

1. **macOS 依赖**: 部分命令需要 macOS 环境（osascript, pmset 等），在 Linux/Windows 上会优雅失败
2. **外部依赖**: 网络命令（my_ip, speedtest）、音乐搜索依赖外部服务可用性
3. **安全限制**: 破坏性操作（lock_screen, shutdown）在 NORMAL 模式下会被拒绝，需在 TRUSTED 模式下测试
4. **沙箱隔离**: 高风险代码执行会通过子进程沙箱隔离
