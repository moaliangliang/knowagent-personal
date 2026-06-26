"""
科技感机器人图标生成器 (Sci-Fi Robot Icon Generator)
为 知行 (ZhiXing) 生成一套科技感机器人图标
"""

from PIL import Image, ImageDraw
import os, math

# ── 调色板 ──
BG_A = (8, 12, 30)        # 深空蓝黑
BG_B = (15, 25, 55)       # 暗蓝
METAL = (180, 200, 225)   # 金属银
METAL_D = (100, 120, 150) # 暗金属
METAL_L = (220, 235, 255) # 亮金属
GLOW = (0, 200, 255)      # 青色发光
GLOW_D = (0, 140, 220)    # 暗青
GLOW_L = (150, 240, 255)  # 亮青
DARK = (20, 25, 45)       # 深色面板
ACCENT = (0, 180, 255)    # 点缀蓝
CIRCUIT = (60, 120, 200, 150)  # 电路线
NODE = (0, 220, 255)      # 节点发光
BODY_A = (25, 40, 70)     # 身体深色
BODY_B = (50, 75, 120)    # 身体亮色
SILVER = (160, 180, 210)  # 银色配件


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def hex_pts(cx, cy, r, rot=0):
    """正六边形顶点"""
    pts = []
    for i in range(6):
        a = rot + i * math.pi / 3
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def draw_robot(draw, cx, cy, s):
    """在 (cx,cy) 处画科技机器人，s=尺寸缩放基准"""

    # ── 背景光圈 (深色渐变) ──
    for i in range(10, 0, -1):
        r = int(s * 0.47 * i / 10)
        c = lerp(BG_B, BG_A, (10 - i) / 9)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)

    # ── 装饰性同心圆环 ──
    for i in range(3):
        r = int(s * 0.38 + i * 6)
        draw.arc([cx - r, cy - r, cx + r, cy + r], 0, 360,
                 fill=(0, 180, 255, 20 - i * 5), width=1)

    hr = s * 0.33          # 头部尺寸
    hx, hy = cx, cy - s * 0.04  # 头中心

    # ── 头部轮廓 (六边形) ──
    head_r = hr
    rot = math.pi / 6  # 30度让六边形尖朝上
    hex_h = hex_pts(hx, hy, head_r, rot)
    draw.polygon(hex_h, fill=DARK, outline=METAL_D, width=max(1, int(s * 0.008)))

    # 头部内边框
    hex_h_inner = hex_pts(hx, hy, head_r * 0.88, rot)
    draw.polygon(hex_h_inner, outline=(0, 180, 255, 60), width=1)

    # ── 左右护耳 / 侧面板 ──
    for side in [-1, 1]:
        # 侧板
        px = hx + side * head_r * 1.05
        pts = [
            (px - side * s * 0.03, hy - head_r * 0.65),
            (px + side * s * 0.06, hy - head_r * 0.70),
            (px + side * s * 0.08, hy - head_r * 0.20),
            (px - side * s * 0.04, hy - head_r * 0.15),
        ]
        draw.polygon(pts, fill=METAL_D)
        # 侧板发光点
        draw.ellipse([
            px + side * s * 0.02 - s * 0.012, hy - head_r * 0.45 - s * 0.012,
            px + side * s * 0.02 + s * 0.012, hy - head_r * 0.45 + s * 0.012
        ], fill=GLOW)

    # ── 头顶天线 ──
    ant_x = hx
    ant_base = hy - head_r * 0.80
    ant_top = hy - head_r * 1.15
    # 天线杆
    draw.rectangle([
        ant_x - s * 0.008, ant_top,
        ant_x + s * 0.008, ant_base
    ], fill=SILVER)
    # 天线球
    draw.ellipse([
        ant_x - s * 0.025, ant_top - s * 0.025,
        ant_x + s * 0.025, ant_top + s * 0.025
    ], fill=GLOW)
    # 天线球辉光
    draw.ellipse([
        ant_x - s * 0.045, ant_top - s * 0.045,
        ant_x + s * 0.045, ant_top + s * 0.045
    ], fill=(0, 200, 255, 60))

    # 信号波纹
    for i, rad in enumerate([s * 0.07, s * 0.11, s * 0.15]):
        draw.arc([ant_x - rad, ant_top - rad, ant_x + rad, ant_top + rad],
                 -40 + i * 15, 40 + i * 15, fill=(0, 220, 255, 100 - i * 25), width=1)

    # ── HUD 眼睛 (科技感护目镜) ──
    es = head_r * 0.28     # 眼间距
    ey = hy + head_r * 0.02

    for ex in [hx - es, hx + es]:
        # 眼眶 (多边形)
        ew = head_r * 0.20
        eh = head_r * 0.22
        # 六边形眼眶
        eye_pts = []
        for i in range(6):
            a = i * math.pi / 3
            rx = ew if i % 2 == 0 else ew * 0.8
            ry = eh if i % 2 == 0 else eh * 0.8
            eye_pts.append((ex + rx * math.cos(a), ey + ry * math.sin(a)))
        draw.polygon(eye_pts, fill=(0, 0, 0, 200), outline=GLOW_D, width=max(1, int(s * 0.005)))

        # LED 瞳孔 (发光)
        pupil_rw = ew * 0.40
        pupil_rh = eh * 0.55
        # 主发光
        pupil_pts = []
        for i in range(6):
            a = -math.pi / 2 + i * math.pi / 3
            pupil_pts.append((
                ex + pupil_rw * math.cos(a),
                ey + pupil_rh * math.sin(a)
            ))
        draw.polygon(pupil_pts, fill=GLOW)
        # 内亮光
        inner_pts = []
        for i in range(6):
            a = -math.pi / 2 + i * math.pi / 3
            inner_pts.append((
                ex + pupil_rw * 0.5 * math.cos(a),
                ey + pupil_rh * 0.5 * math.sin(a)
            ))
        draw.polygon(inner_pts, fill=GLOW_L)

        # 发光扩散
        draw.ellipse([
            ex - ew * 1.2, ey - eh * 1.2,
            ex + ew * 1.2, ey + eh * 1.2
        ], fill=(0, 200, 255, 25))

    # ── 额头 HUD 指示灯 ──
    hud_y = hy - head_r * 0.35
    for i, dx in enumerate([-s * 0.04, 0, s * 0.04]):
        draw.ellipse([
            hx + dx - s * 0.012, hud_y - s * 0.012,
            hx + dx + s * 0.012, hud_y + s * 0.012
        ], fill=(0, 255, 200, 150) if i == 1 else (0, 200, 255, 80))

    # ── 嘴巴 (科技感灯条) ──
    my = hy + head_r * 0.40
    mw = head_r * 0.35
    mh = head_r * 0.05
    # 灯条槽
    draw.rounded_rectangle([
        hx - mw, my - mh,
        hx + mw, my + mh
    ], radius=s * 0.015, fill=DARK, outline=METAL_D, width=max(1, int(s * 0.004)))

    # 灯条分段发光
    segs = 7
    seg_w = (mw * 2 - s * 0.02) / segs
    for i in range(segs):
        x1 = hx - mw + s * 0.01 + i * seg_w
        x2 = x1 + seg_w * 0.7
        alpha = 200 if i in (1, 3, 5) else 60
        draw.rectangle([x1, my - mh + s * 0.01, x2, my + mh - s * 0.01],
                       fill=(0, 220, 255, alpha))

    # ── 脸颊电路纹路 ──
    for side in [-1, 1]:
        # 从眼下延伸的电路线
        cx_pt = hx + side * es * 0.6
        cy_pt = ey + head_r * 0.12
        # 线
        draw.line([
            (cx_pt, cy_pt),
            (cx_pt + side * s * 0.06, cy_pt + s * 0.04),
            (cx_pt + side * s * 0.10, cy_pt + s * 0.02),
        ], fill=CIRCUIT, width=max(1, int(s * 0.004)))
        # 节点
        draw.ellipse([
            cx_pt + side * s * 0.10 - s * 0.008, cy_pt + s * 0.02 - s * 0.008,
            cx_pt + side * s * 0.10 + s * 0.008, cy_pt + s * 0.02 + s * 0.008
        ], fill=NODE)

    # ── 颈部和身体 ──
    bt = hy + head_r * 0.55   # 脖子底
    bb = hy + head_r * 0.90   # 身体底

    # 脖子 (圆柱)
    draw.rectangle([
        hx - s * 0.04, hy + head_r * 0.50,
        hx + s * 0.04, bt
    ], fill=METAL_D)
    # 脖子环
    draw.ellipse([
        hx - s * 0.055, bt - s * 0.015,
        hx + s * 0.055, bt + s * 0.015
    ], fill=SILVER)

    # 身体
    body_w = head_r * 0.48
    body_pts = [
        (hx - body_w, bt),
        (hx + body_w, bt),
        (hx + body_w * 1.1, bb),
        (hx - body_w * 1.1, bb),
    ]
    draw.polygon(body_pts, fill=BODY_A)
    draw.polygon(body_pts, outline=METAL_D, width=max(1, int(s * 0.004)))

    # 身体中心装饰
    draw.ellipse([
        hx - s * 0.045, bt + s * 0.025,
        hx + s * 0.045, bt + s * 0.09
    ], fill=GLOW)
    draw.ellipse([
        hx - s * 0.025, bt + s * 0.035,
        hx + s * 0.025, bt + s * 0.08
    ], fill=GLOW_L)

    # 身体线条
    for i in range(2):
        ly = bt + s * 0.04 + i * s * 0.025
        draw.line([
            (hx - body_w * 0.7, ly),
            (hx + body_w * 0.7, ly)
        ], fill=(60, 120, 200, 80), width=1)

    # ── 周围浮动科技元素 ──
    for angle, dist, size_s in [
        (0.3, 0.62, 0.025),
        (1.8, 0.58, 0.020),
        (3.5, 0.60, 0.022),
        (4.8, 0.55, 0.018),
    ]:
        ex = hx + math.cos(angle) * hr * dist
        ey = hy + math.sin(angle) * hr * dist
        # 菱形科技点
        ds = s * size_s
        pts = [
            (ex, ey - ds), (ex + ds, ey),
            (ex, ey + ds), (ex - ds, ey)
        ]
        draw.polygon(pts, fill=GLOW_D if angle < 3 else ACCENT)

    # ── 外发光 (科技蓝) ──
    glow = Image.new("RGBA", (int(s * 1.2), int(s * 1.2)), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gc = int(s * 0.6)
    for i in range(8, 0, -1):
        r = int(gc + i * 5)
        a = 15 - i * 1
        if a > 0:
            gd.ellipse([s * 0.6 - r, s * 0.6 - r, s * 0.6 + r, s * 0.6 + r],
                       outline=(0, 150, 255, a), width=2)
    draw.bitmap((int(cx - s * 0.6), int(cy - s * 0.6)), glow, fill=None)


def gen_icon(path, size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_robot(draw, size // 2, size // 2, size)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    img.save(path, "PNG")
    print(f"  ✓ {path}  ({size}x{size})")


def main():
    print("🤖 生成科技感机器人 图标...\n")

    print("📦 应用图标:")
    gen_icon("electron-app/build/icon.png", 512)
    gen_icon("chrome-extension/icon.png", 128)

    print("\n🔧 托盘图标:")
    for sfx, sz in [("", 22), ("@2x", 44)]:
        # 彩色托盘
        gen_icon(f"electron-app/build/tray_color{sfx}.png", sz)
        # 单色托盘
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        draw_robot(d, sz // 2, sz // 2, sz)
        img.save(f"electron-app/build/tray{sfx}.png", "PNG")
        print(f"  ✓ electron-app/build/tray{sfx}.png  ({sz}x{sz})")
        # 模板图标 (全白)
        img2 = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(img2)
        bak = {}
        for k in ["BG_A", "BG_B", "METAL", "METAL_D", "METAL_L", "GLOW", "GLOW_D",
                   "GLOW_L", "DARK", "ACCENT", "CIRCUIT", "NODE", "BODY_A", "BODY_B", "SILVER"]:
            bak[k] = globals()[k]
            globals()[k] = (255, 255, 255)
        draw_robot(d2, sz // 2, sz // 2, sz)
        globals().update(bak)
        img2.save(f"electron-app/build/trayTemplate{sfx}.png", "PNG")
        print(f"  ✓ electron-app/build/trayTemplate{sfx}.png  ({sz}x{sz})")

    # 更新内嵌 base64
    print("\n🔄 更新内嵌图标...")
    with open("electron-app/build/tray_color.png", "rb") as f:
        import base64
        b64 = base64.b64encode(f.read()).decode()

    import re
    with open("electron-app/main.js", "r") as f:
        js = f.read()

    old_b64 = re.search(r'const PNG_BASE64 = "([^"]+)"', js)
    if old_b64:
        js = js.replace(old_b64.group(1), b64)
        with open("electron-app/main.js", "w") as f:
            f.write(js)
        print(f"  ✓ 更新 main.js 内嵌图标 ({len(b64)} bytes)")

    # Windows .ico
    print("\n🪟 Windows 图标:")
    img = Image.open("electron-app/build/icon.png")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
    imgs[0].save("electron-app/build/icon.ico", format="ICO", sizes=sizes, append_images=imgs[1:])
    print("  ✓ electron-app/build/icon.ico")

    img_tray = Image.open("electron-app/build/tray_color.png")
    t_16 = img_tray.resize((16, 16), Image.LANCZOS)
    t_24 = img_tray.resize((24, 24), Image.LANCZOS)
    t_32 = img_tray.resize((32, 32), Image.LANCZOS)
    t_16.save("electron-app/build/tray.ico", format="ICO", sizes=[(16, 16), (24, 24), (32, 32)])
    print("  ✓ electron-app/build/tray.ico")

    print("\n✨ 全部完成!")


if __name__ == "__main__":
    main()
