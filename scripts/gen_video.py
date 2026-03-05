#!/usr/bin/env python3
"""
CaptainCast · 视频生成脚本 v2
生成 B站 16:9 (1920x1080) 和 视频号 1:1 (1080x1080) 视频

运行：
  python3 scripts/gen_video.py --ep 002
  python3 scripts/gen_video.py --ep 001
"""
import sys, json, subprocess, tempfile, random, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── 调色板 ─────────────────────────────────────────────
GOLD       = (200, 169, 110)
GOLD_LIGHT = (235, 208, 155)
GOLD_DIM   = (110, 82, 40)
DARK       = (6, 6, 16)
DARK2      = (12, 12, 26)
WHITE      = (248, 245, 238)
GRAY_L     = (195, 188, 175)
GRAY_D     = (140, 132, 118)

# 字体路径（按优先级）
FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]
FONT_MONO_PATH = "/System/Library/Fonts/Menlo.ttc"


# ─── 工具 ───────────────────────────────────────────────
def get_ep():
    for i, a in enumerate(sys.argv):
        if a == '--ep' and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    eps = sorted(Path("episodes").glob("ep*/config.json"))
    return eps[-1].parent.name.replace("ep", "") if eps else "001"


def fnt(size, bold=False):
    """尝试加载中文字体，PingFang 优先"""
    for path in FONT_PATHS:
        try:
            idx = 1 if bold and "PingFang" in path else 0
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def fnt_mono(size):
    try:
        return ImageFont.truetype(FONT_MONO_PATH, size)
    except Exception:
        return ImageFont.load_default()


def fill_crop(img, target_w, target_h):
    """等比缩放后裁剪到目标尺寸（cover 模式）"""
    ow, oh = img.size
    scale = max(target_w / ow, target_h / oh)
    nw, nh = int(ow * scale), int(oh * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    x = (nw - target_w) // 2
    y = (nh - target_h) // 2
    return img.crop((x, y, x + target_w, y + target_h))


def add_rounded_corners(img, radius=24):
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, img.width, img.height], radius=radius, fill=255
    )
    img.putalpha(mask)
    return img


def draw_gradient(img, x0, y0, x1, y1, color_start, color_end, steps=80):
    """在 img 上叠加线性渐变矩形（RGBA）"""
    overlay = img if img.mode == "RGBA" else img.convert("RGBA")
    tmp = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(tmp)
    dx = (x1 - x0) / steps
    for i in range(steps):
        t = i / steps
        r = int(color_start[0] + t * (color_end[0] - color_start[0]))
        g = int(color_start[1] + t * (color_end[1] - color_start[1]))
        b = int(color_start[2] + t * (color_end[2] - color_start[2]))
        a = int(color_start[3] + t * (color_end[3] - color_start[3]))
        cx = int(x0 + i * dx)
        draw.rectangle([cx, y0, cx + int(dx) + 1, y1], fill=(r, g, b, a))
    return Image.alpha_composite(overlay, tmp)


def add_stars(img, count=200, seed=42):
    """添加金色星点背景"""
    rng = random.Random(seed)
    W, H = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    for _ in range(count):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, H - 1)
        r = rng.choice([1, 1, 1, 2])
        a = rng.randint(25, 90)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*GOLD, a))
    return img


def draw_glow_border(canvas, x, y, w, h, radius=24, glow_color=GOLD, glow_px=18):
    """在 canvas 上绘制圆角发光边框（先画模糊扩散层，再画锐利金线）"""
    # 发光扩散层
    glow_img = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_img)
    for i in range(glow_px, 0, -1):
        a = int(60 * (i / glow_px) ** 2)
        gd.rounded_rectangle(
            [x - i, y - i, x + w + i, y + h + i],
            radius=radius + i, outline=(*glow_color, a), width=2
        )
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=6))
    canvas = Image.alpha_composite(canvas, glow_img)
    # 锐利金边
    bd = ImageDraw.Draw(canvas)
    bd.rounded_rectangle([x, y, x + w, y + h], radius=radius,
                          outline=(*GOLD_LIGHT, 200), width=2)
    return canvas


def draw_ep_badge(draw, x, y, ep_num, fn):
    """绘制 EP.001 胶囊徽章"""
    text = f"EP.{ep_num}"
    tw = draw.textlength(text, font=fn)
    pad_x, pad_y = 18, 8
    bw = tw + pad_x * 2
    bh = fn.size + pad_y * 2
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=bh // 2,
                            fill=GOLD_DIM, outline=(*GOLD, 180), width=1)
    draw.text((x + pad_x, y + pad_y), text, font=fn, fill=(*GOLD_LIGHT, 255))
    return bw, bh


def wrap_text(text, max_chars):
    """按最大字符数分行（中文优先在标点处换行）"""
    lines = []
    buf = []
    for ch in text:
        buf.append(ch)
        if len(buf) >= max_chars or ch in "，。？！；":
            lines.append("".join(buf))
            buf = []
    if buf:
        lines.append("".join(buf))
    return lines


def text_shadow(draw, x, y, text, fn, fill, offset=3, shadow_a=150):
    draw.text((x + offset, y + offset), text, font=fn, fill=(*DARK, shadow_a))
    draw.text((x, y), text, font=fn, fill=fill)


# ─── B站帧 1920×1080 ──────────────────────────────────
def make_frame_bilibili(cover_path, cfg, ep_num):
    W, H = 1920, 1080
    WAVE_H = 140
    CONTENT_H = H - WAVE_H  # 940

    cover_orig = Image.open(cover_path).convert("RGB")

    # ── 背景：填满 + 重度模糊 + 渐变蒙层 ──
    bg = fill_crop(cover_orig, W, H)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=48))
    bg = bg.convert("RGBA")
    # 全局深色底
    dark_layer = Image.new("RGBA", (W, H), (*DARK, 195))
    bg = Image.alpha_composite(bg, dark_layer)
    # 从左往右加深（让右侧文字区域更暗）
    bg = draw_gradient(bg, W // 2, 0, W, H,
                       (DARK[0], DARK[1], DARK[2], 0),
                       (DARK[0], DARK[1], DARK[2], 120))
    # 星点
    bg = add_stars(bg, count=180, seed=int(ep_num) * 7)

    # ── 封面图：左侧，垂直居中 ──
    PAD = 70
    cov_h = CONTENT_H - PAD * 2
    cov_w = int(cover_orig.width * cov_h / cover_orig.height)
    cov = cover_orig.resize((cov_w, cov_h), Image.LANCZOS)
    cov = add_rounded_corners(cov, radius=20)
    cov_x = PAD + 30
    cov_y = PAD

    # 阴影
    shadow_r = 28
    shadow = Image.new("RGBA", (cov_w + shadow_r * 4, cov_h + shadow_r * 4), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [shadow_r * 2, shadow_r * 2, cov_w + shadow_r * 2, cov_h + shadow_r * 2],
        radius=20, fill=(0, 0, 0, 100)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_r))
    bg.paste(shadow.convert("RGB"), (cov_x - shadow_r * 2, cov_y - shadow_r * 2),
             shadow.split()[3])
    bg.paste(cov.convert("RGB"), (cov_x, cov_y), cov.split()[3])

    # 发光金边
    bg = draw_glow_border(bg, cov_x, cov_y, cov_w, cov_h, radius=20)

    # ── 右侧文字区域 ──
    GUTTER = 64
    text_x = cov_x + cov_w + GUTTER
    text_right = W - GUTTER
    text_w = text_right - text_x

    draw = ImageDraw.Draw(bg)

    # 解析标题
    title_full = cfg.get("title", "")
    subtitle = title_full.split("：", 1)[1] if "：" in title_full else title_full
    ep_label = title_full.split("：", 1)[0] if "：" in title_full else f"船长电台{ep_num}"

    ty = cov_y + 40

    # 节目名（金色，带下划线）
    fn_brand = fnt(36, bold=True)
    brand_txt = "CaptainCast  超时空电台"
    draw.text((text_x, ty), brand_txt, font=fn_brand, fill=GOLD)
    ty += fn_brand.size + 10
    bw = int(draw.textlength(brand_txt, font=fn_brand))
    draw.rectangle([text_x, ty, text_x + bw, ty + 2], fill=(*GOLD_DIM, 200))
    ty += 18

    # EP 徽章 + 来源标签
    fn_badge = fnt(22)
    badge_w, badge_h = draw_ep_badge(draw, text_x, ty, ep_num, fn_badge)
    # 来源标签旁边
    fn_src = fnt(22)
    draw.text((text_x + badge_w + 16, ty + (badge_h - fn_src.size) // 2),
              ep_label, font=fn_src, fill=GRAY_D)
    ty += badge_h + 30

    # 金色分隔线
    draw.rectangle([text_x, ty, text_x + text_w, ty + 1], fill=(*GOLD, 100))
    ty += 22

    # 主标题（最大字号，换行）
    fn_title = fnt(62, bold=True)
    title_lines = wrap_text(subtitle, max_chars=13)[:3]
    for line in title_lines:
        text_shadow(draw, text_x, ty, line.strip(), fn_title, WHITE, offset=4, shadow_a=180)
        ty += fn_title.size + 12

    ty += 18

    # 摘要（最多2行）
    digest = cfg.get("digest", "")
    fn_digest = fnt(26)
    digest_lines = wrap_text(digest, max_chars=24)[:2]
    for line in digest_lines:
        draw.text((text_x, ty), line.strip(), font=fn_digest, fill=GRAY_L)
        ty += fn_digest.size + 10

    # 底部 URL + 品牌
    fn_url = fnt_mono(22)
    url_txt = "wyonliu.github.io/CaptainCast"
    draw.text((text_x, CONTENT_H - 60), url_txt, font=fn_url, fill=GOLD_DIM)

    # ── 波形区 ──
    wave_overlay = Image.new("RGBA", (W, WAVE_H), (*DARK, 230))
    bg.paste(wave_overlay.convert("RGB"), (0, CONTENT_H), wave_overlay.split()[3])
    # 金色分隔线
    draw.rectangle([0, CONTENT_H - 3, W, CONTENT_H + 1], fill=(*GOLD, 220))

    return bg.convert("RGB")


# ─── 视频号帧 1080×1080 ──────────────────────────────
def make_frame_shipinhao(cover_path, cfg, ep_num):
    W, H = 1080, 1080
    WAVE_H = 180

    cover_orig = Image.open(cover_path).convert("RGB")

    # 背景：重度模糊
    bg = fill_crop(cover_orig, W, H)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    bg = bg.convert("RGBA")
    dark_layer = Image.new("RGBA", (W, H), (*DARK, 200))
    bg = Image.alpha_composite(bg, dark_layer)
    # 底部加深（给文字区域）
    bg = draw_gradient(bg, 0, H // 2, W, H,
                       (DARK[0], DARK[1], DARK[2], 0),
                       (DARK[0], DARK[1], DARK[2], 160),)
    bg = add_stars(bg, count=160, seed=int(ep_num) * 13)

    # ── 顶部品牌条 ──
    BRAND_H = 70
    brand_bar = Image.new("RGBA", (W, BRAND_H), (*DARK2, 210))
    bg.paste(brand_bar.convert("RGB"), (0, 0), brand_bar.split()[3])
    draw = ImageDraw.Draw(bg)
    fn_brand = fnt(30, bold=True)
    brand_txt = "✦  CaptainCast 超时空电台  ✦"
    blen = draw.textlength(brand_txt, font=fn_brand)
    draw.text(((W - blen) // 2, (BRAND_H - fn_brand.size) // 2),
              brand_txt, font=fn_brand, fill=GOLD)
    # 品牌条下边线
    draw.rectangle([0, BRAND_H, W, BRAND_H + 2], fill=(*GOLD, 160))

    # ── 封面图居中（品牌条下方，文字区域上方）──
    TEXT_H = 300  # 下部文字区
    IMG_AREA_Y = BRAND_H + 20
    IMG_AREA_H = H - TEXT_H - BRAND_H - 20 - 20  # 去掉上下边距
    cov_h = IMG_AREA_H
    cov_w = int(cover_orig.width * cov_h / cover_orig.height)
    cov = cover_orig.resize((cov_w, cov_h), Image.LANCZOS)
    cov = add_rounded_corners(cov, radius=18)
    cov_x = (W - cov_w) // 2
    cov_y = IMG_AREA_Y + 10

    # 阴影
    shadow = Image.new("RGBA", (cov_w + 60, cov_h + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [30, 30, cov_w + 30, cov_h + 30], radius=18, fill=(0, 0, 0, 110)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=20))
    bg.paste(shadow.convert("RGB"), (cov_x - 30, cov_y - 30), shadow.split()[3])
    bg.paste(cov.convert("RGB"), (cov_x, cov_y), cov.split()[3])
    bg = draw_glow_border(bg, cov_x, cov_y, cov_w, cov_h, radius=18)

    # ── 下部文字区 ──
    text_y0 = H - TEXT_H - WAVE_H
    # 半透明文字区背景
    txt_bg = Image.new("RGBA", (W, TEXT_H + WAVE_H), (*DARK, 0))
    draw2 = ImageDraw.Draw(txt_bg)
    draw2.rectangle([0, 0, W, TEXT_H], fill=(*DARK2, 180))
    bg.paste(txt_bg.convert("RGB"), (0, text_y0), txt_bg.split()[3])

    draw = ImageDraw.Draw(bg)
    # 金色上边线
    draw.rectangle([0, text_y0, W, text_y0 + 2], fill=(*GOLD, 200))

    ty = text_y0 + 20

    # EP 徽章 + 分隔线
    fn_badge = fnt(24)
    badge_w, badge_h = draw_ep_badge(draw, (W - 120) // 2, ty, ep_num, fn_badge)
    ty += badge_h + 14

    draw.rectangle([(W - 180) // 2, ty, (W + 180) // 2, ty + 1], fill=(*GOLD, 120))
    ty += 14

    # 副标题（最多2行，居中）
    title_full = cfg.get("title", "")
    subtitle = title_full.split("：", 1)[1] if "：" in title_full else title_full
    fn_title = fnt(50, bold=True)
    title_lines = wrap_text(subtitle, max_chars=11)[:2]
    for line in title_lines:
        lw = draw.textlength(line.strip(), font=fn_title)
        lx = (W - lw) // 2
        text_shadow(draw, lx, ty, line.strip(), fn_title, WHITE, offset=4)
        ty += fn_title.size + 8

    ty += 6
    # 摘要（1行，居中，截断）
    digest = cfg.get("digest", "")[:28] + "…"
    fn_digest = fnt(26)
    dw = draw.textlength(digest, font=fn_digest)
    draw.text(((W - dw) // 2, ty), digest, font=fn_digest, fill=GRAY_L)

    # ── 波形区 ──
    wave_y = H - WAVE_H
    wave_overlay = Image.new("RGBA", (W, WAVE_H), (*DARK, 225))
    bg.paste(wave_overlay.convert("RGB"), (0, wave_y), wave_overlay.split()[3])
    draw.rectangle([0, wave_y - 3, W, wave_y + 1], fill=(*GOLD, 220))

    return bg.convert("RGB")


# ─── ffmpeg 合成 ─────────────────────────────────────
def build_video(frame_path, audio_path, out_path, W, H, wave_h, fps=30):
    """
    波形：双层叠加，营造「宇宙琴弦」效果
      - 主弦 (sharp): p2p 模式，细如弦，金色 0xc8a96e
      - 光晕 (glow):  cline 模式，浅金 0xf0d890，高斯模糊后 screen 混合
    结果：发光的细线在深空中颤动，像拨动宇宙的弦
    """
    wave_y = H - wave_h
    fc = (
        # 分离音频为两路
        f"[1:a]asplit=2[a1][a2];"
        # 主弦：p2p 点对点连线，cbrt 压缩动态，细且有张力
        f"[a1]showwaves=s={W}x{wave_h}:mode=p2p:scale=cbrt"
        f":colors=0xc8a96e@0.92:draw=full[sharp];"
        # 光晕：cline 填充，轻描，再做高斯模糊
        f"[a2]showwaves=s={W}x{wave_h}:mode=cline:scale=sqrt"
        f":colors=0xf0d890@0.35:draw=full[soft];"
        f"[soft]gblur=sigma=5[glow];"
        # screen 混合：细弦 + 光晕 = 发光的宇宙琴弦
        f"[sharp][glow]blend=all_mode=screen[waves];"
        f"[0:v][waves]overlay=0:{wave_y}[vout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(frame_path),
        "-i", str(audio_path),
        "-filter_complex", fc,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k",
        "-shortest",
        "-movflags", "+faststart",
        str(out_path)
    ]
    print(f"  ffmpeg 合成中... ({W}x{H})")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("  ❌ ffmpeg 错误:")
        print(result.stderr[-1200:])
        return False
    return True


# ─── 主流程 ──────────────────────────────────────────
def main():
    ep = get_ep()
    cfg_path = Path(f"episodes/ep{ep}/config.json")
    if not cfg_path.exists():
        print(f"❌ 找不到 {cfg_path}"); return

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    img_dir = Path(f"episodes/ep{ep}/images")
    cover_path = img_dir / cfg["thumb_image"]
    audio_path = Path(f"audio/output/ep{ep}_podcast.mp3")
    if not audio_path.exists():
        audio_path = Path(f"audio/output/ep{ep}_podcast_64k.mp3")
    out_dir = Path(f"episodes/ep{ep}/videos")
    out_dir.mkdir(exist_ok=True)

    preview_only = "--preview" in sys.argv

    print("=" * 56)
    print(f"CaptainCast EP.{ep} · 视频生成 v2")
    print(f"  封面: {cover_path.name}")
    if not preview_only:
        print(f"  音频: {audio_path.name}")
    print("=" * 56)

    with tempfile.TemporaryDirectory() as tmp:
        # B站 1920x1080
        print("\n🎬 B站版 (1920×1080)...")
        bili_frame = Path(tmp) / "bili_frame.png"
        frame = make_frame_bilibili(cover_path, cfg, ep)
        frame.save(str(bili_frame), "PNG")
        preview = out_dir / f"ep{ep}_preview_bilibili.png"
        frame.save(str(preview))
        print(f"  📐 预览帧: {preview}")

        if not preview_only and audio_path.exists():
            bili_out = out_dir / f"ep{ep}_bilibili.mp4"
            if build_video(bili_frame, audio_path, bili_out, 1920, 1080, 140):
                mb = bili_out.stat().st_size / 1024 / 1024
                print(f"  ✅ {bili_out.name}  ({mb:.1f} MB)")

        # 视频号 1080x1080
        print("\n🎬 视频号版 (1080×1080)...")
        ship_frame = Path(tmp) / "ship_frame.png"
        frame2 = make_frame_shipinhao(cover_path, cfg, ep)
        frame2.save(str(ship_frame), "PNG")
        preview2 = out_dir / f"ep{ep}_preview_shipinhao.png"
        frame2.save(str(preview2))
        print(f"  📐 预览帧: {preview2}")

        if not preview_only and audio_path.exists():
            ship_out = out_dir / f"ep{ep}_shipinhao.mp4"
            if build_video(ship_frame, audio_path, ship_out, 1080, 1080, 180):
                mb = ship_out.stat().st_size / 1024 / 1024
                print(f"  ✅ {ship_out.name}  ({mb:.1f} MB)")

    print(f"\n✨ 完成！{out_dir}/")
    print("=" * 56)

    # 提示用 Preview 查看
    import subprocess as sp
    sp.run(["open", str(preview), str(preview2)], check=False)


if __name__ == "__main__":
    main()
