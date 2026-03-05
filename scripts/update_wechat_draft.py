"""
CaptainCast · EP.001 微信草稿更新（全自动版）

音频自动化说明：
  微信开发者 API 上传音频后只返回 media_id，不返回 voice_encode_fileid。
  正确的音频标签是 <mp-common-mpaudio voice_encode_fileid="...">, 不是 <mpvoice>。

  每集流程（一次性手动步骤）：
    1. 在后台编辑器插入音频并保存
    2. python3 scripts/update_wechat_draft.py --discover   # 提取 fileid
    3. 把 fileid 填入脚本常量，后续全自动

运行：python3 scripts/update_wechat_draft.py
"""
import requests, os, json, re, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
APPID  = os.getenv('WECHAT_APPID')
SECRET = os.getenv('WECHAT_APPSECRET')
BASE   = "https://api.weixin.qq.com"
IMG_DIR = Path("episodes/ep001/images")
ARTICLE = Path("episodes/ep001/article.md")

# ── EP.001 常量 ──────────────────────────────────────────────────────────────
REAL_DRAFT_ID  = "54miGLDUQtgVc43kEhtbCHdLaORzj8Q4nDRL3dZesYnnFhEWQQRQnR3I-bgGIRJJ"
THUMB_MEDIA_ID = "54miGLDUQtgVc43kEhtbCK7EM-hd2NEGluE4bXkV2Wpg2n2J9NBW3N_i9mREsJwT"

# voice_encode_fileid：从后台编辑器插入音频后通过 --discover 提取
# 解码值：3225097164_100000173（账号内部ID_文件序号，每次上传递增）
VOICE_ENCODE_FILEID = "MzIyNTA5NzE2NF8xMDAwMDAxNzM="
AUDIO_NAME          = "ep001_podcast_64k.mp3"
AUDIO_DURATION_MS   = 259000    # 4分19秒，毫秒
AUDIO_HIGH_KB       = 2028.21
AUDIO_LOW_KB        = 472.23
AUDIO_SRC_KB        = 472.2


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


def discover_fileid(token, draft_id=REAL_DRAFT_ID):
    """从已有草稿中提取 voice_encode_fileid（用于新集首次配置）"""
    r = _post_json(f"{BASE}/cgi-bin/draft/get", token, {"media_id": draft_id})
    content = r.get("news_item", [{}])[0].get("content", "")
    m = re.search(r'voice_encode_fileid="([^"]+)"', content)
    if m:
        import base64
        fileid = m.group(1)
        decoded = base64.b64decode(fileid + "==").decode()
        print(f"\n✅ 发现 voice_encode_fileid: {fileid}")
        print(f"   解码值: {decoded}")
        print(f"\n将以下常量填入脚本:")
        print(f'   VOICE_ENCODE_FILEID = "{fileid}"')
        return fileid
    print("⚠️  草稿中未找到音频标签，请先在后台编辑器插入音频并保存")
    return None


def audio_tag(fileid, name, duration_ms, high_kb, low_kb, src_kb):
    """生成微信原生音频标签 <mp-common-mpaudio>"""
    mins = duration_ms // 60000
    secs = (duration_ms % 60000) // 1000
    play_len_str = f"{mins}分{secs}秒" if secs else f"{mins}分钟"
    import urllib.parse
    src = (f"/cgi-bin/readtemplate?t=tmpl/audio_tmpl"
           f"&name={urllib.parse.quote(name)}"
           f"&play_length={urllib.parse.quote(play_len_str)}")
    return (
        f'<mp-common-mpaudio'
        f' class="js_editor_audio res_iframe js_uneditable custom_select_card"'
        f' data-pluginname="insertaudio"'
        f' name="{name}"'
        f' src="{src}"'
        f' isaac2="1"'
        f' low_size="{low_kb}"'
        f' source_size="{src_kb}"'
        f' high_size="{high_kb}"'
        f' play_length="{duration_ms}"'
        f' data-trans_state="1"'
        f' data-verify_state="3"'
        f' voice_encode_fileid="{fileid}">'
        f'</mp-common-mpaudio>'
    )


# ── 精品 HTML 生成 ─────────────────────────────────────────────────────────
def build_html(md_text, img_urls):
    """生成带音频、优化排版的微信文章 HTML"""

    GOLD = "#c8a96e"
    DARK = "#1a1a1a"
    GRAY = "#666"
    BG   = "#faf8f3"
    LINE = "#e8dfc8"

    parts = []

    # ── 顶部：原生音频播放器 ──────────────────────────────────────────────
    parts.append(
        f'<section nodeleaf="">'
        + audio_tag(VOICE_ENCODE_FILEID, AUDIO_NAME, AUDIO_DURATION_MS,
                    AUDIO_HIGH_KB, AUDIO_LOW_KB, AUDIO_SRC_KB)
        + f'</section>'
    )

    # ── 解析 Markdown ──────────────────────────────────────────────────────
    lines = md_text.split("\n")
    section_count = 0
    insert_img_after = {1: 0, 3: 1}   # 第1节后插父女图，第3节后插灵机图

    i = 0
    while i < len(lines):
        line = lines[i]

        if re.match(r'^---+$', line.strip()):
            section_count += 1
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
            parts.append(
                f'<div style="text-align:center;margin:28px 0;">'
                f'<span style="color:{GOLD};font-size:18px;letter-spacing:6px;">· · ·</span>'
                f'</div>'
            )
            i += 1
            continue

        if re.match(r'^# [^#]', line):
            text = _inline(line[2:], GOLD, DARK)
            parts.append(
                f'<h1 style="font-size:24px;font-weight:bold;color:{DARK};'
                f'margin:0 0 6px;line-height:1.3;">{text}</h1>'
            )
        elif line.startswith("## "):
            text = _inline(line[3:], GOLD, DARK)
            parts.append(
                f'<h2 style="font-size:18px;font-weight:bold;color:{DARK};'
                f'margin:32px 0 12px;padding:12px 16px;'
                f'background:{BG};border-left:4px solid {GOLD};border-radius:0 6px 6px 0;">'
                f'{text}</h2>'
            )
        elif line.startswith("> "):
            text = _inline(line[2:], GOLD, DARK)
            parts.append(
                f'<blockquote style="border-left:none;margin:20px 0;padding:20px 24px;'
                f'background:{BG};border-radius:8px;border:1px solid {LINE};'
                f'font-size:17px;line-height:1.8;color:{DARK};font-weight:500;">'
                f'{text}</blockquote>'
            )
        elif line.strip() == "":
            pass
        elif re.match(r'^\*\*.+\*\*$', line.strip()):
            text = line.strip()[2:-2]
            parts.append(
                f'<p style="font-size:17px;font-weight:bold;color:{DARK};'
                f'margin:16px 0;line-height:1.7;text-align:center;'
                f'padding:12px 0;">{text}</p>'
            )
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
    parts.append(
        f'<section style="background:{BG};border-radius:12px;padding:20px 24px;'
        f'margin:32px 0 0;border:1px solid {LINE};text-align:center;">'
        f'<p style="font-size:14px;color:{GRAY};margin:0 0 6px;">🚀 CaptainCast 超时空电台</p>'
        f'<p style="font-size:13px;color:#999;margin:0;">'
        f'下期：灵机共鸣——当100万人同时非理性，宇宙会发生什么？</p>'
        f'</section>'
    )

    return (
        '<section style="font-family:-apple-system,PingFang SC,Helvetica Neue,sans-serif;'
        'max-width:680px;margin:0 auto;padding:0 4px;">\n'
        + "\n".join(parts)
        + "\n</section>"
    )


def _inline(text, gold, dark):
    text = re.sub(r'\*\*(.+?)\*\*',
        rf'<strong style="color:{dark};font-weight:bold;">\1</strong>', text)
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
        print("  ✅ 草稿更新成功")
        return True
    raise Exception(f"草稿更新失败: {data}")


def main():
    # --discover 模式：从草稿中提取 voice_encode_fileid
    if "--discover" in sys.argv:
        token = get_token()
        discover_fileid(token)
        return

    print("=" * 54)
    print("CaptainCast EP.001 · 草稿全自动更新（含音频）")
    print("=" * 54 + "\n")

    token = get_token()

    # 1. 上传正文配图
    print("\n🖼  上传正文配图...")
    img_urls = []
    for fname in ["03_father_daughter.png", "02_lingji_vs_jicheng.png",
                  "01_cover.png", "04_jianyi_reveal.png"]:
        img_urls.append(upload_article_img(token, IMG_DIR / fname))

    # 2. 生成 HTML（音频 fileid 已内置，无需上传）
    print("\n📝 生成优化排版 HTML（含原生音频播放器）...")
    md_text = ARTICLE.read_text(encoding="utf-8")
    html = build_html(md_text, img_urls)
    print(f"  ✅ HTML {len(html)} 字符")

    # 3. 更新草稿
    print("\n📋 更新草稿...")
    update_draft(token, REAL_DRAFT_ID, THUMB_MEDIA_ID, html)

    print("\n" + "=" * 54)
    print("✨ 完成！去公众号后台 草稿箱 → 群发 即可发布")
    print("=" * 54)


if __name__ == "__main__":
    main()
