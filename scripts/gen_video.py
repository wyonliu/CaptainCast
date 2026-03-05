#!/usr/bin/env python3
"""
CaptainCast · 视频生成脚本 v3
生成 B站 16:9 (1920x1080) 和 视频号 1:1 (1080x1080) 视频

运行：
  python3 scripts/gen_video.py --ep 002           # 生成全量视频
  python3 scripts/gen_video.py --ep 001 --preview # 仅生成静帧预览（快）
"""
import sys, json, subprocess, tempfile, random, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── 调色板 ─────────────────────────────────────────────
GOLD       = (200, 169, 110)   # 主金色
GOLD_L     = (240, 210, 140)   # 亮金（高光）
GOLD_DIM   = (100, 72, 32)     # 暗金（徽章底）
AMBER      = (220, 130, 50)    # 琥珀橙（装饰）
DARK       = (5, 5, 14)        # 宇宙黑
DARK2      = (10, 10, 22)      # 次深
WHITE      = (252, 248, 240)   # 暖白（主标题）
GRAY_L     = (190, 182, 168)   # 浅灰（摘要）
GRAY_D     = (130, 122, 108)   # 深灰（次要信息）

# 字体（优先 PingFang SC，回退 STHeiti）
FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/Library/Fonts/STHeiti Medium.ttc",
]
FONT_MONO = "/System/Library/Fonts/Menlo.ttc"


# ─── 工具函数 ────────────────────────────────────────────
def get_ep():
    for i, a in enumerate(sys.argv):
        if a == "--ep" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    eps = sorted(Path("episodes").glob("ep*/config.json"))
    return eps[-1].parent.name.replace("ep", "") if eps else "001"


def fnt(size, bold=False):
    for path in FONT_PATHS:
        try:
            idx = 1 if (bold and "PingFang" in path) else 0
            f = ImageFont.truetype(path, size, index=idx)
            return f
        except Exception:
            continue
    return ImageFont.load_default()


def fnt_mono(size):
    try:
        return ImageFont.truetype(FONT_MONO, size)
    except Exception:
        return ImageFont.load_default()


def fill_crop(img, W, H):
    ow, oh = img.size
    scale = max(W / ow, H / oh)
    nw, nh = int(ow * scale), int(oh * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - W) // 2, (nh - H) // 2
    return img.crop((x, y, x + W, y + H))


def rounded(img, radius=20):
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, img.width, img.height], radius=radius, fill=255
    )
    img.putalpha(mask)
    return img


def gradient_h(canvas, x0, x1, y0, y1, ca, cb, steps=100):
    """水平线性渐变叠加（RGBA）"""
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sw = (x1 - x0) / steps
    for i in range(steps):
        t = i / steps
        r = int(ca[0] + t * (cb[0] - ca[0]))
        g = int(ca[1] + t * (cb[1] - ca[1]))
        b = int(ca[2] + t * (cb[2] - ca[2]))
        a = int(ca[3] + t * (cb[3] - ca[3]))
        cx = int(x0 + i * sw)
        d.rectangle([cx, y0, cx + int(sw) + 1, y1], fill=(r, g, b, a))
    return Image.alpha_composite(canvas, layer)


def gradient_v(canvas, y0, y1, x0, x1, ca, cb, steps=80):
    """垂直线性渐变叠加（RGBA）"""
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sh = (y1 - y0) / steps
    for i in range(steps):
        t = i / steps
        r = int(ca[0] + t * (cb[0] - ca[0]))
        g = int(ca[1] + t * (cb[1] - ca[1]))
        b = int(ca[2] + t * (cb[2] - ca[2]))
        a = int(ca[3] + t * (cb[3] - ca[3]))
        cy = int(y0 + i * sh)
        d.rectangle([x0, cy, x1, cy + int(sh) + 1], fill=(r, g, b, a))
    return Image.alpha_composite(canvas, layer)


def add_stars(canvas, count=200, seed=42):
    """多层星点（有大有小，有亮有暗）"""
    rng = random.Random(seed)
    W, H = canvas.size
    d = ImageDraw.Draw(canvas, "RGBA")
    for _ in range(count):
        x, y = rng.randint(0, W - 1), rng.randint(0, H - 1)
        r = rng.choices([1, 1, 1, 2, 3], weights=[50, 30, 10, 8, 2])[0]
        a = rng.randint(20, 110)
        col = rng.choices([GOLD, GOLD_L, AMBER, (255, 255, 255)],
                          weights=[40, 30, 20, 10])[0]
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*col, a))
    return canvas


def add_radio_ripples(canvas, cx, cy, count=6, max_r=400, seed=0):
    """同心电台波纹（发光金圈，由内向外衰减）"""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(count):
        t = (i + 1) / count
        r = int(max_r * t)
        a = int(80 * (1 - t) ** 1.5)
        w = max(1, int(3 * (1 - t)))
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=(*GOLD, a), width=w)
    # 轻微模糊让圆更柔和
    layer = layer.filter(ImageFilter.GaussianBlur(radius=3))
    return Image.alpha_composite(canvas, layer)


def add_glow_border(canvas, x, y, w, h, radius=20):
    """图片金色发光边框"""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(16, 0, -1):
        a = int(55 * (i / 16) ** 2)
        d.rounded_rectangle(
            [x - i, y - i, x + w + i, y + h + i],
            radius=radius + i, outline=(*GOLD, a), width=2
        )
    layer = layer.filter(ImageFilter.GaussianBlur(radius=5))
    canvas = Image.alpha_composite(canvas, layer)
    ImageDraw.Draw(canvas).rounded_rectangle(
        [x, y, x + w, y + h], radius=radius,
        outline=(*GOLD_L, 190), width=2
    )
    return canvas


def ep_badge(draw, x, y, ep_num, fn):
    text = f"EP.{ep_num}"
    tw = int(draw.textlength(text, font=fn))
    px, py = 16, 7
    bw, bh = tw + px * 2, fn.size + py * 2
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=bh // 2,
                            fill=GOLD_DIM, outline=(*GOLD, 200), width=1)
    draw.text((x + px, y + py), text, font=fn, fill=(*GOLD_L, 255))
    return bw, bh


def wrap_px(text, max_w, draw, fn):
    """基于像素宽度换行，在标点处优先断行"""
    BREAKS = set("，。？！；、：…")
    lines, buf = [], []
    for ch in text:
        buf.append(ch)
        cur_w = draw.textlength("".join(buf), font=fn)
        if cur_w >= max_w or ch in BREAKS:
            lines.append("".join(buf))
            buf = []
    if buf:
        lines.append("".join(buf))
    return lines


def txt_shadow(draw, x, y, text, fn, fill, off=3, sha=160):
    draw.text((x + off, y + off), text, font=fn, fill=(*DARK, sha))
    draw.text((x, y), text, font=fn, fill=fill)


def add_sine_wave_deco(canvas, y_center, W, amplitude=18, color=GOLD_DIM, alpha=60):
    """背景装饰波纹——正弦曲线"""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = []
    freq = 2 * math.pi / (W / 3)  # 3个完整波形
    for x in range(W):
        y = int(y_center + amplitude * math.sin(freq * x))
        pts.append((x, y))
    d.line(pts, fill=(*color, alpha), width=2)
    layer = layer.filter(ImageFilter.GaussianBlur(radius=2))
    return Image.alpha_composite(canvas, layer)


# ─── B站帧 1920×1080 ──────────────────────────────────
def make_frame_bilibili(cover_path, cfg, ep_num):
    W, H = 1920, 1080
    WAVE_H = 200      # 底部波形区高度（加高）
    CONTENT_H = H - WAVE_H  # 880 px 内容区

    cover_orig = Image.open(cover_path).convert("RGB")

    # ── 背景 ──
    bg = fill_crop(cover_orig, W, H)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=50))
    bg = bg.convert("RGBA")
    # 全局深色
    bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (*DARK, 200)))
    # 左→右渐变（左侧留出封面亮区，右侧文字区更暗）
    bg = gradient_h(bg, W // 3, W, 0, CONTENT_H,
                    (*DARK, 0), (*DARK, 140))
    # 星空
    bg = add_stars(bg, count=220, seed=int(ep_num) * 11)

    # ── 封面图：左侧垂直居中 ──
    PAD = 60
    cov_h = CONTENT_H - PAD * 2        # 760 px
    cov_w = int(cover_orig.width * cov_h / cover_orig.height)
    cov_x, cov_y = PAD + 20, PAD

    # 在封面后面画电台波纹
    cx = cov_x + cov_w // 2
    cy = cov_y + cov_h // 2
    bg = add_radio_ripples(bg, cx, cy, count=7, max_r=max(cov_w, cov_h) // 2 + 100)

    # 封面图阴影
    sh_r = 30
    shadow = Image.new("RGBA", (cov_w + sh_r * 4, cov_h + sh_r * 4), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [sh_r * 2, sh_r * 2, cov_w + sh_r * 2, cov_h + sh_r * 2],
        radius=20, fill=(0, 0, 0, 110)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=sh_r))
    bg.paste(shadow.convert("RGB"), (cov_x - sh_r * 2, cov_y - sh_r * 2), shadow.split()[3])

    cov = cover_orig.resize((cov_w, cov_h), Image.LANCZOS)
    cov = rounded(cov, radius=20)
    bg.paste(cov.convert("RGB"), (cov_x, cov_y), cov.split()[3])
    bg = add_glow_border(bg, cov_x, cov_y, cov_w, cov_h, radius=20)

    # ── 装饰正弦波（内容区中部背景）──
    for offset, amp, alpha in [(-60, 14, 30), (0, 22, 50), (60, 12, 25)]:
        bg = add_sine_wave_deco(bg, CONTENT_H // 2 + offset, W, amp, GOLD_DIM, alpha)

    # ── 右侧文字区 ──
    GUTTER = 56
    text_x = cov_x + cov_w + GUTTER
    text_w = W - text_x - GUTTER

    draw = ImageDraw.Draw(bg)

    # 解析标题
    title_full = cfg.get("title", "")
    subtitle = title_full.split("：", 1)[1] if "：" in title_full else title_full

    # 计算文字总高度，然后垂直居中
    fn_brand  = fnt(34, bold=True)
    fn_badge  = fnt(22)
    fn_title  = fnt(60, bold=True)
    fn_digest = fnt(26)
    fn_url    = fnt_mono(22)

    title_lines = wrap_px(subtitle, text_w, draw, fn_title)[:3]
    digest_lines = wrap_px(cfg.get("digest", ""), text_w - 20, draw, fn_digest)[:2]

    block_h = (fn_brand.size + 14 +      # 节目名
               10 + 2 + 18 +             # 分割线
               32 + 14 +                 # EP 徽章行
               len(title_lines) * (fn_title.size + 10) + 20 +  # 标题
               len(digest_lines) * (fn_digest.size + 8) + 20 + # 摘要
               fn_url.size)              # URL

    ty = max(PAD + 30, (CONTENT_H - block_h) // 2)

    # 品牌名
    draw.text((text_x, ty), "船长与麦洛的超时空电台", font=fn_brand, fill=GOLD)
    ty += fn_brand.size + 14
    bw = int(draw.textlength("船长与麦洛的超时空电台", font=fn_brand))
    draw.rectangle([text_x, ty, text_x + bw, ty + 2], fill=(*GOLD_DIM, 200))
    ty += 18

    # EP 徽章 + 节目标签
    bw2, bh2 = ep_badge(draw, text_x, ty, ep_num, fn_badge)
    ep_label = title_full.split("：", 1)[0] if "：" in title_full else f"船长电台{ep_num}"
    fn_src = fnt(22)
    draw.text((text_x + bw2 + 14, ty + (bh2 - fn_src.size) // 2),
              ep_label, font=fn_src, fill=GRAY_D)
    ty += bh2 + 22

    # 金色细分割线
    draw.rectangle([text_x, ty, text_x + text_w, ty + 1], fill=(*GOLD, 80))
    ty += 20

    # 主标题（逐行绘制，带阴影）
    for line in title_lines:
        txt_shadow(draw, text_x, ty, line.strip(), fn_title, WHITE, off=4, sha=180)
        ty += fn_title.size + 10
    ty += 16

    # 摘要
    for line in digest_lines:
        draw.text((text_x, ty), line.strip(), font=fn_digest, fill=GRAY_L)
        ty += fn_digest.size + 8
    ty += 18

    # URL
    draw.text((text_x, ty), "wyonliu.github.io/CaptainCast", font=fn_url, fill=GOLD_DIM)

    # ── 波形区底部 ──
    # 深色底
    wave_bg = Image.new("RGBA", (W, WAVE_H), (*DARK, 235))
    bg.paste(wave_bg.convert("RGB"), (0, CONTENT_H), wave_bg.split()[3])
    # 波形区装饰：左侧"⊙ 电台波"小图标
    draw.rectangle([0, CONTENT_H - 3, W, CONTENT_H + 1], fill=(*GOLD, 220))

    fn_wave_label = fnt(20)
    draw.text((30, CONTENT_H + (WAVE_H // 2) - 12),
              "◉  船长与麦洛的超时空电台 · 正在播放", font=fn_wave_label, fill=(*GOLD_DIM, 200))

    return bg.convert("RGB")


# ─── 视频号帧 1080×1080 ──────────────────────────────
def make_frame_shipinhao(cover_path, cfg, ep_num):
    W, H = 1080, 1080
    WAVE_H = 200

    cover_orig = Image.open(cover_path).convert("RGB")

    # ── 背景 ──
    bg = fill_crop(cover_orig, W, H)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (*DARK, 205)))
    # 下半部分加深（文字区）
    bg = gradient_v(bg, H // 2, H, 0, W, (*DARK, 0), (*DARK, 170))
    bg = add_stars(bg, count=180, seed=int(ep_num) * 17)

    # ── 顶部品牌条 ──
    BRAND_H = 72
    bar = Image.new("RGBA", (W, BRAND_H), (*DARK2, 220))
    bg.paste(bar.convert("RGB"), (0, 0), bar.split()[3])
    draw = ImageDraw.Draw(bg)
    fn_brand = fnt(28, bold=True)
    brand_txt = "✦  船长与麦洛的超时空电台  ✦"
    blen = int(draw.textlength(brand_txt, font=fn_brand))
    draw.text(((W - blen) // 2, (BRAND_H - fn_brand.size) // 2),
              brand_txt, font=fn_brand, fill=GOLD)
    draw.rectangle([0, BRAND_H, W, BRAND_H + 2], fill=(*GOLD, 160))

    # ── 封面图 ──
    TEXT_H = 280
    IMG_Y0 = BRAND_H + 16
    IMG_ZONE_H = H - TEXT_H - WAVE_H - BRAND_H - 16 - 8
    cov_h = IMG_ZONE_H
    cov_w = int(cover_orig.width * cov_h / cover_orig.height)
    cov_x = (W - cov_w) // 2
    cov_y = IMG_Y0 + 8

    # 电台波纹
    bg = add_radio_ripples(bg, cov_x + cov_w // 2, cov_y + cov_h // 2,
                           count=6, max_r=cov_w // 2 + 80)
    # 阴影
    sh_r = 24
    shw = Image.new("RGBA", (cov_w + sh_r * 4, cov_h + sh_r * 4), (0, 0, 0, 0))
    ImageDraw.Draw(shw).rounded_rectangle(
        [sh_r * 2, sh_r * 2, cov_w + sh_r * 2, cov_h + sh_r * 2],
        radius=18, fill=(0, 0, 0, 110)
    )
    shw = shw.filter(ImageFilter.GaussianBlur(radius=sh_r))
    bg.paste(shw.convert("RGB"), (cov_x - sh_r * 2, cov_y - sh_r * 2), shw.split()[3])

    cov = cover_orig.resize((cov_w, cov_h), Image.LANCZOS)
    cov = rounded(cov, radius=18)
    bg.paste(cov.convert("RGB"), (cov_x, cov_y), cov.split()[3])
    bg = add_glow_border(bg, cov_x, cov_y, cov_w, cov_h, radius=18)

    # ── 文字区 ──
    TEXT_Y = H - TEXT_H - WAVE_H
    txt_panel = Image.new("RGBA", (W, TEXT_H), (*DARK2, 210))
    bg.paste(txt_panel.convert("RGB"), (0, TEXT_Y), txt_panel.split()[3])
    draw = ImageDraw.Draw(bg)
    draw.rectangle([0, TEXT_Y, W, TEXT_Y + 2], fill=(*GOLD, 200))

    ty = TEXT_Y + 20
    fn_badge = fnt(24)
    bw, bh = ep_badge(draw, (W - 90) // 2, ty, ep_num, fn_badge)
    ty += bh + 14

    draw.rectangle([(W - 160) // 2, ty, (W + 160) // 2, ty + 1], fill=(*GOLD, 120))
    ty += 16

    title_full = cfg.get("title", "")
    subtitle = title_full.split("：", 1)[1] if "：" in title_full else title_full
    fn_title = fnt(48, bold=True)
    title_lines = wrap_px(subtitle, W - 100, draw, fn_title)[:2]
    for line in title_lines:
        lw = int(draw.textlength(line.strip(), font=fn_title))
        txt_shadow(draw, (W - lw) // 2, ty, line.strip(), fn_title, WHITE, off=4)
        ty += fn_title.size + 8

    ty += 6
    fn_digest = fnt(24)
    digest = cfg.get("digest", "")
    digest_lines = wrap_px(digest, W - 100, draw, fn_digest)[:1]
    for line in digest_lines:
        lw = int(draw.textlength(line.strip(), font=fn_digest))
        draw.text(((W - lw) // 2, ty), line.strip(), font=fn_digest, fill=GRAY_L)

    # ── 波形区 ──
    wave_y = H - WAVE_H
    wave_bg = Image.new("RGBA", (W, WAVE_H), (*DARK, 235))
    bg.paste(wave_bg.convert("RGB"), (0, wave_y), wave_bg.split()[3])
    draw.rectangle([0, wave_y - 3, W, wave_y + 1], fill=(*GOLD, 220))
    fn_wl = fnt(18)
    wl = "◉  正在播放"
    wlw = int(draw.textlength(wl, font=fn_wl))
    draw.text(((W - wlw) // 2, wave_y + (WAVE_H // 2) - 12),
              wl, font=fn_wl, fill=(*GOLD_DIM, 200))

    return bg.convert("RGB")


# ─── ffmpeg 合成（宇宙琴弦波形 v3）─────────────────────
def build_video(frame_path, audio_path, out_path, W, H, wave_h, fps=30):
    """
    宇宙琴弦 v3：三色双声道
      左声道 → 暖金 #ffd080
      右声道 → 琥珀 #e88040
      p2p 模式（细如琴弦）+ cbrt 压缩动态，在深色背景下发光
      不使用 screen 混合（避免 yuv420p 偏色），直接单层叠加
    """
    wave_y = H - wave_h
    fc = (
        # p2p 模式：两声道双色
        f"[1:a]showwaves=s={W}x{wave_h}:mode=p2p:scale=cbrt"
        f":colors=0xffd080|0xe88040:draw=full[waves];"
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
        print(result.stderr[-1500:])
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

    print("=" * 58)
    print(f"CaptainCast EP.{ep} · 视频生成 v3")
    print(f"  封面: {cover_path.name}")
    if not preview_only:
        print(f"  音频: {audio_path.name}")
    print("=" * 58)

    with tempfile.TemporaryDirectory() as tmp:
        # B站 1920×1080
        print("\n🎬 B站版 (1920×1080)...")
        frame = make_frame_bilibili(cover_path, cfg, ep)
        bili_frame = Path(tmp) / "bili.png"
        frame.save(str(bili_frame), "PNG")
        preview = out_dir / f"ep{ep}_preview_bilibili.png"
        frame.save(str(preview))
        print(f"  📐 预览帧: {preview}")

        if not preview_only and audio_path.exists():
            out = out_dir / f"ep{ep}_bilibili.mp4"
            if build_video(bili_frame, audio_path, out, 1920, 1080, 200):
                print(f"  ✅ {out.name}  ({out.stat().st_size/1024/1024:.1f} MB)")

        # 视频号 1080×1080
        print("\n🎬 视频号版 (1080×1080)...")
        frame2 = make_frame_shipinhao(cover_path, cfg, ep)
        ship_frame = Path(tmp) / "ship.png"
        frame2.save(str(ship_frame), "PNG")
        preview2 = out_dir / f"ep{ep}_preview_shipinhao.png"
        frame2.save(str(preview2))
        print(f"  📐 预览帧: {preview2}")

        if not preview_only and audio_path.exists():
            out2 = out_dir / f"ep{ep}_shipinhao.mp4"
            if build_video(ship_frame, audio_path, out2, 1080, 1080, 200):
                print(f"  ✅ {out2.name}  ({out2.stat().st_size/1024/1024:.1f} MB)")

    print(f"\n✨ 完成！{out_dir}/")
    print("=" * 58)
    import subprocess as sp
    sp.run(["open", str(preview), str(preview2)], check=False)


if __name__ == "__main__":
    main()
