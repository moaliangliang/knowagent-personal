"""用户转化漏斗 — 非侵入式的 Star / 赞助 / Pro 提示。

追踪启动次数和提示状态，状态保存在 ~/.zhixing/funnel.json。
完全本地、无网络请求、不收集任何个人信息。

支付平台（混合方案）:
  🇨🇳 爱发电 — https://afdian.com/a/你的ID  （替换为实际地址）
  🌍 Lemon Squeezy — https://你的产品.lemonsqueezy.com（替换为实际地址）
"""

import json
import os
import webbrowser

from zhixing.config import CONFIG_DIR

FUNNEL_FILE = os.path.join(CONFIG_DIR, "funnel.json")

# ── 链接配置 ─────────────────────────────────────────────
# 使用时替换为实际注册后的地址

GITHUB_URL = "https://github.com/zhixing-ai/zhixing"

# 🇨🇳 中国用户支付入口（爱发电 / 面包多 / 微信）
SPONSOR_URL_CN = "https://afdian.com/a/moaliangliang"

# 🌍 全球用户支付入口（Lemon Squeezy / Gumroad）
SPONSOR_URL_EN = "https://moaliangliang.lemonsqueezy.com"


def _sponsor_url(lang: str = "zh") -> str:
    """根据系统语言返回对应支付链接。"""
    if lang == "zh":
        return SPONSOR_URL_CN
    return SPONSOR_URL_EN


# ── 状态管理 ─────────────────────────────────────────────

DEFAULT_STATE = {
    "launch_count": 0,
    "star_prompt_shown": False,
    "sponsor_prompt_shown": False,
    "pro_prompt_shown": False,
    "dismissed": False,
}


def _load() -> dict:
    try:
        with open(FUNNEL_FILE) as f:
            state = json.load(f)
        for k, v in DEFAULT_STATE.items():
            state.setdefault(k, v)
        return state
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_STATE)


def _save(state: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(FUNNEL_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def increment_launch() -> dict:
    state = _load()
    state["launch_count"] += 1
    _save(state)
    return state


# ── 漏斗提示 ─────────────────────────────────────────────


def get_funnel_message(state: dict, lang: str = "zh") -> str | None:
    """根据当前状态判断是否需要展示提示。"""
    if state.get("dismissed"):
        return None

    launches = state.get("launch_count", 0)

    # ── Star 提示：第 3 次启动 ──────────────────────────
    if launches >= 3 and not state.get("star_prompt_shown"):
        state["star_prompt_shown"] = True
        _save(state)
        if lang == "zh":
            return (
                "  ⭐ 喜欢知行 (ZhiXing)？欢迎在 GitHub 点个 Star 支持！\n"
                f"     {GITHUB_URL}\n"
                "     输入 \x1b[1mstar\x1b[0m 打开，或 \x1b[1mdismiss\x1b[0m 不再提示"
            )
        return (
            "  ⭐ Like 知行 (ZhiXing)? Give it a Star on GitHub!\n"
            f"     {GITHUB_URL}\n"
            "     Type \x1b[1mstar\x1b[0m to open, or \x1b[1mdismiss\x1b[0m to hide"
        )

    # ── 赞助提示：第 10 次启动 ─────────────────────────
    if launches >= 10 and not state.get("sponsor_prompt_shown"):
        url = _sponsor_url(lang)
        if not url:
            return None
        state["sponsor_prompt_shown"] = True
        _save(state)
        if lang == "zh":
            return (
                "  ☕ 如果这个工具帮你省了时间，欢迎赞助支持持续开发！\n"
                "     输入 \x1b[1msponsor\x1b[0m 查看详情，或 \x1b[1mdismiss\x1b[0m 不再提示"
            )
        return (
            "  ☕ If this tool saved you time, consider sponsoring development!\n"
            "     Type \x1b[1msponsor\x1b[0m for details, or \x1b[1mdismiss\x1b[0m to hide"
        )

    # ── Pro 升级提示：第 20 次启动（如果还没激活） ────
    if launches >= 20 and not state.get("pro_prompt_shown"):
        from zhixing.agent.pro import is_pro
        if not is_pro():
            state["pro_prompt_shown"] = True
            _save(state)
            if lang == "zh":
                return (
                    "  💎 用了这么久了，升级 Pro 解锁增强番茄钟等更多功能！\n"
                    "     输入 \x1b[1mpro\x1b[0m 查看，或 \x1b[1mdismiss\x1b[0m 不再提示"
                )
            return (
                "  💎 Been using this a while? Upgrade to Pro for enhanced features!\n"
                "     Type \x1b[1mpro\x1b[0m to view, or \x1b[1mdismiss\x1b[0m to hide"
            )

    return None


def get_state() -> dict:
    return _load()


# ── 页面跳转 ─────────────────────────────────────────────


def open_github():
    webbrowser.open(GITHUB_URL)


def open_sponsor(lang: str = "zh"):
    """根据语言打开对应的支付页面。"""
    url = _sponsor_url(lang)
    if url:
        webbrowser.open(url)


def get_sponsor_text(lang: str = "zh") -> str:
    """返回赞助/购买信息文本。"""
    cn_url = SPONSOR_URL_CN
    en_url = SPONSOR_URL_EN

    if lang == "zh":
        lines = [
            "☕ \x1b[1m支持知行 (ZhiXing) 开发\x1b[0m",
            "",
            "你可以通过以下方式支持这个项目：",
            "",
            f"  \x1b[96m⭐\x1b[0m \x1b[1mGitHub Star\x1b[0m — 让更多人发现",
            f"     {GITHUB_URL}",
            "",
            f"  \x1b[93m❤️\x1b[0m \x1b[1m爱发电\x1b[0m — ¥39/年 或 ¥99 永久 Pro License（中国大陆）",
            f"     {cn_url}" if cn_url else "",
            "",
            f"  \x1b[93m🌍\x1b[0m \x1b[1mLemon Squeezy\x1b[0m — $19/year · $49 lifetime Pro License（Global）",
            f"     {en_url}" if en_url else "",
            "",
            "\x1b[2m你的支持让开源项目持续前进 🚀\x1b[0m",
        ]
    else:
        lines = [
            "☕ \x1b[1mSupport 知行 (ZhiXing) Development\x1b[0m",
            "",
            "You can support this project by:",
            "",
            f"  \x1b[96m⭐\x1b[0m \x1b[1mGitHub Star\x1b[0m — Help others discover",
            f"     {GITHUB_URL}",
            "",
            f"  \x1b[93m🌍\x1b[0m \x1b[1mLemon Squeezy\x1b[0m — $9/year · $19 lifetime Pro License",
            f"     {en_url}" if en_url else "",
            "",
            f"  \x1b[93m❤️\x1b[0m \x1b[1m爱发电 (Aifadian)\x1b[0m — ¥39/year · ¥99 lifetime (China)",
            f"     {cn_url}" if cn_url else "",
            "",
            "\x1b[2mYour support keeps open source moving forward 🚀\x1b[0m",
        ]
    return "\n".join(lines)


def set_dismissed():
    state = _load()
    state["dismissed"] = True
    _save(state)
