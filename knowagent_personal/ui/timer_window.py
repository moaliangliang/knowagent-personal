"""番茄钟窗口 — macOS 倒计时 GUI。

基于 tkinter 实现:
- 大字体倒计时显示 (MM:SS)
- 暂停/继续/取消
- 窗口置顶，不阻塞终端
- 完成后通知 + 可选朗读
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field

TIMER_CONFIG = os.path.expanduser("~/.knowagent/timer_config.json")
DEFAULT_CONFIG = {
    "work_minutes": 25,
    "break_minutes": 5,
    "long_break_minutes": 15,
    "pomodoros_before_long_break": 4,
    "sound_enabled": True,
    "auto_start_break": False,
}


def _load_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(TIMER_CONFIG):
        try:
            with open(TIMER_CONFIG) as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception:
            pass
    return config


@dataclass
class TimerState:
    """番茄钟状态。"""
    phase: str = "idle"           # idle / working / break / long_break / paused
    minutes: int = 25
    seconds: int = 0
    remaining: int = 0            # 剩余秒数
    pomodoros: int = 0            # 已完成番茄数
    elapsed: int = 0              # 已用秒数
    paused_remaining: int = 0     # 暂停时剩余秒数
    callbacks: dict = field(default_factory=dict)

    @property
    def display(self) -> str:
        m = self.remaining // 60
        s = self.remaining % 60
        return f"{m:02d}:{s:02d}"

    @property
    def progress(self) -> float:
        if self.minutes <= 0:
            return 0
        total = self.minutes * 60
        return (total - self.remaining) / total


class TomatoWindow:
    """番茄钟窗口 — tkinter 倒计时 GUI。

    用法:
        win = TomatoWindow()
        win.start(minutes=25, name="专注")
        win.wait()  # 可选：阻塞直到完成
    """

    def __init__(self):
        self._root = None
        self._label = None
        self._progress = None
        self._pause_btn = None
        self._state = TimerState()
        self._timer_id = None
        self._done_event = threading.Event()

    def start(self, minutes: int = 25, name: str = "番茄钟") -> str:
        """启动番茄钟。返回结果字符串。"""
        self._state.minutes = minutes
        self._state.remaining = minutes * 60
        self._state.phase = "working"

        # 在后台线程启动 tkinter
        thread = threading.Thread(target=self._run_gui, args=(name,), daemon=True)
        thread.start()

        # 等待完成或被取消
        self._done_event.wait()

        # 清理
        if self._state.phase == "cancelled":
            return f"❌ [{name}] 已取消"
        return f"✅ [{name}] {minutes} 分钟完成 🍅"

    def _run_gui(self, name: str):
        """运行 GUI 主循环。"""
        import tkinter as tk
        from tkinter import font

        self._root = tk.Tk()
        self._root.title(f"🍅 {name}")
        self._root.geometry("320x240")
        self._root.resizable(False, False)
        self._root.attributes("-topmost", True)
        self._root.protocol("WM_DELETE_WINDOW", self._cancel)

        # 配色
        bg = "#2c2c2c"
        fg = "#ffffff"
        accent = "#e67e22"
        self._root.configure(bg=bg)

        # 图标
        try:
            self._root.iconbitmap(default="")
        except Exception:
            pass

        # ── 倒计时数字 ──
        timer_font = font.Font(family="Helvetica Neue", size=64, weight="bold")
        self._label = tk.Label(
            self._root, text=self._state.display,
            font=timer_font, bg=bg, fg=accent,
        )
        self._label.pack(pady=(30, 5))

        # ── 进度条 (简单 Canvas) ──
        self._progress_canvas = tk.Canvas(self._root, width=260, height=8,
                                          bg="#444", highlightthickness=0)
        self._progress_canvas.pack(pady=5)
        self._progress_bar = self._progress_canvas.create_rectangle(
            0, 0, 0, 8, fill=accent, outline="",
        )

        # ── 状态文字 ──
        status_font = font.Font(family="Helvetica Neue", size=12)
        self._status = tk.Label(
            self._root, text=name, font=status_font, bg=bg, fg="#aaa",
        )
        self._status.pack(pady=2)

        # ── 番茄计数 ──
        self._pomodoro_label = tk.Label(
            self._root, text="", font=status_font, bg=bg, fg="#888",
        )
        self._pomodoro_label.pack(pady=2)

        # ── 按钮 ──
        btn_frame = tk.Frame(self._root, bg=bg)
        btn_frame.pack(pady=(10, 0))

        btn_style = {"font": ("Helvetica Neue", 11),
                     "bg": "#444", "fg": "white",
                     "relief": "flat", "padx": 16, "pady": 6,
                     "cursor": "hand2", "activebackground": "#555"}

        self._pause_btn = tk.Button(
            btn_frame, text="⏸ 暂停", command=self._toggle_pause, **btn_style,
        )
        self._pause_btn.pack(side="left", padx=6)

        tk.Button(
            btn_frame, text="✕ 取消", command=self._cancel, **btn_style,
        ).pack(side="left", padx=6)

        # ── 绑定键盘 ──
        self._root.bind("<space>", lambda e: self._toggle_pause())
        self._root.bind("<Escape>", lambda e: self._cancel())
        self._root.bind("<Return>", lambda e: self._cancel())

        # ── 启动倒计时 ──
        self._tick()
        self._root.mainloop()

    def _tick(self):
        """每秒更新一次。"""
        if self._state.phase == "paused":
            self._timer_id = self._root.after(500, self._tick)
            return

        if self._state.remaining <= 0:
            self._finish()
            return

        self._state.remaining -= 1
        self._state.elapsed += 1
        self._update_display()

        self._timer_id = self._root.after(1000, self._tick)

    def _update_display(self):
        """更新界面显示。"""
        if self._label:
            self._label.config(text=self._state.display)

        if self._progress_canvas and self._progress_bar:
            bar_width = int(260 * self._state.progress)
            self._progress_canvas.coords(self._progress_bar, 0, 0, bar_width, 8)

        if self._pomodoro_label:
            icon = "🍅" * min(self._state.pomodoros, 10)
            self._pomodoro_label.config(text=icon)

    def _toggle_pause(self):
        """暂停/继续切换。"""
        if self._state.phase == "working":
            self._state.phase = "paused"
            self._state.paused_remaining = self._state.remaining
            if self._pause_btn:
                self._pause_btn.config(text="▶ 继续")
            if self._status:
                self._status.config(text="⏸ 已暂停", fg="#f1c40f")
            if self._label:
                self._label.config(fg="#f1c40f")
        elif self._state.phase == "paused":
            self._state.phase = "working"
            self._state.remaining = self._state.paused_remaining
            if self._pause_btn:
                self._pause_btn.config(text="⏸ 暂停")
            if self._status:
                self._status.config(text="", fg="#aaa")
            if self._label:
                self._label.config(fg="#e67e22")

    def _cancel(self):
        """取消计时。"""
        self._state.phase = "cancelled"
        self._done_event.set()
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass

    def _finish(self):
        """计时完成。"""
        self._state.pomodoros += 1

        # 通知
        self._send_notification("🍅 时间到！")
        self._speak("时间到")

        # 更新界面显示完成状态
        if self._label:
            self._label.config(text="✅ 完成！", fg="#2ecc71")
        if self._status:
            self._status.config(text="🎉 太棒了！休息一下吧", fg="#2ecc71")
        if self._pause_btn:
            self._pause_btn.config(text="✔ 关闭", command=self._cancel)

        self._done_event.set()

        # 3 秒后自动关闭
        if self._root:
            self._root.after(3000, self._close_if_not_cancelled)

    def _close_if_not_cancelled(self):
        if self._state.phase != "cancelled":
            try:
                self._root.destroy()
            except Exception:
                pass

    def wait(self):
        """等待计时完成。"""
        self._done_event.wait()

    @staticmethod
    def _send_notification(text: str, title: str = "🍅 番茄钟"):
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{text}" with title "{title}" sound name "default"'],
            capture_output=True, timeout=5,
        )

    @staticmethod
    def _speak(text: str):
        subprocess.run(["say", text], capture_output=True, timeout=10)


def start_timer(minutes: int = 25, name: str = "番茄钟") -> str:
    """启动番茄钟（快捷入口）。"""
    win = TomatoWindow()
    return win.start(minutes=minutes, name=name)
