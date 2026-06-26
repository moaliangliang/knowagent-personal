# 知行 Workflow 测试指南

## 前置条件

```bash
# 1. 确保在项目根目录
cd ~/workspace/knowagent-personal

# 2. 确保包已安装
pip install -e .
```

---

## 一、运行自动化测试（共 17 个场景）

### 方式 A：一键运行全部

```bash
python3 tests/test_workflow.py
```

预期输出结尾：
```
============================================================
  结果: 17/17 通过
============================================================
```

### 方式 B：pytest 运行（带详细输出）

```bash
python3 -m pytest tests/test_workflow.py -v
```

### 方式 C：只运行某个场景

```bash
# 按场景名过滤
python3 -m pytest tests/test_workflow.py -v -k "basic"
python3 -m pytest tests/test_workflow.py -v -k "preset"
python3 -m pytest tests/test_workflow.py -v -k "yaml"
```

---

## 二、手动测试场景

### 场景 1：CLI 工作流预设

```bash
zhi workflow
```

应该看到 3 个预设：
- 系统报告
- 音乐时光
- 摸鱼预警

选择序号执行，观察步骤是否按顺序执行。

### 场景 2：工作流命令

```bash
# 直接在工作流编辑器中测试
# 打开 Electron 桌面窗口
cd ~/workspace/knowagent-personal/electron-app
npx electron .

# 切换到"工作流"标签
# 拖拽步骤到画布
# 点击 ▶ 运行
```

### 场景 3：auto_script YAML 脚本

```yaml
# 创建测试脚本文件 /tmp/test_workflow.yaml
steps:
  - action: screenshot
    name: 第1步-截图
  - action: wait
    value: 1
  - action: screenshot
    name: 第2步-截图
```

```bash
# 通过命令行执行
zhi auto_script path=/tmp/test_workflow.yaml
```

### 场景 4：多步骤参数工作流

```bash
zhi workflow_execute steps='[{"cmd":"system_volume","params":{"level":30},"desc":"音量30"},{"cmd":"system_volume","params":{"level":50},"desc":"音量50"}]'
```

应看到进度显示 `1/2 → 2/2`，音量先设为 30 再设为 50。

### 场景 5：音乐搜索工作流

```bash
zhi 播放周杰伦的歌
```

应通过网易云音乐完整播放。

---

## 三、测试截图

测试完成后，截图保存在：

```
tests/screenshots/
├── wf_test_results.png    # 17 场景测试结果
└── wf_cli.png             # CLI 工作流界面
```

如需重新截图：

```bash
# 运行测试 + 截取结果
python3 tests/test_workflow.py
screencapture -x tests/screenshots/wf_test_results.png

# 截取 CLI 工作流界面
zhi workflow
screencapture -x tests/screenshots/wf_cli.png
```

---

## 四、测试场景详解

| 编号 | 场景名 | 测试内容 | 预期结果 |
|------|--------|----------|---------|
| 1 | 命令注册 | `workflow_execute` / `auto_script` 在 COMMANDS 中 | 注册成功 |
| 2 | 预设存在 | 3 个 CLI 预设工作流 | 全部存在 |
| 3 | 预设结构 | 每个预设步骤包含 cmd + desc | 结构完整 |
| 4 | 基础执行 | 两个系统命令按顺序执行 | 进度显示 1/2 → 2/2 |
| 5 | 空步骤 | 传入空步骤列表 | 报错提示 |
| 6 | 无效命令 | 传入不存在的命令名 | 跳过并继续 |
| 7 | 参数传递 | 带参命令如 `system_volume level=50` | 参数生效 |
| 8 | 音乐搜索 | 搜索周杰伦 | 返回结果 |
| 9 | Harness 事件 | EventBus.on/emit 正常 | 方法存在 |
| 10 | 权限级别 | workflow_execute 权限 | DESTRUCTIVE 或 COMMANDS 模式 |
| 11 | YAML 解析 | 解析 4 步 YAML 脚本 | 步骤结构正确 |
| 12 | 步骤类型 | workflow.js 定义的 14 种类型 | 全部存在 |
| 13 | YAML 导出 | workflow.js 导出功能 | toYaml 函数存在 |
| 14 | 多步顺序 | 音量 30 → 50 顺序执行 | 最终音量 50 |
| 15 | 错误恢复 | 失败步骤后继续执行后续 | 音量仍被设置 |
| 16 | 预设命令 | 预设中的所有命令在 COMMANDS 中 | 全部有效 |
| 17 | 步骤计数 | 预设总步骤数 | >= 6 |

---

## 五、常见问题

**Q: 测试报错 `ModuleNotFoundError: No module named 'zhixing'`**

```bash
pip install -e .
```

**Q: Electron 窗口打不开**

```bash
cd electron-app && npx electron .
```

**Q: 截图命令不可用**

```bash
# screencapture 是 macOS 自带命令，无需安装
# 如果没有权限，在 Terminal 设置中允许屏幕录制
```

**Q: 部分测试因网络问题失败**

场景 5（音乐搜索）和场景 4（wifi_status）依赖外部服务。如果网络不可用会失败，不影响其他场景。

**Q: 如何添加新的测试场景**

在 `tests/test_workflow.py` 中添加新的 `test_*` 函数，然后在 `tests` 列表末尾追加 `("场景名", 函数名)`。
