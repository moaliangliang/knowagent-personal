#!/usr/bin/env python3
"""生成 App Store / GitHub 发布用截图素材"""

import os
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "store")
os.makedirs(OUTPUT, exist_ok=True)

# Store 截图尺寸
STORE_SIZES = {
    "macos": (2880, 1800),   # Retina 5K
    "github-social": (1280, 640),
}

# 生成 macOS 风格截图（带窗口阴影和圆角）
def make_store_screenshot(app_title="ZhiXing · 知行") -> Image.Image:
    w, h = STORE_SIZES["macos"]
    img = Image.new("RGBA", (w, h), (245, 245, 247))
    draw = ImageDraw.Draw(img)

    # 顶部状态栏
    draw.rectangle([0, 0, w, 60], fill=(255, 255, 255))
    draw.rectangle([0, 60, w, 61], fill=(220, 220, 222))

    # 应用窗口（居中，带圆角 + 阴影）
    win_w, win_h = 1200, 750
    win_x = (w - win_w) // 2
    win_y = (h - win_h) // 2 + 20

    # 窗口阴影
    shadow_w, shadow_h = win_w + 40, win_h + 40
    shadow = Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([10, 10, win_w + 29, win_h + 29], radius=16, fill=(0, 0, 0, 40))
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    # Paste shadow onto background first
    img.paste(shadow, (win_x - 20, win_y - 20), shadow)

    # 窗口主体（白色背景）
    win = Image.new("RGBA", (win_w, win_h), (255, 255, 255))
    wdraw = ImageDraw.Draw(win)

    # 标题栏
    title_colors = [(102, 126, 234), (118, 75, 162)]
    for i in range(48):
        ratio = i / 48
        r = int(title_colors[0][0] + (title_colors[1][0] - title_colors[0][0]) * ratio)
        g = int(title_colors[0][1] + (title_colors[1][1] - title_colors[0][1]) * ratio)
        b = int(title_colors[0][2] + (title_colors[1][2] - title_colors[0][2]) * ratio)
        wdraw.line([(0, i), (win_w, i)], fill=(r, g, b))

    # 交通灯按钮
    for btn_x, btn_color in [(16, "#ff5f57"), (36, "#febc2e"), (56, "#28c840")]:
        wdraw.ellipse([btn_x, 16, btn_x + 14, 30], fill=btn_color)

    # 标题文字
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 14)
    except Exception:
        font = ImageFont.load_default()
        font_small = font

    # 标签栏
    wdraw.rectangle([0, 48, win_w, 49], fill=(230, 230, 232))
    tabs = ["💬 对话", "📋 待办", "⚡ 工作流"]
    for i, tab in enumerate(tabs):
        tx = 24 + i * 100
        color = (102, 126, 234) if i == 0 else (140, 140, 142)
        wdraw.text((tx, 60), tab, font=font_small, fill=color)

    # 对话区域（带示例消息）
    msgs = [
        ("user", "系统状态"),
        ("bot", "📋 系统状态 — MacBook\n  🖥 CPU: 23%\n  🧠 内存: 10.2/32.0 GB\n  💾 磁盘: 187/512 GB\n  ⏱ 运行: 3天14小时"),
        ("user", "看看"),
        ("bot", "📸 截屏分析 (Vision OCR)\n  找到了 42 个文字块\n  包含: 菜单栏、窗口标题、代码编辑器"),
        ("user", "播放 周杰伦 稻香"),
        ("bot", "🎵 正在播放: 稻香 — 周杰伦\n  来源: Apple Music"),
    ]

    y_pos = 100
    for role, text in msgs:
        # 头像
        avatar_color = (102, 126, 234) if role == "user" else (200, 200, 204)
        wdraw.ellipse([20, y_pos + 4, 44, y_pos + 28], fill=avatar_color)
        if role == "user":
            wdraw.text((28, y_pos + 8), "你", font=font_small, fill=(255, 255, 255))
        else:
            wdraw.text((26, y_pos + 6), "⬡", font=font_small, fill=(255, 255, 255))

        # 气泡
        lines = text.split("\n")
        bubble_h = max(30, len(lines) * 22 + 16)
        bx = 52
        bw = 500
        bubble_color = (102, 126, 234) if role == "user" else (240, 240, 245)
        text_color = (255, 255, 255) if role == "user" else (50, 50, 55)
        wdraw.rounded_rectangle([bx, y_pos, bx + bw, y_pos + bubble_h], radius=10, fill=bubble_color)

        for j, line in enumerate(lines):
            wdraw.text((bx + 12, y_pos + 8 + j * 22), line, font=font_small, fill=text_color)

        y_pos += bubble_h + 12

    # 输入框底部
    wdraw.rectangle([0, win_h - 60, win_w, win_h], fill=(248, 248, 250))
    wdraw.rectangle([0, win_h - 61, win_w, win_h - 60], fill=(230, 230, 232))
    wdraw.rounded_rectangle([16, win_h - 50, win_w - 70, win_h - 18], radius=18,
                           fill=(255, 255, 255), outline=(210, 210, 215))
    wdraw.text((30, win_h - 42), "输入命令...", font=font_small, fill=(190, 190, 195))
    wdraw.ellipse([win_w - 58, win_h - 46, win_w - 22, win_h - 10], fill=(102, 126, 234))
    wdraw.text((win_w - 44, win_h - 34), "➤", font=font_small, fill=(255, 255, 255))

    # 底部栏
    wdraw.text((20, win_h - 80), "💡 输入 help 查看命令", font=font_small, fill=(102, 126, 234))

    # 合成
    win_rounded = Image.new("RGBA", (win_w, win_h), (0, 0, 0, 0))
    wr_draw = ImageDraw.Draw(win_rounded)
    wr_draw.rounded_rectangle([0, 0, win_w-1, win_h-1], radius=16, fill=(255, 255, 255))
    win = Image.composite(win, win_rounded, win_rounded.split()[0])
    img.paste(win, (win_x, win_y), win)

    return img


# ── 生成 ──

print("生成 Mac App Store 截图 (2880×1800)...")
screenshot = make_store_screenshot()
screenshot.save(os.path.join(OUTPUT, "screenshot-macos.png"), "PNG")
print(f"  ✅ {OUTPUT}/screenshot-macos.png ({screenshot.size[0]}×{screenshot.size[1]})")

print("\n生成 GitHub Social Preview (1280×640)...")
social = Image.new("RGBA", (1280, 640), (102, 126, 234))
sdraw = ImageDraw.Draw(social)

# 渐变背景
for y in range(640):
    ratio = y / 640
    r = int(102 + (118 - 102) * ratio)
    g = int(126 + (75 - 126) * ratio)
    b = int(234 + (162 - 234) * ratio)
    sdraw.line([(0, y), (1279, y)], fill=(r, g, b))

# 品牌文字
try:
    font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 72)
    font_sub = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 32)
except Exception:
    font_title = ImageFont.load_default()
    font_sub = font_title

sdraw.text((80, 180), "⬡ 知行", font=font_title, fill=(255, 255, 255))
sdraw.text((80, 280), "ZhiXing · AI-powered macOS Desktop Automation", font=font_sub, fill=(220, 220, 255))
sdraw.text((80, 380), "101 系统命令 · 可视化工作流 · RAG 知识库 · Ollama/OpenAI", font=font_sub, fill=(200, 200, 240))

# 右侧装饰圆
for i in range(3):
    cx = 1000 + i * 80
    cy = 200 + i * 60
    alpha = 80 - i * 20
    sdraw.ellipse([cx-60, cy-60, cx+60, cy+60], fill=(255, 255, 255, alpha))

social.save(os.path.join(OUTPUT, "github-social-preview.png"), "PNG")
print(f"  ✅ {OUTPUT}/github-social-preview.png ({social.size[0]}×{social.size[1]})")

print("\n─── 全部完成 ───")
print(f"输出目录: {OUTPUT}")
