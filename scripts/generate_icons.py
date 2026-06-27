#!/usr/bin/env python3
"""知行 (ZhiXing) 统一图标生成器

生成所有图标文件并使用统一的品牌识别：
  紫色渐变圆 + 白色「知」字（或纯白色 Z，用于极小尺寸）

输出:
  chrome-extension/icon.png
  electron-app/build/{icon.png, tray*.png, icon.ico}
  以及 main.js 中使用的替换用 Base64 数据
"""

import os
import math
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── 品牌色 ──────────────────────────────────────
PURPLE_A = (102, 126, 234)   # #667eea
PURPLE_B = (118, 75, 162)    # #764ba2
WHITE    = (255, 255, 255, 255)
BLACK    = (0, 0, 0, 255)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME_EXT_DIR = os.path.join(PROJECT_ROOT, "chrome-extension")
BUILD_DIR = os.path.join(PROJECT_ROOT, "electron-app", "build")


# ── 绘图工具 ─────────────────────────────────────

def _find_cjk_font(min_size: int = 100) -> str | None:
    """Find the best available CJK font for drawing the 知 character."""
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, min_size)
                return p
            except Exception:
                continue
    return None


def _draw_gradient_circle(draw, cx, cy, radius, color_a, color_b):
    """Draw a vertical gradient-filled circle."""
    for y in range(cy - radius, cy + radius):
        for x in range(cx - radius, cx + radius):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist > radius:
                continue
            ratio = (y - (cy - radius)) / (2 * radius)
            ratio = max(0, min(1, ratio))
            r = int(color_a[0] + (color_b[0] - color_a[0]) * ratio)
            g = int(color_a[1] + (color_b[1] - color_a[1]) * ratio)
            b = int(color_a[2] + (color_b[2] - color_a[2]) * ratio)
            # anti-aliased edge
            alpha = 255
            if radius - dist < 1.5:
                alpha = int(255 * max(0, (radius - dist) / 1.5))
            draw.point((x, y), fill=(r, g, b, alpha))


def _draw_z_shape(draw, cx, cy, size, color=WHITE, width_factor=0.18):
    """Draw a stylized white Z shape at center."""
    half = size / 2
    t = size * width_factor  # stroke thickness

    # Z is drawn as 3 segments: top bar, diagonal, bottom bar
    margin = size * 0.22
    x0 = cx - half + margin
    x1 = cx + half - margin
    y0 = cy - half + margin
    y1 = cy + half - margin

    # Top bar: left to right (with rounded caps via circle overlap)
    draw.rectangle([x0, y0, x1, y0 + t], fill=color)
    # Bottom bar: left to right
    draw.rectangle([x0, y1 - t, x1, y1], fill=color)
    # Diagonal: top-right to bottom-left
    draw.polygon([
        (x1, y0),
        (x1, y0 + t),
        (x0 + t, y1),
        (x0, y1 - t),
    ], fill=color)

    # Small diamond accent at top-right
    dia_size = t * 1.2
    draw.polygon([
        (x1 + dia_size * 0.3, y0 + t * 0.3),
        (x1, y0 + t * 0.3 - dia_size * 0.5),
        (x1 - dia_size * 0.3, y0 + t * 0.3),
        (x1, y0 + t * 0.3 + dia_size * 0.5),
    ], fill=color)


def _draw_zhi_char(draw, cx, cy, size, color=WHITE, font_path=None):
    """Draw the Chinese character 知 at center using a CJK font."""
    char_size = int(size * 0.6)
    font_path = font_path or _find_cjk_font(char_size)
    if not font_path:
        # Fallback: draw a simple Z instead
        _draw_z_shape(draw, cx, cy, size, color)
        return

    try:
        font = ImageFont.truetype(font_path, char_size)
    except Exception:
        _draw_z_shape(draw, cx, cy, size, color)
        return

    # Get bounding box for centering
    bbox = font.getbbox("知")
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]
    char_x = cx - char_w // 2 - bbox[0]
    char_y = cy - char_h // 2 - bbox[1]

    draw.text((char_x, char_y), "知", font=font, fill=color)


# ── 图标生成器 ───────────────────────────────────

def make_icon(size: int, with_char: bool = True) -> Image.Image:
    """Create a ZhiXing brand icon with purple gradient + 知 character."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = size // 2
    radius = size // 2 - max(1, size // 40)  # slight inset

    # Gradient circle
    _draw_gradient_circle(draw, cx, cy, radius, PURPLE_A, PURPLE_B)

    # Soft inner glow
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for i in range(max(1, size // 10)):
        alpha = int(20 * (1 - i / (size / 10)))
        gdraw.ellipse(
            [cx - radius + i, cy - radius + i, cx + radius - i, cy + radius - i],
            outline=(255, 255, 255, alpha),
        )
    img = Image.alpha_composite(img, glow)

    # Character
    if with_char and size >= 32:
        char_size = int(size * 0.55)
        font_path = _find_cjk_font(char_size)
        if font_path:
            # Draw 知 on a separate layer for crispness
            layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            ldraw = ImageDraw.Draw(layer)
            _draw_zhi_char(ldraw, cx, cy, size, WHITE, font_path)
            img = Image.alpha_composite(img, layer)
        else:
            # Fallback to Z shape
            layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            ldraw = ImageDraw.Draw(layer)
            _draw_z_shape(ldraw, cx, cy, size, WHITE)
            img = Image.alpha_composite(img, layer)

    return img


def make_tray(size: int, template: bool = False) -> Image.Image:
    """Create a tray icon (simpler version for small sizes)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = size // 2
    radius = size // 2 - 1

    if template:
        # macOS template: black only, system handles dark/light
        draw.ellipse([1, 1, size - 2, size - 2], fill=(0, 0, 0, 200))
        if size >= 16:
            _draw_z_shape(draw, cx, cy, size, color=(0, 0, 0, 255), width_factor=0.12)
    else:
        _draw_gradient_circle(draw, cx, cy, radius, PURPLE_A, PURPLE_B)
        if size >= 12:
            _draw_z_shape(draw, cx, cy, size, color=WHITE, width_factor=0.12)

    return img


# ── 批量生成 ─────────────────────────────────────

def generate_all():
    os.makedirs(CHROME_EXT_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    # ── 1. Chrome 扩展图标 ──
    icon_128 = make_icon(128)
    icon_128.save(os.path.join(CHROME_EXT_DIR, "icon.png"))
    print(f"✅ Chrome 扩展图标: chrome-extension/icon.png (128×128)")

    # ── 2. Electron 应用图标 ──
    icon_1024 = make_icon(1024)
    icon_1024.save(os.path.join(BUILD_DIR, "icon.png"))
    print(f"✅ Electron 应用图标: build/icon.png (1024×1024)")

    # ── 3. Tray 图标（macOS light mode） ──
    make_tray(22).save(os.path.join(BUILD_DIR, "tray.png"))
    make_tray(44).save(os.path.join(BUILD_DIR, "tray@2x.png"))
    print(f"✅ 托盘图标 (light): tray.png / tray@2x.png")

    # ── 4. Tray 图标（macOS dark mode = template） ──
    make_tray(22, template=True).save(os.path.join(BUILD_DIR, "trayTemplate.png"))
    make_tray(44, template=True).save(os.path.join(BUILD_DIR, "trayTemplate@2x.png"))
    print(f"✅ 托盘图标 (template): trayTemplate.png / trayTemplate@2x.png")

    # ── 5. Tray 图标（Windows/Linux 彩色） ──
    make_tray(16).save(os.path.join(BUILD_DIR, "tray_color.png"))
    make_tray(32).save(os.path.join(BUILD_DIR, "tray_color@2x.png"))
    print(f"✅ 托盘图标 (color): tray_color.png / tray_color@2x.png")

    # ── 6. 生成 Base64 数据（用于 Electron main.js 内嵌） ──
    tray_22 = make_tray(22)
    bio = BytesIO()
    tray_22.save(bio, format="PNG")
    b64 = base64.b64encode(bio.getvalue()).decode("ascii")
    print(f"\n✅ Tray Base64 数据 (22×22, {len(b64)} 字符)")
    print(f"   用于替换 main.js 中的 PNG_BASE64")

    # ── 7. 生成 floatBtn HTML 数据 ──
    float_icon = make_icon(64)
    bio2 = BytesIO()
    float_icon.save(bio2, format="PNG")
    float_b64 = base64.b64encode(bio2.getvalue()).decode("ascii")
    print(f"\n✅ FloatBtn Base64 数据 (32×32, {len(float_b64)} 字符)")
    print(f"   用于替换 main.js 中的 Z 字母按钮")

    # ── 8. 验证所有生成文件 ──
    print("\n─── 文件清单 ───")
    for f in sorted(os.listdir(CHROME_EXT_DIR)):
        fp = os.path.join(CHROME_EXT_DIR, f)
        if os.path.isfile(fp) and f.endswith(".png"):
            print(f"  📦 chrome-extension/{f}  ({os.path.getsize(fp)} bytes)")
    for f in sorted(os.listdir(BUILD_DIR)):
        fp = os.path.join(BUILD_DIR, f)
        if os.path.isfile(fp) and (f.endswith(".png") or f.endswith(".ico")):
            print(f"  📦 build/{f}  ({os.path.getsize(fp)} bytes)")

    return b64, float_b64


if __name__ == "__main__":
    tray_b64, float_b64 = generate_all()
