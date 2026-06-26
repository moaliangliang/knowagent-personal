"""
知行托盘图标生成器 — 简洁文字标，22x22 清晰可见
"""
from PIL import Image, ImageDraw, ImageFont
import os, base64

def gen_tray_icons():
    base = "electron-app/build"
    for suffix, size in [("", 22), ("@2x", 44)]:
        s = size

        # 彩色托盘：青色 Z 字母 + 发光背景
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # 背景圆
        d.ellipse([1, 1, s-2, s-2], fill=(0, 180, 255, 200))

        # Z 字母（白色）
        # 使用比例绘制 Z
        margin = s * 0.2
        line_w = max(1, s // 8)
        # Z 的三条线
        d.line([(margin, margin), (s-margin, margin)], fill=(255, 255, 255, 230), width=line_w)
        d.line([(s-margin, margin), (margin, s-margin)], fill=(255, 255, 255, 230), width=line_w)
        d.line([(margin, s-margin), (s-margin, s-margin)], fill=(255, 255, 255, 230), width=line_w)

        img.save(f"{base}/tray_color{suffix}.png", "PNG")
        img.save(f"{base}/tray{suffix}.png", "PNG")
        print(f"  ✓ {base}/tray{suffix}.png ({size}x{size})")

        # 模板图标（纯白色，macOS 自动处理明暗模式）
        tmpl = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmpl)
        # 纯白 Z
        td.line([(margin, margin), (s-margin, margin)], fill=(255, 255, 255), width=line_w)
        td.line([(s-margin, margin), (margin, s-margin)], fill=(255, 255, 255), width=line_w)
        td.line([(margin, s-margin), (s-margin, s-margin)], fill=(255, 255, 255), width=line_w)
        tmpl.save(f"{base}/trayTemplate{suffix}.png", "PNG")
        print(f"  ✓ {base}/trayTemplate{suffix}.png ({size}x{size})")

    # 输出 main.js 用的 base64
    print()
    with open(f"{base}/tray_color.png", "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    print(f"Base64 ({len(b64)} bytes):")
    print(b64)

if __name__ == "__main__":
    gen_tray_icons()
