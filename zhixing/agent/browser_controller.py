"""跨平台浏览器控制器 — macOS 用 AppleScript，Windows 用 Playwright。

自动化浏览器操作的统一接口。
"""

import os
import platform
import subprocess
import time
import re
import json

# ── 平台检测 ──────────────────────────────────

IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

# ── 浏览器检测 ────────────────────────────────

_playwright_available = False
try:
    import playwright
    _playwright_available = True
except ImportError:
    pass


def _find_chrome() -> str | None:
    """查找 Chrome 浏览器路径。"""
    if IS_WIN:
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
    elif IS_MAC:
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
    return None


# ── macOS AppleScript 控制器 ──────────────────


def _mac_osa(script: str) -> str:
    """执行 AppleScript，返回 stdout。"""
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception as e:
        return f"❌ {e}"


def _mac_js(js: str) -> str:
    """在 Chrome 当前标签页执行 JavaScript（macOS）。"""
    # 转义：JS 中的双引号需要转义
    escaped = js.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    script = f'''
    tell application "Google Chrome"
        set result to execute active tab of window 1 javascript "{escaped}"
        return result
    end tell'''
    return _mac_osa(script)


def _mac_get_url() -> str:
    """获取当前页面 URL（macOS）。"""
    return _mac_osa('''
    tell application "Google Chrome"
        return URL of active tab of window 1
    end tell''')


def _mac_get_title() -> str:
    """获取当前页面标题（macOS）。"""
    return _mac_osa('''
    tell application "Google Chrome"
        return title of active tab of window 1
    end tell''')


def _mac_click_text(text: str) -> bool:
    """在页面中按文字点击（macOS）。"""
    result = _mac_js(f"""
    (function(){{
        var all = document.querySelectorAll('a, button, input[type="submit"], input[type="button"], [role="button"], span, div');
        var lower = "{text}".toLowerCase();
        for (var i = 0; i < all.length; i++) {{
            var t = (all[i].innerText || all[i].value || all[i].getAttribute('title') || all[i].getAttribute('aria-label') || '').toLowerCase();
            if (t.indexOf(lower) !== -1) {{
                all[i].click();
                return "clicked";
            }}
        }}
        return "not found";
    }})()
    """)
    return "clicked" in result


def _mac_fill(label: str, value: str) -> bool:
    """在页面中找输入框并填入（macOS）。"""
    result = _mac_js(f"""
    (function(){{
        var inputs = document.querySelectorAll('input, textarea');
        var val = "{value}";
        for (var i = 0; i < inputs.length; i++) {{
            var el = inputs[i];
            var p = (el.placeholder || '').toLowerCase();
            var id = el.id || '';
            if (p.indexOf("{label.lower()}") !== -1 || id.indexOf("{label.lower()}") !== -1) {{
                el.value = val;
                el.dispatchEvent(new Event('input', {{bubbles:true}}));
                el.dispatchEvent(new Event('change', {{bubbles:true}}));
                return "filled";
            }}
        }}
        return "not found";
    }})()
    """)
    return "filled" in result


def _mac_get_html() -> str:
    """获取当前页面 HTML（macOS）。"""
    return _mac_js("document.body.innerHTML.substring(0, 50000)")


def _mac_get_text() -> str:
    """获取当前页面文本（macOS）。"""
    return _mac_js("document.body.innerText.substring(0, 50000)")


def _mac_get_elements() -> list[dict]:
    """获取页面上所有可交互元素（macOS）。"""
    raw = _mac_js("""
    (function(){
    var all = document.querySelectorAll('a, button, input, select, textarea, [onclick], [role="button"]');
    var found = [];
    for (var i = 0; i < all.length; i++) {
        var el = all[i];
        var t = (el.innerText || '').trim();
        if (!t) t = (el.getAttribute('title') || el.getAttribute('aria-label') || el.getAttribute('alt') || el.value || el.placeholder || '').trim();
        var tag = el.tagName;
        var rect = el.getBoundingClientRect();
        if (t && rect.width > 10) {
            found.push({t: t.substring(0, 60), g: tag});
        }
    }
    var seen = new Set();
    return JSON.stringify(found.filter(function(e){var k=e.t;if(seen.has(k))return false;seen.add(k);return true;}));
    })()
    """)
    try:
        return json.loads(raw)
    except:
        return []


# ── Windows Playwright 控制器 ─────────────────

_win_page = None
_win_browser = None


def _win_ensure_page():
    """确保 Playwright 页面已连接。"""
    global _win_page, _win_browser
    if _win_page is not None:
        try:
            _win_page.title()
            return True
        except:
            _win_page = None

    try:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()

        # 尝试连接已有 Chrome（通过 CDP）
        try:
            _win_browser = p.chromium.connect_over_cdp("http://localhost:9222")
            _win_page = _win_browser.contexts[0].pages[0]
        except:
            # 启动新浏览器
            chrome_path = _find_chrome()
            if chrome_path:
                _win_browser = p.chromium.launch(
                    headless=False,
                    executable_path=chrome_path,
                    args=["--remote-debugging-port=9222"],
                )
            else:
                _win_browser = p.chromium.launch(headless=False)
            _win_page = _win_browser.new_page()

        return True
    except Exception as e:
        print(f"[Playwright] 连接失败: {e}")
        return False


def _win_js(js: str) -> str:
    """在页面中执行 JavaScript（Windows）。"""
    if not _win_ensure_page():
        return "❌ 浏览器未连接"
    try:
        result = _win_page.evaluate(js)
        return str(result) if result is not None else ""
    except Exception as e:
        return f"❌ {e}"


def _win_get_url() -> str:
    return _win_page.url if _win_page else ""


def _win_get_title() -> str:
    if not _win_ensure_page():
        return ""
    return _win_page.title()


def _win_get_text() -> str:
    if not _win_ensure_page():
        return ""
    try:
        return _win_page.inner_text("body")[:50000]
    except:
        return ""


def _win_get_elements() -> list[dict]:
    if not _win_ensure_page():
        return []
    try:
        raw = _win_page.evaluate("""
        (function(){
        var all = document.querySelectorAll('a, button, input, select, textarea, [onclick], [role="button"]');
        var found = [];
        for (var i = 0; i < all.length; i++) {
            var el = all[i];
            var t = (el.innerText || '').trim();
            if (!t) t = (el.getAttribute('title') || el.getAttribute('aria-label') || el.getAttribute('alt') || el.value || el.placeholder || '').trim();
            var tag = el.tagName;
            var rect = el.getBoundingClientRect();
            if (t && rect.width > 10) {
                found.push({t: t.substring(0, 60), g: tag});
            }
        }
        var seen = new Set();
        return JSON.stringify(found.filter(function(e){var k=e.t;if(seen.has(k))return false;seen.add(k);return true;}));
        })()
        """)
        return json.loads(raw)
    except:
        return []


def _win_click_text(text: str) -> bool:
    if not _win_ensure_page():
        return False
    try:
        _win_page.click(f"text={text}", timeout=5000)
        return True
    except:
        # 备选方案：JS 点击
        try:
            result = _win_page.evaluate(f"""
            (function(){{
                var lower = "{text}".toLowerCase();
                var all = document.querySelectorAll('a, button, [role="button"], span, div');
                for (var i = 0; i < all.length; i++) {{
                    var t = (all[i].innerText || all[i].value || all[i].title || '').toLowerCase();
                    if (t.indexOf(lower) !== -1) {{
                        all[i].click();
                        return true;
                    }}
                }}
                return false;
            }})()
            """)
            return result is True
        except:
            return False


def _win_fill(label: str, value: str) -> bool:
    if not _win_ensure_page():
        return False
    try:
        _win_page.fill(f"input[placeholder*='{label}'], textarea[placeholder*='{label}']", value, timeout=5000)
        return True
    except:
        try:
            _win_page.evaluate(f"""
            (function(){{
                var inputs = document.querySelectorAll('input, textarea');
                for (var i = 0; i < inputs.length; i++) {{
                    var p = (inputs[i].placeholder || '').toLowerCase();
                    if (p.indexOf('{label.lower()}') !== -1) {{
                        inputs[i].value = '{value}';
                        inputs[i].dispatchEvent(new Event('input', {{bubbles:true}}));
                        return true;
                    }}
                }}
                return false;
            }})()
            """)
            return True
        except:
            return False


# ── 统一对外接口 ──────────────────────────────


def js(code: str) -> str:
    """在浏览器中执行 JavaScript。"""
    if IS_WIN and _playwright_available:
        return _win_js(code)
    return _mac_js(code)


def get_url() -> str:
    if IS_WIN and _playwright_available:
        return _win_get_url()
    return _mac_get_url()


def get_title() -> str:
    if IS_WIN and _playwright_available:
        return _win_get_title()
    return _mac_get_title()


def get_text() -> str:
    if IS_WIN and _playwright_available:
        return _win_get_text()
    return _mac_get_text()


def get_elements() -> list[dict]:
    """获取页面上所有可交互元素。"""
    if IS_WIN and _playwright_available:
        return _win_get_elements()
    return _mac_get_elements()


def click_text(text: str) -> bool:
    """按文字点击页面元素。"""
    if IS_WIN and _playwright_available:
        return _win_click_text(text)
    return _mac_click_text(text)


def fill(label: str, value: str) -> bool:
    """在输入框中填入内容。"""
    if IS_WIN and _playwright_available:
        return _win_fill(label, value)
    return _mac_fill(label, value)


def navigate(url: str):
    """导航到 URL。"""
    if IS_WIN and _playwright_available:
        if _win_ensure_page():
            try:
                _win_page.goto(url, timeout=30000)
            except:
                pass
    else:
        _mac_osa(f'''
        tell application "Google Chrome"
            set URL of active tab of window 1 to "{url}"
        end tell''')


def get_platform() -> str:
    """返回当前平台描述。"""
    if IS_WIN:
        return f"Windows + {'Playwright' if _playwright_available else '基础模式'}"
    return "macOS + AppleScript"


def is_connected() -> bool:
    """检查浏览器是否可连接。"""
    try:
        url = get_url()
        return bool(url)
    except:
        return False
