#!/usr/bin/env python3
"""生成社交媒体宣传配图（小红书 / 朋友圈 / 公众号卡片）

使用说明：
  python3 scripts/generate-posters.py

输出：
  docs/posters/ 目录下生成以下图片：
    01-cover.png       封面图（竖版 1080x1440）
    02-features.png    功能一览（竖版）
    03-compare.png     使用对比（竖版）
    04-commands.png    命令列表（竖版）
    05-skill.png       通用 Skill 系统（竖版）
"""

import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "posters",
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 配色方案 ──
BG_DARK = (12, 12, 18)
BG_CARD = (28, 28, 38)
BG_CARD_HIGHLIGHT = (38, 38, 52)
ACCENT_BLUE = (100, 200, 255)
ACCENT_GREEN = (80, 220, 160)
ACCENT_ORANGE = (255, 180, 80)
ACCENT_PURPLE = (180, 130, 255)
TEXT_WHITE = (255, 255, 255)
TEXT_GRAY = (170, 170, 185)
TEXT_DIM = (120, 120, 140)
W, H = 1080, 1440  # 竖版

# ── 字体 ──
FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]
FONT_FILE = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        FONT_FILE = fp
        break


def get_font(size: int):
    if FONT_FILE:
        try:
            return ImageFont.truetype(FONT_FILE, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _center_text(draw, y, text, font, fill=TEXT_WHITE):
    """居中绘制文字"""
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return y + (bbox[3] - bbox[1])


def _wrap_text(draw, text, font, max_width):
    """按宽度换行"""
    lines = []
    for paragraph in text.split("\n"):
        words = list(paragraph) if any('一' <= c <= '鿿' for c in paragraph) else paragraph.split()
        if isinstance(words, list) and any('一' <= c <= '鿿' for c in paragraph):
            # CJK: 逐字换行
            line = ""
            for ch in paragraph:
                test_line = line + ch
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > max_width and line:
                    lines.append(line)
                    line = ch
                else:
                    line = test_line
            if line:
                lines.append(line)
        else:
            # 英文: 逐词换行
            line = ""
            for w in words:
                test_line = f"{line} {w}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] > max_width and line:
                    lines.append(line)
                    line = w
                else:
                    line = test_line
            if line:
                lines.append(line)
    return lines


def _draw_card(draw, x, y, w, h, color=BG_CARD, radius=16):
    """绘制圆角卡片"""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=color)


def _draw_badge(draw, x, y, text, color=ACCENT_BLUE):
    """绘制标签"""
    font = get_font(22)
    bbox = draw.textbbox((0, 0), text, font=font)
    pw, ph = 12, 6
    bw = (bbox[2] - bbox[0]) + pw * 2
    bh = (bbox[3] - bbox[1]) + ph * 2
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=10, fill=(*color[:3], 30))
    draw.text((x + pw, y + ph), text, font=font, fill=color)


# ═════════════════════════════════════════════════════════
#  图片生成函数
# ═════════════════════════════════════════════════════════

def generate_cover():
    """封面图：Mac Agent Personal"""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # 顶部装饰线条
    for i in range(5):
        draw.rectangle([0, H // 2 - 200 + i * 140, W, H // 2 - 195 + i * 140],
                       fill=(*ACCENT_BLUE, 20 + i * 10))

    # 主标题
    title_font = get_font(72)
    _center_text(draw, 280, "🧠 Mac Agent Personal", title_font, TEXT_WHITE)

    # 副标题
    sub_font = get_font(36)
    _center_text(draw, 380, "你的 Mac 桌面 AI 助手", sub_font, TEXT_GRAY)

    # 核心卖点卡片
    features = [
        ("83", "个系统命令"),
        ("中文", "自然语言"),
        ("开源", "MIT 协议"),
        ("离线", "本地运行"),
    ]
    card_w = 200
    card_h = 120
    gap = 30
    total_w = card_w * 4 + gap * 3
    start_x = (W - total_w) // 2
    for i, (num, label) in enumerate(features):
        cx = start_x + i * (card_w + gap)
        cy = 520
        _draw_card(draw, cx, cy, card_w, card_h, BG_CARD_HIGHLIGHT)
        num_font = get_font(48)
        bbox = draw.textbbox((0, 0), num, font=num_font)
        draw.text((cx + (card_w - (bbox[2] - bbox[0])) // 2, cy + 20),
                  num, font=num_font, fill=ACCENT_BLUE)
        label_font = get_font(24)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        draw.text((cx + (card_w - (bbox[2] - bbox[0])) // 2, cy + 75),
                  label, font=label_font, fill=TEXT_GRAY)

    # 能力列表
    cap_font = get_font(28)
    caps = [
        "🔧 调亮度 · 调音量 · 锁屏 · 关机 · 重启",
        "📁 搜文件 · 压缩 · 解压 · 图片转换 · OCR",
        "🌐 公网IP · 测速 · 翻译 · Ping · 下载",
        "💬 企业微信 · 飞书 · 钉钉 · 一键群发",
        "📊 VPN · 磁盘监控 · 电池健康 · CPU温度",
        "🤖 AI对话 · 代码审查 · 图片生成 · 知识库",
    ]
    cy = 700
    for cap in caps:
        _center_text(draw, cy, cap, cap_font, TEXT_GRAY)
        cy += 45

    # 底部
    footer_font = get_font(24)
    _center_text(draw, 1050, "⭐ 开源免费 · 83 个命令 · 全部中文直达", footer_font, TEXT_DIM)
    _center_text(draw, 1100, "github.com/moaliangliang/knowagent-personal", footer_font, ACCENT_BLUE)

    path = os.path.join(OUTPUT_DIR, "01-cover.png")
    img.save(path)
    print(f"  ✅ 封面图: {path}")


def generate_features():
    """功能一览图"""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    _center_text(draw, 60, "📋 功能一览", get_font(48), TEXT_WHITE)
    _center_text(draw, 120, "83 个系统命令 · 全部中文直达", get_font(28), TEXT_GRAY)

    categories = [
        ("🔧 系统控制", 11, "亮度 / 音量 / 睡眠 / 关机 / 重启\n屏保 / 专注模式 / 系统状态 / 电池 / WiFi / 锁屏"),
        ("🌐 网络工具", 7, "公网IP / 测速 / HTTP请求\n文件下载 / Whois / Ping / 端口检测"),
        ("📁 文件管理", 8, "Spotlight搜索 / 内容搜索 / 压缩 / 解压\n废纸篓 / 重复文件 / 图片转换 / 浏览"),
        ("💻 开发工具", 3, "Homebrew / 进程管理 / Docker"),
        ("🎬 媒体处理", 6, "录屏 / 录音 / 视频信息 / 图片OCR\n截图 / 截图分析"),
        ("📅 日常效率", 7, "番茄钟 / 剪贴板历史 / 翻译\n快捷指令 / 通知 / 日历 / 提醒"),
        ("🤖 AI 增强", 5, "AI对话 / 文本摘要 / 代码审查\n图片生成 / 知识库搜索"),
        ("📊 监控 & VPN", 4, "磁盘监控 / 电池健康 / CPU温度\n双VPN管理 (aTrust + FortiGate)"),
        ("💬 企业通讯", 4, "企业微信 / 飞书 / 钉钉\n一键群发 (Webhook/API/UI)"),
        ("🔐 安全 & 工具", 5, "Keychain加密 / 剪贴板历史\n配置热加载 / 凭据管理 / Skill系统"),
    ]

    y = 180
    col_w = (W - 120) // 2
    for i, (name, count, desc) in enumerate(categories):
        col = i % 2
        row = i // 2
        cx = 40 + col * (col_w + 40)
        cy = y + row * 125
        _draw_card(draw, cx, cy, col_w, 115, BG_CARD)
        # 分类名 + 数量
        name_font = get_font(26)
        draw.text((cx + 20, cy + 12), f"{name}  ({count})", font=name_font, fill=ACCENT_BLUE)
        # 描述
        desc_font = get_font(20)
        for li, line in enumerate(desc.split("\n")):
            draw.text((cx + 20, cy + 48 + li * 28), line, font=desc_font, fill=TEXT_GRAY)

    # 底部
    _center_text(draw, 1350, "github.com/moaliangliang/knowagent-personal", get_font(24), ACCENT_BLUE)

    path = os.path.join(OUTPUT_DIR, "02-features.png")
    img.save(path)
    print(f"  ✅ 功能图: {path}")


def generate_compare():
    """使用对比图：之前 vs 之后"""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    _center_text(draw, 50, "⚡ 之前 vs 之后", get_font(48), TEXT_WHITE)

    comparisons = [
        ("调低屏幕亮度",
         "❌ 系统设置 → 显示器 → 拖亮度条",
         "✅ 说一句：ka 亮度 40"),
        ("搜索文件",
         "❌ 打开Finder → 搜索 → 筛结果",
         "✅ 说一句：ka 搜索文件 query=合同"),
        ("翻译",
         "❌ 打开浏览器 → 打开翻译网站 → 粘贴",
         "✅ 说一句：ka 翻译 hello"),
        ("连VPN",
         "❌ 打开VPN软件 → 输入密码 → 连接",
         "✅ 说一句：ka vpn_status action=connect"),
        ("发通知",
         "❌ 打开企业微信 → 找群 → 打字 → 发送",
         "✅ 说一句：ka wecom text=下午开会"),
        ("查系统状态",
         "❌ 打开活动监视器 → 看CPU/内存",
         "✅ 说一句：ka 系统状态"),
    ]

    y = 130
    card_h = 140
    for i, (title, before, after) in enumerate(comparisons):
        cy = y + i * (card_h + 20)
        _draw_card(draw, 40, cy, W - 80, card_h, BG_CARD)

        # 标题
        t_font = get_font(28)
        draw.text((60, cy + 12), f"📌 {title}", font=t_font, fill=TEXT_WHITE)

        # 之前
        b_font = get_font(22)
        draw.text((60, cy + 55), before, font=b_font, fill=TEXT_DIM)
        # 之后
        draw.text((60, cy + 90), after, font=b_font, fill=ACCENT_GREEN)

    # 总结
    sum_font = get_font(28)
    _center_text(draw, 1250, "✨ 一句话搞定，不用记命令", sum_font, ACCENT_BLUE)
    _center_text(draw, 1300, "github.com/moaliangliang/knowagent-personal", get_font(24), ACCENT_BLUE)

    path = os.path.join(OUTPUT_DIR, "03-compare.png")
    img.save(path)
    print(f"  ✅ 对比图: {path}")


def generate_commands():
    """命令列表图"""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    _center_text(draw, 40, "🔍 83 个命令一览", get_font(42), TEXT_WHITE)

    cmd_groups = [
        ("🔧 系统", "亮度｜音量｜睡眠｜关机｜重启\n屏保｜专注｜系统状态｜电池｜WiFi｜锁屏"),
        ("🌐 网络", "公网IP｜测速｜HTTP请求｜下载\nWhois｜Ping｜端口检测"),
        ("📁 文件", "搜索｜内容搜索｜压缩｜解压\n废纸篓｜重复文件｜图片转换｜浏览"),
        ("💻 开发", "Homebrew｜进程管理｜Docker"),
        ("🎬 媒体", "录屏｜录音｜视频信息\n图片OCR｜截图｜截图分析"),
        ("📅 日常", "番茄钟｜剪贴板历史｜翻译\n快捷指令｜通知｜日历｜提醒"),
        ("🤖 AI", "对话｜摘要｜代码审查\n图片生成｜知识库搜索"),
        ("📊 监控", "磁盘｜电池健康｜CPU温度\nVPN管理 (aTrust+FortiGate)"),
        ("💬 通讯", "企业微信｜飞书｜钉钉｜群发"),
        ("🔐 工具", "Keychain｜剪贴板历史\n配置加载｜凭据管理｜Skill"),
    ]

    y = 100
    per_row = 2
    cw = (W - 120) // 2
    for i, (title, cmds) in enumerate(cmd_groups):
        col = i % per_row
        row = i // per_row
        cx = 40 + col * (cw + 40)
        cy = y + row * 130
        _draw_card(draw, cx, cy, cw, 120, BG_CARD)
        draw.text((cx + 18, cy + 12), title, font=get_font(26), fill=ACCENT_BLUE)
        for li, line in enumerate(cmds.split("\n")):
            draw.text((cx + 18, cy + 50 + li * 30), line, font=get_font(20), fill=TEXT_GRAY)

    _center_text(draw, 1370, "github.com/moaliangliang/knowagent-personal", get_font(24), ACCENT_BLUE)

    path = os.path.join(OUTPUT_DIR, "04-commands.png")
    img.save(path)
    print(f"  ✅ 命令图: {path}")


def generate_skill():
    """通用 Skill 系统配图"""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    _center_text(draw, 50, "🧩 通用 Skill 系统", get_font(48), TEXT_WHITE)
    _center_text(draw, 110, "像装 App 一样装技能", get_font(28), TEXT_GRAY)

    # 代码示例卡片
    code = '''# ~/.zhixing/skills/weather.py
from zhixing.plugins import Skill

class WeatherSkill(Skill):
    name = "天气查询"
    description = "查询城市天气"

    def cmd_weather(self, params):
        """查询天气。city: 城市名"""
        city = params.get("city", "北京")
        return f"☀️ {city} 25°C 晴天"'''

    _draw_card(draw, 60, 160, W - 120, 420, BG_CARD_HIGHLIGHT)
    code_font = get_font(22)
    y = 185
    for line in code.split("\n"):
        color = TEXT_GRAY if line.startswith(" ") or line.startswith("\t") else TEXT_WHITE
        draw.text((80, y), line, font=code_font, fill=color)
        y += 32

    # 能力说明
    features = [
        ("📝 自动注册", "cmd_ 方法自动变为系统命令，无需手动配置"),
        ("📋 自动 Schema", "函数签名自动生成 OpenAI 兼容 tool schema"),
        ("🔌 即放即用", "文件放入 ~/.zhixing/skills/ 目录，重启即加载"),
        ("🌍 远程安装", "支持 gh:user/repo 从 GitHub 安装"),
        ("🔍 发现与管理", "skill list / search / install / remove 完整生命周期"),
    ]
    y = 620
    for title, desc in features:
        _draw_card(draw, 60, y, W - 120, 75, BG_CARD)
        draw.text((80, y + 10), title, font=get_font(26), fill=ACCENT_BLUE)
        draw.text((80, y + 42), desc, font=get_font(20), fill=TEXT_GRAY)
        y += 85

    _center_text(draw, 1200, "社区共建，万人万面", get_font(28), ACCENT_BLUE)
    _center_text(draw, 1260, "github.com/moaliangliang/knowagent-personal", get_font(24), ACCENT_BLUE)

    path = os.path.join(OUTPUT_DIR, "05-skill.png")
    img.save(path)
    print(f"  ✅ Skill图: {path}")


# ═════════════════════════════════════════════════════════
#  主函数
# ═════════════════════════════════════════════════════════

def main():
    print("🎨 生成宣传配图...")
    print(f"   输出目录: {OUTPUT_DIR}\n")
    generate_cover()
    generate_features()
    generate_compare()
    generate_commands()
    generate_skill()
    print(f"\n✅ 全部生成完成! 共 5 张图片")
    print(f"   路径: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
