#!/usr/bin/env python3
"""生成小红书图文笔记图片"""

import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "xiaohongshu")
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 配色
BG_COLOR = (15, 15, 20)      # 深色背景
CARD_COLOR = (30, 30, 40)    # 卡片底色
ACCENT_COLOR = (100, 200, 255)  # 强调色蓝
TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (180, 180, 190)
TITLE_FONT_SIZE = 48
BODY_FONT_SIZE = 32
W, H = 1080, 1440  # 小红书标准竖版

# 尝试加载字体
FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]
FONT = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        FONT = fp
        break

def get_font(size):
    if FONT:
        try:
            return ImageFont.truetype(FONT, size)
        except Exception:
            pass
    return ImageFont.load_default()


def draw_card(img, title, body_lines, accent_line="", screenshot=None):
    draw = ImageDraw.Draw(img)

    # Background
    draw.rectangle([(0, 0), (W, H)], fill=BG_COLOR)

    # Accent top bar
    draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)

    # Title
    title_font = get_font(TITLE_FONT_SIZE)
    draw.text((60, 80), title, fill=TEXT_WHITE, font=title_font)

    # Accent line
    if accent_line:
        accent_font = get_font(36)
        draw.text((60, 150), accent_line, fill=ACCENT_COLOR, font=accent_font)

    # Screenshot
    if screenshot and os.path.exists(screenshot):
        try:
            simg = Image.open(screenshot).convert("RGB")
            # Resize to fit card width
            simg_w, simg_h = simg.size
            target_w = W - 120
            target_h = int(simg_h * target_w / simg_w)
            if target_h > 700:
                target_h = 700
                target_w = int(simg_w * 700 / simg_h)
            simg = simg.resize((target_w, target_h), Image.LANCZOS)
            img.paste(simg, (60, 200))
        except Exception:
            pass

    # Body text
    y_start = 940 if screenshot else 200
    body_font = get_font(BODY_FONT_SIZE)
    for i, line in enumerate(body_lines):
        draw.text((60, y_start + i * 52), line, fill=TEXT_GRAY, font=body_font)

    # Bottom watermark
    draw.text((60, H - 60), "🧠 Mac Agent Personal", fill=(80, 80, 90), font=get_font(24))
    return img


# ═══════════════════════════════════════
# 图1: 封面
# ═══════════════════════════════════════
img = Image.new("RGB", (W, H), BG_COLOR)
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)

# Big emoji
draw.text((60, 200), "🧠", fill=TEXT_WHITE, font=get_font(120))
draw.text((60, 350), "Mac Agent Personal", fill=TEXT_WHITE, font=get_font(56))
draw.text((60, 430), "开源的 Mac 桌面 AI 助手", fill=TEXT_GRAY, font=get_font(36))
draw.text((60, 520), "30+ 命令 · 本地 LLM · 离线运行", fill=ACCENT_COLOR, font=get_font(32))

# Feature bullets
features = ["🎵 说句话就放音乐", "📸 截屏自动 OCR", "📧 读邮件/发邮件",
            "📚 本地知识库 RAG", "🖱️ UI 自动化", "⌨️ 键盘/快捷键模拟"]
for i, f in enumerate(features):
    draw.text((100, 660 + i * 60), f, fill=TEXT_WHITE, font=get_font(32))

draw.text((60, H - 120), "完全开源 · MIT 协议", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, H - 80), "GitHub 搜索: knowagent-personal", fill=ACCENT_COLOR, font=get_font(28))
img.save(os.path.join(OUTPUT_DIR, "01-cover.png"))
print("✅ 图1 封面")

# ═══════════════════════════════════════
# 图2: 系统状态
# ═══════════════════════════════════════
draw_card(img.copy(), "🖥️ 系统状态",
    ["说句「系统状态」就能看到", "CPU、内存、磁盘、网络", "一目了然"],
    accent_line="ka 系统状态",
    screenshot=os.path.join(SCREENSHOT_DIR, "01-system-status.png")
).save(os.path.join(OUTPUT_DIR, "02-system.png"))
print("✅ 图2 系统状态")

# ═══════════════════════════════════════
# 图3: 音乐播放
# ═══════════════════════════════════════
img = Image.new("RGB", (W, H), BG_COLOR)
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)
draw.text((60, 80), "🎵 音乐控制", fill=TEXT_WHITE, font=get_font(TITLE_FONT_SIZE))
draw.text((60, 150), "说句话就放歌", fill=ACCENT_COLOR, font=get_font(36))
draw.text((60, 220), "ka 播放周杰伦的歌", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, 280), "→ 搜索 Apple Music 在线曲库", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 340), "→ 播放 30 秒预览", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 400), "→ 在 Music App 打开完整版", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 460), "→ 自动点击播放按钮", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 560), "也支持控制音量、切歌、本地曲库搜索", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, H - 80), "🎵 Apple Music · 本地曲库 · 在线搜索", fill=TEXT_GRAY, font=get_font(28))
img.save(os.path.join(OUTPUT_DIR, "03-music.png"))
print("✅ 图3 音乐")

# ═══════════════════════════════════════
# 图4: 截图+OCR
# ═══════════════════════════════════════
img = Image.new("RGB", (W, H), BG_COLOR)
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)
draw.text((60, 80), "📸 截图 + OCR", fill=TEXT_WHITE, font=get_font(TITLE_FONT_SIZE))
draw.text((60, 150), "截屏并识别文字", fill=ACCENT_COLOR, font=get_font(36))
draw.text((60, 220), "ka 看看屏幕上有什么字", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, 300), "① 截屏（支持区域截图）", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 360), "② macOS Vision 原生 OCR", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 420), "③ 中英文混合识别", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 480), "④ 回退 Tesseract 引擎", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 580), "比传统 OCR 工具准确率高很多", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, H - 80), "📸 macOS Vision Framework", fill=TEXT_GRAY, font=get_font(28))
img.save(os.path.join(OUTPUT_DIR, "04-ocr.png"))
print("✅ 图4 截图OCR")

# ═══════════════════════════════════════
# 图5: RAG 知识库
# ═══════════════════════════════════════
img = Image.new("RGB", (W, H), BG_COLOR)
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)
draw.text((60, 80), "📚 个人知识库 RAG", fill=TEXT_WHITE, font=get_font(TITLE_FONT_SIZE))
draw.text((60, 150), "搜自己的文档和笔记", fill=ACCENT_COLOR, font=get_font(36))
draw.text((60, 220), "ka rag index ~/Documents", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, 280), "→ 索引 TXT/MD/Python 等文件", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 340), "→ ChromaDB 本地向量存储", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 400), "→ 自然语言搜索", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 460), "→ Agent 自动调用", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 560), "全部在本地运行\n不上传任何数据到云端", fill=TEXT_GRAY, font=get_font(28))
draw.text((60, H - 80), "📚 ChromaDB · 本地嵌入 · 隐私优先", fill=TEXT_GRAY, font=get_font(28))
img.save(os.path.join(OUTPUT_DIR, "05-rag.png"))
print("✅ 图5 RAG知识库")

# ═══════════════════════════════════════
# 图6: 更多功能
# ═══════════════════════════════════════
img = Image.new("RGB", (W, H), BG_COLOR)
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)
draw.text((60, 80), "🔧 还有更多", fill=TEXT_WHITE, font=get_font(TITLE_FONT_SIZE))
draw.text((60, 150), "33 个内置命令，还在增加", fill=ACCENT_COLOR, font=get_font(36))

all_features = [
    "📧 邮件: 读/搜/发 Mail.app + 邮箱大师",
    "🖱️ UI 自动化: AX 界面树/查找/点击",
    "⌨️ 键盘: 模拟输入/快捷键/复合键",
    "📋 系统: CPU/内存/磁盘/网络/电池/WiFi",
    "🗓️ 日历: 查询今日日程",
    "📎 剪贴板: 读写",
    "🔔 通知: 弹窗提醒",
    "🔒 锁屏: 一键锁定",
    "🗣️ 语音: 语音输入识别",
    "🔗 插件: 自定义扩展",
]
for i, f in enumerate(all_features):
    draw.text((60, 230 + i * 54), f, fill=TEXT_WHITE, font=get_font(28))

draw.text((60, H - 120), "33 commands and growing...", fill=TEXT_GRAY, font=get_font(28))
img.save(os.path.join(OUTPUT_DIR, "06-more.png"))
print("✅ 图6 更多功能")

# ═══════════════════════════════════════
# 图7: 结尾 + 安装方式
# ═══════════════════════════════════════
img = Image.new("RGB", (W, H), BG_COLOR)
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (W, 8)], fill=ACCENT_COLOR)
draw.text((60, 200), "🆓 开源免费", fill=TEXT_WHITE, font=get_font(56))
draw.text((60, 300), "MIT 协议 · 完全开源", fill=TEXT_GRAY, font=get_font(32))

draw.text((60, 420), "安装方式", fill=ACCENT_COLOR, font=get_font(36))
draw.text((60, 480), "pip install knowagent-personal", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 540), "然后输入 ka 启动", fill=TEXT_GRAY, font=get_font(28))

draw.text((60, 660), "前提条件", fill=ACCENT_COLOR, font=get_font(36))
draw.text((60, 720), "macOS 11.0+ · Python 3.10+", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 780), "Ollama（可选，用于 AI 对话）", fill=TEXT_GRAY, font=get_font(28))

draw.text((60, 920), "GitHub", fill=ACCENT_COLOR, font=get_font(36))
draw.text((60, 980), "搜索: knowagent-personal", fill=TEXT_WHITE, font=get_font(32))
draw.text((60, 1040), "或扫码访问", fill=TEXT_GRAY, font=get_font(28))

draw.text((60, H - 80), "🧠 如果你觉得有用，点个 ❤️ 支持一下", fill=TEXT_GRAY, font=get_font(28))
img.save(os.path.join(OUTPUT_DIR, "07-end.png"))
print("✅ 图7 结尾")

print(f"\n📁 全部图片已保存到: {OUTPUT_DIR}")
