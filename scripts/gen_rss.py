#!/usr/bin/env python3
"""
CaptainCast · RSS Feed 生成器
生成标准 podcast RSS，托管在 GitHub Pages
提交到：小宇宙 / 喜马拉雅 / Apple Podcasts / Spotify

运行：
  python3 scripts/gen_rss.py
  # 生成 podcast.xml，然后 git push 即自动更新所有平台
"""
import json, os
from pathlib import Path
from datetime import datetime, timezone

# ─── 播客元信息 ───────────────────────────────────────────
PODCAST_META = {
    "title":       "船长与麦洛的超时空电台",
    "subtitle":    "灵机 山海 宇宙",
    "description": "一个父亲和女儿的科幻故事，一套AI协同内容创作系统，一场关于人类非理性的宇宙哲学。每期探索一个让你停下来想一想的问题。",
    "author":      "船长",
    "email":       "captaincast@wyonliu.com",     # 可改成真实邮箱
    "website":     "https://wyonliu.github.io/CaptainCast/",
    "image":       "https://wyonliu.github.io/CaptainCast/media/podcast_cover_1400.png",
    "language":    "zh-cn",
    "category":    "Science Fiction",             # Apple Podcasts 分类
    "category2":   "Technology",
    "explicit":    "no",
    "copyright":   f"Copyright {datetime.now().year} 船长时空站",
    "feed_url":    "https://wyonliu.github.io/CaptainCast/podcast.xml",
    "base_audio":  "https://wyonliu.github.io/CaptainCast/media/",
}

# ─── 集数信息（手动维护或从 config.json 读取）──────────────
# 音频托管在 GitHub Pages /media/ 目录
# 命名规范: ep001_podcast_64k.mp3, ep002_podcast_64k.mp3
EPISODES = []

def load_episodes():
    """从 episodes/ep*/config.json 读取集数信息"""
    eps = sorted(Path("episodes").glob("ep*/config.json"))
    for cfg_path in eps:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            ep_num = cfg.get("ep", "000")

            # 音频文件大小（用于 RSS enclosure length）
            audio_local = Path(f"audio/output/ep{ep_num}_podcast_64k.mp3")
            audio_size = audio_local.stat().st_size if audio_local.exists() else 0

            # 发布时间（用 config 里的 update_time 或当前时间）
            pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

            # 时长（秒）
            duration_s = cfg.get("audio_duration_ms", 0) // 1000
            duration_str = f"{duration_s // 3600}:{(duration_s % 3600) // 60:02d}:{duration_s % 60:02d}"

            EPISODES.append({
                "ep":          ep_num,
                "title":       cfg.get("title", f"EP.{ep_num}"),
                "subtitle":    cfg.get("digest", "")[:100],
                "description": cfg.get("digest", ""),
                "audio_url":   f"{PODCAST_META['base_audio']}ep{ep_num}_podcast_64k.mp3",
                "audio_size":  audio_size,
                "audio_type":  "audio/mpeg",
                "duration":    duration_str,
                "pub_date":    pub_date,
                "episode_num": int(ep_num),
                "link":        f"https://wyonliu.github.io/CaptainCast/ep{ep_num}.html",
                "image":       f"https://wyonliu.github.io/CaptainCast/media/ep{ep_num}_cover.png",
            })
        except Exception as e:
            print(f"⚠️  {cfg_path}: {e}")
    # 最新集数在前
    EPISODES.sort(key=lambda x: x["episode_num"], reverse=True)

def escape_xml(s):
    return (s.replace("&", "&amp;")
              .replace("<", "&lt;")
              .replace(">", "&gt;")
              .replace('"', "&quot;"))

def sanitize_title(s):
    """RSS 标题安全化：替换各平台可能拒绝的特殊字符"""
    return (s.replace("：", ": ")   # 全角冒号 → 半角冒号
              .replace("，", ", ")  # 全角逗号 → 半角逗号
              .replace("、", ", ")  # 顿号 → 半角逗号
              .replace("。", ". ")  # 句号 → 半角句号
              .replace("【", "[").replace("】", "]")
              .replace("·", " ").replace("•", " ")
              .replace("©", "").replace("  ", " ")  # © 和双空格
              .strip())

def generate_rss():
    load_episodes()
    m = PODCAST_META

    items = []
    for ep in EPISODES:
        items.append(f"""
    <item>
      <title>{escape_xml(sanitize_title(ep['title']))}</title>
      <itunes:title>{escape_xml(sanitize_title(ep['title']))}</itunes:title>
      <itunes:subtitle>{escape_xml(sanitize_title(ep['subtitle']))}</itunes:subtitle>
      <description><![CDATA[{ep['description']}]]></description>
      <itunes:summary><![CDATA[{ep['description']}]]></itunes:summary>
      <link>{ep['link']}</link>
      <guid isPermaLink="false">captaincast-ep{ep['ep']}</guid>
      <pubDate>{ep['pub_date']}</pubDate>
      <enclosure url="{ep['audio_url']}"
                 length="{ep['audio_size']}"
                 type="{ep['audio_type']}" />
      <itunes:duration>{ep['duration']}</itunes:duration>
      <itunes:episode>{ep['episode_num']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>no</itunes:explicit>
      <itunes:image href="{ep['image']}" />
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:podcast="https://podcastindex.org/namespace/1.0"
  xmlns:atom="http://www.w3.org/2005/Atom">

  <channel>
    <title>{escape_xml(m['title'])}</title>
    <link>{m['website']}</link>
    <description><![CDATA[{m['description']}]]></description>
    <language>{m['language']}</language>
    <copyright>{escape_xml(m['copyright'])}</copyright>
    <managingEditor>{m['email']}</managingEditor>
    <webMaster>{m['email']}</webMaster>
    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
    <atom:link href="{m['feed_url']}" rel="self" type="application/rss+xml" />

    <!-- iTunes / Apple Podcasts -->
    <itunes:title>{escape_xml(m['title'])}</itunes:title>
    <itunes:subtitle>{escape_xml(sanitize_title(m['subtitle']))}</itunes:subtitle>
    <itunes:summary><![CDATA[{m['description']}]]></itunes:summary>
    <itunes:author>{m['author']}</itunes:author>
    <itunes:owner>
      <itunes:name>{m['author']}</itunes:name>
      <itunes:email>{m['email']}</itunes:email>
    </itunes:owner>
    <itunes:image href="{m['image']}" />
    <itunes:category text="{m['category2']}"/>
    <itunes:category text="{m['category']}"/>
    <itunes:explicit>{m['explicit']}</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{"".join(items)}
  </channel>
</rss>"""

    out = Path("podcast.xml")
    out.write_text(rss, encoding="utf-8")
    print(f"✅ 生成 podcast.xml（{len(EPISODES)} 集）")
    print(f"   Feed URL: {m['feed_url']}")
    print(f"\n📋 提交步骤：")
    print(f"   1. git push 后 feed 生效")
    print(f"   2. 小宇宙：xyzfm.app → 提交播客 → 填入 {m['feed_url']}")
    print(f"   3. 喜马拉雅：ximalaya.com/main-player → 主播中心 → RSS 导入")
    print(f"   4. Apple Podcasts：podcastsconnect.apple.com → 提交 RSS")
    print(f"   5. Spotify：podcasters.spotify.com → 提交 RSS")
    print(f"\n⚠️  注意：需先把 mp3 文件上传到 GitHub Pages /media/ 目录")
    print(f"   ep001_podcast_64k.mp3 → media/ep001_podcast_64k.mp3")
    print(f"   ep002_podcast_64k.mp3 → media/ep002_podcast_64k.mp3")

if __name__ == "__main__":
    generate_rss()
