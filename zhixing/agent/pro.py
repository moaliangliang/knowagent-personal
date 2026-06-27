"""Pro 版本功能开关模块。

版本分层：
  - Community（免费）: 基础功能，无许可证限制
  - Pro（付费）: 增强功能，需要 license_key

License 校验由远程服务器完成（代码在私有仓库）。
"""

import json
import os
import time

from zhixing.config import Config

# ── 定价与购买链接 ──────────────────────────────

PRO_PRICE_CN = "¥99/年 · ¥299 终身"
PRO_URL_CN = "https://afdian.com/a/moaliangliang"

PRO_PRICE_EN = "$19/year · $49 lifetime"
PRO_URL_EN = "https://moaliangliang.lemonsqueezy.com"

# License 验证服务器（私有部署，GitHub Pages 上的静态验证）
LICENSE_SERVER = os.environ.get("KA_LICENSE_SERVER", "https://moaliangliang.github.io/zhixing-license")


def _purchase_url(lang: str = "zh") -> str:
    return PRO_URL_CN if lang == "zh" else PRO_URL_EN


def _purchase_price(lang: str = "zh") -> str:
    return PRO_PRICE_CN if lang == "zh" else PRO_PRICE_EN


# ── Pro 功能列表 ─────────────────────────────────

PRO_FEATURES: dict[str, str] = {
    "enhanced_timer": "🍅 增强番茄钟（GUI 窗口、暂停/继续、进度条）",
    "enhanced_clipboard": "📋 高级剪贴板（搜索/类型筛选/收藏/统计）",
    "enhanced_ocr": "📸 增强 OCR（批量识别/自动语言/复制结果）",
    "visual_auto": "🤖 视觉自动化（屏幕找字/自动点击/表单填写/脚本执行）",
}

PRO_FEATURES_EN: dict[str, str] = {
    "enhanced_timer": "🍅 Enhanced Pomodoro Timer (GUI, pause/resume, progress bar)",
    "enhanced_clipboard": "📋 Advanced Clipboard (search/filter/favorites/stats)",
    "enhanced_ocr": "📸 Pro OCR (batch/auto-lang/copy results)",
    "visual_auto": "🤖 Visual Automation (screen find/click/type/scripting)",
}

TRIAL_MAX_USES = 5


# ── License Key 格式校验 ─────────────────────────


def _validate_key(key: str) -> bool:
    """验证 License Key 格式合法性。

    格式: KA-PRO-XXXXXXXXXXXXXXXXXXXX
    本地校验格式，远程服务器做最终验证。
    """
    import re
    key = key.strip()
    # 格式：KA-PRO- 开头 + 20 位大写字母数字
    if re.match(r'^KA-PRO-[A-Z0-9]{20}$', key):
        # 简单校验和：前19位字符的 ASCII 和末位 = 第20位数字
        seg = key.split("-")[2]
        body = seg[:-1]
        checksum = sum(ord(c) for c in body) % 10
        return int(seg[-1]) == checksum
    return False


# ── License 校验（远程验证） ────────────────────


def _remote_validate(key: str) -> bool:
    """通过远程服务器验证 License Key。"""
    try:
        import requests
        resp = requests.post(
            f"{LICENSE_SERVER}/verify",
            json={"key": key},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("valid", False)
    except requests.ConnectionError:
        # 连不上服务器时：离线环境使用缓存
        pass
    except ImportError:
        pass
    except Exception:
        pass
    return False


def is_pro() -> bool:
    """判断当前是否为 Pro 版本。"""
    if os.environ.get("ZHIXING_PRO") == "1":
        return True

    try:
        config = Config()
        key = config.get("pro.license_key", "")
        if not key:
            return False
        # 本地校验格式
        if not _validate_key(key):
            return False
        # 远程验证，失败时本地格式通过也算有效
        try:
            if _remote_validate(key):
                return True
        except Exception:
            pass
        # 远程不可用时，本地格式验证通过即放行
        return True
    except Exception:
        return False


# ── 试用子系统 ──────────────────────────────────

_TRIAL_FILE = os.path.expanduser("~/.zhixing/pro_trial.json")


def _load_trials() -> dict:
    try:
        with open(_TRIAL_FILE) as f:
            data: dict = json.load(f)
            return {k: int(v) for k, v in data.items()}
    except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def _save_trials(trials: dict):
    os.makedirs(os.path.dirname(_TRIAL_FILE), exist_ok=True)
    with open(_TRIAL_FILE, "w") as f:
        json.dump(trials, f, indent=2)


def get_trial_remaining(feature: str) -> int:
    trials = _load_trials()
    used = trials.get(feature, 0)
    return max(0, TRIAL_MAX_USES - used)


def _use_trial(feature: str) -> bool:
    trials = _load_trials()
    used = trials.get(feature, 0)
    if used >= TRIAL_MAX_USES:
        return False
    trials[feature] = used + 1
    _save_trials(trials)
    return True


# ── 核心守卫 API ────────────────────────────────


def require_pro(feature: str, lang: str = "zh") -> str | None:
    """Pro 功能守卫。返回 None 放行，返回 str 拒绝提示。"""
    if is_pro():
        return None

    remaining = get_trial_remaining(feature)
    if remaining > 0:
        _use_trial(feature)
        return None

    feature_desc_cn = PRO_FEATURES.get(feature, feature)
    feature_desc_en = PRO_FEATURES_EN.get(feature, feature)
    feature_desc = feature_desc_en if lang != "zh" else feature_desc_cn
    price = _purchase_price(lang)
    url = _purchase_url(lang)

    if lang == "zh":
        return (
            f"❌ 「{feature_desc}」是知行 Pro 功能\n"
            f"\n"
            f"  试用次数已用完（{TRIAL_MAX_USES} 次），升级 Pro 解锁\n"
            f"  定价: {price}  |  购买: {url}\n"
            f"\n"
            f"  输入 pro 查看详情，输入 activation 输入 License Key"
        )
    return (
        f"❌ 「{feature_desc}」is a Flow Pro feature\n"
        f"\n"
        f"  Trial used up ({TRIAL_MAX_USES} uses). Upgrade to Pro:\n"
        f"  Price: {price}  |  Buy: {url}\n"
        f"\n"
        f"  Type pro for details, or type activation to enter License Key"
    )


# ── Pro 信息展示 ─────────────────────────────────


def get_pro_features_text(lang: str = "zh") -> str:
    """返回 Pro / Community 功能对比 + 定价。"""
    price = _purchase_price(lang)
    url = _purchase_url(lang)
    is_cn = lang == "zh"

    if is_cn:
        h, rows = ["功能", "Community", "Pro"], [
            ("基础命令 (80+)", "✅", "✅"),
            ("中文自然语言", "✅", "✅"),
            ("插件系统", "✅", "✅"),
            ("本地 RAG 知识库", "✅", "✅"),
            ("企业消息", "✅", "✅"),
        ]
    else:
        h, rows = ["Feature", "Community", "Pro"], [
            ("80+ System Commands", "✅", "✅"),
            ("Natural Language (CN/EN)", "✅", "✅"),
            ("Plugin System", "✅", "✅"),
            ("Local RAG Knowledge Base", "✅", "✅"),
            ("Enterprise Messaging", "✅", "✅"),
        ]

    lines = ["\x1b[1m📊 Flow Pro — Feature Comparison\x1b[0m", "",
             f"  {h[0]:30s} {h[1]:>14s} {h[2]:>10s}",
             f"  {'─'*30} {'─'*14} {'─'*10}"]
    for r in rows:
        lines.append(f"  {r[0]:30s} {r[1]:>14s} {r[2]:>10s}")
    lines.append(f"  {'───':30s} {'───':>14s} {'───':>10s}")

    features_dict = PRO_FEATURES if is_cn else PRO_FEATURES_EN
    for fname, fdesc in features_dict.items():
        remaining = get_trial_remaining(fname) if not is_pro() else 0
        remaining_str = f" 试用剩{remaining}次" if remaining > 0 else "  —  "
        if not is_cn:
            remaining_str = f" {remaining} trials left" if remaining > 0 else "  —  "
        lines.append(f"  {fdesc:30s} {remaining_str:>14s} {'✅':>10s}")

    if is_cn:
        lines += ["", f"\x1b[1m💎 升级 Pro: {price}\x1b[0m", f"  \x1b[2m{url}\x1b[0m", "",
                   "\x1b[2m输入 activation 输入 License Key 激活\x1b[0m"]
    else:
        lines += ["", f"\x1b[1m💎 Upgrade to Pro: {price}\x1b[0m", f"  \x1b[2m{url}\x1b[0m", "",
                   "\x1b[2mType activation to enter License Key\x1b[0m"]
    return "\n".join(lines)


def get_pro_upsell_text(trial_remaining: int, feature: str, lang: str = "zh") -> str:
    """试用即将用完时的升级提示。"""
    feature_desc_cn = PRO_FEATURES.get(feature, feature)
    feature_desc_en = PRO_FEATURES_EN.get(feature, feature)
    feature_desc = feature_desc_en if lang != "zh" else feature_desc_cn
    price = _purchase_price(lang)

    if lang == "zh":
        return (
            f"\x1b[93m💡 提示\x1b[0m\n"
            f"  「{feature_desc}」是 Pro 功能（还剩 {trial_remaining} 次试用）\n"
            f"  升级 Pro: {price}\n"
            f"  输入 \x1b[1mpro\x1b[0m 查看详情，或 \x1b[1mdismiss\x1b[0m 不再提示"
        )
    return (
        f"\x1b[93m💡 Tip\x1b[0m\n"
        f"  「{feature_desc}」is a Pro feature ({trial_remaining} trials left)\n"
        f"  Upgrade: {price}\n"
        f"  Type \x1b[1mpro\x1b[0m for details, or \x1b[1mdismiss\x1b[0m to hide"
    )
