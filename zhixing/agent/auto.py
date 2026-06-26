"""视觉自动化 — 看屏幕、找文字、点击、输入。

Pro 功能，基于 macOS Vision Framework OCR + Accessibility API +
cliclick 实现「看→找→点→输」的视觉自动化闭环。

使用场景:
  - 网站信息注册
  - 表单自动填写
  - GUI 测试脚本执行
  - 重复性 UI 操作自动化
"""

import json
import os
import re
import subprocess
import time

import yaml

# ── 常量 ─────────────────────────────────────────────────

_BIN_DIR = os.path.expanduser("~/.zhixing/bin")
_SCREEN_OCR = os.path.join(_BIN_DIR, "screen_ocr")


# ── 工具函数 ─────────────────────────────────────────────


def _ensure_binary() -> str | None:
    """确保 screen_ocr 二进制已编译。"""
    if os.path.exists(_SCREEN_OCR):
        return _SCREEN_OCR
    # 尝试从项目目录编译
    project_bin = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "swift", "screen_ocr",
    )
    if os.path.exists(project_bin + ".swift"):
        try:
            subprocess.run(
                ["swiftc", "-O", "-o", project_bin, project_bin + ".swift"],
                capture_output=True, timeout=60,
            )
            os.makedirs(_BIN_DIR, exist_ok=True)
            subprocess.run(["cp", project_bin, _SCREEN_OCR], timeout=5)
            return _SCREEN_OCR
        except Exception:
            pass
    return None


def _screenshot(path: str = "", copy_to_clipboard: bool = True) -> str:
    """截图并返回路径。

    默认保存到 ~/Pictures/ 目录，文件名带时间戳。
    copy_to_clipboard: 是否同时复制到剪贴板（默认 True）
    """
    if not path:
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.expanduser(f"~/Pictures/ka_screenshot_{ts}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 保存到文件
    subprocess.run(["screencapture", path], capture_output=True, timeout=10)
    # 复制到剪贴板
    if copy_to_clipboard:
        subprocess.run(["screencapture", "-c"], capture_output=True, timeout=10)
    return path


def _ocr_image(path: str) -> dict | None:
    """对图片做 Vision OCR，返回 JSON 数据。"""
    binary = _ensure_binary()
    if not binary:
        return None
    try:
        r = subprocess.run(
            [binary, path, "--json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if r.returncode == 0 and r.stdout.strip():
            data = json.loads(r.stdout)
            return data
    except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def _copy_to_clipboard(text: str):
    """复制文本到 macOS 剪贴板。"""
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode("utf-8"), timeout=5)
    except Exception:
        pass


def _find_center(blocks: list[dict], target: str) -> tuple[int, int] | None:
    """在 OCR 结果中查找目标文字，返回屏幕坐标 (cx, cy)。"""
    target_lower = target.lower()
    for block in blocks:
        text = block.get("text", "")
        if target_lower in text.lower():
            # 取文字块的中间位置
            # x, y 是 OCR 返回的左上角坐标，加偏移作为点击点
            cx = block["x"] + 40  # 估算文字宽度的一半
            cy = block["y"] + 15  # 估算文字高度的一半
            return (cx, cy)
    return None


def _click_at(x: int, y: int) -> bool:
    """点击屏幕坐标。"""
    try:
        subprocess.run(
            ["cliclick", f"c:{x},{y}"],
            capture_output=True, timeout=5,
        )
        return True
    except Exception:
        return False


def _type_text(text: str):
    """在当前焦点输入文字。"""
    try:
        import shlex
        safe = text.replace("'", "'\\''")
        subprocess.run(
            ["cliclick", f"t:{safe}"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _press_key(key: str):
    """按键盘键。"""
    try:
        subprocess.run(
            ["cliclick", f"kp:{key}"],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


# ── 命令处理器 ───────────────────────────────────────────


def cmd_auto_find(params: dict) -> str:
    """🔍 在屏幕上查找文字，返回坐标。

    参数:
        text (str): 要查找的文字（支持模糊匹配）
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    text = params.get("text", "")
    if not text:
        return "❌ 需要 text 参数"

    path = _screenshot()
    data = _ocr_image(path)
    # 截图已保存到 ~/Downloads/，不再删除

    if not data:
        return "❌ Vision OCR 不可用（screen_ocr 未编译）"

    blocks = data.get("blocks", [])
    if not blocks:
        return f"🔍 屏幕上未找到文字「{text}」"

    matched = [b for b in blocks if text.lower() in b.get("text", "").lower()]

    if not matched:
        # 显示所有文字供参考
        all_texts = [b["text"] for b in blocks if b.get("text")]
        return (
            f"🔍 未找到「{text}」\n"
            f"   屏幕上的文字: {', '.join(all_texts[:10])}"
        )

    lines = [f"🔍 找到「{text}」— {len(matched)} 处:"]
    for i, b in enumerate(matched, 1):
        cx = b["x"] + 40
        cy = b["y"] + 15
        lines.append(f"  {i}. 「{b['text']}」→ ({cx}, {cy})")

    return "\n".join(lines)


def cmd_auto_click(params: dict) -> str:
    """👆 在屏幕上找到文字并点击。

    参数:
        text (str): 目标文字
        wait (int, optional): 点击后等待秒数，默认 0.5
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    text = params.get("text", "")
    wait = float(params.get("wait", 0.5))

    if not text:
        return "❌ 需要 text 参数"

    path = _screenshot()
    data = _ocr_image(path)
    # 截图已保存到 ~/Downloads/，不再删除

    if not data or not data.get("blocks"):
        return f"❌ 屏幕上未找到「{text}」"

    pos = _find_center(data["blocks"], text)
    if not pos:
        return f"👆 未找到「{text}」"

    _click_at(*pos)
    time.sleep(wait)
    return f"👆 已点击「{text}」→ ({pos[0]}, {pos[1]})"


def cmd_auto_type(params: dict) -> str:
    """⌨️ 找到文字标签，在旁边输入内容。

    参数:
        label (str): 标签文字（如「用户名」、「邮箱」）
        value (str): 要输入的内容
        wait (int, optional): 输入后等待秒数，默认 0.3
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    label = params.get("label", "")
    value = params.get("value", "")

    if not label or not value:
        return "❌ 需要 label 和 value 参数"

    wait = float(params.get("wait", 0.3))

    # 先截图找标签位置
    path = _screenshot()
    data = _ocr_image(path)
    # 截图已保存到 ~/Downloads/，不再删除

    if not data or not data.get("blocks"):
        return f"❌ 未找到「{label}」"

    # 找到标签，点击其右侧
    pos = _find_center(data["blocks"], label)
    if not pos:
        return f"❌ 未找到标签「{label}」"

    # 点击标签旁边的输入框位置（向右偏移）
    _click_at(pos[0] + 80, pos[1])
    time.sleep(0.3)
    _type_text(value)
    time.sleep(wait)

    return f"⌨️ 在「{label}」旁输入「{value}」"


def _hide_ka_button():
    """隐藏页面中的 🤖 按钮（跨平台）。"""
    _chrome_js("try{document.getElementById('ka-btn').style.display='none';document.getElementById('ka-panel').style.display='none'}catch(e){}")


def _show_ka_button():
    """显示 🤖 按钮（跨平台）。"""
    _chrome_js("try{var b=document.getElementById('ka-btn');if(b){b.style.removeProperty('display')}}catch(e){}")


def cmd_auto_screenshot(params: dict) -> str:
    """📸 截屏 + OCR 识别，显示所有文字及坐标。

    参数:
        hide_btn (bool, optional): 是否隐藏悬浮按钮，默认 true
        copy (bool, optional): 是否复制结果到剪贴板，默认 true
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    hide_btn = params.get("hide_btn", "true") in ("true", "True", "1", True)
    copy = params.get("copy", "true") in ("true", "True", "1", True)

    # 隐藏 🤖 按钮+面板
    if hide_btn:
        _hide_ka_button()
        time.sleep(0.5)

    path = _screenshot(copy_to_clipboard=copy)

    # 显示 🤖 按钮
    if hide_btn:
        _show_ka_button()

    data = _ocr_image(path)

    if not data:
        return "❌ Vision OCR 不可用"

    blocks = data.get("blocks", [])
    if not blocks:
        return "📸 屏幕分析完成，未识别到文字"

    w, h = data.get("width", 0), data.get("height", 0)
    lines = [f"📸 屏幕分析 ({w}x{h}) — {len(blocks)} 个文字块:"]
    full_text = []
    for i, b in enumerate(blocks, 1):
        lines.append(f"  {i}. ({b['x']:4d}, {b['y']:3d})  {b['text']}")
        full_text.append(b['text'])

    result = "\n".join(lines)
    if copy:
        result += f"\n\n✅ 图片已复制到剪贴板"
    return result


def cmd_auto_script(params: dict) -> str:
    """📋 执行自动化测试脚本（YAML 格式）。

    参数:
        path (str): YAML 脚本文件路径
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    script_path = params.get("path", "")
    if not script_path:
        return "❌ 需要 path 参数（YAML 脚本路径）"

    script_path = os.path.expanduser(script_path)
    if not os.path.isfile(script_path):
        return f"❌ 脚本文件不存在: {script_path}"

    try:
        with open(script_path, encoding="utf-8") as f:
            steps = yaml.safe_load(f)
    except Exception as e:
        return f"❌ 脚本读取失败: {e}"

    if not isinstance(steps, list):
        return "❌ 脚本格式错误：应为步骤列表"

    # 逐条执行
    results = []
    total = len(steps)
    for i, step in enumerate(steps, 1):
        action = step.get("action", "")
        target = step.get("target", "")
        value = step.get("value", "")
        name = step.get("name", "")
        wait = float(step.get("wait", 0.5))

        try:
            if action == "screenshot":
                p = _screenshot(os.path.expanduser(f"~/Pictures/ka_auto_{name or i}.png"))
                results.append(f"  [{i}/{total}] 📸 截图: {name or i}")
            elif action == "click":
                # 截图 + 找文字 + 点击
                sp = _screenshot()
                data = _ocr_image(sp)
                os.remove(sp)
                pos = _find_center(data["blocks"], target) if data else None
                if pos:
                    _click_at(*pos)
                    results.append(f"  [{i}/{total}] 👆 点击「{target}」")
                else:
                    results.append(f"  [{i}/{total}] ❌ 未找到「{target}」")
            elif action == "type":
                _type_text(value)
                results.append(f"  [{i}/{total}] ⌨️ 输入「{value}」")
            elif action == "press":
                _press_key(target)
                results.append(f"  [{i}/{total}] ⌨️ 按键「{target}」")
            elif action == "wait":
                time.sleep(float(target))
                results.append(f"  [{i}/{total}] ⏳ 等待 {target}s")
            elif action == "assert":
                sp = _screenshot()
                data = _ocr_image(sp)
                os.remove(sp)
                found = any(target.lower() in b.get("text", "").lower() for b in (data.get("blocks", []) if data else []))
                if found:
                    results.append(f"  [{i}/{total}] ✅ 断言通过: 「{target}」")
                else:
                    results.append(f"  [{i}/{total}] ❌ 断言失败: 未出现「{target}」")
            else:
                results.append(f"  [{i}/{total}] ⚠️ 未知操作: {action}")

            time.sleep(wait)
        except Exception as e:
            results.append(f"  [{i}/{total}] ❌ 异常: {e}")

    success = sum(1 for r in results if "❌" not in r and "⚠️" not in r)
    return (
        f"📋 自动化脚本执行完成  {success}/{total} 步成功\n"
        + "\n".join(results)
    )


# ── Web 浏览器自动化（Chrome AppleScript） ────────────────


from zhixing.agent.browser_controller import (
    js as _bc_js,
    click_text as _bc_click,
    fill as _bc_fill,
    get_url as _bc_url,
    get_title as _bc_title,
    get_text as _bc_text,
    get_elements as _bc_elements,
    navigate as _bc_navigate,
    get_platform as _bc_platform,
)


def _chrome_js(js: str) -> str:
    """跨平台执行浏览器 JavaScript。"""
    return _bc_js(js)


def _chrome_click(text: str) -> bool:
    """跨平台按文字点击页面元素。"""
    return _bc_click(text)


def _chrome_fill(label: str, value: str) -> bool:
    """跨平台在输入框中填入内容。"""
    return _bc_fill(label, value)


def cmd_auto_web(params: dict) -> str:
    """🌐 Chrome 网页自动化 — 导航/点击/填表/截图。

    直接在 Chrome 中操作，不需要屏幕可见。
    支持 YAML 脚本执行。

    参数:
        action (str): navigate | click | fill | screenshot | script
        url (str, optional): action=navigate 时的 URL
        text (str, optional): action=click 时的目标文字
        label (str, optional): action=fill 时的标签文字
        value (str, optional): action=fill 时的输入值
        path (str, optional): action=script 时的 YAML 脚本路径
        wait (int, optional): 操作后等待秒数，默认 1
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    action = params.get("action", "screenshot")
    url = params.get("url", "")
    text = params.get("text", "")
    label = params.get("label", "")
    value = params.get("value", "")
    script_path = params.get("path", "")
    wait = float(params.get("wait", 1))

    if action == "navigate":
        if not url:
            return "❌ navigate 需要 url 参数"
        osascript_cmd = f'''
        tell application "Google Chrome"
            set URL of active tab of window 1 to "{url}"
        end tell'''
        try:
            subprocess.run(["osascript", "-e", osascript_cmd], capture_output=True, timeout=10)
        except Exception as e:
            return f"❌ 导航失败: {e}"
        time.sleep(wait)
        return f"🌐 已导航到: {url}"

    if action == "click":
        if not text:
            return "❌ click 需要 text 参数"
        ok = _chrome_click(text)
        time.sleep(wait)
        return f"🌐 点击{'✅' if ok else '❌'}「{text}」"

    if action == "fill":
        if not label or not value:
            return "❌ fill 需要 label 和 value 参数"
        ok = _chrome_fill(label, value)
        time.sleep(wait)
        return f"🌐 {'✅' if ok else '❌'} 填入「{label}」=「{value}」"

    if action == "screenshot":
        # 隐藏终端 → 截图 → 恢复终端
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to set visible of process "Terminal" to false',
        ], capture_output=True, timeout=5)
        time.sleep(0.5)
        sp = _screenshot()  # 保存到 ~/Downloads/
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to set visible of process "Terminal" to true',
        ], capture_output=True, timeout=5)

        data = _ocr_image(sp)
        os.remove(sp)
        if not data or not data.get("blocks"):
            return "📸 截屏完成，未识别到文字"
        blocks = data["blocks"]
        lines = [f"📸 网页截图 ({data['width']}x{data['height']}) — {len(blocks)} 个文字块:"]
        for i, b in enumerate(blocks[:30], 1):
            lines.append(f"  {i}. {b['text']}")
        if len(blocks) > 30:
            lines.append(f"  ... 还有 {len(blocks)-30} 个")
        return "\n".join(lines)

    if action == "script":
        if not script_path:
            return "❌ script 需要 path 参数"
        script_path = os.path.expanduser(script_path)
        if not os.path.isfile(script_path):
            return f"❌ 脚本文件不存在: {script_path}"
        try:
            with open(script_path, encoding="utf-8") as f:
                steps = yaml.safe_load(f)
        except Exception as e:
            return f"❌ 脚本读取失败: {e}"
        if not isinstance(steps, list):
            return "❌ 脚本格式错误"
        results = []
        for i, step in enumerate(steps, 1):
            act = step.get("action", "")
            tgt = step.get("target", "")
            val = step.get("value", "")
            w = float(step.get("wait", 1))
            try:
                if act == "navigate":
                    _chrome_js(f"window.location.href='{val}'")
                    results.append(f"  [{i}] 🌐 导航: {val}")
                elif act == "click":
                    ok = _chrome_click(tgt)
                    results.append(f"  [{i}] {'✅' if ok else '❌'} 点击: {tgt}")
                elif act == "fill":
                    ok = _chrome_fill(tgt, val)
                    results.append(f"  [{i}] {'✅' if ok else '❌'} 填表: {tgt}={val}")
                elif act == "screenshot":
                    results.append(f"  [{i}] 📸 截图: {tgt or i}")
                elif act == "wait":
                    results.append(f"  [{i}] ⏳ 等待 {w}s")
                else:
                    results.append(f"  [{i}] ⚠️ 未知: {act}")
                time.sleep(w)
            except Exception as e:
                results.append(f"  [{i}] ❌ 异常: {e}")
        return "🌐 浏览器脚本完成\n" + "\n".join(results)

    return "❌ 未知 action: " + action


# ── KiKi 风格：任务规划 + 逐步执行 ─────────────────────


def _get_interactive_elements() -> list[dict]:
    """获取页面上所有可交互元素（含 title/aria-label）。"""
    raw = _chrome_js("""
    (function(){
    var all = document.querySelectorAll('a, button, input, select, textarea, [onclick], [role="button"], [tabindex]:not([tabindex="-1"])');
    var found = [];
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var t = (el.innerText || '').trim();
        if (!t) t = (el.getAttribute('title') || el.getAttribute('aria-label') || el.getAttribute('alt') || el.value || el.placeholder || '').trim();
        var tag = el.tagName;
        var rect = el.getBoundingClientRect();
        if (t && rect.width > 10) {
            found.push({t: t.substring(0, 60), g: tag, v: rect.left + ',' + rect.top});
        }
    }
    var seen = new Set();
    return JSON.stringify(found.filter(function(e){var k=e.t;if(seen.has(k))return false;seen.add(k);return true;}));
    })()
    """) or "[]"
    try:
        import json as _j
        return _j.loads(raw)
    except:
        return []


def _exec_step(action: str, target: str, value: str = "") -> str:
    """执行单个步骤，返回结果描述。"""
    try:
        if action == "click":
            ok = _chrome_click(target)
            time.sleep(0.5)
            return f"✅ 点击「{target}」" if ok else f"❌ 未找到「{target}」"
        elif action == "fill":
            ok = _chrome_fill(target, value)
            time.sleep(0.3)
            return f"✅ 填入「{target}」" if ok else f"❌ 未找到「{target}」"
        elif action == "navigate":
            _chrome_js(f"window.location.href='{value}'")
            time.sleep(2)
            return f"✅ 导航到 {value[:50]}"
        elif action == "type":
            _type_text(value)
            time.sleep(0.3)
            return f"✅ 输入「{value}」"
        elif action == "press":
            _press_key(value)
            time.sleep(0.3)
            return f"✅ 按键「{value}」"
        elif action == "wait":
            time.sleep(float(target))
            return f"⏳ 等待 {target}s"
        elif action == "screenshot":
            return "📸 已截屏"
        else:
            return f"⚠️ 未知操作: {action}"
    except Exception as e:
        return f"❌ 异常: {e}"


def cmd_auto_plan(params: dict) -> str:
    """🎯 KiKi 风格 — 自动分解任务并逐步执行。

    参数:
        task (str): 任务描述，如「在 Windchill 中创建新物料」
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    task = params.get("task", params.get("text", params.get("keyword", "")))
    if not task:
        return "❌ 需要 task 参数"

    url = _chrome_js("window.location.href") or ""
    title = _chrome_js("document.title") or ""
    elements = _get_interactive_elements()

    # ── 处理创建类型选择（用户点击类型按钮后） ────
    if task.startswith("创建类型 "):
        parts = task.split(" ", 2)
        if len(parts) >= 2 and "|" in parts[1]:
            type_value, type_label = parts[1].split("|", 1)
            # 选择下拉框
            _chrome_js(f"""
            (function(){{
            var sel = document.querySelector('select');
            if (!sel) return;
            sel.value = '{type_value}';
            sel.dispatchEvent(new Event('change', {{bubbles: true}}));
            }})()
            """)
            time.sleep(0.5)
            # 点击完成
            _chrome_click("完成")
            time.sleep(1)
            return f"✅ 已选择类型「{type_label}」并提交创建"
        return "❌ 参数错误"

    # ── 检测是否在新建部件表单页面 ──────────────
    if "createPartWizard" in url or "新建部件" in title:
        # 获取类型选项
        options_raw = _chrome_js("""
        (function(){
        var sel = document.querySelector('select');
        if (!sel) return '[]';
        var opts = [];
        for (var i = 1; i < sel.options.length; i++) {
            opts.push({label: sel.options[i].text, value: sel.options[i].value});
        }
        return JSON.stringify(opts);
        })()
        """) or "[]"
        import json as _j2
        try:
            type_opts = _j2.loads(options_raw)
        except:
            type_opts = []
        if type_opts:
            options = []
            for opt in type_opts:
                label = opt.get("label", "")
                value = opt.get("value", "")
                options.append({
                    "label": f"📦 {label}",
                    "command": f"创建类型 {value}|{label}",
                })
            return _j2.dumps({
                "type": "interactive",
                "message": f"📋 新建部件 — 请选择物料类型：",
                "options": options,
            }, ensure_ascii=False)

    # ── 任务识别与步骤规划 ─────────────────────
    task_lower = task.lower()
    steps = []

    # 规则: 创建物料/零件/部件
    if any(k in task_lower for k in ["创建物料", "新建物料", "创建零件", "新增零件", "创建部件"]):
        steps = [
            ("click", "操作", ""),
            ("click", "新建", ""),
            ("click", "新建部件", ""),
        ]
    # 规则: 搜索零件
    elif any(k in task_lower for k in ["搜索零件", "查找零件", "搜索部件", "查询"]):
        kw = task_lower.replace("搜索", "").replace("查找", "").replace("查询", "").replace("零件", "").replace("物料", "").strip()
        steps = [
            ("click", "搜索", ""),
            ("fill", "搜索", kw or "零件"),
            ("press", "enter", ""),
        ]
    # 规则: 提交审批/提交任务
    elif any(k in task_lower for k in ["提交审批", "提交任务", "提交更改"]):
        steps = [
            ("click", "操作", ""),
            ("click", "提交", ""),
        ]
    # 规则: Windchill 打开产品结构
    elif any(k in task_lower for k in ["打开产品", "产品结构", "浏览产品"]):
        steps = [
            ("click", "产品", ""),
            ("click", "主机物料库", ""),
            ("click", "01 部件", ""),
        ]
    else:
        # 未匹配: 先试 LLM 对话
        try:
            from zhixing.config import Config
            from zhixing.agent.llm import LLMClient
            _cfg = Config()
            _llm = LLMClient(_cfg)
            _avail, _ = _llm.check_available()
            if _avail:
                _resp = _llm.chat([
                    {"role": "system", "content": "你是知行智能助手，可以帮助用户完成电脑操作。请简短回答（80字以内）。"},
                    {"role": "user", "content": task},
                ])
                _reply = _resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                if _reply:
                    return _reply.strip()
        except Exception:
            pass

        # 未匹配且 LLM 不可用: 显示可选操作类型
        suggestions = [
            ("📦 创建物料", "帮我 创建物料"),
            ("🔍 搜索零件", "帮我 搜索零件"),
            ("📋 待办列表", "待办列表"),
            ("📸 截屏分析", "看看"),
            ("⚡ 系统状态", "状态"),
        ]
        # 加上来自页面的可操作元素
        page_actions = []
        if elements:
            for e in elements[:8]:
                tag = e['t'][:20]
                page_actions.append((f"点击「{tag}」", f"点击 {e['t']}"))
        opts = suggestions + page_actions
        return json.dumps({
            "type": "interactive",
            "message": f"🎯 任务: {task}\n📋 当前: {title}\n\n请选择操作类型：",
            "options": [{"label": l, "command": c} for l, c in opts[:12]],
        }, ensure_ascii=False)

    # ── 逐步执行 ──────────────────────────────
    result_lines = [f"🎯 任务: {task}", f"📋 共 {len(steps)} 步", ""]
    success = True
    for i, (action, target, value) in enumerate(steps, 1):
        result = _exec_step(action, target, value)
        status = "✅" if "✅" in result else "❌"
        if "❌" in result:
            success = False
        result_lines.append(f"  [{i}/{len(steps)}] {result}")
        if "❌" in result:
            result_lines.append(f"  ⚠️ 当前页面可能没有「{target}」按钮")
            # 显示可用的按钮
            btns = [e["t"] for e in elements if e["g"] in ("BUTTON", "A")]
            if btns:
                result_lines.append(f"  💡 可选按钮: {', '.join(btns[:10])}")
            break

    result_lines.append("")
    if success:
        result_lines.append("🎉 任务执行完成")
    else:
        result_lines.append("📌 输入具体步骤手动操作")

    return "\n".join(result_lines)


# ── 智能页面操作（分析→找入口→确认→执行） ──────────────


def cmd_auto_exec(params: dict) -> str:
    """🤖 智能页面操作 — 分析当前页面，找到操作入口，确认后执行。

    参数:
        task (str): 要做的事情描述，如「创建物料」「提交订单」
        execute (str): "true" 时直接执行匹配的操作
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("visual_auto")
    if guard is not None:
        return guard

    task = params.get("task", params.get("text", params.get("keyword", "")))
    execute_mode = params.get("execute", "false") in ("true", "True", "1", True)

    if not task:
        return "❌ 需要 task 参数（描述你要做什么）"

    # 提取页面上的可操作元素（含 title/aria-label 等属性）
    elements = _chrome_js("""
    (function(){
    var all = document.querySelectorAll('a, button, input[type="submit"], input[type="button"], [role="button"], select, textarea, [onclick], img');
    var found = [];
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        // 获取名称：优先 innerText > title > aria-label > alt > value > placeholder > data-id > className
        var t = (el.innerText || '').trim();
        if (!t) t = (el.getAttribute('title') || el.getAttribute('aria-label') || el.getAttribute('alt') || el.value || el.placeholder || el.getAttribute('data-id') || el.className || '').trim();
        var tag = el.tagName;
        var type = el.type || '';
        var rect = el.getBoundingClientRect();
        if (t && rect.width > 10) {
            found.push({text: t.substring(0, 60), tag: tag, type: type});
        }
    }
    // 去重
    var seen = new Set();
    return JSON.stringify(found.filter(function(e){var k=e.text;if(seen.has(k))return false;seen.add(k);return true;}));
    })()
    """) or "[]"

    import json as _json
    try:
        el_list = _json.loads(elements)
    except:
        el_list = []

    # 用关键词匹配
    task_keywords = [kw for kw in task.lower().split() if len(kw) > 1]
    matched = []
    for el in el_list:
        text_lower = el.get("text", "").lower()
        if any(kw in text_lower for kw in task_keywords):
            matched.append(el)

    url = _chrome_js("window.location.href") or ""
    title = _chrome_js("document.title") or ""

    # 执行模式：直接点击最佳匹配
    if execute_mode:
        if matched:
            target = matched[0]["text"]
            _chrome_click(target)
            return f"✅ 已执行: 点击「{target}」"
        # 无匹配时找第一个按钮
        buttons = [e for e in el_list if e["tag"] in ("BUTTON", "A") and len(e["text"]) > 1]
        if buttons:
            target = buttons[0]["text"]
            _chrome_click(target)
            return f"✅ 已执行: 点击「{target}」"
        return "❌ 未找到可执行的操作"

    # 分析模式：展示并确认
    lines = [f"📋 当前页面: {title}", f"🔗 {url[:80]}", ""]
    if matched:
        lines.append(f"🔍 找到 {len(matched)} 个匹配入口:")
        lines.extend(f"  ✅ {e['text']}" for e in matched[:8])
    elif el_list:
        lines.append(f"🔍 未找到直接匹配，页面可操作元素 ({len(el_list)} 个):")
        lines.extend(f"  • {e['text']}" for e in el_list[:15])
    else:
        lines.append("⚠️ 页面未检测到可操作元素")

    lines.append("")
    if matched:
        lines.append(f"📌 输入「确认」执行: 点击「{matched[0]['text']}」")
    lines.append("📌 或输入具体指令")
    return "\n".join(lines)


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "auto_find": cmd_auto_find,
    "auto_click": cmd_auto_click,
    "auto_type": cmd_auto_type,
    "auto_screenshot": cmd_auto_screenshot,
    "auto_script": cmd_auto_script,
    "auto_web": cmd_auto_web,
    "auto_exec": cmd_auto_exec,
    "auto_plan": cmd_auto_plan,
}

TOOL_SCHEMAS: dict = {
    "auto_plan": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "任务描述，如「创建物料」「搜索零件」"},
        },
        "required": ["task"],
    },
    "auto_exec": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "要做的事情，如「创建物料」「提交订单」"},
        },
        "required": ["task"],
    },
    "auto_web": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "fill", "screenshot", "script"],
                "description": "操作: navigate=导航, click=点击, fill=填表, screenshot=截图验证, script=执行脚本",
            },
            "url": {"type": "string", "description": "导航 URL（action=navigate）"},
            "text": {"type": "string", "description": "目标文字（action=click）"},
            "label": {"type": "string", "description": "标签文字（action=fill）"},
            "value": {"type": "string", "description": "输入值（action=fill / navigate）"},
            "path": {"type": "string", "description": "YAML 脚本路径（action=script）"},
            "wait": {"type": "number", "description": "等待秒数，默认 1"},
        },
        "required": ["action"],
    },
    "auto_find": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要查找的文字"},
        },
        "required": ["text"],
    },
    "auto_click": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要点击的文字"},
            "wait": {"type": "number", "description": "点击后等待秒数，默认0.5"},
        },
        "required": ["text"],
    },
    "auto_type": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "标签文字（如用户名）"},
            "value": {"type": "string", "description": "要输入的内容"},
            "wait": {"type": "number", "description": "输入后等待秒数，默认0.3"},
        },
        "required": ["label", "value"],
    },
    "auto_screenshot": {
        "type": "object",
        "properties": {},
    },
    "auto_script": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "YAML 脚本路径"},
        },
        "required": ["path"],
    },
}
