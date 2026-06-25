"""番茄钟窗口 — macOS 倒计时 GUI。

采用子进程模式启动 tkinter，避免 macOS tkinter 主线程限制。
- 大字体倒计时显示 (MM:SS)
- 暂停/继续/取消
- 窗口置顶，不阻塞终端
- 完成后通知 + 语音
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap


def start_timer(minutes: int = 25, name: str = "番茄钟") -> str:
    """启动番茄钟（子进程模式，不阻塞主进程）。"""
    # 生成独立 timer 脚本
    script = textwrap.dedent(f'''\
    import tkinter as tk
    from tkinter import font
    import subprocess as _sp
    import sys

    root = tk.Tk()
    root.title("🍅 {name}")
    root.geometry("320x240")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    bg = "#2c2c2c"
    accent = "#e67e22"
    root.configure(bg=bg)

    remaining = {minutes} * 60
    paused = False
    paused_remaining = remaining

    # ── 倒计时数字 ──
    timer_font = font.Font(family="Helvetica Neue", size=64, weight="bold")
    label = tk.Label(root, text="", font=timer_font, bg=bg, fg=accent)
    label.pack(pady=(30, 5))

    # ── 进度条 ──
    canvas = tk.Canvas(root, width=260, height=8, bg="#444", highlightthickness=0)
    canvas.pack(pady=5)
    bar = canvas.create_rectangle(0, 0, 0, 8, fill=accent, outline="")

    # ── 状态文字 ──
    status_font = font.Font(family="Helvetica Neue", size=12)
    status = tk.Label(root, text="{name}", font=status_font, bg=bg, fg="#aaa")
    status.pack(pady=2)

    # ── 按钮 ──
    def toggle_pause():
        global paused, paused_remaining, remaining
        if not paused:
            paused = True
            paused_remaining = remaining
            btn.config(text="▶ 继续")
            status.config(text="⏸ 已暂停", fg="#f1c40f")
            label.config(fg="#f1c40f")
        else:
            paused = False
            remaining = paused_remaining
            btn.config(text="⏸ 暂停")
            status.config(text="", fg="#aaa")
            label.config(fg=accent)

    def cancel():
        root.after_cancel(timer_id) if "timer_id" in dir() else None
        root.destroy()
        sys.exit(0)

    def finish():
        root.after_cancel(timer_id)
        label.config(text="✅ 完成！", fg="#2ecc71")
        status.config(text="🎉 时间到！", fg="#2ecc71")
        btn.config(text="✔ 关闭", command=root.destroy)
        _sp.run(["osascript", "-e", 'display notification "🍅 时间到！" with title "番茄钟" sound name "default"'], capture_output=True)
        _sp.run(["say", "时间到"], capture_output=True)
        root.after(3000, root.destroy)

    def tick():
        global remaining, timer_id
        if paused:
            timer_id = root.after(500, tick)
            return
        if remaining <= 0:
            finish()
            return
        remaining -= 1
        m, s = divmod(remaining, 60)
        label.config(text=f"{{m:02d}}:{{s:02d}}")
        bar_w = int(260 * (1 - remaining / ({minutes} * 60)))
        canvas.coords(bar, 0, 0, bar_w, 8)
        timer_id = root.after(1000, tick)

    btn_frame = tk.Frame(root, bg=bg)
    btn_frame.pack(pady=(10, 0))
    s = {{"font": ("Helvetica Neue", 11), "bg": "#444", "fg": "white",
          "relief": "flat", "padx": 16, "pady": 6, "activebackground": "#555"}}
    btn = tk.Button(btn_frame, text="⏸ 暂停", command=toggle_pause, **s)
    btn.pack(side="left", padx=6)
    tk.Button(btn_frame, text="✕ 取消", command=cancel, **s).pack(side="left", padx=6)

    root.bind("<space>", lambda e: toggle_pause())
    root.bind("<Escape>", lambda e: cancel())

    tick()
    root.mainloop()
    ''')

    # 写入临时文件并启动子进程
    fd, path = tempfile.mkstemp(suffix=".py", prefix="tomato_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(script)
        subprocess.Popen(
            [sys.executable, path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return f"❌ 启动番茄钟失败: {e}"

    return f"🍅 [{name}] {minutes} 分钟倒计时已启动（窗口已打开）"

