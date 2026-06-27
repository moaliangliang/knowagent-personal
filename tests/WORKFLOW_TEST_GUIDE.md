# 知行工作流测试指南

工作流是知行的核心功能，允许将多个系统命令编排成自动化流水线。
本文档指导你逐步完成 3 个层级的详细测试。

---

## 目录

1. [前置准备](#1-前置准备)
2. [第一层：CLI 预设工作流（3 个场景）](#2-cli-预设工作流)
3. [第二层：API 驱动工作流（5 个场景）](#3-api-驱动工作流)
4. [第三层：Electron 可视化编辑器（4 个场景）](#4-electron-可视化编辑器)
5. [问题记录表](#5-问题记录表)

---

## 1. 前置准备

```bash
# 确保包已安装
cd ~/workspace/knowagent-personal
pip install -e .

# 确保 Electron 依赖已安装
cd electron-app && npm install && cd ..
```

### 测试环境确认

```bash
# 确认 zhi 命令可用
zhi --help

# 应显示命令列表
# 确认 workflow 相关命令存在
zhi help | grep workflow
# 应看到: workflow_execute, auto_script
```

---

## 2. CLI 预设工作流

知行内置 3 个预设工作流，可通过 CLI 交互菜单选择执行。

### 场景 1: 系统报告工作流

```bash
zhi workflow
```
**预期行为**:
- 显示 3 个预设选项：系统报告、音乐时光、摸鱼预警
- 选择 **1（系统报告）**
- 依次执行 4 个步骤：
  1. ✅ 检查系统 (system_status)
  2. ✅ 检查电池 (battery_status)
  3. ✅ 检查网络 (wifi_status)
  4. ✅ 今日日程 (calendar)
- 最终输出: `📋 工作流完成（4/4 步成功）`

**检查点**:
- 每一步有进度指示 `[1/4]` `[2/4]` ...
- 每步输出内容非空
- 步骤之间有 ~0.5s 间隔（不会瞬间完成）

### 场景 2: 音乐时光工作流

```bash
zhi workflow
```
选择 **2（音乐时光）**:

**预期行为**:
- 第 1 步：搜索并播放"经典"音乐
  - 如果本地 Music 曲库有歌 → ✅ 直接播放
  - 如果安装了 yt-dlp → 尝试从网易云下载并播放（约 10-15s）
  - 如果无 yt-dlp 且无本地曲库 → ❌ 快速跳过（不阻塞）
- 第 2 步：弹出系统通知"音乐已开始播放"

**检查点**:
- 如果第 1 步失败，第 2 步仍执行（错误恢复）
- 通知出现在 macOS 右上角
- **注意**: 音乐搜索依赖网络，首次使用可能需安装 yt-dlp（`brew install yt-dlp`）

### 场景 3: 摸鱼预警工作流

```bash
zhi workflow
```
选择 **3（摸鱼预警）**:

**预期行为**:
- 第 1 步：截屏
- 第 2 步：弹出通知"注意! 老板来了!"

**检查点**:
- 截图文件保存到 `~/Pictures/` 目录
- 通知显示正确文案

---

## 3. API 驱动工作流

通过 `workflow_execute` 命令直接传入 JSON 参数，测试边界条件。

### 场景 4: 基础多步工作流

```bash
zhi workflow_execute steps='[
  {"cmd":"system_status","desc":"系统状态"},
  {"cmd":"battery_status","desc":"电池状态"},
  {"cmd":"disk_monitor","desc":"磁盘监控"}
]'
```

**预期**: `📋 工作流完成（3/3 步成功）`

### 场景 5: 带参数的工作流

```bash
zhi workflow_execute steps='[
  {"cmd":"system_volume","params":{"level":30},"desc":"音量30"},
  {"cmd":"display_brightness","params":{"level":80},"desc":"亮度80"},
  {"cmd":"system_volume","params":{"level":50},"desc":"恢复音量50"}
]'
```

**预期**:
- 音量先降到 30 → 亮度调到 80 → 音量恢复 50
- 最终检查：确认音量不是 30 而是 50

### 场景 6: 带等待间隔的工作流

```bash
zhi workflow_execute steps='[
  {"cmd":"notification","params":{"text":"3秒后第二条"},"desc":"通知1","wait":1},
  {"cmd":"notification","params":{"text":"第二条通知"},"desc":"通知2","wait":3},
  {"cmd":"notification","params":{"text":"间隔3秒"},"desc":"通知3"}
]'
```

**预期**:
- 通知 1 出现 → 1 秒后 → 通知 2 出现 → 3 秒后 → 通知 3 出现
- `wait` 参数控制步骤间间隔

### 场景 7: 错误恢复测试

```bash
zhi workflow_execute steps='[
  {"cmd":"non_existent_cmd_xxx","desc":"这个命令不存在"},
  {"cmd":"notification","params":{"text":"错误后我仍执行了!"},"desc":"恢复成功"}
]'
```

**预期**:
- 第 1 步：❌ 未知命令（跳过）
- 第 2 步：✅ 恢复成功
- 最终：`📋 工作流完成（1/2 步成功）`
- **关键**: 第二步的通知仍会弹出

### 场景 8: 空步骤/边界条件

```bash
# 空步骤列表
zhi workflow_execute steps='[]'
# 预期: ❌ 需要 steps 参数

# 缺少 steps 参数
zhi workflow_execute
# 预期: ❌ 需要 steps 参数

# 超大步骤数（压力测试）
zhi workflow_execute steps='[
  {"cmd":"notification","params":{"text":"批量测试1"},"desc":"t1"},
  {"cmd":"notification","params":{"text":"批量测试2"},"desc":"t2"},
  {"cmd":"notification","params":{"text":"批量测试3"},"desc":"t3"},
  {"cmd":"notification","params":{"text":"批量测试4"},"desc":"t4"},
  {"cmd":"notification","params":{"text":"批量测试5"},"desc":"t5"}
]'
# 预期: 5/5 步成功
```

---

## 4. Electron 可视化编辑器

启动桌面应用，使用可视化方式构建和执行工作流。

### 场景 9: 启动 Electron 工作流编辑器

```bash
cd ~/workspace/knowagent-personal/electron-app
npx electron .
```

**预期**:
- 窗口打开
- 底部有工作流标签（Workflow / 工作流）
- 点击切换到工作流标签页

**首次打开检查点**:
- 左侧调色板显示 14 种步骤类型（分组：触发器、逻辑、数据、动作）
- 中间画布区域为空
- 右侧参数编辑区显示"选择一个步骤"
- 顶部工具栏：▶ 运行、💾 保存、📂 加载、🗑️ 清空、📋 导出 YAML

### 场景 10: 拖拽构建工作流

在左侧调色板中，依次点击以下步骤添加到画布：

| 顺序 | 步骤类型 | 参数 | 说明 |
|:---:|---------|------|------|
| 1 | 🌐 Navigate | url=`https://example.com` | 打开网页 |
| 2 | ⏳ Wait | seconds=`2` | 等待加载 |
| 3 | 👆 Click | target=`More information` | 点击链接 |
| 4 | 📸 Screenshot | (无参数) | 截图保存 |
| 5 | ✅ Assert | target=`Example Domain` | 验证页面文字 |

**预期**:
- 每次点击步骤类型，步骤出现在画布列表中
- 步骤带有序号、图标、颜色
- 点击某个步骤，右侧显示该步骤的参数编辑区
- 步骤计数显示 "5 步"

### 场景 11: 参数编辑与验证

1. 点击画布中的 **Navigate** 步骤
2. 右侧参数区出现 URL 输入框
3. 输入 `https://www.baidu.com`
4. 点击 **Assert** 步骤
5. 参数区出现 target 输入框
6. 输入 `百度`

**检查点**:
- 参数值被正确保存（点击其它步骤再回来，值还在）
- 参数输入框有 placeholder 提示
- 步骤在画布上显示已设置参数的摘要

### 场景 12: 运行工作流

1. 构建好上述 5 步工作流
2. 点击 **▶ 运行** 按钮

**预期**:
- 当前正在执行的步骤高亮或闪烁
- 执行完成后步骤全部标记 ✅ 或 ❌
- 如果 Chrome 未打开，Navigate 步骤可能失败
- 最终结果摘要显示 `✅ 5 步完成`

**检查点**:
- 运行过程中界面不卡死（异步执行）
- 失败步骤不影响后续步骤执行
- 结果清晰显示每步状态

### 场景 13: YAML 导出/导入

1. 构建一个 3 步工作流（如：Navigate → Wait → Screenshot）
2. 点击 **📋 导出 YAML**
3. 检查复制到剪贴板的 YAML 内容

**预期 YAML 格式**:
```yaml
steps:
  - action: navigate
    params:
      value: https://example.com
    name: 打开网页
  - action: wait
    params:
      seconds: 2
    name: 等待
  - action: screenshot
    name: 截图
```

4. 点击 **🗑️ 清空** 清空画布
5. 点击 **📂 加载** 导入刚才导出的 YAML
6. 检查画布是否恢复为之前的 3 步工作流

### 场景 14: 保存/加载工作流

1. 构建一个 3 步工作流
2. 点击 **💾 保存**
3. 在弹出的输入框中输入名称 "测试工作流"
4. 点击 **🗑️ 清空** 清空画布
5. 点击 **📂 加载**
6. 列表中应出现 "测试工作流"
7. 点击加载，画布恢复保存的工作流

**检查点**:
- 保存后即使关闭 Electron 再打开，保存的工作流仍在
- 可保存多个工作流
- 可删除已保存的工作流

### 场景 15: 社区版步骤限制

Community 版限制最多 5 步。测试限制：

1. 添加 5 个步骤
2. 尝试添加第 6 个步骤
3. **预期**: 弹出提示 "Community 版最多 5 步，升级 Pro 解锁"

---

## 5. 问题记录表

测试过程中发现问题时，记录到此表中：

| # | 场景 | 严重级别 | 问题描述 | 步骤 | 预期 | 实际 | 截图 |
|---|:----:|:-------:|---------|:----:|:----:|:----:|:----:|
|   |      | 🔴P0/🟡P1/🟠P2/🔵P3 | | | | | |
|   |      |         |         | | | | |
|   |      |         |         | | | | |

### 严重级别说明

| 级别 | 标签 | 说明 |
|:----:|:----:|------|
| 🔴 P0 | Critical | 崩溃、数据丢失、安全漏洞 |
| 🟡 P1 | High | 主要功能失效、工作流无法执行 |
| 🟠 P2 | Medium | 次要功能异常、边界条件错误 |
| 🔵 P3 | Low | 文案问题、颜色/样式、代码异味 |

---

## 快速执行脚本

如果需要一次性清除测试产生的临时文件：

```bash
# 清除测试截图
rm -f ~/Pictures/ka_screenshot_*.png

# 清除 Electron 缓存（谨慎)
# rm -rf ~/Library/Application\ Support/Electron
```
