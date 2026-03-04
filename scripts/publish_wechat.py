"""
CaptainCast · EP.001 微信公众号自动发布
步骤：获取 token → 上传封面图 → 上传正文图 → 生成 HTML → 创建草稿 → 发布
运行：python3 scripts/publish_wechat.py
"""
import requests, os, json, re

def _post_json(url, token, payload, timeout=30):
    """所有含中文字段的 POST 都用此函数，avoid ensure_ascii=True 导致超长"""
    return requests.post(url,
        params={"access_token": token},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout
    ).json()
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
APPID  = os.getenv('WECHAT_APPID')
SECRET = os.getenv('WECHAT_APPSECRET')

IMG_DIR = Path("episodes/ep001/images")
ARTICLE = Path("episodes/ep001/article.md")
BASE    = "https://api.weixin.qq.com"


# ── 1. Access Token ────────────────────────────────────────────────────────
def get_token():
    r = requests.get(f"{BASE}/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": APPID, "secret": SECRET},
        timeout=15)
    data = r.json()
    assert "access_token" in data, f"token 失败: {data}"
    print(f"✅ access_token 获取成功")
    return data["access_token"]


# ── 2. 上传永久素材图片（封面用）─────────────────────────────────────────
def upload_thumb(token, img_path):
    with open(img_path, "rb") as f:
        r = requests.post(
            f"{BASE}/cgi-bin/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (img_path.name, f, "image/png")},
            timeout=60
        )
    data = r.json()
    if "media_id" in data:
        print(f"  ✅ 封面上传: media_id={data['media_id']}")
        return data["media_id"], data.get("url", "")
    raise Exception(f"封面上传失败: {data}")


# ── 3. 上传正文图片（临时 CDN，文章内嵌用）────────────────────────────────
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
        print(f"  ✅ 正文图上传: {img_path.name} → {data['url'][:60]}...")
        return data["url"]
    raise Exception(f"正文图上传失败: {data}")


# ── 4. Markdown → 微信 HTML ────────────────────────────────────────────────
# 全部用 inline style，微信不支持 <style> 标签块
S = {
    "h1":  'style="font-size:22px;font-weight:bold;color:#1a1a1a;margin:24px 0 8px;line-height:1.4;"',
    "h2":  'style="font-size:18px;font-weight:bold;color:#c8a96e;margin:28px 0 10px;border-left:4px solid #c8a96e;padding-left:10px;line-height:1.4;"',
    "h3":  'style="font-size:16px;font-weight:bold;color:#333;margin:20px 0 8px;"',
    "p":   'style="font-size:16px;line-height:1.9;color:#333;margin:12px 0;"',
    "bq":  'style="border-left:3px solid #c8a96e;margin:16px 0;padding:10px 16px;background:#faf8f3;color:#666;font-size:15px;line-height:1.7;"',
    "hr":  'style="border:none;border-top:1px solid #e0d5c0;margin:28px 0;"',
    "img": 'style="max-width:100%;display:block;margin:20px auto;border-radius:6px;"',
    "cap": 'style="text-align:center;font-size:13px;color:#999;margin-top:-12px;"',
}

def md_to_html(md_text, img_urls):
    """Markdown → 微信兼容 HTML（全 inline style）"""
    lines = md_text.split("\n")
    html_parts = []
    section_count = 0
    insert_after = {1: 0, 3: 2}   # 第1节后插 img[0]，第3节后插 img[2]

    for line in lines:
        if re.match(r'^---+$', line.strip()):
            section_count += 1
            if section_count in insert_after and img_urls:
                idx = insert_after[section_count]
                if idx < len(img_urls):
                    html_parts.append(f'<img src="{img_urls[idx]}" {S["img"]} />')
            html_parts.append(f'<hr {S["hr"]} />')
            continue

        if line.startswith("# ") and not line.startswith("## "):
            html_parts.append(f'<h1 {S["h1"]}>{_inline(line[2:])}</h1>')
        elif line.startswith("## "):
            html_parts.append(f'<h2 {S["h2"]}>{_inline(line[3:])}</h2>')
        elif line.startswith("### "):
            html_parts.append(f'<h3 {S["h3"]}>{_inline(line[4:])}</h3>')
        elif line.startswith("> "):
            html_parts.append(f'<blockquote {S["bq"]}>{_inline(line[2:])}</blockquote>')
        elif line.strip() == "":
            pass
        else:
            html_parts.append(f'<p {S["p"]}>{_inline(line)}</p>')

    # 末尾加图
    if len(img_urls) >= 4:
        html_parts.append(f'<img src="{img_urls[1]}" {S["img"]} />')
        html_parts.append(f'<p {S["cap"]}>灵机 vs 寂熵</p>')
        html_parts.append(f'<img src="{img_urls[3]}" {S["img"]} />')
        html_parts.append(f'<p {S["cap"]}>减一·显现</p>')

    return '<section style="font-family:-apple-system,PingFang SC,sans-serif;">\n' + \
           "\n".join(html_parts) + "\n</section>"


def _inline(text):
    text = re.sub(r'\*\*(.+?)\*\*',
        r'<strong style="color:#1a1a1a;font-weight:bold;">\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


# ── 5. 创建草稿 ────────────────────────────────────────────────────────────
def create_draft(token, thumb_media_id, html_content):
    payload = {
        "articles": [{
            "title": "如果你能给女儿造一个宇宙",
            "author": "船长",
            "digest": "凌晨两点，借钱发完工资的爸爸，开始给12岁女儿造一个宇宙。这是《神临山海》的起点，也是灵机理论的诞生地。",
            "content": html_content,
            "thumb_media_id": thumb_media_id,
            "content_source_url": "https://wyonliu.github.io/CaptainCast/",
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }
    data = _post_json(f"{BASE}/cgi-bin/draft/add", token, payload)
    if "media_id" in data:
        print(f"  ✅ 草稿创建成功: media_id={data['media_id']}")
        return data["media_id"]
    raise Exception(f"草稿创建失败: {data}")


# ── 6. 自由发布（发布到账号文章列表，不群发）─────────────────────────────
def free_publish(token, media_id):
    data = _post_json(f"{BASE}/cgi-bin/freepublish/submit", token, {"media_id": media_id})
    if data.get("errcode", -1) == 0 or "publish_id" in data:
        print(f"  ✅ 发布成功! publish_id={data.get('publish_id', 'N/A')}")
        return data
    raise Exception(f"发布失败: {data}")


# ── MAIN ───────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("CaptainCast EP.001 · 微信公众号发布")
    print("=" * 50 + "\n")

    token = get_token()

    # 上传封面（01_cover.png 作为封面）
    print("\n📌 上传封面图...")
    thumb_id, thumb_url = upload_thumb(token, IMG_DIR / "01_cover.png")

    # 上传正文配图（02 父女送别、03 灵机vs寂熵、04 减一显现）
    print("\n🖼  上传正文配图...")
    article_imgs = []
    for fname in ["03_father_daughter.png", "02_lingji_vs_jicheng.png",
                  "01_cover.png", "04_jianyi_reveal.png"]:
        url = upload_article_img(token, IMG_DIR / fname)
        article_imgs.append(url)

    # 转换文章
    print("\n📝 转换 Markdown → HTML...")
    md_text = ARTICLE.read_text(encoding="utf-8")
    html_content = md_to_html(md_text, article_imgs)
    print(f"  ✅ HTML 生成完成，{len(html_content)} 字符")

    # 创建草稿
    print("\n📋 创建草稿...")
    draft_media_id = create_draft(token, thumb_id, html_content)

    # 发布
    print("\n🚀 发布中...")
    result = free_publish(token, draft_media_id)

    print("\n" + "=" * 50)
    print("✨ EP.001 已发布到公众号！")
    print("   去公众号后台 → 发布记录 查看效果")
    print("=" * 50)


if __name__ == "__main__":
    main()
