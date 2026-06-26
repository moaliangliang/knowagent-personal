#!/usr/bin/env python3
"""知行 (ZhiXing) WebSocket Server — 连接 Chrome 扩展和后端自动化引擎。

运行: python3 server.py
然后在 Chrome 中按 Ctrl+Cmd+1 并排看效果。
"""

import asyncio
import json
import os
import sys
import subprocess
import time
import websockets

# 添加项目路径
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

WS_PORT = 9510

connected_clients = set()


async def handle_message(ws, msg: dict):
    """处理来自 Chrome 扩展的消息。"""
    action = msg.get("action", "")
    params = msg.get("params", {})

    # 设置 Pro 环境
    env = os.environ.copy()
    env["ZHIXING_PRO"] = "1"

    try:
        if action == "ping":
            return {"type": "pong"}

        elif action == "page_info":
            # 扩展发送的页面信息
            return {
                "type": "result",
                "data": f"📄 当前页面: {params.get('url', '')[:80]}",
            }

        elif action == "command":
            cmd = params.get("cmd", "")
            rest = params.get("rest", "")

            # 执行 ka 命令（走 Python）
            if cmd == "状态":
                from zhixing.agent.tools import cmd_system_status
                result = cmd_system_status({})
            elif cmd == "搜索":
                keyword = rest or params.get("keyword", "")
                from zhixing.agent.tools import cmd_music_search_online
                result = cmd_music_search_online({"keyword": keyword})
            elif cmd == "网页":
                url = rest or params.get("url", "")
                if url:
                    from zhixing.agent.auto import cmd_auto_web
                    result = cmd_auto_web({"action": "navigate", "url": url})
                else:
                    result = "❌ 需要 URL"
            elif cmd == "点击":
                text = rest or params.get("text", "")
                if text:
                    from zhixing.agent.auto import cmd_auto_web
                    result = cmd_auto_web({"action": "click", "text": text})
                else:
                    result = "❌ 需要目标文字"
            elif cmd == "填入":
                label = rest
                value = params.get("value", "")
                if label and value:
                    from zhixing.agent.auto import cmd_auto_web
                    result = cmd_auto_web({"action": "fill", "label": label, "value": value})
                else:
                    result = "❌ 需要 label 和 value"
            elif cmd == "截图":
                from zhixing.agent.auto import cmd_auto_web
                result = cmd_auto_web({"action": "screenshot"})
            elif cmd == "看看":
                from zhixing.agent.auto import cmd_auto_screenshot
                result = cmd_auto_screenshot({})
            elif cmd == "找":
                text = rest or params.get("text", "")
                if text:
                    from zhixing.agent.auto import cmd_auto_find
                    result = cmd_auto_find({"text": text})
                else:
                    result = "❌ 需要搜索文字"
            elif cmd == "help":
                result = (
                    "可用的命令:\n"
                    "  状态      — 系统状态\n"
                    "  搜索 xxx  — 搜索音乐\n"
                    "  网页 url  — 打开网页\n"
                    "  点击 xxx  — 点击屏幕文字\n"
                    "  填入 标签=值 — 表单填写\n"
                    "  截图      — 截屏分析\n"
                    "  看看      — 查看屏幕文字\n"
                    "  找 xxx   — 查找文字位置"
                )
            else:
                result = f"未知命令: {cmd}。输入 help 查看可用命令"

        else:
            result = f"未知 action: {action}"

        return {"type": "result", "data": str(result)}

    except Exception as e:
        return {"type": "error", "data": f"❌ {e}"}


async def handler(ws):
    """WebSocket 连接处理器。"""
    connected_clients.add(ws)
    print(f"🟢 Chrome 扩展已连接 ({len(connected_clients)} 个连接)")
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
                response = await handle_message(ws, msg)
                await ws.send(json.dumps(response, ensure_ascii=False))
            except json.JSONDecodeError:
                await ws.send(json.dumps({"type": "error", "data": "JSON 格式错误"}))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(ws)
        print(f"🔴 Chrome 扩展断开连接 ({len(connected_clients)} 个连接)")


async def main():
    print(f"🚀 知行 (ZhiXing) WebSocket 服务器启动 ws://localhost:{WS_PORT}")
    print(f"   在 Chrome 中打开任意网页，侧边栏会自动连接")
    async with websockets.serve(handler, "localhost", WS_PORT):
        await asyncio.Future()  # 永久运行


if __name__ == "__main__":
    asyncio.run(main())
