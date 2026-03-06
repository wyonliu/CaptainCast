"""
CaptainCast · 微信草稿发布（通用，支持任意集数）

运行：
  python3 scripts/publish_wechat.py --ep 002          # 创建/更新草稿
  python3 scripts/publish_wechat.py --ep 002 --discover # 提取 voice_encode_fileid

音频自动化说明：
  每集首次：
    1. 后台编辑器打开草稿 → 插入音频 → 保存
    2. python3 scripts/publish_wechat.py --ep 002 --discover
    3. 把 fileid 填入 episodes/ep002/config.json → voice_encode_fileid
    4. 重新运行本脚本，之后全自动
"""
import requests, os, json, re, sys, urllib.parse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
APPID  = os.getenv('WECHAT_APPID')
SECRET = os.getenv('WECHAT_APPSECRET')
BASE   = "https://api.weixin.qq.com"

DRAFT_ID_KEY = "draft_media_id"
THUMB_ID_KEY = "thumb_media_id"


def _post_json(url, token, payload, timeout=30):
    r = requests.post(url,
        params={"access_token": token},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=timeout
    )
    return json.loads(r.content.decode('utf-8'))


def get_token():
    r = requests.get(f"{BASE}/cgi-bin/token",
        params={"grant_type": "client_credential", "appid": APPID, "secret": SECRET},
        timeout=15)
    data = json.loads(r.content.decode('utf-8'))
    assert "access_token" in data, f"token 获取失败: {data}"
    print("✅ access_token 获取成功")
    return data["access_token"]


def upload_img_to_article(token, img_path):
    with open(img_path, "rb") as f:
        r = requests.post(f"{BASE}/cgi-bin/media/uploadimg",
            params={"access_token": token},
            files={"media": (img_path.name, f, "image/png")},
            timeout=60)
    data = json.loads(r.content.decode('utf-8'))
    if "url" in data:
        print(f"  ✅ {img_path.name} → {data['url'][:55]}...")
        return data["url"]
    raise Exception(f"图片上传失败: {data}")


def upload_thumb(token, img_path):
    with open(img_path, "rb") as f:
        r = requests.post(f"{BASE}/cgi-bin/material/add_material",
            params={"access_token": token, "type": "image"},
            files={"media": (img_path.name, f, "image/png")},
            timeout=60)
    data = json.loads(r.content.decode('utf-8'))
    if "media_id" in data:
        print(f"  ✅ 封面图 media_id: {data['media_id'][:30]}...")
        return data["media_id"]
    raise Exception(f"封面图上传失败: {data}")


def upload_voice(token, mp3_path):
    with open(mp3_path, "rb") as f:
        r = requests.post(f"{BASE}/cgi-bin/material/add_material",
            params={"access_token": token, "type": "voice"},
            files={"media": (mp3_path.name, f, "audio/mpeg")},
            timeout=120)
    data = json.loads(r.content.decode('utf-8'))
    if "media_id" in data:
        print(f"  ✅ 音频素材 media_id: {data['media_id'][:30]}...")
        return data["media_id"]
    raise Exception(f"音频上传失败: {data}")


def audio_tag(fileid, name, duration_ms, high_kb, low_kb, src_kb):
    mins = duration_ms // 60000
    secs = (duration_ms % 60000) // 1000
    play_str = f"{mins}分{secs}秒" if secs else f"{mins}分钟"
    src = (f"/cgi-bin/readtemplate?t=tmpl/audio_tmpl"
           f"&name={urllib.parse.quote(name)}"
           f"&play_length={urllib.parse.quote(play_str)}")
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


def _inline(text):
    # 先处理行内代码 `...`，HTML转义内容，防止 <mpvoice> 等标签混入HTML
    def _code_span(m):
        safe = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (f'<span style="font-family:Menlo,Consolas,monospace;'
                f'background:#f0ede6;color:#c0392b;padding:1px 5px;'
                f'border-radius:3px;font-size:14px;">{safe}</span>')
    text = re.sub(r'`([^`]+)`', _code_span, text)
    text = re.sub(r'\*\*(.+?)\*\*',
        r'<strong style="color:#1a1a1a;font-weight:bold;">\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


def build_html(cfg, img_urls):
    GOLD    = "#c8a96e"
    GOLD_L  = "#e0c88a"       # 亮金
    GOLD_D  = "#8a6830"       # 暗金
    DARK    = "#1a1a1a"
    DARK_BG = "#0d0d1a"       # 深夜色，用于头部卡片
    MID_BG  = "#111120"       # 代码块背景
    BG      = "#faf8f3"       # 暖米色，引用块背景
    LINE    = "#e8dfc8"
    TEXT    = "#333333"
    MUTED   = "#888888"

    fileid = cfg.get("voice_encode_fileid", "")
    insert_after = {int(k): v for k, v in cfg.get("insert_img_after_section", {}).items()}
    ep = cfg["ep"]
    title_full = cfg.get("title", "")
    subtitle = title_full.split("：", 1)[1] if "：" in title_full else title_full
    digest = cfg.get("digest", "")
    next_ep = cfg.get("next_ep_hint", "下期精彩，敬请期待")

    parts = []

    # ── ① 头部品牌卡片（深色，参考 ep001.html 风格）──
    parts.append(
        f'<section style="background:{DARK_BG};border-radius:16px;'
        f'padding:24px 20px 22px;margin:0 0 20px;">'
        # 节目标签
        f'<p style="font-size:11px;letter-spacing:3px;color:{GOLD};'
        f'margin:0 0 14px;font-weight:500;">✦ 船长与麦洛的超时空电台 ✦</p>'
        # EP 徽章
        f'<section style="display:inline-block;background:transparent;'
        f'border:1px solid {GOLD_D};border-radius:20px;'
        f'padding:3px 14px;margin:0 0 14px;">'
        f'<span style="font-size:12px;color:{GOLD};letter-spacing:1px;">EP.{ep}</span>'
        f'</section>'
        # 副标题
        f'<p style="font-size:20px;font-weight:bold;color:#f0e8d0;'
        f'line-height:1.45;margin:0 0 12px;">{subtitle}</p>'
        # 摘要一句话
        f'<p style="font-size:13px;color:{MUTED};line-height:1.7;margin:0;">{digest}</p>'
        f'</section>'
    )

    # ── ② 音频播放器 ──
    if fileid:
        parts.append(
            '<section nodeleaf="">'
            + audio_tag(fileid, cfg["audio_name"], cfg["audio_duration_ms"],
                        cfg["audio_high_kb"], cfg["audio_low_kb"], cfg["audio_src_kb"])
            + '</section>'
        )
        parts.append(
            f'<p style="font-size:12px;color:{MUTED};text-align:center;'
            f'margin:8px 0 28px;">↑ 点击收听完整播客版本</p>'
        )

    md_text = Path(f"episodes/ep{ep}/output/article.md").read_text(encoding="utf-8")
    lines = md_text.split("\n")
    section_count = 0
    used_img_idxs = set()
    section_heading_count = 0

    def _esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))

    i = 0
    while i < len(lines):
        line = lines[i]

        # ── 分隔线 `---` ──
        if re.match(r'^---+$', line.strip()):
            section_count += 1
            if section_count in insert_after:
                idx = insert_after[section_count]
                if idx < len(img_urls) and img_urls[idx]:
                    used_img_idxs.add(idx)
                    parts.append(
                        f'<img src="{img_urls[idx]}" style="max-width:100%;'
                        f'width:100%;display:block;margin:20px auto;'
                        f'border-radius:10px;" />'
                    )
            # 精致分隔符
            parts.append(
                f'<section style="text-align:center;margin:28px 0;">'
                f'<span style="color:{GOLD_D};font-size:12px;letter-spacing:8px;">✦ · ✦</span>'
                f'</section>'
            )
            i += 1; continue

        # ── H1（文章大标题，通常第一行）──
        if re.match(r'^# [^#]', line):
            # 头部卡片已经有标题，H1 只作为内容区开场，用较小字号
            parts.append(
                f'<p style="font-size:18px;font-weight:bold;color:{DARK};'
                f'line-height:1.45;margin:0 0 6px;">{_inline(line[2:])}</p>'
            )

        # ── H2（章节标题，金色左竖线+底划线强调）──
        elif line.startswith("## "):
            section_heading_count += 1
            parts.append(
                f'<section style="margin:36px 0 14px;">'
                # 小号章节号
                f'<p style="font-size:11px;color:{GOLD_D};letter-spacing:3px;'
                f'margin:0 0 6px;">第 {section_heading_count} 节</p>'
                # 主标题文字
                f'<p style="font-size:18px;font-weight:bold;color:{DARK};'
                f'line-height:1.4;margin:0 0 8px;">{_inline(line[3:])}</p>'
                # 金色短横线
                f'<section style="width:32px;height:3px;background:{GOLD};'
                f'border-radius:2px;"></section>'
                f'</section>'
            )

        # ── 引用块（> text）──
        elif line.startswith("> "):
            parts.append(
                f'<section style="margin:22px 0;padding:18px 20px;'
                f'background:{BG};border-radius:10px;'
                f'border-left:3px solid {GOLD};">'
                f'<p style="font-size:15px;line-height:1.85;color:{DARK};'
                f'font-weight:500;margin:0;">{_inline(line[2:])}</p>'
                f'</section>'
            )

        # ── 代码块 ──
        elif line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_html = "".join(
                f'<p style="margin:1px 0;font-size:13px;line-height:1.75;'
                f'font-family:Menlo,Consolas,monospace;color:{GOLD};">'
                f'{_esc(ln) if ln.strip() else "&nbsp;"}</p>'
                for ln in code_lines
            )
            parts.append(
                f'<section style="background:{MID_BG};padding:14px 16px;'
                f'border-radius:8px;margin:16px 0;">'
                f'{code_html}</section>'
            )

        # ── 空行 ──
        elif line.strip() == "":
            pass

        # ── 独立加粗行（拉拉拉 pull-quote）──
        elif re.match(r'^\*\*.+\*\*$', line.strip()):
            inner = line.strip()[2:-2]
            parts.append(
                f'<section style="margin:24px 0;padding:18px 20px 18px 22px;'
                f'border-left:3px solid {GOLD};background:{BG};border-radius:0 10px 10px 0;">'
                f'<p style="font-size:15px;font-weight:bold;color:{DARK};'
                f'line-height:1.75;margin:0;">{inner}</p>'
                f'</section>'
            )

        # ── 普通正文 ──
        else:
            parts.append(
                f'<p style="font-size:15px;line-height:1.95;color:{TEXT};margin:14px 0;">'
                f'{_inline(line)}</p>'
            )
        i += 1

    # ── 末尾插入未使用的图片 ──
    for idx in range(len(img_urls)):
        if idx not in used_img_idxs and img_urls[idx]:
            parts.append(
                f'<img src="{img_urls[idx]}" style="max-width:100%;width:100%;'
                f'display:block;margin:24px auto;border-radius:10px;" />'
            )

    # ── 尾部卡片 ──
    parts.append(
        f'<section style="background:{DARK_BG};border-radius:14px;'
        f'padding:22px 20px;margin:36px 0 0;text-align:center;">'
        f'<p style="font-size:12px;color:{GOLD};letter-spacing:2px;margin:0 0 10px;">'
        f'✦ 船长与麦洛的超时空电台 ✦</p>'
        f'<p style="font-size:13px;color:#aaa;line-height:1.7;margin:0 0 14px;">'
        f'每期一个让你停下来想一想的问题<br/>'
        f'关注我们，下期见</p>'
        f'<p style="font-size:12px;color:{GOLD_D};margin:0;">'
        f'▶ {next_ep}</p>'
        f'</section>'
    )

    return (
        '<section style="font-family:-apple-system,\'PingFang SC\',\'Helvetica Neue\',sans-serif;'
        'max-width:680px;margin:0 auto;padding:0 2px;">\n'
        + "\n".join(parts) + "\n</section>"
    )


def create_or_update_draft(token, cfg, thumb_id, html):
    existing = cfg.get(DRAFT_ID_KEY, "")
    payload_articles = {
        "title":              cfg["title"],
        "author":             cfg["author"],
        "digest":             cfg["digest"],
        "content":            html,
        "thumb_media_id":     thumb_id,
        "content_source_url": cfg["content_source_url"],
        "need_open_comment":  1,
        "only_fans_can_comment": 0
    }
    if existing:
        data = _post_json(f"{BASE}/cgi-bin/draft/update", token,
            {"media_id": existing, "index": 0, "articles": payload_articles})
        if data.get("errcode", -1) == 0:
            print(f"  ✅ 草稿已更新: {existing[:30]}...")
            return existing
        print(f"  ⚠️  更新失败 {data}，尝试新建...")
    data = _post_json(f"{BASE}/cgi-bin/draft/add", token,
        {"articles": [payload_articles]})
    mid = data.get("media_id", "")
    if mid:
        print(f"  ✅ 新草稿: {mid[:30]}...")
        return mid
    raise Exception(f"草稿创建失败: {data}")


def discover_fileid(token, cfg):
    draft_id = cfg.get(DRAFT_ID_KEY, "")
    if not draft_id:
        print("❌ config.json 中没有 draft_media_id，请先运行发布脚本")
        return
    r = _post_json(f"{BASE}/cgi-bin/draft/get", token, {"media_id": draft_id})
    content = r.get("news_item", [{}])[0].get("content", "")
    m = re.search(r'voice_encode_fileid="([^"]+)"', content)
    if m:
        import base64
        fileid = m.group(1)
        decoded = base64.b64decode(fileid + "==").decode()
        ep = cfg["ep"]
        print(f"\n✅ 发现 voice_encode_fileid: {fileid}")
        print(f"   解码值: {decoded}")
        print(f'\n自动写入 config.json...')
        cfg["voice_encode_fileid"] = fileid
        Path(f"episodes/ep{ep}/config.json").write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 已保存，重新运行: python3 scripts/publish_wechat.py --ep {ep}")
        return fileid
    print("⚠️  草稿中未找到音频标签，请先在后台编辑器插入音频并保存")


def main():
    ep = "001"
    discover_mode = "--discover" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == '--ep' and i + 1 < len(sys.argv):
            ep = sys.argv[i + 1].zfill(3)

    cfg_path = Path(f"episodes/ep{ep}/config.json")
    if not cfg_path.exists():
        print(f"❌ 未找到 {cfg_path}")
        return
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    img_dir = Path(f"episodes/ep{ep}/output/images")

    print("=" * 54)
    print(f"CaptainCast EP.{ep} · {'提取音频fileid' if discover_mode else '发布微信草稿'}")
    print("=" * 54 + "\n")

    token = get_token()

    if discover_mode:
        discover_fileid(token, cfg)
        return

    # 1. 封面图
    thumb_id = cfg.get(THUMB_ID_KEY, "")
    if not thumb_id:
        print(f"\n🖼  上传封面图...")
        thumb_id = upload_thumb(token, img_dir / cfg["thumb_image"])
        cfg[THUMB_ID_KEY] = thumb_id
    else:
        print(f"✅ 封面图复用: {thumb_id[:30]}...")

    # 2. 正文配图
    print(f"\n🖼  上传正文配图...")
    img_urls = []
    for fname in cfg["images_order"]:
        try:
            img_urls.append(upload_img_to_article(token, img_dir / fname))
        except Exception as e:
            print(f"  ⚠️  {fname}: {e}")
            img_urls.append("")

    # 3. 音频（首次上传，等待手动插入获取 fileid）
    # 微信 add_material voice 接口限制约 2MB，长节目可能超出，失败时跳过继续建图文草稿
    if not cfg.get("voice_encode_fileid"):
        audio_path = Path(f"audio/output/ep{ep}_podcast_64k.mp3")
        if audio_path.exists() and not cfg.get("voice_media_id"):
            fsize_mb = audio_path.stat().st_size / 1024 / 1024
            print(f"\n🎙  上传音频素材... ({fsize_mb:.1f} MB)")
            try:
                voice_media_id = upload_voice(token, audio_path)
                cfg["voice_media_id"] = voice_media_id
            except Exception as e:
                print(f"  ⚠️  音频 API 上传失败（{fsize_mb:.1f}MB）：{e}")
                print(f"  → 跳过，先建图文草稿。音频请在公众号后台编辑器手动插入")

    # 4. HTML
    print(f"\n📝 生成 HTML...")
    html = build_html(cfg, img_urls)
    print(f"  ✅ {len(html)} 字符" +
          ("  🎙 含音频" if cfg.get("voice_encode_fileid") else "  ⏳ 待音频fileid"))

    # 5. 草稿
    print(f"\n📋 创建/更新草稿...")
    draft_id = create_or_update_draft(token, cfg, thumb_id, html)
    cfg[DRAFT_ID_KEY] = draft_id

    # 6. 保存 config
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ config.json 已更新（记录 draft_id + thumb_id）")

    print("\n" + "=" * 54)
    if cfg.get("voice_encode_fileid"):
        print("✨ 完成！去公众号后台 草稿箱 → 群发 即可发布")
    else:
        print("📋 草稿已创建，还需处理音频（1分钟）：")
        print(f"   1. 后台编辑器打开草稿 → 插入音频 → 保存")
        print(f"   2. python3 scripts/publish_wechat.py --ep {ep} --discover")
        print(f"   3. 重新运行: python3 scripts/publish_wechat.py --ep {ep}")
    print("=" * 54)


if __name__ == "__main__":
    main()
