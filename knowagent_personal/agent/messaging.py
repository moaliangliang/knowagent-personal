"""企业消息集成 — 企业微信 / 飞书 / 钉钉

支持三种方式发送消息：
1. Webhook Bot（最简单，无需开发者身份）
2. 官方 REST API（需应用凭证）
3. UI 自动化（通过 macOS AX API 模拟操作）

配置存储在 ~/.knowagent/config.yaml 的 messaging 段，
敏感信息建议通过 ka credential 存入 Keychain。
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Literal

import requests

# ── 平台配置 ─────────────────────────────────────────────

PLATFORM_INFO = {
    "wecom": {
        "name": "企业微信",
        "webhook_host": "qyapi.weixin.qq.com",
        "webhook_path": "/cgi-bin/webhook/send",
        "webhook_key_param": "key",
        "api_host": "qyapi.weixin.qq.com",
        "send_path": "/cgi-bin/message/send",
        "token_path": "/cgi-bin/gettoken",
    },
    "feishu": {
        "name": "飞书",
        "webhook_host": "open.feishu.cn",
        "webhook_path": "/open-apis/bot/v2/hook",
        "webhook_key_param": None,  # key 在 URL 路径中
        "api_host": "open.feishu.cn",
        "send_path": "/open-apis/im/v1/messages",
        "token_path": "/open-apis/auth/v3/tenant_access_token/internal",
    },
    "dingtalk": {
        "name": "钉钉",
        "webhook_host": "oapi.dingtalk.com",
        "webhook_path": "/robot/send",
        "webhook_key_param": "access_token",
        "api_host": "oapi.dingtalk.com",
        "send_path": "/v1.0/im/messages/send",
        "token_path": "/v1.0/oauth2/accessToken",
    },
}


# ═════════════════════════════════════════════════════════
#  配置管理
# ═════════════════════════════════════════════════════════

def _get_config() -> dict:
    """从 config.yaml 读取消息平台配置"""
    from knowagent_personal.config import Config
    cfg = Config()
    return {
        # 企业微信
        "wecom_webhook_key": cfg.get("messaging.wecom.webhook_key", ""),
        "wecom_corp_id": cfg.get("messaging.wecom.corp_id", ""),
        "wecom_corp_secret": cfg.get("messaging.wecom.corp_secret", ""),
        "wecom_agent_id": cfg.get("messaging.wecom.agent_id", ""),
        # 飞书
        "feishu_webhook_key": cfg.get("messaging.feishu.webhook_key", ""),
        "feishu_app_id": cfg.get("messaging.feishu.app_id", ""),
        "feishu_app_secret": cfg.get("messaging.feishu.app_secret", ""),
        # 钉钉
        "dingtalk_webhook_token": cfg.get("messaging.dingtalk.webhook_token", ""),
        "dingtalk_app_key": cfg.get("messaging.dingtalk.app_key", ""),
        "dingtalk_app_secret": cfg.get("messaging.dingtalk.app_secret", ""),
    }


def _get_webhook_url(platform: str) -> str | None:
    """获取指定平台的 Webhook URL"""
    cfg = _get_config()
    info = PLATFORM_INFO[platform]

    if platform == "wecom":
        key = cfg.get("wecom_webhook_key", "")
        if not key:
            return None
        return f"https://{info['webhook_host']}{info['webhook_path']}?{info['webhook_key_param']}={key}"

    if platform == "feishu":
        key = cfg.get("feishu_webhook_key", "")
        if not key:
            return None
        return f"https://{info['webhook_host']}{info['webhook_path']}/{key}"

    if platform == "dingtalk":
        token = cfg.get("dingtalk_webhook_token", "")
        if not token:
            return None
        return f"https://{info['webhook_host']}{info['webhook_path']}?{info['webhook_key_param']}={token}"

    return None


# ═════════════════════════════════════════════════════════
#  发送消息（Webhook Bot）
# ═════════════════════════════════════════════════════════

def _send_webhook(platform: str, text: str) -> str:
    """通过 Webhook Bot 发送纯文本消息"""
    url = _get_webhook_url(platform)
    if not url:
        return f"❌ {PLATFORM_INFO[platform]['name']} Webhook 未配置\n   config.yaml 添加 messaging.{platform}.webhook_key"

    if platform == "wecom":
        payload = {"msgtype": "text", "text": {"content": text}}
    elif platform == "feishu":
        payload = {"msg_type": "text", "content": {"text": text}}
    elif platform == "dingtalk":
        payload = {"msgtype": "text", "text": {"content": text}}
    else:
        return f"❌ 不支持的平台: {platform}"

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if resp.ok and data.get("errcode", data.get("code", 0)) == 0:
            return f"✅ 已通过 Webhook 发送到 {PLATFORM_INFO[platform]['name']}"
        err_msg = data.get("errmsg", data.get("msg", data.get("message", str(data))))
        return f"❌ {PLATFORM_INFO[platform]['name']} Webhook 发送失败: {err_msg}"
    except requests.RequestException as e:
        return f"❌ 网络请求失败: {e}"


# ═════════════════════════════════════════════════════════
#  发送消息（Markdown / 富文本）
# ═════════════════════════════════════════════════════════

def _send_webhook_markdown(platform: str, title: str, markdown: str) -> str:
    """通过 Webhook Bot 发送 Markdown 消息"""
    url = _get_webhook_url(platform)
    if not url:
        return _send_webhook(platform, f"{title}\n{markdown}")

    if platform == "wecom":
        payload = {"msgtype": "markdown", "markdown": {"content": markdown}}
    elif platform == "feishu":
        payload = {"msg_type": "interactive", "card": {
            "header": {"title": {"tag": "plain_text", "content": title}},
            "elements": [{"tag": "markdown", "content": markdown}],
        }}
    elif platform == "dingtalk":
        payload = {"msgtype": "markdown", "markdown": {"title": title, "text": markdown}}
    else:
        return f"❌ 不支持的平台: {platform}"

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if resp.ok and data.get("errcode", data.get("code", 0)) == 0:
            return f"✅ 已发送 Markdown 到 {PLATFORM_INFO[platform]['name']}"
        err_msg = data.get("errmsg", data.get("msg", data.get("message", str(data))))
        return f"❌ 发送失败: {err_msg}"
    except requests.RequestException as e:
        return f"❌ 网络请求失败: {e}"


# ═════════════════════════════════════════════════════════
#  通过 macOS UI 自动化发送（不使用 API）
# ═════════════════════════════════════════════════════════

def _osa_escape(s: str) -> str:
    """Escape string for safe use inside an AppleScript string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _send_via_ui(platform: str, contact: str, text: str) -> str:
    """通过 macOS UI 自动化模拟发送消息。
    需要目标应用已安装并登录。
    """
    app_names = {
        "wecom": "企业微信",
        "feishu": "飞书",
        "dingtalk": "钉钉",
    }
    app_name = app_names.get(platform, platform)
    platform_name = PLATFORM_INFO[platform]["name"]

    try:
        # 1. 激活应用
        subprocess.run(["osascript", "-e",
            f'tell application "{app_name}" to activate'], timeout=10)
        time.sleep(1.5)

        # 2. 搜索联系人（Cmd+F 或 Cmd+Shift+F）
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to keystroke "f" using command down'], timeout=5)
        time.sleep(0.5)
        subprocess.run(["osascript", "-e",
            f'tell application "System Events" to keystroke "{_osa_escape(contact)}"'], timeout=5)
        time.sleep(1.5)

        # 3. 回车进入对话
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to key code 36'], timeout=5)
        time.sleep(0.5)

        # 4. 输入消息
        safe_text = _osa_escape(text)
        subprocess.run(["osascript", "-e",
            f'tell application "System Events" to keystroke "{safe_text}"'], timeout=10)

        # 5. 发送（Cmd+Enter）
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to keystroke return using command down'], timeout=5)
        time.sleep(0.5)

        return f"✅ 已通过 UI 模拟在 {platform_name} 中给 {contact} 发送消息"

    except subprocess.TimeoutExpired:
        return f"❌ 操作超时，请确认 {platform_name} 已打开并登录"
    except FileNotFoundError:
        return f"❌ 未安装 {platform_name}"
    except Exception as e:
        return f"❌ 模拟操作失败: {e}"


# ═════════════════════════════════════════════════════════
#  API Token 管理
# ═════════════════════════════════════════════════════════

def _get_api_token(platform: str) -> str | None:
    """获取官方 API 的 access_token"""
    cfg = _get_config()
    info = PLATFORM_INFO[platform]

    try:
        if platform == "wecom":
            cid = cfg.get("wecom_corp_id", "")
            secret = cfg.get("wecom_corp_secret", "")
            if not cid or not secret:
                return None
            r = requests.get(
                f"https://{info['api_host']}{info['token_path']}",
                params={"corpid": cid, "corpsecret": secret},
                timeout=10,
            )
            return r.json().get("access_token")

        elif platform == "feishu":
            app_id = cfg.get("feishu_app_id", "")
            secret = cfg.get("feishu_app_secret", "")
            if not app_id or not secret:
                return None
            r = requests.post(
                f"https://{info['api_host']}{info['token_path']}",
                json={"app_id": app_id, "app_secret": secret},
                timeout=10,
            )
            return r.json().get("tenant_access_token")

        elif platform == "dingtalk":
            app_key = cfg.get("dingtalk_app_key", "")
            secret = cfg.get("dingtalk_app_secret", "")
            if not app_key or not secret:
                return None
            r = requests.post(
                f"https://{info['api_host']}{info['token_path']}",
                json={"appKey": app_key, "appSecret": secret},
                timeout=10,
            )
            return r.json().get("accessToken")
    except Exception:
        return None

    return None


# ═════════════════════════════════════════════════════════
#  命令函数
# ═════════════════════════════════════════════════════════

def cmd_wecom(params: dict) -> str:
    """企业微信集成。action=send(默认)/uibot/send_markdown，text=消息内容，contact=联系人"""
    action = params.get("action", "send")
    text = params.get("text", params.get("keyword", "Hello from Mac Agent"))
    contact = params.get("contact", "")

    if action == "uibot":
        if not contact:
            return "❌ UI 模拟模式需要 contact 参数（联系人名）"
        return _send_via_ui("wecom", contact, text)

    if action == "send_markdown":
        title = params.get("title", "Mac Agent 通知")
        return _send_webhook_markdown("wecom", title, text)

    return _send_webhook("wecom", text)


def cmd_feishu(params: dict) -> str:
    """飞书集成。action=send(默认)/uibot/send_markdown，text=消息内容，contact=联系人"""
    action = params.get("action", "send")
    text = params.get("text", params.get("keyword", "Hello from Mac Agent"))
    contact = params.get("contact", "")

    if action == "uibot":
        if not contact:
            return "❌ UI 模拟模式需要 contact 参数（联系人名）"
        return _send_via_ui("feishu", contact, text)

    if action == "send_markdown":
        title = params.get("title", "Mac Agent 通知")
        return _send_webhook_markdown("feishu", title, text)

    return _send_webhook("feishu", text)


def cmd_dingtalk(params: dict) -> str:
    """钉钉集成。action=send(默认)/uibot/send_markdown，text=消息内容，contact=联系人"""
    action = params.get("action", "send")
    text = params.get("text", params.get("keyword", "Hello from Mac Agent"))
    contact = params.get("contact", "")

    if action == "uibot":
        if not contact:
            return "❌ UI 模拟模式需要 contact 参数（联系人名）"
        return _send_via_ui("dingtalk", contact, text)

    if action == "send_markdown":
        title = params.get("title", "Mac Agent 通知")
        return _send_webhook_markdown("dingtalk", title, text)

    return _send_webhook("dingtalk", text)


def cmd_broadcast(params: dict) -> str:
    """一键群发到所有已配置的平台。
    text=消息内容，title=标题(可选)，platforms=all(默认)/wecom,feishu
    """
    text = params.get("text", params.get("keyword", ""))
    if not text:
        return "❌ 需要 text 参数"
    title = params.get("title", "Mac Agent 通知")
    platforms_str = params.get("platforms", "all")

    if platforms_str == "all":
        platforms = ["wecom", "feishu", "dingtalk"]
    else:
        platforms = [p.strip() for p in platforms_str.split(",") if p.strip()]

    results = []
    for p in platforms:
        if p in PLATFORM_INFO:
            r = _send_webhook(p, text)
            results.append(f"  {PLATFORM_INFO[p]['name']}: {r}")
        else:
            results.append(f"  {p}: ❌ 不支持的平台")

    return f"📋 群发结果 ({len(results)} 个平台):\n" + "\n".join(results)


# ── 命令注册 ─────────────────────────────────────────────

COMMANDS: dict = {
    "wecom": cmd_wecom,
    "feishu": cmd_feishu,
    "dingtalk": cmd_dingtalk,
    "broadcast": cmd_broadcast,
}

TOOL_SCHEMAS: dict = {
    "wecom": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "send(默认)发文本, send_markdown发富文本, uibot模拟操作",
                "enum": ["send", "send_markdown", "uibot"],
            },
            "text": {"type": "string", "description": "消息内容"},
            "contact": {"type": "string", "description": "联系人（uibot 模式需要）"},
            "title": {"type": "string", "description": "消息标题（markdown 模式）"},
        },
    },
    "feishu": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "send(默认)发文本, send_markdown发富文本, uibot模拟操作",
                "enum": ["send", "send_markdown", "uibot"],
            },
            "text": {"type": "string", "description": "消息内容"},
            "contact": {"type": "string", "description": "联系人（uibot 模式需要）"},
            "title": {"type": "string", "description": "消息标题（markdown 模式）"},
        },
    },
    "dingtalk": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "send(默认)发文本, send_markdown发富文本, uibot模拟操作",
                "enum": ["send", "send_markdown", "uibot"],
            },
            "text": {"type": "string", "description": "消息内容"},
            "contact": {"type": "string", "description": "联系人（uibot 模式需要）"},
            "title": {"type": "string", "description": "消息标题（markdown 模式）"},
        },
    },
    "broadcast": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "消息内容"},
            "title": {"type": "string", "description": "消息标题（可选）"},
            "platforms": {
                "type": "string",
                "description": "目标平台，逗号分隔，默认 all（全部已配置的平台）",
            },
        },
        "required": ["text"],
    },
}
