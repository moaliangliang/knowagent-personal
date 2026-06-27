#!/usr/bin/env python3
"""生成知行 (ZhiXing) 演示 GIF — 直接渲染，不依赖屏幕截图"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 品牌色 ──
PURPLE_A = (102, 126, 234)
PURPLE_B = (118, 75, 162)
WHITE    = (255, 255, 255)
BG_LIGHT = (245, 245, 247)
TEXT_MAIN = (50, 50, 55)
TEXT_GRAY = (140, 140, 142)
CHAT_USER_BG = (102, 126, 234)
CHAT_BOT_BG  = (240, 240, 245)

WIN_W, WIN_H = 420, 600


def _load_font(size):
    try:
        return ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", size)
    except Exception:
        return ImageFont.load_default()


def draw_title_bar(draw):
    """紫色渐变标题栏"""
    for i in range(40):
        ratio = i / 40
        r = int(PURPLE_A[0] + (PURPLE_B[0] - PURPLE_A[0]) * ratio)
        g = int(PURPLE_A[1] + (PURPLE_B[1] - PURPLE_A[1]) * ratio)
        b = int(PURPLE_A[2] + (PURPLE_B[2] - PURPLE_A[2]) * ratio)
        draw.line([(0, i), (WIN_W, i)], fill=(r, g, b))
    # Title
    draw.text((44, 9), "⬡ 知行", font=_load_font(15), fill=WHITE)
    # Traffic lights
    for bx, bc in [(12, "#ff5f57"), (28, "#febc2e"), (44, "#28c840")]:
        draw.ellipse([bx, 12, bx + 10, 22], fill=bc)


def draw_status_bar(draw, connected=True):
    draw.rectangle([0, 40, WIN_W, 58], fill=WHITE)
    c = "#22c55e" if connected else "#ef4444"
    t = "● 已连接  ws://localhost:9510" if connected else "○ 未连接"
    draw.text((14, 43), t, font=_load_font(10), fill=c)


def draw_chat_area(draw, messages):
    """绘制对话区域"""
    draw.rectangle([0, 58, WIN_W, WIN_H - 94], fill=(245, 246, 248))
    y = 68
    for role, text in messages:
        font = _load_font(12)
        # Avatar
        avatar_color = PURPLE_A if role == "user" else (200, 200, 204)
        draw.ellipse([14, y, 34, y + 20], fill=avatar_color)
        if role == "user":
            draw.text((20, y + 3), "你", font=_load_font(9), fill=WHITE)
        else:
            draw.text((18, y + 2), "⬡", font=_load_font(9), fill=WHITE)

        # Bubble
        lines = text.split("\n")
        bh = max(26, len(lines) * 18 + 12)
        bx, bw = 42, 340
        bc = CHAT_USER_BG if role == "user" else CHAT_BOT_BG
        tc = WHITE if role == "user" else TEXT_MAIN
        draw.rounded_rectangle([bx, y, bx + bw, y + bh], radius=10, fill=bc)

        for j, line in enumerate(lines):
            draw.text((bx + 10, y + 6 + j * 18), line, font=font, fill=tc)

        y += bh + 10
    return y


def draw_input_area(draw, placeholder="输入命令..."):
    draw.rectangle([0, WIN_H - 94, WIN_W, WIN_H - 34], fill=WHITE)
    draw.line([(0, WIN_H - 95), (WIN_W, WIN_H - 95)], fill=(230, 230, 232))
    draw.rounded_rectangle([12, WIN_H - 84, WIN_W - 60, WIN_H - 48], radius=18,
                          fill=WHITE, outline=(210, 210, 215))
    draw.text((26, WIN_H - 76), placeholder, font=_load_font(12), fill=(190, 190, 195))
    draw.ellipse([WIN_W - 50, WIN_H - 80, WIN_W - 14, WIN_H - 44], fill=PURPLE_A)
    draw.text((WIN_W - 36, WIN_H - 66), "➤", font=_load_font(14), fill=WHITE)


def draw_footer(draw):
    draw.rectangle([0, WIN_H - 34, WIN_W, WIN_H], fill=(248, 248, 250))
    draw.line([(0, WIN_H - 35), (WIN_W, WIN_H - 35)], fill=(230, 230, 232))
    draw.text((14, WIN_H - 26), "💡 输入 help 查看命令", font=_load_font(10), fill=PURPLE_A)


def render_frame(messages, placeholder="输入命令...", typing_text=None):
    """渲染一帧画面"""
    img = Image.new("RGBA", (WIN_W, WIN_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw_title_bar(draw)
    draw_status_bar(draw)
    last_y = draw_chat_area(draw, messages)
    draw_input_area(draw, placeholder)

    # 如果有正在输入的文字，画在输入框上
    if typing_text:
        draw.rectangle([12, WIN_H - 84, WIN_W - 60, WIN_H - 48], fill=WHITE,
                      outline=PURPLE_A)
        draw.text((26, WIN_H - 76), typing_text, font=_load_font(12), fill=TEXT_MAIN)

    draw_footer(draw)
    return img


# ── 创建动画帧 ─────────────────────────────────

frames = []
delays = []

# Scene 1: 初始界面 — 显示欢迎消息
msg1 = [
    ("bot", "⬡ 知行已启动\n\n试试: 状态 / 看看 / 帮助"),
]
frames.append(render_frame(msg1))
delays.append(100)  # 1.0s

# Scene 2: 用户输入"状态"
frames.append(render_frame(msg1, typing_text="状态"))
delays.append(60)  # 0.6s

# Scene 3: 用户消息 + 系统回复结果
msg2 = msg1 + [
    ("user", "状态"),
]
frames.append(render_frame(msg2))
delays.append(40)

msg3 = msg2 + [
    ("bot", "📋 系统状态\n  🖥 CPU: 23%\n  🧠 内存: 10.2/32.0 GB\n  💾 磁盘: 187/512 GB\n  ⏱ 运行: 3天14小时"),
]
frames.append(render_frame(msg3))
delays.append(120)  # 1.2s

# Scene 4: 用户输入"看看"
frames.append(render_frame(msg3, typing_text="看看"))
delays.append(50)

msg4 = msg3 + [
    ("user", "看看"),
]
frames.append(render_frame(msg4))
delays.append(40)

msg5 = msg4 + [
    ("bot", "📸 截屏分析 (Vision OCR)\n  找到 52 个文字块\n  区域: 3024×1964 px\n  包含: 菜单栏、窗口、代码"),
]
frames.append(render_frame(msg5))
delays.append(120)

# Scene 5: 用户输入 help
frames.append(render_frame(msg5, typing_text="help"))
delays.append(50)

msg6 = msg5 + [
    ("user", "help"),
]
frames.append(render_frame(msg6))
delays.append(40)

msg7 = msg6 + [
    ("bot", "━ 可用命令 ━\n  状态    — 系统状态\n  搜索    — 在线播放音乐\n  网页    — 打开网页\n  点击    — 点击文字\n  截图    — 截屏分析\n  看看    — 截屏识别文字\n  找      — 查找文字位置\n  复制    — 复制到剪贴板\n  待办    — 待办管理\n  VPN     — VPN 连接\n  日历    — 今日日程\n  翻译    — 翻译文本"),
]
frames.append(render_frame(msg7))
delays.append(150)

# Scene 6: 回到初始（循环点）
frames.append(render_frame(msg1))
delays.append(80)

# ── 保存 GIF ──

gif_path = os.path.join(OUTPUT_DIR, "demo.gif")
# Convert to RGB then quantize for GIF
frames_rgb = [f.convert("RGB") for f in frames]
frames_pal = [f.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for f in frames_rgb]
frames_pal[0].save(
    gif_path,
    save_all=True,
    append_images=frames_pal[1:],
    duration=delays,
    loop=0,
    optimize=True,
)

print(f"✅ 演示 GIF 已生成: {gif_path}")
print(f"   帧数: {len(frames)}")
print(f"   总时长: {sum(delays)/100:.1f}s")
print(f"   大小: {os.path.getsize(gif_path)/1024:.0f} KB")
