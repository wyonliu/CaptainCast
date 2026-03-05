# CaptainCast 多平台发布 Checklist
# 更新：2026-03-06 / 整理：小安

---

## 一、当前发布状态总览

| 平台 | EP.001 | EP.002 | 自动化 |
|------|--------|--------|--------|
| 公众号（船长时空站） | ✅ 已发 | ✅ 已发 | ✅ publish_wechat.py |
| 小宇宙 | ✅ RSS自动 | ✅ RSS自动 | ✅ gen_rss.py |
| Spotify | ✅ RSS自动 | ✅ RSS自动 | ✅ gen_rss.py |
| Apple Podcasts | ✅ RSS自动 | ✅ RSS自动 | ✅ gen_rss.py |
| 喜马拉雅 | ✅ 手动 | ✅ 手动 | ⏳ 需20粉+3集 |
| B站 | ⏳ 待上传 | ⏳ 待上传 | 手动 |
| 视频号 | ⏳ 待上传 | ⏳ 待上传 | 手动 |
| 小红书 | ⏳ 待发布 | ⏳ 待发布 | 手动 |
| X (@CaptainWyon) | ⏳ 待发布 | ⏳ 待发布 | ✅ publish_x.py |

---

## 二、B站上传指南

### 视频文件位置
```
episodes/ep001/videos/ep001_bilibili.mp4    (1920x1080, ~80MB)
episodes/ep002/videos/ep002_bilibili.mp4    (1920x1080, ~100MB)
```

### 封面图
```
episodes/ep001/videos/ep001_preview_bilibili.png
episodes/ep002/videos/ep002_preview_bilibili.png
```

### 发布参数
| 字段 | EP.001 | EP.002 |
|------|--------|--------|
| 标题 | EP.001 如果你能给女儿造一个宇宙｜船长时空站 | EP.002 造宇宙的第一天，每一个报错都是新变量｜船长时空站 |
| 分区 | 知识 > 科学科普 | 知识 > 科学科普 |
| 标签 | 科幻,播客,神临山海,宇宙,AI,父女,灵机理论 | AI,播客,自动化,创作幕后,神临山海,科幻 |
| 简介 | （复制自下方） | （复制自下方） |

### EP.001 B站简介
```
【船长时空站 EP.001】如果你能给女儿造一个宇宙

一个父亲的故事：凌晨两点，借钱发完最后一个月的工资，然后开始给女儿写一个科幻世界。

本期核心：
🧠 灵机理论——AI随机数是假的，人类的非理性才是宇宙进化发动机
🌌 山海世界观——和现实等重的存在，眼泪是真的，选择有后果
🔥 最大反转——收割者是点火者，痛苦是爱的最高形式

📻 全平台收听：
小宇宙：https://www.xiaoyuzhoufm.com/podcast/69a942fad7ec33e774506f7c
Spotify：https://open.spotify.com/show/0rkHdRZTYg7ksxN0zhtzNu
Apple Podcasts：https://podcasts.apple.com/us/podcast/船长时空站/id1882655595

#神临山海 #科幻播客 #灵机理论 #父女 #AI
```

### EP.002 B站简介
```
【船长时空站 EP.002】造宇宙的第一天，每一个报错都是新变量

幕后揭秘：这期播客是如何被AI自动化全链路生成的

本期核心：
🤖 声音克隆 + 图像生成 + 视频自动化 + 多平台发布
💡 报错=灵机：每一个失败都是宇宙给你的新变量
🎙️ 硅基协同创作的第一天——这就是灵机理论的实践

📻 全平台收听：
小宇宙：https://www.xiaoyuzhoufm.com/podcast/69a942fad7ec33e774506f7c
Spotify：https://open.spotify.com/show/0rkHdRZTYg7ksxN0zhtzNu
Apple Podcasts：https://podcasts.apple.com/us/podcast/船长时空站/id1882655595

#AI播客 #自动化创作 #神临山海 #科幻 #创作幕后
```

---

## 三、视频号上传指南

### 视频文件位置
```
episodes/ep001/videos/ep001_shipinhao.mp4   (1080x1080, ~60MB)
episodes/ep002/videos/ep002_shipinhao.mp4   (1080x1080, ~75MB)
```

### 发布参数
| 字段 | EP.001 | EP.002 |
|------|--------|--------|
| 标题 | 凌晨两点，他在给女儿造宇宙 #神临山海 | 每一个报错都是新变量 #AI协同创作 |
| 话题 | #神临山海 #科幻播客 #父女 | #AI #播客自动化 #科幻 |
| 关联公众号 | 船长时空站 → 对应文章 | 船长时空站 → 对应文章 |

---

## 四、小红书发布指南

### 文案文件位置
```
episodes/ep001/xiaohongshu.md  ← 三图文案（周一/三/五 各一图）
```

### 发布时间
- 第一图（情感钩）：周一 9:00
- 第二图（知识钩）：周三 9:00
- 第三图（反转钩）：周五 9:00

### 每图发布步骤
1. 打开 xiaohongshu.md，复制对应图的正文
2. 封面用 `media/podcast_cover_1400.png` 或 EP 配图（16:9）
3. 标签：复制文案末尾的 # 标签
4. 发布后：评论区置顶 "完整音频在小宇宙/Spotify搜 [船长时空站]"
5. 开启「关联外部链接」→ 填小宇宙 URL

### EP.001 图片推荐
- 第一图封面：`episodes/ep001/images/` 中父女送别图（3:4）
- 第二图封面：灵机vs寂熵图（1:1）
- 第三图封面：减一显现图（16:9 横转竖裁）

---

## 五、X Thread 发布（@CaptainWyon）

```bash
# 发布 EP.001 Thread（5条）
env http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087 \
python3 scripts/publish_x.py --ep 001

# 发布 EP.002 Thread（4条）
env http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087 \
python3 scripts/publish_x.py --ep 002

# 先干跑测试
env http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087 \
python3 scripts/publish_x.py --ep 001 --dry-run
```

**推荐发布时间：周日（UTC+8 上午 10:00，对应美西 Fri 6pm）**

---

## 六、RSS 更新流程（新集数上线后）

```bash
# 1. 更新 media/ 中的音频文件
cp audio/output/ep003_podcast_64k.mp3 media/ep003_podcast_64k.mp3
cp media/ep003_cover.png media/  # 或沿用统一封面

# 2. 在 gen_rss.py 的 EPISODES 列表中添加新集数

# 3. 生成并推送
python3 scripts/gen_rss.py
git add podcast.xml media/ep003_podcast_64k.mp3
git commit -m "feat: 发布EP.003"
git push

# 小宇宙/Spotify/Apple Podcasts 会在30分钟内自动更新
```

---

## 七、BGM 引入计划（EP.003+）

### 选音乐的标准
- 免商业版权（CC0 或 CC BY），不要 CC BY-NC-SA 等
- 时长：找10分钟+的长音乐，循环播放
- 调性：空灵感、东方感、科幻感，不能有人声

### 推荐搜索关键词
- Pixabay: "ambient space", "meditation Chinese", "cinematic ambient"
- FMA: "electronic ambient", "dark ambient"
- YouTube Audio Library: "space", "serene"

### 技术实现（gen_voice.py合并阶段）
```python
from pydub import AudioSegment

bgm = AudioSegment.from_file("media/bgm.mp3")
bgm = bgm - 18  # 降低18dB（背景音）
# 循环BGM到总时长
while len(bgm) < len(combined):
    bgm = bgm + bgm
bgm = bgm[:len(combined)]
final = combined.overlay(bgm)
```

---

*整理：小安 / 2026-03-06*
