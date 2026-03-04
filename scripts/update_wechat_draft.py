"""
CaptainCast · EP.001 微信草稿优化
1. 上传压缩音频（ep001_podcast_64k.mp3）为永久语音素材
2. 删除测试草稿
3. 用 <mpvoice> 将音频嵌入文章顶部 + 优化排版
4. 更新真正的草稿
运行：python3 scripts/update_wechat_draft.py
"""
import requests, os, json, re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
APPID  = os.getenv('WECHAT_APPID')
SECRET = os.getenv('WECHAT_APPSECRET')
BASE   = "https://api.weixin.qq.com"
IMG_DIR = Path("episodes/ep001/images")
ARTICLE = Path("episodes/ep001/article.md")
AUDIO   = Path("audio/output/ep001_podcast_64k.mp3")

# 真正的文章草稿 media_id（最新创建的那个）
REAL_DRAFT_ID = "54miGLDUQtgVc43kEhtbCHdLaORzj8Q4nDRL3dZesYnnFhEWQQRQnR3I-bgGIRJJ"
# 封面图 media_id（已上传的永久素材）
THUMB_MEDIA_ID = "54miGLDUQtgVc43kEhtbCK7EM-hd2NEGluE4bXkV2Wpg2n2J9NBW3N_i9mREsJwT"
# 要删除的测试草稿
TEST_DRAFT_IDS = [
    "54miGLDUQtgVc43kEhtbCPf-Lrh4VShvLFyoy6S5vKnK8sN1Tima1FLnGOXtOz_h",  # 测试2
    "54miGLDUQtgVc43kEhtbCDxGz7OUoyrlogxkWE9iQzoxwRc7NjRACdm9ObvYYyzj",   # 测试草稿
    "54miGLDUQtgVc43kEhtbCKLCBq_VqAKP_RR1APZuSjIoJH1RXfMpSqmJgiDJYbyi",  # 重复文章草稿
]


def _post_json(url, token, payload, timeout=30):
    return requests.post(url,
        params={"access_token": token},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout
    ).json()


def get_token():
    r = requests.get(f"{BASE}/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": APPID, "secret": SECRET},
        timeout=15)
    data = r.json()
    assert "access_token" in data, f"token 获取失败: {data}"
    print("✅ access_token 获取成功")
    return data["access_token"]


def upload_voice(token, mp3_path):
    """上传 MP3 为永久语音素材，返回 media_id"""
    with open(mp3_path, "rb") as f:
        r = requests.post(
            f"{BASE}/cgi-bin/material/add_material",
            params={"access_token": token, "type": "voice"},
            files={"media": (mp3_path.name, f, "audio/mpeg")},
            timeout=60
        )
    data = r.json()
    if "media_id" in data:
        print(f"  ✅ 音频上传成功: media_id={data['media_id']}")
        return data["media_id"]
    raise Exception(f"音频上传失败: {data}")


def upload_article_img(token, img_path):
    with open(img_path, "rb") as f:
        r = requests.post(
            f"{BASE}/cgi-bin/media/uploadimg",
            params={"access_token": token},
            files={"media": (img_path.name, f, "image/png")},
            timeout=60
        )
    data = r.json()
    if "url" in data:
        print(f"  ✅ {img_path.name} → {data['url'][:55]}...")
        return data["url"]
    raise Exception(f"图片上传失败: {data}")


def delete_draft(token, media_id):
    data = _post_json(f"{BASE}/cgi-bin/draft/delete", token, {"media_id": media_id})
    if data.get("errcode", -1) == 0:
        print(f"  ✅ 已删除: {media_id[:30]}...")
    else:
        print(f"  ⚠️  删除失败: {data}")


# ── 精品 HTML 生成 ─────────────────────────────────────────────────────────
def build_html(md_text, voice_media_id, img_urls):
    """生成带音频、优化排版的微信文章 HTML"""

    # 颜色主题
    GOLD   = "#c8a96e"
    DARK   = "#1a1a1a"
    GRAY   = "#666"
    BG     = "#faf8f3"
    LINE   = "#e8dfc8"

    parts = []

    # ── 顶部音频提示（API 不支持 mpvoice，后台编辑器手动插入音频）────────
    parts.append(
        f'<section style="background:{BG};border-radius:12px;padding:18px 22px;'
        f'margin:0 0 24px;border:1px solid {LINE};">'
        f'<p style="font-size:14px;color:{GOLD};margin:0 0 4px;font-weight:bold;">'
        f'🎙 CaptainCast 超时空电台 · EP.001</p>'
        f'<p style="font-size:13px;color:{GRAY};margin:0;line-height:1.6;">'
        f'点击右上角菜单 → 在浏览器中打开，可收听完整播客音频</p>'
        f'</section>'
    )

    # ── 解析 Markdown ──────────────────────────────────────────────────────
    lines = md_text.split("\n")
    section_count = 0
    # 图片插入策略：第1节后插父女图，第3节后插灵机图
    insert_img_after = {1: 0, 3: 1}

    i = 0
    while i < len(lines):
        line = lines[i]

        # 分隔线
        if re.match(r'^---+$', line.strip()):
            section_count += 1
            # 插图
            if section_count in insert_img_after and img_urls:
                idx = insert_img_after[section_count]
                if idx < len(img_urls):
                    captions = ["父女·送别", "灵机 vs 寂熵"]
                    parts.append(
                        f'<img src="{img_urls[idx]}" style="max-width:100%;display:block;'
                        f'margin:24px auto 8px;border-radius:8px;" />'
                    )
                    parts.append(
                        f'<p style="text-align:center;font-size:12px;color:#999;'
                        f'margin:0 0 24px;letter-spacing:1px;">{captions[idx]}</p>'
                    )
            # 金色分隔线
            parts.append(
                f'<div style="text-align:center;margin:28px 0;">'
                f'<span style="color:{GOLD};font-size:18px;letter-spacing:6px;">· · ·</span>'
                f'</div>'
            )
            i += 1
            continue

        # H1（文章标题，跳过——微信用 title 字段）
        if re.match(r'^# [^#]', line):
            # 显示为副标题样式
            text = _inline(line[2:], GOLD, DARK)
            parts.append(
                f'<h1 style="font-size:24px;font-weight:bold;color:{DARK};'
                f'margin:0 0 6px;line-height:1.3;">{text}</h1>'
            )

        # H2 章节标题
        elif line.startswith("## "):
            text = _inline(line[3:], GOLD, DARK)
            num = text.split("、")[0] if "、" in text else ""
            rest = text.split("、", 1)[1] if "、" in text else text
            parts.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:{DARK};'
                f'margin:32px 0 12px;padding:12px 16px;'
                f'background:linear-gradient(135deg,{BG},{BG});'
                f'border-left:4px solid {GOLD};border-radius:0 6px 6px 0;">'
                f'{text}</h2>'
            )

        # blockquote → 醒目引用框
        elif line.startswith("> "):
            text = _inline(line[2:], GOLD, DARK)
            parts.append(
                f'<blockquote style="border-left:none;margin:20px 0;padding:20px 24px;'
                f'background:{BG};border-radius:8px;border:1px solid {LINE};'
                f'font-size:17px;line-height:1.8;color:{DARK};font-weight:500;">'
                f'{text}</blockquote>'
            )

        # 空行
        elif line.strip() == "":
            pass

        # 加粗独占一行的 → 突出显示
        elif re.match(r'^\*\*.+\*\*$', line.strip()):
            text = line.strip()[2:-2]
            parts.append(
                f'<p style="font-size:17px;font-weight:bold;color:{DARK};'
                f'margin:16px 0;line-height:1.7;text-align:center;'
                f'padding:12px 0;">{text}</p>'
            )

        # 普通段落
        else:
            text = _inline(line, GOLD, DARK)
            parts.append(
                f'<p style="font-size:16px;line-height:1.9;color:#333;'
                f'margin:14px 0;">{text}</p>'
            )
        i += 1

    # ── 末尾两张图 ─────────────────────────────────────────────────────────
    if len(img_urls) >= 4:
        for idx, cap in [(2, "封面·麦洛&小墨"), (3, "减一·显现")]:
            parts.append(
                f'<img src="{img_urls[idx]}" style="max-width:100%;display:block;'
                f'margin:24px auto 8px;border-radius:8px;" />'
            )
            parts.append(
                f'<p style="text-align:center;font-size:12px;color:#999;'
                f'margin:0 0 24px;letter-spacing:1px;">{cap}</p>'
            )

    # ── 结尾关注引导 ────────────────────────────────────────────────────────
    parts.append(f"""
<section style="background:{BG};border-radius:12px;padding:20px 24px;margin:32px 0 0;border:1px solid {LINE};text-align:center;">
  <p style="font-size:14px;color:{GRAY};margin:0 0 6px;">🚀 CaptainCast 超时空电台</p>
  <p style="font-size:13px;color:#999;margin:0;">下期：灵机共鸣——当100万人同时非理性，宇宙会发生什么？</p>
</section>
""".strip())

    return (
        '<section style="font-family:-apple-system,PingFang SC,Helvetica Neue,sans-serif;'
        'max-width:680px;margin:0 auto;padding:0 4px;">\n'
        + "\n".join(parts)
        + "\n</section>"
    )


def _inline(text, gold, dark):
    """处理行内加粗，转为 inline style"""
    text = re.sub(
        r'\*\*(.+?)\*\*',
        rf'<strong style="color:{dark};font-weight:bold;">\1</strong>',
        text
    )
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


def update_draft(token, draft_media_id, thumb_media_id, html_content):
    payload = {
        "media_id": draft_media_id,
        "index": 0,
        "articles": {
            "title": "如果你能给女儿造一个宇宙",
            "author": "船长",
            "digest": "凌晨两点，借钱发完工资的爸爸，开始给12岁女儿造一个宇宙。这是《神临山海》的起点，也是灵机理论的诞生地。",
            "content": html_content,
            "thumb_media_id": thumb_media_id,
            "content_source_url": "https://wyonliu.github.io/CaptainCast/",
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }
    }
    data = _post_json(f"{BASE}/cgi-bin/draft/update", token, payload)
    if data.get("errcode", -1) == 0:
        print(f"  ✅ 草稿更新成功")
        return True
    raise Exception(f"草稿更新失败: {data}")


def main():
    print("=" * 54)
    print("CaptainCast EP.001 · 草稿优化（音频 + 排版）")
    print("=" * 54 + "\n")

    token = get_token()

    # 1. 上传压缩音频
    print(f"\n🎙  上传播客音频（{AUDIO.stat().st_size // 1024} KB）...")
    voice_media_id = upload_voice(token, AUDIO)

    # 2. 重新上传正文图（顺序：父女送别、灵机vs寂熵、封面麦洛、减一显现）
    print("\n🖼  上传正文配图...")
    img_urls = []
    for fname in ["03_father_daughter.png", "02_lingji_vs_jicheng.png",
                  "01_cover.png", "04_jianyi_reveal.png"]:
        img_urls.append(upload_article_img(token, IMG_DIR / fname))

    # 3. 生成优化 HTML
    print("\n📝 生成优化排版 HTML...")
    md_text = ARTICLE.read_text(encoding="utf-8")
    html = build_html(md_text, voice_media_id, img_urls)
    print(f"  ✅ HTML {len(html)} 字符")

    # 4. 更新真正的草稿
    print(f"\n📋 更新草稿...")
    update_draft(token, REAL_DRAFT_ID, THUMB_MEDIA_ID, html)

    # 5. 删除测试草稿
    print(f"\n🗑  删除测试草稿...")
    for mid in TEST_DRAFT_IDS:
        delete_draft(token, mid)

    print("\n" + "=" * 54)
    print("✨ 完成！去公众号后台 草稿箱 → 群发 即可发布")
    print("=" * 54)


if __name__ == "__main__":
    main()
