"""番茄钟窗口 — macOS 原生 Swift 窗口。

使用独立编译的 Swift 二进制（swift/timer_window），
保证窗口始终显示在最前方。
"""

from __future__ import annotations

import os
import subprocess
import sys

_SWIFT_BIN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "swift", "timer_window",
)


def _ensure_binary() -> str | None:
    """确保 Swift 二进制已编译。"""
    if os.path.exists(_SWIFT_BIN):
        return _SWIFT_BIN
    source = _SWIFT_BIN + ".swift"
    if not os.path.exists(source):
        return None
    try:
        subprocess.run(
            ["swiftc", "-O", "-o", _SWIFT_BIN, source],
            capture_output=True, timeout=60,
        )
        return _SWIFT_BIN if os.path.exists(_SWIFT_BIN) else None
    except Exception:
        return None


def start_timer(minutes: int = 25, name: str = "番茄钟") -> str:
    """启动番茄钟。"""
    binary = _ensure_binary()
    if binary:
        subprocess.Popen(
            [binary, str(minutes), name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"🍅 [{name}] {minutes} 分钟倒计时已启动"

    # 回退: tkinter
    try:
        return _start_tkinter(minutes, name)
    except Exception:
        pass

    # 再回退: 通知模式
    _notify(name, f"{minutes} 分钟倒计时开始")
    import time
    time.sleep(minutes * 60)
    _notify(name, "时间到！")
    _say("时间到")
    return f"✅ [{name}] {minutes} 分钟计时结束"


def _start_tkinter(minutes: int, name: str) -> str:
    """回退: tkinter 窗口（子进程）。"""
    import textwrap
    import tempfile

    script = textwrap.dedent(f'''\
    import tkinter as tk
    from tkinter import font
    import subprocess as _sp

    root = tk.Tk()
    root.title("🍅 {name}")
    root.geometry("320x240")
    root.attributes("-topmost", True)
    root.lift()

    remaining = {minutes} * 60
    paused = False
    paused_remaining = remaining

    timer_font = font.Font(family="Helvetica Neue", size=64, weight="bold")
    label = tk.Label(root, text="", font=timer_font, bg="#2c2c2c", fg="#e67e22")
    label.pack(pady=(30, 5))

    canvas = tk.Canvas(root, width=260, height=8, bg="#444", highlightthickness=0)
    canvas.pack(pady=5)
    bar = canvas.create_rectangle(0, 0, 0, 8, fill="#e67e22", outline="")

    status = tk.Label(root, text="{name}", font=("Helvetica Neue", 12), bg="#2c2c2c", fg="#aaa")
    status.pack(pady=2)

    def toggle():
        global paused, paused_remaining, remaining
        nonlocal paused, paused_remaining, remaining
        if not paused:
            paused = True; paused_remaining = remaining
            btn.config(text="▶ 继续")
            label.config(fg="#f1c40f")
            status.config(text="⏸ 已暂停", fg="#f1c40f")
        else:
            paused = False; remaining = paused_remaining
            btn.config(text="⏸ 暂停")
            label.config(fg="#e67e22")
            status.config(text="", fg="#aaa")

    def cancel():
        root.destroy()

    def finish():
        label.config(text="✅ 完成！", fg="#2ecc71")
        status.config(text="🎉 时间到！", fg="#2ecc71")
        btn.config(text="✔ 关闭", command=root.destroy)
        _sp.run(["osascript", "-e", 'display notification "🍅 时间到！" with title "番茄钟"'], capture_output=True)
        _sp.run(["say", "时间到"], capture_output=True)
        root.after(3000, root.destroy)

    def tick():
        nonlocal remaining
        if paused:
            root.after(500, tick); return
        remaining -= 1
        if remaining <= 0: finish(); return
        m, s = divmod(remaining, 60)
        label.config(text=f"{{m:02d}}:{{s:02d}}")
        bar_w = int(260 * (1 - remaining / ({minutes} * 60)))
        canvas.coords(bar, 0, 0, bar_w, 8)
        root.after(1000, tick)

    btn_f = tk.Frame(root, bg="#2c2c2c")
    btn_f.pack(pady=(10, 0))
    btn = tk.Button(btn_f, text="⏸ 暂停", command=toggle,
        font=("Helvetica Neue", 11), bg="#444", fg="white", relief="flat", padx=16, pady=6)
    btn.pack(side="left", padx=6)
    tk.Button(btn_f, text="✕ 取消", command=cancel,
        font=("Helvetica Neue", 11), bg="#444", fg="white", relief="flat", padx=16, pady=6
    ).pack(side="left", padx=6)
    root.bind("<space>", lambda e: toggle())
    root.bind("<Escape>", lambda e: cancel())
    tick()
    root.mainloop()
    ''')

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
    return f"🍅 [{name}] {minutes} 分钟倒计时已启动"


def _notify(title: str, text: str):
    subprocess.run(
        ["osascript", "-e",
         f'display notification "{text}" with title "{title}" sound name "default"'],
        capture_output=True, timeout=5,
    )


def _say(text: str):
    subprocess.run(["say", text], capture_output=True, timeout=10)
