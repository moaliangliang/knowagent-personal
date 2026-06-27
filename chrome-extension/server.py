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
                    "━━━ 可用的命令 ━━━\n"
                    "\n"
                    "┃ 系统控制\n"
                    "  状态           系统状态（CPU/内存/磁盘）\n"
                    "  电池           电池信息\n"
                    "  网络           WiFi 状态\n"
                    "  锁屏           锁定屏幕\n"
                    "  通知 内容      发送通知\n"
                    "  朗读 内容      语音朗读\n"
                    "  语音           语音输入\n"
                    "\n"
                    "┃ 网页自动化\n"
                    "  网页 url       Safari 打开网页\n"
                    "  点击 文字      点击屏幕上的文字\n"
                    "  填入 标签=值   表单填写\n"
                    "  截图           截屏保存\n"
                    "  看看           截屏并识别文字\n"
                    "  找 文字        查找文字位置\n"
                    "  打字 内容      在当前焦点输入文字\n"
                    "  快捷键 键      模拟按键（如 enter/tab/ctrl_c）\n"
                    "\n"
                    "┃ 音乐\n"
                    "  搜索 关键词    在线搜索并播放音乐\n"
                    "  下一首         切换到下一首\n"
                    "  停止           停止播放\n"
                    "  音量 0-100     设置音量\n"
                    "\n"
                    "┃ 苹果生态\n"
                    "  日历           今日日程\n"
                    "  邮件           读取收件箱\n"
                    "  邮箱大师       读取邮箱大师邮件\n"
                    "  提醒 内容      添加提醒事项\n"
                    "  备忘录         列出备忘录\n"
                    "  联系人 姓名    搜索联系人\n"
                    "  APP 应用名     打开指定应用\n"
                    "\n"
                    "┃ 文件与剪贴板\n"
                    "  目录 路径      列出目录文件\n"
                    "  复制 内容      复制到剪贴板\n"
                    "  粘贴           读取剪贴板\n"
                    "\n"
                    "┃ 待办事项\n"
                    "  待办           查看待办列表\n"
                    "  添加待办 内容  新增待办\n"
                    "  完成待办 编号  标记完成\n"
                    "  删除待办 编号  删除待办\n"
                    "\n"
                    "┃ VPN/网络\n"
                    "  VPN 状态       VPN 连通性检测\n"
                    "  VPN 连接 公司名  连接公司 VPN\n"
                    "  自动登录 站点  网页自动填表登录\n"
                    "\n"
                    "┃ 其他\n"
                    "  搜索文件 名    查找文件\n"
                    "  翻译 文本      翻译文字\n"
                    "  计时器 分钟    倒计时\n"
                    "  help           显示此帮助"
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
                request_id = msg.pop("requestId", None)
                response = await handle_message(ws, msg)
                if request_id:
                    response["requestId"] = request_id
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
