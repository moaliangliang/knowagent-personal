"""用户转化漏斗 — 非侵入式的 Star / 赞助提示。

追踪启动次数和提示状态，状态保存在 ~/.knowagent/funnel.json。
完全本地、无网络请求、不收集任何个人信息。
"""

import json
import os
import webbrowser

from knowagent_personal.config import CONFIG_DIR

FUNNEL_FILE = os.path.join(CONFIG_DIR, "funnel.json")

# GitHub 仓库地址（来自 pyproject.toml）
GITHUB_URL = "https://github.com/knowagent/knowagent-personal"

# 赞助页地址（可修改为你实际启用的赞助平台链接为空字符串则跳过赞助提示）  # noqa
SPONSOR_URL = "https://github.com/sponsors/knowagent"

DEFAULT_STATE = {
    "launch_count": 0,
    "star_prompt_shown": False,
    "sponsor_prompt_shown": False,
    "dismissed": False,
}


def _load() -> dict:
    """读取漏斗状态，不存在时返回默认值。"""
    try:
        with open(FUNNEL_FILE) as f:
            state = json.load(f)
        for k, v in DEFAULT_STATE.items():
            state.setdefault(k, v)
        return state
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_STATE)


def _save(state: dict):
    """持久化漏斗状态。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(FUNNEL_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def increment_launch() -> dict:
    """启动计数 +1，返回更新后的状态。"""
    state = _load()
    state["launch_count"] += 1
    _save(state)
    return state


def get_funnel_message(state: dict, lang: str = "zh") -> str | None:
    """根据当前状态判断是否需要展示提示。

    Args:
        state: funnel 状态字典。
        lang: "zh" 或 "en"。

    Returns:
        提示文本（含 ANSI 颜色），如果无需展示则返回 None。
    """
    if state.get("dismissed"):
        return None

    launches = state.get("launch_count", 0)

    # ── Star 提示：第 3 次启动，仅一次 ──────────────────
    if launches >= 3 and not state.get("star_prompt_shown"):
        state["star_prompt_shown"] = True
        _save(state)
        if lang == "zh":
            return (
                "  ⭐ 喜欢 Mac Agent Personal？欢迎在 GitHub 点个 Star 支持！\n"
                f"     {GITHUB_URL}\n"
                "     输入 \x1b[1mstar\x1b[0m 打开页面，或输入 \x1b[1mdismiss\x1b[0m 不再提示"
            )
        else:
            return (
                "  ⭐ Like Mac Agent Personal? Give it a Star on GitHub!\n"
                f"     {GITHUB_URL}\n"
                "     Type \x1b[1mstar\x1b[0m to open, or \x1b[1mdismiss\x1b[0m to hide"
            )

    # ── 赞助提示：第 10 次启动，仅一次 ─────────────────
    if launches >= 10 and not state.get("sponsor_prompt_shown"):
        if not SPONSOR_URL:
            return None  # 未配置赞助链接时跳过
        state["sponsor_prompt_shown"] = True
        _save(state)
        if lang == "zh":
            return (
                "  ☕ 如果这个工具帮你省了时间，欢迎赞助支持持续开发！\n"
                f"     输入 \x1b[1msponsor\x1b[0m 了解详情，或输入 \x1b[1mdismiss\x1b[0m 不再提示"
            )
        else:
            return (
                "  ☕ If this tool saved you time, consider sponsoring development!\n"
                "     Type \x1b[1msponsor\x1b[0m for details, or \x1b[1mdismiss\x1b[0m to hide"
            )

    return None


def get_state() -> dict:
    """公开读取当前状态。"""
    return _load()


def open_github():
    """在浏览器中打开 GitHub 仓库。"""
    webbrowser.open(GITHUB_URL)


def open_sponsor():
    """在浏览器中打开赞助页面。"""
    if SPONSOR_URL:
        webbrowser.open(SPONSOR_URL)


def get_sponsor_text(lang: str = "zh") -> str:
    """返回赞助信息文本，供 ka sponsor 命令使用。"""
    if lang == "zh":
        lines = [
            "☕ \x1b[1m支持 Mac Agent Personal 开发\x1b[0m",
            "",
            "如果你喜欢这个工具，可以通过以下方式支持：",
            "",
            f"  \x1b[96m⭐\x1b[0m \x1b[1mGitHub Star\x1b[0m — 让更多人发现这个项目",
            f"     {GITHUB_URL}",
        ]
        if SPONSOR_URL:
            lines += [
                "",
                f"  \x1b[93m❤️\x1b[0m \x1b[1m赞助\x1b[0m — 支持持续开发和维护",
                f"     {SPONSOR_URL}",
            ]
        lines += [
            "",
            "\x1b[2m你的支持是开源项目持续前进的动力 🚀\x1b[0m",
        ]
    else:
        lines = [
            "☕ \x1b[1mSupport Mac Agent Personal Development\x1b[0m",
            "",
            "If you find this tool useful, here's how to help:",
            "",
            f"  \x1b[96m⭐\x1b[0m \x1b[1mGitHub Star\x1b[0m — Help others discover the project",
            f"     {GITHUB_URL}",
        ]
        if SPONSOR_URL:
            lines += [
                "",
                f"  \x1b[93m❤️\x1b[0m \x1b[1mSponsor\x1b[0m — Support ongoing development",
                f"     {SPONSOR_URL}",
            ]
        lines += [
            "",
            "\x1b[2mYour support keeps open source moving forward 🚀\x1b[0m",
        ]
    return "\n".join(lines)


def set_dismissed():
    """标记用户已选择不再提示。"""
    state = _load()
    state["dismissed"] = True
    _save(state)
