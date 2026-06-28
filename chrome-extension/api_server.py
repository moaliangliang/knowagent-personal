"""知行 HTTP API 服务器 — 供 iOS 快捷指令等外部客户端调用。

端口: 9512
鉴权: Token（存储在 ~/.zhixing/config.yaml 的 api_token 字段）

API:
  POST /api/command    — 执行系统命令
  POST /api/chat       — AI 对话
  GET  /api/ping       — 健康检查

iOS 快捷指令用法:
  "获取内容 URL" → URL: http://你的MacIP:9512/api/command
  → 方法: POST
  → 请求体: {"command": "系统状态", "token": "你的Token"}
  → 返回: {"ok": true, "data": "..."}
"""

import json
import os

from aiohttp import web

from zhixing.config import Config

# ── 配置 ──────────────────────────────────────────

API_PORT = int(os.environ.get("ZHIXING_API_PORT", "9512"))

# ── 鉴权 ──────────────────────────────────────────

def _verify_token(request) -> bool:
    """验证请求 Token。"""
    cfg = Config()
    expected = cfg.get("api_token", "") or os.environ.get("ZHIXING_API_TOKEN", "")
    if not expected:
        return True  # 未配置 Token 时开放访问（开发模式）
    token = ""
    # 从 Header 或 Body 获取
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        try:
            body = request.get("body_data", {})
            token = body.get("token", "")
        except Exception:
            pass
    return token == expected


# ── 路由处理 ─────────────────────────────────────

@web.middleware
async def auth_middleware(request, handler):
    """全局鉴权中间件。"""
    if request.path == "/api/ping":
        return await handler(request)
    body = await request.json() if request.can_read_body else {}
    request["body_data"] = body
    if not _verify_token(request):
        return web.json_response({"ok": False, "error": "未授权，请提供有效 Token"}, status=401)
    return await handler(request)


async def handle_ping(request):
    """健康检查。"""
    return web.json_response({"ok": True, "type": "pong", "version": "2.0.0"})


async def handle_command(request):
    """执行系统命令。

    请求体: {"command": "系统状态", "token": "..."}
    返回: {"ok": true, "data": "命令输出"}
    """
    body = request["body_data"]
    cmd = body.get("command", "").strip()
    if not cmd:
        return web.json_response({"ok": False, "error": "需要 command 参数"})

    try:
        # 解析中文命令别名
        from zhixing.agent.aliases import resolve_cn
        resolved = resolve_cn(cmd)
        if resolved:
            cmd_name, args_str = resolved
        else:
            cmd_name, args_str = cmd, ""

        # 查找并执行命令
        from zhixing.agent.tools import COMMANDS
        handler = COMMANDS.get(cmd_name)
        if not handler:
            return web.json_response({"ok": False, "error": f"未知命令: {cmd}"})

        params = {}
        if args_str:
            # 解析 key=value 参数
            for part in args_str.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k] = v

        result = handler(params)
        return web.json_response({"ok": True, "data": str(result)})

    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


async def handle_chat(request):
    """AI 对话。

    请求体: {"text": "帮我写日报", "token": "..."}
    返回: {"ok": true, "reply": "...", "session_id": "..."}
    """
    body = request["body_data"]
    text = body.get("text", "").strip()
    if not text:
        return web.json_response({"ok": False, "error": "需要 text 参数"})

    try:
        from zhixing.agent.orchestrator import Orchestrator
        from zhixing.agent.usage import check_limit, add_usage
        from zhixing.memory.conversation import create_session, get_openai_history, add_message

        limit_check = check_limit()
        if not limit_check["ok"]:
            return web.json_response({"ok": True, "reply": limit_check["message"], "limit_reached": True})

        session_id = body.get("session_id", "") or create_session()
        history = get_openai_history(session_id)
        add_message(session_id, "user", text)

        orch = Orchestrator()
        result = await orch.process(text, history=history)

        reply = result.get("reply", "")
        add_message(session_id, "assistant", reply)
        add_usage()

        return web.json_response({
            "ok": True,
            "reply": reply,
            "session_id": session_id,
            "tool_calls": result.get("tool_calls", []),
        })

    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)})


# ── 启动 ──────────────────────────────────────────

def create_app() -> web.Application:
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/api/ping", handle_ping)
    app.router.add_post("/api/command", handle_command)
    app.router.add_post("/api/chat", handle_chat)
    return app


async def run_api_server():
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    print(f"🌐 HTTP API 服务已启动 http://0.0.0.0:{API_PORT}")
    print(f"   可用接口:")
    print(f"     GET  /api/ping   — 健康检查")
    print(f"     POST /api/command — 执行命令")
    print(f"     POST /api/chat   — AI 对话")
    token = os.environ.get("ZHIXING_API_TOKEN", "")
    if token:
        print(f"     Token 鉴权已启用")
    else:
        print(f"     ⚠️  未配置 Token（开发模式）")
    print(f"    iOS 快捷指令: http://你的MacIP:{API_PORT}/api/command")
