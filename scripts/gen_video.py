#!/usr/bin/env python3
"""
CaptainCast · 视频生成脚本
生成 B站 16:9 (1920x1080) 和 视频号 1:1 (1080x1080) 视频

运行：
  python3 scripts/gen_video.py --ep 002
  python3 scripts/gen_video.py --ep 001
"""
import sys, json, subprocess, os, shutil, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── 常量 ────────────────────────────────────────────────
GOLD      = (200, 169, 110)
GOLD_DIM  = (140, 110, 70)
DARK      = (10, 10, 22)
WHITE     = (240, 240, 235)
GRAY      = (170, 165, 155)
BG_DARK   = (14, 14, 28, 200)   # 半透明蒙层

FONT_CN   = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_MONO = "/System/Library/Fonts/Menlo.ttc"

# ─── 工具函数 ─────────────────────────────────────────────
def get_ep():
    for i, a in enumerate(sys.argv):
        if a == '--ep' and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    eps = sorted(Path("episodes").glob("ep*/config.json"))
    return eps[-1].parent.name.replace("ep","") if eps else "001"

def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def draw_text_shadow(draw, pos, text, fnt, fill, shadow=(0,0,0), offset=3):
    x, y = pos
    draw.text((x+offset, y+offset), text, font=fnt, fill=shadow + (160,))
    draw.text((x, y), text, font=fnt, fill=fill)

def add_rounded_corners(img, radius=20):
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, img.width, img.height], radius=radius, fill=255)
    result = img.copy()
    result.putalpha(mask)
    return result

# ─── 帧生成 ───────────────────────────────────────────────
def make_frame_bilibili(cover_path, cfg, ep_num):
    """1920x1080 B站 16:9 帧"""
    W, H = 1920, 1080
    WAVE_H = 160       # 底部波形区域高度
    COVER_H = 820      # 封面图高度

    cover_orig = Image.open(cover_path).convert("RGB")

    # ── 背景：封面图填满 → 高斯模糊 → 深色蒙层 ──
    bg_ratio = W / H
    orig_ratio = cover_orig.width / cover_orig.height
    if orig_ratio > bg_ratio:
        bg = cover_orig.resize((int(H * orig_ratio), H), Image.LANCZOS)
        bg = bg.crop(((bg.width - W) // 2, 0, (bg.width - W) // 2 + W, H))
    else:
        bg = cover_orig.resize((W, int(W / orig_ratio)), Image.LANCZOS)
        bg = bg.crop((0, (bg.height - H) // 2, W, (bg.height - H) // 2 + H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=35))
    bg = bg.convert("RGBA")
    # 深色蒙层
    overlay = Image.new("RGBA", (W, H), (8, 8, 18, 210))
    bg = Image.alpha_composite(bg, overlay)

    # 底部波形区域加深
    wave_overlay = Image.new("RGBA", (W, WAVE_H), (4, 4, 12, 230))
    bg.paste(wave_overlay.convert("RGB"),
             (0, H - WAVE_H),
             wave_overlay.split()[3])

    # ── 封面图：左侧居中，圆角，阴影 ──
    cov_w = int(cover_orig.width * COVER_H / cover_orig.height)
    cov = cover_orig.resize((cov_w, COVER_H), Image.LANCZOS)
    cov = add_rounded_corners(cov, radius=24)

    # 阴影层
    shadow = Image.new("RGBA", (cov_w + 40, COVER_H + 40), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle([20, 20, cov_w + 20, COVER_H + 20], radius=24, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))

    cov_x = 80
    cov_y = (H - WAVE_H - COVER_H) // 2
    bg.paste(shadow.convert("RGB"), (cov_x - 20, cov_y - 20), shadow.split()[3])
    bg.paste(cov.convert("RGB"), (cov_x, cov_y), cov.split()[3])

    # ── 右侧文字区域 ──
    draw = ImageDraw.Draw(bg)
    text_x = cov_x + cov_w + 80
    text_w = W - text_x - 80

    title = cfg.get("title", "")
    # 标准化标题：去掉 "船长电台002：" 前缀后取副标题
    short_ep = f"EP.{ep_num}"
    ep_label = cfg.get("title", "").split("：")[0] if "：" in cfg.get("title","") else f"船长电台{ep_num}"
    subtitle = cfg.get("title", "").split("：")[1] if "：" in cfg.get("title","") else cfg.get("title","")

    # 节目名
    ty = cov_y + 80
    fn_show = font(FONT_CN, 38)
    draw.text((text_x, ty), "CaptainCast 超时空电台", font=fn_show, fill=GOLD)
    ty += 56

    # 分割线
    draw.rectangle([text_x, ty, text_x + text_w, ty + 2], fill=GOLD_DIM)
    ty += 24

    # EP 编号
    fn_ep = font(FONT_CN, 28)
    draw.text((text_x, ty), f"船长与麦洛的超时空电台  {short_ep}", font=fn_ep, fill=GRAY)
    ty += 54

    # 主标题（可能需要换行）
    fn_title = font(FONT_CN, 56)
    # 每行约 12-14 个中文字
    words = subtitle.replace("，", "\n").replace("：", "\n") if len(subtitle) > 14 else subtitle
    for line in words.split("\n"):
        draw_text_shadow(draw, (text_x, ty), line.strip(), fn_title, WHITE)
        ty += 74

    ty += 20

    # 摘要（前60字）
    digest = cfg.get("digest", "")[:60]
    fn_digest = font(FONT_CN, 26)
    # 按宽度自动换行
    line_buf, lines = [], []
    for ch in digest:
        line_buf.append(ch)
        if len(line_buf) >= 22:
            lines.append("".join(line_buf))
            line_buf = []
    if line_buf:
        lines.append("".join(line_buf))
    for line in lines[:3]:
        draw.text((text_x, ty), line, font=fn_digest, fill=GRAY)
        ty += 40

    ty += 30
    # 网站
    fn_url = font(FONT_MONO, 24)
    draw.text((text_x, ty), "wyonliu.github.io/CaptainCast", font=fn_url, fill=GOLD_DIM)

    # ── 底部金色装饰线（波形上方） ──
    draw.rectangle([0, H - WAVE_H - 3, W, H - WAVE_H], fill=GOLD)

    return bg.convert("RGB")


def make_frame_shipinhao(cover_path, cfg, ep_num):
    """1080x1080 视频号 1:1 帧"""
    W, H = 1080, 1080

    cover_orig = Image.open(cover_path).convert("RGB")

    # 背景
    bg = cover_orig.resize((W, int(W * cover_orig.height / cover_orig.width)), Image.LANCZOS)
    bg_h = bg.height
    if bg_h >= H:
        bg = bg.crop((0, (bg_h - H) // 2, W, (bg_h - H) // 2 + H))
    else:
        new_bg = Image.new("RGB", (W, H), DARK)
        new_bg.paste(bg, (0, (H - bg_h) // 2))
        bg = new_bg
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    bg = bg.convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (8, 8, 18, 190))
    bg = Image.alpha_composite(bg, overlay)

    # 封面图居中上半部分
    COVER_H = 600
    cov_w = int(cover_orig.width * COVER_H / cover_orig.height)
    cov = cover_orig.resize((cov_w, COVER_H), Image.LANCZOS)
    cov = add_rounded_corners(cov, radius=20)
    cov_x = (W - cov_w) // 2
    cov_y = 60
    bg.paste(cov.convert("RGB"), (cov_x, cov_y), cov.split()[3])

    # 文字区域（下半部分）
    draw = ImageDraw.Draw(bg)
    ty = cov_y + COVER_H + 40

    fn_show = font(FONT_CN, 32)
    show_txt = "CaptainCast 超时空电台"
    draw.text(((W - draw.textlength(show_txt, font=fn_show)) // 2, ty),
              show_txt, font=fn_show, fill=GOLD)
    ty += 52

    # 分割线
    draw.rectangle([(W - 200) // 2, ty, (W + 200) // 2, ty + 2], fill=GOLD_DIM)
    ty += 20

    subtitle = cfg.get("title", "").split("：")[1] if "：" in cfg.get("title","") else cfg.get("title","")
    fn_title = font(FONT_CN, 44)
    draw_text_shadow(draw, ((W - draw.textlength(subtitle, font=fn_title)) // 2, ty),
                     subtitle, fn_title, WHITE)
    ty += 64

    # 波形区
    wave_overlay = Image.new("RGBA", (W, 200), (4, 4, 12, 200))
    bg.paste(wave_overlay.convert("RGB"), (0, H - 200), wave_overlay.split()[3])
    draw.rectangle([0, H - 200 - 3, W, H - 200], fill=GOLD)

    return bg.convert("RGB")


# ─── ffmpeg 合成 ──────────────────────────────────────────
def build_video(frame_path, audio_path, out_path, W, H, wave_h, fps=30):
    """用 ffmpeg 合成静态帧 + 音频 + 波形"""
    wave_y = H - wave_h
    wave_color = "0xc8a96e"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(fps), "-i", str(frame_path),
        "-i", str(audio_path),
        "-filter_complex",
        (
            f"[1:a]showwaves=s={W}x{wave_h}:mode=cline:scale=sqrt"
            f":colors={wave_color}@0.95:draw=full[waves];"
            f"[0:v][waves]overlay=0:{wave_y}[vout]"
        ),
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
        print(result.stderr[-1000:])
        return False
    return True


# ─── 主流程 ───────────────────────────────────────────────
def main():
    ep = get_ep()
    cfg_path = Path(f"episodes/ep{ep}/config.json")
    if not cfg_path.exists():
        print(f"❌ 找不到 {cfg_path}"); return

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    img_dir = Path(f"episodes/ep{ep}/images")
    cover_path = img_dir / cfg["thumb_image"]
    audio_path = Path(f"audio/output/ep{ep}_podcast.mp3")  # 用高质量版本
    if not audio_path.exists():
        audio_path = Path(f"audio/output/ep{ep}_podcast_64k.mp3")
    out_dir = Path(f"episodes/ep{ep}/videos")
    out_dir.mkdir(exist_ok=True)

    print("=" * 56)
    print(f"CaptainCast EP.{ep} · 视频生成")
    print(f"  封面: {cover_path.name}  音频: {audio_path.name}")
    print("=" * 56)

    with tempfile.TemporaryDirectory() as tmp:
        # ── B站版 1920x1080 ──
        print("\n🎬 B站版 (1920×1080)...")
        bili_frame = Path(tmp) / "bili_frame.png"
        frame = make_frame_bilibili(cover_path, cfg, ep)
        frame.save(str(bili_frame), "PNG")
        bili_out = out_dir / f"ep{ep}_bilibili.mp4"
        if build_video(bili_frame, audio_path, bili_out, 1920, 1080, 160):
            size_mb = bili_out.stat().st_size / 1024 / 1024
            print(f"  ✅ {bili_out.name}  ({size_mb:.1f} MB)")

        # ── 视频号版 1080x1080 ──
        print("\n🎬 视频号版 (1080×1080)...")
        ship_frame = Path(tmp) / "ship_frame.png"
        frame2 = make_frame_shipinhao(cover_path, cfg, ep)
        frame2.save(str(ship_frame), "PNG")
        ship_out = out_dir / f"ep{ep}_shipinhao.mp4"
        if build_video(ship_frame, audio_path, ship_out, 1080, 1080, 200):
            size_mb = ship_out.stat().st_size / 1024 / 1024
            print(f"  ✅ {ship_out.name}  ({size_mb:.1f} MB)")

        # 预览帧保存
        preview = out_dir / f"ep{ep}_preview_bilibili.png"
        frame.save(str(preview))
        preview2 = out_dir / f"ep{ep}_preview_shipinhao.png"
        frame2.save(str(preview2))
        print(f"\n📐 预览帧已保存（可用 Preview.app 查看）:")
        print(f"   {preview}")
        print(f"   {preview2}")

    print(f"\n✨ 完成！视频位于 {out_dir}/")
    print("=" * 56)

if __name__ == "__main__":
    main()
