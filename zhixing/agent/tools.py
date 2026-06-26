"""Mac Agent Personal - 核心命令模块

所有 cmd_* 函数统一返回 str（纯文本），格式：
  ✅ 成功信息
  ❌ 错误信息
  📋 数据/列表信息
"""

import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
import urllib.parse

try:
    import psutil
except ImportError:
    psutil = None

from .__tools_init__ import ALL_COMMANDS, ALL_TOOL_SCHEMAS, register_all

# ── 常量 ─────────────────────────────────────────────────

_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # zhixing/
_SWIFT_SOURCE_DIR = os.path.join(os.path.dirname(_PACKAGE_DIR), "swift")
_BIN_DIR = os.path.expanduser("~/.zhixing/bin")


# ── 工具函数 ─────────────────────────────────────────────

def _run_osa(script: str, timeout: int = 30) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()


def _osa_escape(s: str) -> str:
    """Escape a string for safe use in an AppleScript string literal (``""``).

    Escapes ``\\`` first, then ``"``, so that backslashes before quotes
    do not break the escaping.  AppleScript only recognises ``\\"`` as an
    escape sequence inside a string literal.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _fmt_time(seconds: int) -> str:
    """秒数 → 可读时间"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    mins = (seconds % 3600) // 60
    parts = []
    if days: parts.append(f"{days}天")
    if hours: parts.append(f"{hours}小时")
    if mins: parts.append(f"{mins}分钟")
    secs = seconds % 60
    if secs or not parts: parts.append(f"{secs}秒")
    return "".join(parts)


# ── 自动编译 Swift 工具 ──────────────────────────────────

def _ensure_swift_bin(name: str) -> bool:
    """确保 Swift 二进制已编译到 ~/.zhixing/bin/"""
    binary = os.path.join(_BIN_DIR, name)
    source = os.path.join(_SWIFT_SOURCE_DIR, f"{name}.swift")

    if os.path.exists(binary):
        return True

    if not os.path.exists(source):
        return False

    os.makedirs(_BIN_DIR, exist_ok=True)
    try:
        args = ["swiftc", "-O", "-o", binary, source, "-framework", "Cocoa"]
        if name == "ax_inspector":
            args += ["-framework", "ApplicationServices"]
        if name == "screen_ocr":
            args += ["-framework", "Vision"]
        subprocess.run(args, capture_output=True, timeout=60)
        return os.path.exists(binary)
    except Exception:
        return False


# 启动时编译 Swift 工具
_ensure_swift_bin("ax_inspector")
_ensure_swift_bin("screen_ocr")


# ── 命令处理器（全部返回 str）───────────────────────────

def cmd_system_status(params: dict) -> str:
    """系统状态：CPU、内存、磁盘、网络"""
    if not psutil:
        return "❌ psutil 未安装，无法获取系统状态"
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    disk_str = f"💾 磁盘: {disk.free/1024**3:.1f}/{disk.total/1024**3:.1f} GB 空闲 ({disk.percent}% 已用)"
    try:
        di = subprocess.run(["diskutil", "info", "/"], capture_output=True, text=True, timeout=10)
        out = di.stdout
        import re as _re
        c_total = _re.search(r"Container Total Space:\s+(\S+)\s+(\S+)", out)
        c_free = _re.search(r"Container Free Space:\s+(\S+)\s+(\S+)", out)
        if c_total and c_free:
            def _parse_size(m):
                v = float(m.group(1))
                u = m.group(2)
                if u == "KB": return v * 1024**1
                elif u == "MB": return v * 1024**2
                elif u == "GB": return v * 1024**3
                elif u == "TB": return v * 1024**4
                return v
            total_b = _parse_size(c_total)
            free_b = _parse_size(c_free)
            used_b = total_b - free_b
            used_pct = used_b / total_b * 100
            snap_b = total_b - disk.used * (total_b / disk.total) - free_b
            disk_str = f"💾 磁盘: {free_b/1024**3:.1f}/{total_b/1024**3:.1f} GB 空闲 ({used_pct:.1f}% 已用)"
            if snap_b > 1024**3:
                disk_str += f"\n      📸 APFS 快照: {snap_b/1024**3:.1f} GB（可清理腾出空间）"
    except Exception:
        pass

    return (
        f"📋 系统状态 —— {platform.node()} (macOS {platform.mac_ver()[0]})\n"
        f"  🖥 CPU: {cpu}%\n"
        f"  🧠 内存: {mem.used/1024**3:.1f}/{mem.total/1024**3:.1f} GB ({mem.percent}%)\n"
        f"  {disk_str}\n"
        f"  🌐 网络: ↑{net.bytes_sent/1024/1024:.1f}MB ↓{net.bytes_recv/1024/1024:.1f}MB\n"
        f"  ⏱ 运行: {_fmt_time(int(time.time() - psutil.boot_time()))}\n"
        f"  🔄 进程: {len(psutil.pids())}"
    )


def cmd_mail_read(params: dict) -> str:
    """读取 Mac Mail.app 收件箱（支持 account=账户名，如 iCloud/163）"""
    limit = params.get("limit", 10)
    account = params.get("account", "")
    inbox_ref = "inbox"
    if account:
        find_script = f'''tell application "Mail"
            try
                set msgs to messages of inbox of account "{account}"
                return "inbox"
            on error
                try
                    set msgs to messages of mailbox "INBOX" of account "{account}"
                    return "INBOX"
                on error
                    try
                        set msgs to messages of mailbox "Inbox" of account "{account}"
                        return "Inbox"
                    on error
                        return ""
                    end try
                end try
            end try
        end tell'''
        found = _run_osa(find_script)
        if found:
            inbox_ref = f'mailbox "{found}" of account "{account}"'
        else:
            return f"❌ 未找到账户「{account}」的收件箱"
    script = f"""
    tell application "Mail"
        set output to ""
        set msgs to messages of {inbox_ref}
        set msgCount to count of msgs
        if msgCount > {limit} then set msgs to items 1 through {limit} of msgs
        repeat with m in msgs
            try
                set output to output & "---" & return
                set output to output & "发件人: " & sender of m & return
                set output to output & "主题: " & subject of m & return
                set output to output & "时间: " & date received of m & return
            end try
        end repeat
        return output
    end tell"""
    result = _run_osa(script)
    account_desc = f"[{account}] " if account else ""
    return f"📋 {account_desc}收件箱（最近{limit}封）:\n{result}" if result else f"📭 {account_desc}收件箱为空"


def cmd_mail_master(params: dict) -> str:
    """读取邮箱大师 MailMaster 的邮件（直接读 SQLite 数据库）
    参数: limit=数量, mailbox=邮箱ID(1收件箱), account=账户,
          date=日期筛选(如2026-06-01), since=起始日期, until=截止日期"""
    limit = min(int(params.get("limit", 10)), 50)
    mailbox = params.get("mailbox", "1")
    account = params.get("account", "")
    date_filter = params.get("date", "")
    since_filter = params.get("since", "")
    until_filter = params.get("until", "")

    import glob as _glob
    data_dir = os.path.expanduser(
        "~/Library/Containers/com.netease.macmail/Data/Library/Application Support/data")
    if not os.path.exists(data_dir):
        return "❌ 未找到邮箱大师数据目录，请确认已安装并使用邮箱大师"

    mail_dbs = _glob.glob(os.path.join(data_dir, "*", "mail.db"))
    if not mail_dbs:
        mail_dbs = _glob.glob(os.path.join(data_dir, "**", "mail.db"), recursive=True)

    if not mail_dbs:
        return "❌ 未找到邮箱大师邮件数据库"

    if account:
        target_dbs = [d for d in mail_dbs if account.lower() in d.lower()]
        if target_dbs:
            mail_dbs = target_dbs
        else:
            return f"❌ 未找到账户「{account}」的数据库，可用账户: {', '.join(os.path.basename(os.path.dirname(d)) for d in mail_dbs)}"

    try:
        import sqlite3 as _sqlite3
        from datetime import datetime as _dt
        import json as _json

        all_results = []
        content_db_path = os.path.join(os.path.dirname(mail_dbs[0]), "content.db")
        content_conn = None
        if os.path.exists(content_db_path):
            try:
                content_conn = _sqlite3.connect(content_db_path)
            except Exception:
                pass

        conn = _sqlite3.connect(mail_dbs[0])

        date_conditions = []
        date_params = [mailbox]

        def _parse_date(d: str) -> int:
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%Y%m%d"]:
                try:
                    return int(_dt.strptime(d, fmt).timestamp() * 1000)
                except ValueError:
                    pass
            return 0

        if date_filter:
            ts = _parse_date(date_filter)
            if ts:
                date_conditions.append("ReceivedDate >= ? AND ReceivedDate < ?")
                date_params.extend([ts, ts + 86400000])
        if since_filter:
            ts = _parse_date(since_filter)
            if ts:
                date_conditions.append("ReceivedDate >= ?")
                date_params.append(ts)
        if until_filter:
            ts = _parse_date(until_filter)
            if ts:
                date_conditions.append("ReceivedDate < ?")
                date_params.append(ts + 86400000)

        date_sql = " AND " + " AND ".join(date_conditions) if date_conditions else ""
        date_params.append(limit)

        rows = conn.execute(f"""
            SELECT LocalId, Sender, Subject, Summary, ReceivedDate, Unread
            FROM MailMeta
            WHERE Mailbox = ? AND Deleted = 0{date_sql}
            ORDER BY ReceivedDate DESC LIMIT ?
        """, date_params).fetchall()
        conn.close()

        mailbox_names = {"1": "收件箱", "2": "草稿箱", "3": "已发送", "4": "已删除", "5": "垃圾邮件"}

        for lid, sender_json, subject, summary, rdate, unread in rows:
            try:
                sender_info = _json.loads(sender_json) if sender_json and sender_json.startswith("{") else {"name": str(sender_json)}
                sender_name = sender_info.get("name", sender_info.get("mail", "?"))
                sender_mail = sender_info.get("mail", "")
            except Exception:
                sender_name = str(sender_json or "?")
                sender_mail = ""

            ts = _dt.fromtimestamp(rdate / 1000).strftime("%m-%d %H:%M") if rdate else "?"
            mark = "📩" if unread else "  "
            all_results.append((mark, sender_name, sender_mail, subject[:60] if subject else "(无主题)", ts, summary[:80] if summary else ""))

        detail_id = params.get("detail", "")
        body_text = ""
        if detail_id and content_conn:
            try:
                body_row = content_conn.execute(
                    "SELECT Body FROM Content WHERE LocalId = ? LIMIT 1", (int(detail_id),))
                body_data = body_row.fetchone()
                if body_data:
                    body_text = body_data[0][:2000] if body_data[0] else ""
                content_conn.close()
            except Exception:
                pass

        if not all_results:
            mb_name = mailbox_names.get(mailbox, mailbox)
            return f"📭 邮箱大师 [{mb_name}] 暂无邮件"

        lines = [f"📋 邮箱大师 收件箱（最近{len(all_results)}封）:"]
        for mark, name, mail, subj, ts, summary in all_results:
            addr = f" <{mail}>" if mail else ""
            lines.append(f"  {mark} {name}{addr}")
            lines.append(f"      {subj}")
            if summary and not detail_id:
                lines.append(f"      {summary[:60]}")
            lines.append(f"      {ts}")

        if body_text:
            lines.append(f"\n📄 邮件正文 (ID={detail_id}):\n{body_text[:1500]}")

        if content_conn:
            try: content_conn.close()
            except: pass

        return "\n".join(lines)

    except ImportError:
        return "❌ 需要 sqlite3 支持（Python 内置）"
    except Exception as e:
        return f"❌ 读取邮箱大师失败: {e}"


def cmd_mail_send(params: dict) -> str:
    """通过 Mac Mail.app 发送邮件"""
    raw_to = params.get("to", "")
    raw_subject = params.get("subject", "")
    raw_body = params.get("body", "")
    if not raw_to or not raw_subject:
        return "❌ 需要 to 和 subject 参数"
    to = _osa_escape(raw_to)
    subject = _osa_escape(raw_subject)
    body = _osa_escape(raw_body)
    script = f'''
    tell application "Mail"
        set m to make new outgoing message with properties {{subject:"{subject}", content:"{body}"}}
        tell m to make new to recipient at end of to recipients with properties {{address:"{to}"}}
        send m
    end tell'''
    try:
        _run_osa(script)
        return f"✅ 邮件已发送至 {raw_to}，主题: {raw_subject}"
    except Exception as e:
        return f"❌ 发送失败: {e}"


def cmd_notification(params: dict) -> str:
    """Mac 通知弹窗"""
    raw_text = params.get("text", "Mac Agent 通知")
    raw_title = params.get("title", "Mac Agent Personal")
    raw_subtitle = params.get("subtitle", "")
    text = _osa_escape(raw_text)
    title = _osa_escape(raw_title)
    subtitle = _osa_escape(raw_subtitle)
    script = f'display notification "{text}" with title "{title}"'
    if subtitle:
        script += f' subtitle "{subtitle}"'
    script += ' sound name "default"'
    _run_osa(script)
    return f"✅ 通知已发送: {raw_title} - {raw_text}"


def cmd_file_list(params: dict) -> str:
    """列出目录文件"""
    path = params.get("path", os.path.expanduser("~"))
    try:
        items = os.listdir(path)
        lines = [f"📋 目录: {path}（共{len(items)}项）"]
        for name in items[:30]:
            full = os.path.join(path, name)
            is_dir = os.path.isdir(full)
            size = os.path.getsize(full) if os.path.isfile(full) else 0
            icon = "📁" if is_dir else "📄"
            size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B" if size else "-"
            lines.append(f"  {icon} {name}  ({size_str})")
        if len(items) > 30:
            lines.append(f"  ... 还有 {len(items)-30} 项")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 读取目录失败: {e}"


def cmd_screenshot(params: dict) -> str:
    """截屏并返回文件路径"""
    save_path = params.get("save_path", os.path.expanduser(f"~/Pictures/ka_ss_{int(time.time())}.png"))

    # 用 AppleScript 隐藏悬浮按钮 + 面板
    _HIDE_SCRIPT = '''tell application "Google Chrome"
    execute active tab of window 1 javascript "try{document.getElementById('ka-btn').style.display='none';document.getElementById('ka-panel').style.display='none'}catch(e){}"
end tell'''
    try:
        subprocess.run(["osascript", "-e", _HIDE_SCRIPT], capture_output=True, timeout=10)
    except Exception:
        pass
    time.sleep(0.5)

    # 保存到文件 + 复制到剪贴板（分两步）
    r1 = subprocess.run(["screencapture", save_path], capture_output=True, timeout=10)
    r2 = subprocess.run(["screencapture", "-c"], capture_output=True, timeout=10)

    # 用 AppleScript 恢复按钮
    _SHOW_SCRIPT = '''tell application "Google Chrome"
    execute active tab of window 1 javascript "try{document.getElementById('ka-btn').style.removeProperty('display')}catch(e){}"
end tell'''
    try:
        subprocess.run(["osascript", "-e", _SHOW_SCRIPT], capture_output=True, timeout=10)
    except Exception:
        pass

    if r1.returncode == 0 and os.path.exists(save_path):
        return f"✅ 截屏已保存: {save_path} ({os.path.getsize(save_path)/1024:.1f}KB)\n✅ 图片已复制到剪贴板"
    return "❌ 截屏失败"


def cmd_screenshot_analyze(params: dict) -> str:
    """截屏并用 macOS 原生 Vision OCR 识别文字。region='x,y,w,h'(可选)可指定区域"""
    ocr_bin = os.path.join(_BIN_DIR, "screen_ocr")
    save_path = os.path.expanduser(f"~/Pictures/ka_ocr_{int(time.time())}.png")

    region = params.get("region", "")
    if region:
        parts = region.replace(",", " ").split()
        if len(parts) == 4:
            subprocess.run(["screencapture", "-x", "-R", " ".join(parts), save_path],
                capture_output=True, timeout=10)
        else:
            subprocess.run(["screencapture", "-x", save_path], capture_output=True, timeout=10)
    else:
        subprocess.run(["screencapture", "-x", save_path], capture_output=True, timeout=10)

    if not os.path.exists(save_path):
        return "❌ 截屏失败"

    if os.path.exists(ocr_bin):
        try:
            r = subprocess.run([ocr_bin, save_path], capture_output=True, text=True, timeout=30)
            result = r.stdout.strip()
            try: os.remove(save_path)
            except: pass
            return result
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass

    try:
        with open(save_path, "rb") as f:
            img_data = f.read()
        ocr_result = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", "chi_sim+eng", "--psm", "3"],
            input=img_data, capture_output=True, timeout=30)
        text = ocr_result.stdout.decode("utf-8", errors="ignore").strip()
    except Exception:
        text = ""

    try: os.remove(save_path)
    except: pass

    if text:
        lines = text.split("\n")
        return f"📸 截屏分析 (tesseract)\n🔤 {len(lines)} 行文字:\n{text[:3000]}"
    return f"📸 截屏已保存，但未识别到文字"


def cmd_clipboard_read(params: dict) -> str:
    """读取剪贴板"""
    r = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
    text = r.stdout
    if not text:
        return "📋 剪贴板为空"
    if len(text) > 1000:
        return f"📋 剪贴板内容（前1000字）:\n{text[:1000]}...\n（共{len(text)}字符）"
    return f"📋 剪贴板内容:\n{text}"


def cmd_clipboard_write(params: dict) -> str:
    """写入剪贴板"""
    text = params.get("text", "")
    if not text:
        return "❌ 需要 text 参数"
    subprocess.run(["pbcopy"], input=text, text=True, timeout=5)
    return f"✅ 已写入剪贴板（{len(text)}字符）"


def cmd_calendar(params: dict) -> str:
    """读取日历事件（今天）"""
    script = '''
    tell application "Calendar"
        set output to ""
        set today to current date; set time of today to 0
        set tomorrow to today + 86400
        repeat with c in every calendar
            repeat with e in (every event of c whose start date ≥ today and start date < tomorrow)
                set output to output & "---" & return
                set output to output & "标题: " & summary of e & return
                set output to output & "开始: " & start date of e & return
                set output to output & "结束: " & end date of e & return
            end repeat
        end repeat
        return output
    end tell'''
    result = _run_osa(script)
    return f"📋 今日日程:\n{result}" if result else "📭 今日无日程"


def cmd_music_play(params: dict) -> str:
    """播放/暂停音乐（有参数时搜索 Apple Music 在线曲库）"""
    song = params.get("song", "")
    artist = params.get("artist", "")
    if song or artist:
        keyword = f"{artist} {song}".strip()
        return cmd_music_search_online({"keyword": keyword})
    _run_osa('tell application "Music" to playpause')
    r = subprocess.run(["osascript", "-e",
        'tell application "Music" to if player state is playing then return "✅ 正在播放: " & name of current track & " - " & artist of current track else return "⏸ 已暂停"'],
        capture_output=True, text=True, timeout=5)
    return r.stdout.strip() or "⏸ 已切换播放/暂停"


def cmd_music_next(params: dict) -> str:
    """下一首"""
    _run_osa('tell application "Music" to next track')
    r = subprocess.run(["osascript", "-e",
        'tell application "Music" to return "✅ 已切歌，当前: " & name of current track & " - " & artist of current track'],
        capture_output=True, text=True, timeout=5)
    return r.stdout.strip() or "✅ 已切换到下一首"


def cmd_music_volume(params: dict) -> str:
    """设置音量 0-100"""
    level = min(100, max(0, int(params.get("level", 50))))
    _run_osa(f"set volume output volume {level}")
    return f"✅ 音量已设置为: {level}%"


def cmd_music_search(params: dict) -> str:
    """搜索本地音乐库"""
    keyword = params.get("keyword", "")
    if not keyword:
        return "❌ 需要 keyword 参数"
    safe_keyword = _osa_escape(keyword)
    script = f'''
    tell application "Music"
        set results to (every track whose name contains "{safe_keyword}")
        set output to ""
        repeat with t in results
            set output to output & name of t & " - " & artist of t & return
        end repeat
        return output
    end tell'''
    result = _run_osa(script)
    return f"📋 本地音乐库搜索「{keyword}」:\n{result}" if result else f"❌ 本地音乐库中未找到「{keyword}」"


def cmd_music_search_online(params: dict) -> str:
    """搜索 Apple Music 在线曲库并播放预览（30秒）"""
    keyword = params.get("keyword", "")
    if not keyword:
        return "❌ 需要 keyword 参数"

    try:
        for f in os.listdir("/tmp"):
            if f.startswith("agent_preview_") and f.endswith(".m4a"):
                fp = os.path.join("/tmp", f)
                if time.time() - os.path.getmtime(fp) > 60:
                    os.remove(fp)
    except Exception:
        pass

    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(keyword)}&country=cn&media=music&limit=10"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return f"❌ Apple Music 中未找到「{keyword}」"

        first = results[0]
        songs = [f"  {r['trackName']} — {r['artistName']}" for r in results[:5]]

        preview_url = first.get("previewUrl", "")
        if preview_url:
            local_path = f"/tmp/agent_preview_{int(time.time())}.m4a"
            try:
                subprocess.run(["curl", "-sL", preview_url, "-o", local_path],
                    capture_output=True, timeout=15)
                if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                    subprocess.Popen(["afplay", local_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True)
            except Exception:
                pass

        subprocess.Popen(["osascript", "-e",
            f'open location "{first["trackViewUrl"]}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)

        import time as _time
        _time.sleep(2)
        subprocess.run(["osascript", "-e",
            'tell application "System Events" to tell process "Music" to set frontmost to true'],
            capture_output=True, timeout=3)
        btn = subprocess.run(["osascript", "-e", '''
            tell application "System Events"
                tell process "Music"
                    set elems to entire contents of window 1
                    repeat with e in elems
                        try
                            if description of e is "播放" then
                                set p to position of e; set s to size of e
                                return ((item 1 of p) + (item 1 of s) / 2) as text & "," & ((item 2 of p) + (item 2 of s) / 2) as text
                            end if
                        end try
                    end repeat; return ""
                end tell
            end tell
        '''], capture_output=True, text=True, timeout=5)
        coords = btn.stdout.strip()
        if coords and "," in coords:
            try:
                parts = coords.split(",")
                subprocess.Popen(["cliclick", f"c:{int(float(parts[0]))},{int(float(parts[1]))}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True)
            except Exception:
                pass

        return (
            f"🎵 Apple Music 找到 {data['resultCount']} 首「{keyword}」\n"
            f"▶️ 正在播放: {first['trackName']} — {first['artistName']}（预览30秒）\n"
            f"📱 已在 Music App 中打开完整版\n"
            f"热门结果:\n" + "\n".join(songs)
            + '\n\x1b[2m输入 music_pro 获取歌单管理、推荐等增强功能\x1b[0m'
        )
    except Exception as e:
        return f"❌ 搜索失败: {e}"


# ── Pro 版：Apple Music 增强（歌单/推荐/当前播放） ──────


def cmd_music_pro(params: dict) -> str:
    """🎵 Pro 版 Apple Music 管理 — 歌单/推荐/当前播放/队列。

    参数:
        action (str): now | playlist | playlists | recommendations | queue
        name (str, optional): 歌单名称（action=playlist 时）
    """
    from zhixing.agent.pro import require_pro

    guard = require_pro("enhanced_music")
    if guard is not None:
        return guard

    action = params.get("action", "now")

    if action == "now":
        return _music_now_playing()
    if action == "queue":
        return _music_queue()
    if action == "playlists":
        return _music_list_playlists()
    if action == "playlist":
        name = params.get("name", "")
        return _music_play_playlist(name)
    if action == "recommendations":
        return _music_recommendations()

    return "❌ 未知 action: " + action


def _music_now_playing() -> str:
    """当前正在播放的详细信息。"""
    script = '''
    tell application "Music"
        if player state is playing then
            set t to current track
            set output to "▶️ 正在播放:"
            set output to output & "\\n  名称: " & name of t
            set output to output & "\\n  歌手: " & artist of t
            set output to output & "\\n  专辑: " & album of t
            try
                set output to output & "\\n  时长: " & (duration of t as integer) & "秒"
            end try
            try
                set output to output & "\\n  评分: " & (rating of t as integer) & "/100"
            end try
            try
                set output to output & "\\n  播放次数: " & (played count of t as integer)
            end try
            return output
        else
            return "⏸ 当前未在播放"
        end if
    end tell'''
    return _run_osa(script) or "⏸ 当前未在播放"


def _music_queue() -> str:
    """查看播放队列。"""
    script = '''
    tell application "Music"
        try
            set upcomingTracks to (every track of current playlist)
            set total to count of upcomingTracks
            set currentIdx to 0
            try
                set currentIdx to index of current track
            end try
            set output to "📋 播放队列 (" & total & " 首)"
            set count to 0
            repeat with t in upcomingTracks
                set count to count + 1
                if count >= currentIdx and count < currentIdx + 10 then
                    set marker to "▶️" if count = currentIdx else "  "
                    set output to output & "\\n" & marker & " " & name of t & " - " & artist of t
                end if
            end repeat
            if count > currentIdx + 10 then
                set output to output & "\\n  ... 还有 " & (count - currentIdx - 10) & " 首"
            end if
            return output
        on error
            return "❌ 无法读取队列"
        end try
    end tell'''
    return _run_osa(script) or "📋 队列:（暂无数据）"


def _music_list_playlists() -> str:
    """列出用户歌单。"""
    script = '''
    tell application "Music"
        set output to "📋 我的歌单:"
        set count to 0
        repeat with p in (every playlist whose special kind is none)
            set count to count + 1
            set trackCount to count of tracks in p
            set output to output & "\\n  " & count & ". " & name of p & " (" & trackCount & " 首)"
            if count >= 20 then exit repeat
        end repeat
        if count = 0 then
            set output to "📋 无自定义歌单"
        end if
        return output
    end tell'''
    return _run_osa(script) or "📋 歌单:（暂无数据）"


def _music_play_playlist(name: str) -> str:
    """播放指定歌单。"""
    if not name:
        return "❌ 需要 name 参数（歌单名称）"
    safe = _osa_escape(name)
    script = f'''
    tell application "Music"
        try
            set foundPlaylist to (every playlist whose name contains "{safe}")
            if (count of foundPlaylist) > 0 then
                set targetPlaylist to item 1 of foundPlaylist
                play targetPlaylist
                return "✅ 正在播放歌单: " & name of targetPlaylist
            else
                return "❌ 未找到歌单: {name}"
            end if
        on error
            return "❌ 播放失败"
        end try
    end tell'''
    return _run_osa(script) or f"❌ 播放歌单「{name}」失败"


def _music_recommendations() -> str:
    """基于当前播放推荐类似歌曲。"""
    info = _music_now_playing()
    if "未在播放" in info:
        return "🎵 推荐: 输入 music_search_online keyword=热门 来发现新音乐"

    import re
    m = re.search(r"歌手: (.+)", info)
    if not m:
        return "🎵 无法获取当前歌曲信息"
    artist = m.group(1).strip()

    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(artist)}&country=cn&media=music&limit=5"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return f"🎵 未找到「{artist}」相关推荐"
        songs = [f"  {r['trackName']} — {r['artistName']}" for r in results[:5]]
        return f"🎵 基于「{artist}」的推荐:\n" + "\n".join(songs)
    except Exception:
        return f"🎵 推荐: 试试搜索更多 {artist} 的作品"


def cmd_open_app(params: dict) -> str:
    """打开应用"""
    name = params.get("name", "")
    if not name:
        return "❌ 需要 name 参数（如: Music, Safari, Chrome）"
    r = subprocess.run(["osascript", "-e", f'tell application "{name}" to activate'],
        capture_output=True, text=True, timeout=15)
    if r.returncode == 0:
        return f"✅ 已打开: {name}"
    error = r.stderr.strip() or "应用可能不存在"
    return f"❌ 打开 {name} 失败: {error}"


def cmd_open_url(params: dict) -> str:
    """打开 URL"""
    url = params.get("url", "")
    if not url:
        return "❌ 需要 url 参数"
    subprocess.run(["open", url], capture_output=True, timeout=10)
    return f"✅ 已打开: {url}"


def cmd_battery_status(params: dict) -> str:
    """电池状态"""
    r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10)
    return f"🔋 电池状态:\n{r.stdout.strip()}" if r.stdout.strip() else "❌ 无法获取电池信息"


def cmd_wifi_status(params: dict) -> str:
    """WiFi 状态"""
    r = subprocess.run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
        capture_output=True, text=True, timeout=10)
    return f"📶 WiFi:\n{r.stdout.strip()}" if r.stdout.strip() else "📶 WiFi: 未连接或不可用"


def cmd_keyboard_type(params: dict) -> str:
    """在当前焦点处输入文字。短文本用 cliclick 打字，长文本(>50字)用剪贴板+粘贴"""
    text = params.get("text", "")
    if not text:
        return "❌ 需要 text 参数"

    if len(text) > 50 or any(c in text for c in "\"'\\\n\t"):
        subprocess.run(["pbcopy"], input=text, text=True, timeout=5)
        _run_osa('tell application "System Events" to keystroke "v" using command down', timeout=5)
        return f"⌨️ 已粘贴: {text[:50]}{'...' if len(text) > 50 else ''}（{len(text)}字符）"

    import shutil
    if shutil.which("cliclick"):
        safe_text = text.replace("'", "'\\''")
        subprocess.run(["cliclick", f"t:{safe_text}"], capture_output=True, timeout=10)
    else:
        safe = text.replace('"', '\\"')
        _run_osa(f'tell application "System Events" to keystroke "{safe}"', timeout=10)

    return f"⌨️ 已输入: {text[:50]}{'...' if len(text) > 50 else ''}"


_KEY_CODES = {
    "enter": 36, "return": 36, "tab": 48, "space": 49, "delete": 51, "backspace": 51,
    "esc": 53, "escape": 53,
    "left": 123, "right": 124, "down": 125, "up": 126,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "home": 115, "end": 119, "pgup": 116, "pgdn": 121,
    "pageup": 116, "pagedown": 121, "capslock": 57,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
    "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31,
    "p": 35, "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9,
    "w": 13, "x": 7, "y": 16, "z": 6,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23,
    "6": 22, "7": 26, "8": 28, "9": 25,
    "-": 27, "=": 24, "[": 33, "]": 30, ";": 41, "'": 39,
    ",": 43, ".": 47, "/": 44, "`": 50, "\\": 42,
}


def cmd_keyboard_press(params: dict) -> str:
    """模拟键盘按键或快捷键。
    key=键名(如enter/tab/space/a/b/ctrl_c/f5等，复合键用下划线连接如ctrl_c=Ctrl+C)，
    modifiers=修饰键列表(可选，如cmd/shift/option/ctrl)"""
    key = params.get("key", "").lower().strip()
    modifiers = params.get("modifiers", [])
    if isinstance(modifiers, str):
        modifiers = [m.strip().lower() for m in modifiers.split(",")]

    if not key:
        return "❌ 需要 key 参数"

    if "_" in key and not modifiers:
        parts = key.split("_")
        if len(parts) == 2 and parts[0] in ("cmd","shift","option","alt","ctrl","control"):
            modifiers = [parts[0]]
            key = parts[1]

    mods = _build_modifiers(modifiers)

    if len(key) == 1 and key.isalnum():
        _run_osa(f'tell application "System Events" to keystroke "{key}"{{{mods}}}', timeout=10)
        desc = "+".join(modifiers) + "+" if modifiers else ""
        return f"⌨️ 已按下: {desc}{key}"

    code = _KEY_CODES.get(key)
    if code is not None:
        _run_osa(f'tell application "System Events" to key code {code}{{{mods}}}', timeout=10)
        desc = "+".join(modifiers) + "+" if modifiers else ""
        return f"⌨️ 已按下: {desc}{key}"

    return f"❌ 不支持的键: {key}（支持: enter/tab/space/a-z/0-9/f1-f12/ctrl_c等）"


def _build_modifiers(modifiers: list[str]) -> str:
    """构建 AppleScript 修饰键字符串"""
    if not modifiers:
        return ""
    parts = []
    for m in modifiers:
        if m in ("cmd", "command"): parts.append("command down")
        elif m in ("shift",): parts.append("shift down")
        elif m in ("option", "alt"): parts.append("option down")
        elif m in ("ctrl", "control"): parts.append("control down")
    if not parts:
        return ""
    return " using {" + ", ".join(parts) + "}"


def cmd_ui_tree(params: dict) -> str:
    """获取 UI 元素树（Swift 原生 AX API）。app=应用名(可选，默认前台)，depth=深度(默认6)"""
    app_name = params.get("app", "")
    depth = min(int(params.get("depth", 6)), 10)
    inspector = os.path.join(_BIN_DIR, "ax_inspector")

    args = [inspector, "--depth", str(depth)]
    if app_name:
        args += ["--app", app_name]
    else:
        args += ["--frontmost"]

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or "❌ 无输出"
    except FileNotFoundError:
        return "❌ 未找到 ax_inspector"
    except Exception as e:
        return f"❌ 执行失败: {e}"


def cmd_ui_find(params: dict) -> str:
    """在 UI 树中搜索元素（Swift 原生 AX API）。desc=描述关键词，role=角色(可选)，app=应用名(可选)"""
    desc = params.get("desc", "")
    role = params.get("role", "")
    app_name = params.get("app", "")
    if not desc and not role:
        return "❌ 需要 desc 或 role 参数"

    inspector = os.path.join(_BIN_DIR, "ax_inspector")
    args = [inspector, "--find", desc or ""]
    if role:
        args += ["--role", role]
    if app_name:
        args += ["--app", app_name]
    else:
        args += ["--frontmost"]

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or f"❌ 未找到匹配元素"
    except FileNotFoundError:
        return "❌ 未找到 ax_inspector"
    except Exception as e:
        return f"❌ 搜索失败: {e}"


def cmd_ui_click(params: dict) -> str:
    """点击 UI 元素（Swift 原生 AX API）。desc=元素描述(必须)，app=应用名(可选)"""
    desc = params.get("desc", "")
    if not desc:
        return "❌ 需要 desc 参数"

    app_name = params.get("app", "")
    inspector = os.path.join(_BIN_DIR, "ax_inspector")
    args = [inspector, "--click", desc]
    if app_name:
        args += ["--app", app_name]
    else:
        args += ["--frontmost"]

    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15)
        result = r.stdout.strip()

        if not result:
            return f"❌ 未找到「{desc}」"

        if result.startswith("✅"):
            return result

        if result.startswith("pos:"):
            coords = result[4:]
            parts = coords.split(",")
            try:
                cx = int(float(parts[0].strip()))
                cy = int(float(parts[1].strip()))
                subprocess.run(["cliclick", f"c:{cx},{cy}"], timeout=5)
                return f"✅ 已点击「{desc}」({cx},{cy})"
            except (ValueError, IndexError):
                return f"❌ 坐标解析失败: {coords}"

        return result
    except FileNotFoundError:
        return "❌ 未找到 ax_inspector"
    except Exception as e:
        return f"❌ 点击失败: {e}"


def cmd_speak(params: dict) -> str:
    """语音朗读"""
    text = params.get("text", "Hello")
    subprocess.run(["say", text], capture_output=True, timeout=30)
    return f"🔊 已朗读: {text[:50]}{'...' if len(text) > 50 else ''}"


def cmd_lock_screen(params: dict) -> str:
    """锁定屏幕"""
    _run_osa('tell application "System Events" to sleep')
    return "🔒 屏幕已锁定"


def cmd_reminder_add(params: dict) -> str:
    """添加提醒事项"""
    text = params.get("text", "")
    if not text:
        return "❌ 需要 text 参数"
    safe_text = _osa_escape(text)
    _run_osa(f'tell application "Reminders" to make new reminder with properties {{name:"{safe_text}"}}')
    return f"✅ 提醒已添加: {text}"


def cmd_notes_list(params: dict) -> str:
    """列出备忘录"""
    result = _run_osa('tell application "Notes" to set output to ""\nrepeat with n in every note\nset output to output & name of n & return\nend repeat\nreturn output')
    return f"📋 备忘录列表:\n{result}" if result else "📭 暂无备忘录"


def cmd_contacts_search(params: dict) -> str:
    """搜索联系人"""
    kw = params.get("keyword", "")
    if not kw:
        return "❌ 需要 keyword 参数"
    safe_kw = _osa_escape(kw)
    script = f'''tell application "Contacts"
        set output to ""
        set people to every person whose name contains "{safe_kw}"
        repeat with p in people
            set output to output & name of p & return
        end repeat
        return output
    end tell'''
    result = _run_osa(script)
    return f"📋 联系人搜索「{kw}」:\n{result}" if result else f"❌ 未找到联系人: {kw}"


# ── 命令注册表 ───────────────────────────────────────────

def cmd_workflow_execute(params: dict) -> str:
    """执行多步工作流。steps=[{"cmd":"命令名","params":{…},"wait":1.0,"desc":"说明"},…]"""
    steps = params.get("steps", [])
    if not steps or not isinstance(steps, list):
        return "❌ 需要 steps 参数，格式: [{\"cmd\":\"命令名\",\"params\":{…}}]"

    results = []
    total = len(steps)
    for i, step in enumerate(steps, 1):
        cmd = step.get("cmd", "")
        step_params = step.get("params", {})
        desc = step.get("desc", cmd)
        wait = float(step.get("wait", 0.5))

        handler = COMMANDS.get(cmd)
        if not handler:
            results.append(f"  [{i}/{total}] ❌ 未知命令: {cmd}（跳过）")
            continue

        try:
            result = handler(step_params)
            results.append(f"  [{i}/{total}] ✅ {desc}")
            if isinstance(result, str) and len(result) > 200:
                results.append(f"     {result[:200]}...")
            elif isinstance(result, str):
                results.append(f"     {result}")
        except Exception as e:
            results.append(f"  [{i}/{total}] ❌ {desc} 失败: {e}")

        if wait > 0:
            import time as _t
            _t.sleep(wait)

    success = sum(1 for r in results if "✅" in r)
    return (
        f"📋 工作流完成（{success}/{total} 步成功）:\n" + "\n".join(results)
    )


# ── 个人知识库 (RAG) ─────────────────────────────────────
_knowledge_retriever = None


def set_rag(retriever):
    """Inject RAG instance from Agent."""
    global _knowledge_retriever
    _knowledge_retriever = retriever


# ── 配置注入 ────────────────────────────────────────────────
_config_instance = None


def set_config(config):
    """Inject the active Config instance for hot-reload support."""
    global _config_instance
    _config_instance = config


def knowledge_retrieve(query: str, n_results: int = 5) -> str:
    """搜索个人文档和笔记。当用户问到自己文件、笔记、文档时使用此工具。
    自动懒加载 RAG（首次调用时初始化）。
    """
    global _knowledge_retriever
    if not _knowledge_retriever or not _knowledge_retriever._initialized:
        try:
            from zhixing.config import Config
            from zhixing.memory.rag import PersonalRAG
            rag = PersonalRAG(Config())
            if rag.init():
                set_rag(rag)
        except Exception:
            pass
    if not _knowledge_retriever or not _knowledge_retriever._initialized:
        return "个人知识库未启用。请先运行: rag init"
    results = _knowledge_retriever.search(query, n_results=n_results)
    if not results:
        return f"未找到与「{query}」相关的文档。"
    formatted = []
    for r in results:
        formatted.append(f"[来源: {r['source']}]\n{r['content']}")
    return "\n\n---\n\n".join(formatted)


# ── 语音输入 ─────────────────────────────────────────────

def cmd_voice_input(params: dict) -> str:
    """开始语音输入并返回识别结果。调用后等待用户说话。"""
    try:
        import speech_recognition as sr
    except ImportError:
        return "❌ 需要安装 SpeechRecognition: pip install SpeechRecognition"
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        # 先用 Google 在线识别（中文准确度高）
        try:
            text = r.recognize_google(audio, language="zh-CN")
            return f"🎤 语音识别结果: {text}"
        except sr.UnknownValueError:
            pass
        # 回退到 macOS 内置识别
        try:
            text = r.recognize_sphinx(audio)
            return f"🎤 语音识别结果: {text}"
        except Exception:
            return "❌ 无法识别语音内容（请确保麦克风已授权并尝试靠近说话）"
    except sr.WaitTimeoutError:
        return "⏱ 等待语音超时（5秒内未说话）"
    except OSError as e:
        return f"❌ 麦克风不可用: {e}"
    except Exception as e:
        return f"❌ 语音输入失败: {e}"


# ── 命令注册表 ───────────────────────────────────────────

def cmd_vpn_status(params: dict) -> str:
    """VPN 工具 — 连接检测、代理管理、浏览器登录。
    action=status/enable/disable/connect/disconnect/login/fortinet/type/check/safari"""
    from zhixing.agent.vpn import VpnClient

    action = params.get("action", "status")
    vpn = VpnClient()

    # 切换 VPN 类型
    vpn_type = params.get("vpn_type", "")
    if vpn_type:
        return vpn.switch_type(vpn_type)

    actions = {
        "status": lambda: vpn.quick_check(),
        "check": lambda: vpn.quick_check(),
        "enable": lambda: vpn.enable_proxy(),
        "disable": lambda: vpn.disable_proxy(),
        "connect": lambda: vpn.connect(),
        "disconnect": lambda: vpn.disconnect(),
        "login": lambda: vpn.open_browser(),
        "browser": lambda: vpn.open_browser(),
        "safari": lambda: vpn.open_safari(),
        # Fortinet 专用
        "fortinet": lambda: f"{vpn.switch_type('fortinet')}\n\n{vpn.fortinet_connect()}",
        "fortinet_connect": lambda: vpn.fortinet_connect(),
        "fortinet_disconnect": lambda: vpn.fortinet_disconnect(),
        "fortinet_status": lambda: vpn.quick_check(),
    }

    handler = actions.get(action)
    if handler:
        return handler()

    # 显示帮助 + 当前配置
    vpn_type_names = {"atrust": "深信服 aTrust", "fortinet": "FortiGate (openfortivpn)"}
    cur_type = vpn_type_names.get(vpn.vpn_type, vpn.vpn_type)
    cfg = vpn.get_config()

    lines = [
        "📋 VPN 工具 — 可用操作:",
        f"  当前 VPN 类型: {cur_type} ({cfg['vpn_host']}:{cfg['vpn_port']})",
        "",
        "  通用操作:",
        "    vpn_status action=status      查看完整状态（含连通性检测）",
        "    vpn_status action=check       连通性检测",
        "    vpn_status action=enable      启用代理（aTrust）",
        "    vpn_status action=disable     禁用代理",
        "    vpn_status action=login       在浏览器中打开 VPN 登录页",
        "    vpn_status action=connect     一键连接",
        "",
        "  FortiGate VPN (openfortivpn):",
        "    vpn_status action=fortinet    切换到 Fortinet 并连接",
        "    vpn_status action=fortinet_connect     连接 Fortinet",
        "    vpn_status action=fortinet_disconnect  断开 Fortinet",
        "    vpn_status vpn_type=fortinet  切换到 Fortinet 模式",
        "    vpn_status vpn_type=atrust    切换到 aTrust 模式",
        "",
        f"  🔌 代理: {'🟢 已启用' if cfg['enabled'] else '🔴 已禁用'}",
        f"  🌐 VPN:  {cfg['vpn_host']}:{cfg['vpn_port']}",
        f"  📄 配置: {cfg['config_file']}",
    ]
    return "\n".join(lines)


def cmd_knowledge_retrieve(params: dict) -> str:
    """搜索个人文档和笔记。query=搜索关键词"""
    query = params.get("query", "")
    if not query:
        return "❌ 需要 query 参数"
    return knowledge_retrieve(query, n_results=int(params.get("n_results", 5)))


_COMMANDS_EXTRA = {
    "voice_input": cmd_voice_input,
    "knowledge_retrieve": cmd_knowledge_retrieve,
    "music_pro": cmd_music_pro,
}

COMMANDS = {
    "system_status": cmd_system_status,
    "mail_read": cmd_mail_read,
    "mail_master": cmd_mail_master,
    "mail_send": cmd_mail_send,
    "notification": cmd_notification,
    "file_list": cmd_file_list,
    "screenshot": cmd_screenshot,
    "screenshot_analyze": cmd_screenshot_analyze,
    "clipboard_read": cmd_clipboard_read,
    "clipboard_write": cmd_clipboard_write,
    "calendar": cmd_calendar,
    "music_play": cmd_music_play,
    "music_next": cmd_music_next,
    "music_volume": cmd_music_volume,
    "music_search": cmd_music_search,
    "music_search_online": cmd_music_search_online,
    "open_app": cmd_open_app,
    "open_url": cmd_open_url,
    "battery_status": cmd_battery_status,
    "wifi_status": cmd_wifi_status,
    "speak": cmd_speak,
    "keyboard_type": cmd_keyboard_type,
    "keyboard_press": cmd_keyboard_press,
    "ui_tree": cmd_ui_tree,
    "ui_find": cmd_ui_find,
    "ui_click": cmd_ui_click,
    "lock_screen": cmd_lock_screen,
    "reminder_add": cmd_reminder_add,
    "notes_list": cmd_notes_list,
    "contacts_search": cmd_contacts_search,
    "workflow_execute": cmd_workflow_execute,
    "vpn_status": cmd_vpn_status,
}

# Merge extra commands
COMMANDS.update(_COMMANDS_EXTRA)
# knowledge_retrieve is injected via set_rag() and used by Agent's SYSTEM_PROMPT


# ── LLM Tool Definitions ────────────────────────────────

TOOL_SCHEMAS: dict = {
    "music_pro": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["now", "queue", "playlists", "playlist", "recommendations"],
                "description": "操作: now=当前播放, queue=队列, playlists=歌单列表, playlist=播放歌单, recommendations=推荐",
            },
            "name": {
                "type": "string",
                "description": "歌单名称（action=playlist 时）",
            },
        },
        "required": ["action"],
    },
    "music_search_online": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词，如周杰伦"}
        },
        "required": ["keyword"],
    },
    "mail_read": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "读取邮件数量，默认10"},
            "account": {"type": "string", "description": "邮件账户名（如 iCloud/163）"},
        },
    },
    "mail_send": {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "收件人邮箱"},
            "subject": {"type": "string", "description": "邮件主题"},
            "body": {"type": "string", "description": "邮件正文（可选）"},
        },
        "required": ["to", "subject"],
    },
    "screenshot_analyze": {
        "type": "object",
        "properties": {
            "region": {"type": "string", "description": "截屏区域 x,y,w,h（可选）"},
        },
    },
    "keyboard_type": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要输入的文字"},
        },
        "required": ["text"],
    },
    "keyboard_press": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "键名如 enter/tab/space/ctrl_c"},
            "modifiers": {"type": "string", "description": "修饰键，逗号分隔如 cmd,shift"},
        },
        "required": ["key"],
    },
    "ui_click": {
        "type": "object",
        "properties": {
            "desc": {"type": "string", "description": "元素描述/标题"},
            "app": {"type": "string", "description": "应用名（可选）"},
        },
        "required": ["desc"],
    },
    "ui_find": {
        "type": "object",
        "properties": {
            "desc": {"type": "string", "description": "要查找的元素描述"},
            "role": {"type": "string", "description": "角色过滤（可选），如 AXButton"},
            "app": {"type": "string", "description": "应用名（可选）"},
        },
    },
    "open_app": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "应用名称，如 Music/Safari/Chrome"},
        },
        "required": ["name"],
    },
    "open_url": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "完整 URL 地址"},
        },
        "required": ["url"],
    },
    "contacts_search": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "联系人姓名关键词"},
        },
        "required": ["keyword"],
    },
    "reminder_add": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "提醒内容"},
        },
        "required": ["text"],
    },
    "music_volume": {
        "type": "object",
        "properties": {
            "level": {"type": "integer", "description": "音量 0-100"},
        },
    },
    "music_search": {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "搜索关键词"},
        },
        "required": ["keyword"],
    },
    "notification": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "通知文本"},
            "title": {"type": "string", "description": "通知标题（可选）"},
        },
        "required": ["text"],
    },
    "file_list": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "目录路径，默认 ~"},
        },
    },
    "speak": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要朗读的文字"},
        },
        "required": ["text"],
    },
    "clipboard_write": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "要写入剪贴板的内容"},
        },
        "required": ["text"],
    },
    "mail_master": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "读取邮件数量，默认10，最大50"},
            "account": {"type": "string", "description": "邮箱大师账户名"},
            "since": {"type": "string", "description": "起始日期，如 2026-06-01"},
            "until": {"type": "string", "description": "截止日期，如 2026-06-30"},
            "detail": {"type": "string", "description": "邮件 LocalId，查看正文"},
        },
    },
    "vpn_status": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作: status(连通性检测), enable(启用代理), disable(禁用代理), connect(一键连接), disconnect(断开), login(浏览器打开), fortinet(切换到Fortinet并连接), fortinet_connect, fortinet_disconnect",
                "enum": ["status", "check", "enable", "disable", "connect", "disconnect", "login", "browser", "safari", "fortinet", "fortinet_connect", "fortinet_disconnect", "fortinet_status"],
            },
            "vpn_type": {
                "type": "string",
                "description": "切换 VPN 类型: atrust(深信服,默认) 或 fortinet(FortiGate openfortivpn)",
                "enum": ["atrust", "fortinet"],
            },
        },
    },
    "knowledge_retrieve": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词，如「机器学习的笔记」"},
            "n_results": {"type": "integer", "description": "返回结果数量，默认5"},
        },
        "required": ["query"],
    },
}


# Register todo commands
from zhixing.agent.todo import (
    cmd_todo_add, cmd_todo_list, cmd_todo_done,
    cmd_todo_undo, cmd_todo_delete, cmd_todo_reminders,
)

COMMANDS.update({
    "todo_add": cmd_todo_add,
    "todo_list": cmd_todo_list,
    "todo_done": cmd_todo_done,
    "todo_undo": cmd_todo_undo,
    "todo_delete": cmd_todo_delete,
    "todo_reminders": cmd_todo_reminders,
})
TOOL_SCHEMAS.update({
    "todo_add": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "事项内容"},
            "priority": {"type": "string", "description": "优先级 high/medium/low", "enum": ["high", "medium", "low"]},
            "category": {"type": "string", "description": "分类"},
            "due_date": {"type": "string", "description": "截止日期 YYYY-MM-DD"},
        },
        "required": ["title"],
    },
    "todo_list": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "分类过滤"},
            "include_done": {"type": "string", "description": "包含已完成"},
        },
    },
    "todo_done": {
        "type": "object",
        "properties": {"id": {"type": "integer", "description": "事项编号"}},
        "required": ["id"],
    },
    "todo_undo": {
        "type": "object",
        "properties": {"id": {"type": "integer", "description": "事项编号"}},
        "required": ["id"],
    },
    "todo_delete": {
        "type": "object",
        "properties": {"id": {"type": "integer", "description": "事项编号"}},
        "required": ["id"],
    },
    "todo_reminders": {"type": "object", "properties": {}},
})

# Register commands from tool modules (ai_tools, dev_tools, file_tools, etc.)
register_all(COMMANDS, TOOL_SCHEMAS)

# ── 运行时命令注册（供插件系统使用）────────────────────

def register_command(name: str, handler, schema: dict | None = None) -> None:
    """动态注册一个新命令。供插件系统调用。"""
    COMMANDS[name] = handler
    if schema:
        TOOL_SCHEMAS[name] = schema


def unregister_command(name: str) -> None:
    """动态卸载一个命令。供插件系统调用。"""
    COMMANDS.pop(name, None)
    TOOL_SCHEMAS.pop(name, None)


def get_tool_definitions() -> list[dict]:
    """Generate OpenAI-compatible tool definitions for all commands."""
    defs = []
    for name, func in COMMANDS.items():
        desc = (func.__doc__ or "").strip().split("\n")[0]
        schema = TOOL_SCHEMAS.get(name, {
            "type": "object",
            "properties": {},
        })
        defs.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            },
        })
    return defs
