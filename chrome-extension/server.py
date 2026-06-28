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

        elif action == "chat":
            # AI 对话模式 — 自然语言 → AI Orchestrator → 工具调用 → 回复
            from zhixing.agent.orchestrator import Orchestrator
            from zhixing.agent.usage import check_limit, add_usage, get_usage, FREE_MONTHLY_LIMIT
            from zhixing.memory.conversation import (
                create_session, get_openai_history, add_message,
            )

            user_input = params.get("text", "").strip()
            session_id = params.get("session_id", "")

            if not user_input:
                return {"type": "chat_response", "data": {"reply": "请输入内容", "error": False}}

            # 用量检查
            limit_check = check_limit()
            if not limit_check["ok"]:
                return {"type": "chat_response", "data": {
                    "reply": limit_check["message"],
                    "error": False,
                    "limit_reached": True,
                }}

            # 会话管理
            if not session_id:
                session_id = create_session()
            history = get_openai_history(session_id)

            # 保存用户消息
            add_message(session_id, "user", user_input)

            # 执行编排
            orchestrator = Orchestrator()
            result = await orchestrator.process(user_input, history=history)

            reply = result.get("reply", "")
            error = result.get("error", False)

            # 保存 AI 回复
            add_message(session_id, "assistant", reply)

            # 记录用量
            add_usage()

            remaining = FREE_MONTHLY_LIMIT - get_usage()
            tip = ""
            if 0 < remaining <= 3:
                tip = f"\n\n💡 本月还剩 {remaining} 次免费对话"

            return {
                "type": "chat_response",
                "data": {
                    "reply": reply + tip,
                    "session_id": session_id,
                    "tool_calls": result.get("tool_calls", []),
                    "error": error,
                    "remaining": remaining,
                },
            }

        elif action == "set_config":
            # 保存配置（如 API Key）
            from zhixing.config import Config
            cfg = Config()
            key = params.get("key", "")
            value = params.get("value", "")
            if key and value:
                # 拒绝打码的值写回配置文件
                if "****" in str(value):
                    return {"type": "result", "data": "⚠️ 检测到打码的 Key，未保存。请重新输入完整的 API Key"}
                cfg.set(key, value)
                cfg.save()
                return {"type": "result", "data": f"✅ {key} 已保存"}
            return {"type": "result", "data": "❌ 需要 key 和 value 参数"}

        elif action == "get_config":
            # 读取配置
            from zhixing.config import Config
            cfg = Config()
            key = params.get("key", "")
            if key:
                val = cfg.get(key, "")
                # 掩盖 API Key
                if "key" in key.lower() and val:
                    val = val[:8] + "****" + val[-4:] if len(val) > 12 else "****"
                return {"type": "result", "data": val}
            return {"type": "result", "data": ""}

        elif action == "market_list":
            # 获取技能市场列表
            import json as _json
            index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zhixing", "skills_index.json")
            try:
                with open(index_path) as _f:
                    index = _json.load(_f)
                return {"type": "result", "data": index.get("skills", [])}
            except Exception as e:
                return {"type": "result", "data": [], "error": str(e)}

        elif action == "skill_install":
            # 安装技能
            name = params.get("name", "")
            if not name:
                return {"type": "result", "data": "❌ 需要 name 参数"}
            from zhixing.agent.skill_manager import SkillManager
            try:
                sm = SkillManager()
                # 从 index 查找安装 URL
                import json as _json
                index_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zhixing", "skills_index.json")
                with open(index_path) as _f:
                    index = _json.load(_f)
                url = ""
                for s in index.get("skills", []):
                    if s["name"] == name:
                        url = s["install_url"]
                        break
                if url:
                    result = sm.install_skill(url)
                    return {"type": "result", "data": f"✅ 技能「{name}」安装成功"}
                else:
                    return {"type": "result", "data": f"❌ 未找到技能「{name}」"}
            except Exception as e:
                return {"type": "result", "data": f"❌ 安装失败: {e}"}

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
    print(f"🚀 知行 (ZhiXing) 服务启动")
    print(f"   WebSocket: ws://localhost:{WS_PORT}   (Chrome 扩展 + Electron)")
    print(f"   HTTP API:  http://localhost:9512      (iOS 快捷指令 + 外部调用)")
    print()

    # 同时启动 WebSocket 和 HTTP API
    async with websockets.serve(handler, "localhost", WS_PORT):
        # 导入 HTTP API 服务器（iOS 快捷指令）
        import importlib.util
        _api_spec = importlib.util.spec_from_file_location(
            "api_server",
            os.path.join(os.path.dirname(__file__), "api_server.py"),
        )
        _api_mod = importlib.util.module_from_spec(_api_spec)
        _api_spec.loader.exec_module(_api_mod)
        run_api_server = _api_mod.run_api_server
        api_task = asyncio.create_task(run_api_server())
        await asyncio.Future()  # 永久运行


if __name__ == "__main__":
    asyncio.run(main())
