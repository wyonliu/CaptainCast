# CaptainCast · 多平台发布规划
> 整理人：小安 | 2026-03-05

---

## 一、平台矩阵总览

| 平台 | 形式 | 核心受众 | 发布频率 | 状态 |
|------|------|----------|----------|------|
| **公众号** | 长图文 2800字 | 中文读者 | 每期 | ✅ 已接入 |
| **小红书** | 三图文案 | 18-35岁女性/Z世代 | 每期 | ✅ 脚本就绪 |
| **B站** | 视频播客 15min | 科技/科幻爱好者 | 每期 | 🔧 需手动上传 |
| **视频号** | 3min切片 | 微信生态用户 | 每期 | 🔧 需手动上传 |
| **小宇宙** | RSS 音频播客 | 播客重度用户 | 每期 | 📋 注册后自动 |
| **喜马拉雅** | RSS 音频播客 | 广大有声市场 | 每期 | 📋 注册后自动 |
| **Apple Podcasts** | RSS | 国际华语 | 每期 | 📋 注册后自动 |
| **Spotify** | RSS | 国际华语/英语 | 每期 | 📋 注册后自动 |
| **X (Twitter)** | 英文Thread | 全球科技圈 | 每期 | 🔧 需 API Key |

---

## 二、已就绪资产

每期 Claude 自动生成：
```
audio/output/ep{N}_podcast.mp3          ← 高质量音频（主）
audio/output/ep{N}_podcast_64k.mp3      ← 省流版
episodes/ep{N}/videos/ep{N}_bilibili.mp4   ← B站视频
episodes/ep{N}/videos/ep{N}_shipinhao.mp4  ← 视频号视频
episodes/ep{N}/images/*.png             ← 配图
episodes/ep{N}/article.md              ← 公众号长文
episodes/ep{N}/xiaohongshu.md          ← 小红书三图
```

RSS Feed（已上线）：
`https://wyonliu.github.io/CaptainCast/podcast.xml`

---

## 三、各平台注册 & 接入流程

### 3.1 小宇宙（优先）

**受众**：高质量播客圈，口碑扩散效率最高

**注册步骤**：
1. 打开 [https://creators.xiaoyuzhou.fm](https://creators.xiaoyuzhou.fm)
2. 手机号注册，填写创作者信息
3. 「节目管理」→「添加节目」→ 选「RSS导入」
4. 填入 RSS 地址：`https://wyonliu.github.io/CaptainCast/podcast.xml`
5. 等待审核（通常24小时内）

**你需要提供给我**：
- 小宇宙账号邮箱/手机号（用于后续自动发布通知）

---

### 3.2 喜马拉雅

**受众**：基数最大，老年/下沉市场，品牌曝光

**注册步骤**：
1. [https://www.ximalaya.com](https://www.ximalaya.com) → 「主播入驻」
2. 实名认证（需身份证）
3. 「我的」→「播客」→「RSS 导入」→ 填写 RSS 地址

**你需要提供给我**：无需额外信息，RSS 已自动同步

---

### 3.3 Apple Podcasts（苹果播客）

**受众**：海外华人 + 国内苹果用户

**注册步骤**（约10分钟）：
1. 需要 Apple ID（推荐用个人 Apple ID 即可）
2. 打开 [https://podcastsconnect.apple.com](https://podcastsconnect.apple.com)
3. 登录 → 「+」添加节目 → 填入 RSS 地址
4. 审核约3-5个工作日

**你需要提供给我**：
- Apple ID 邮箱（用于查看收听数据）

---

### 3.4 Spotify

**受众**：国际受众 + 国内部分用户

**注册步骤**：
1. [https://podcasters.spotify.com](https://podcasters.spotify.com)
2. 用 Spotify 账号登录（如无可免费注册）
3. 「添加播客」→ 填入 RSS 地址
4. 填写节目信息（节目语言选「中文」）

**你需要提供给我**：Spotify 账号邮箱

---

### 3.5 B站（视频投稿）

**现状**：视频已自动生成，但 B站 API 投稿需要 UP 主账号 + `SESSDATA` Cookie。

**手动上传流程**：
1. 登录 B站 → 「投稿」→ 上传视频
2. 上传 `episodes/ep{N}/videos/ep{N}_bilibili.mp4`
3. 标题：直接用节目标题（如「船长电台001：如果你能给女儿造一个宇宙」）
4. 分区：「知识 → 科学科普」或「生活 → 日常」
5. 封面：从 `episodes/ep{N}/images/01_cover.png` 上传
6. 简介：直接用 digest 字段内容

**实现自动上传，你需要提供我**：
- B站 `SESSDATA` Cookie（登录后 → F12 → Application → Cookies）
- 我会写 `publish_bilibili.py` 脚本

---

### 3.6 视频号

**现状**：视频号暂无 API，必须手动上传。

**手动上传流程**：
1. 微信 → 视频号 → 发视频
2. 上传 `episodes/ep{N}/videos/ep{N}_shipinhao.mp4`
3. 文案从小红书文案第一条取，精简到140字
4. 话题：#科幻 #播客 #CaptainCast

---

### 3.7 X（英文 Thread）

**规划**：每期发一个3-5条的英文 Thread，链接回 RSS/GitHub Pages。

**你需要提供给我**：
- X API Key + Secret + Access Token（Developer Portal 申请）
- 或者：X 账号密码（Claude 浏览器登录手动发）

**Thread 模板**（Claude 自动生成）：
```
1/ [Hook — 1句情感钩子，英文]
   → "A father borrowed money at 2am to pay his team's last salary.
   Then he started writing a sci-fi universe for his daughter."

2/ [知识点简介 + 世界观 1句]
3/ [灵机理论 核心句]
4/ [收听链接 + 下期预告]
```

---

## 四、给我即可全自动的信息清单

> 一次性提供，后续每期无需重复

| 信息 | 用途 | 格式 |
|------|------|------|
| B站 `SESSDATA` Cookie | 自动投稿 | 字符串，约100字符 |
| X API Key 四件套 | 自动发 Thread | 在 `.env` 里填 |
| 苹果/Spotify 邮箱 | 人工辅助注册 | 邮箱地址 |

---

## 五、每期发布 SOP（小安执行）

```
Day 0（录音当天）
  └─ 船长提供：EP.XXX 脚本 / 简介 / 配图 Prompt
  └─ 小安：gen_image.py → gen_voice.py → gen_video.py → 发布公众号

Day 1（次日）
  ├─ 公众号 长图文（群发，21:00）
  ├─ 小宇宙/喜马拉雅/Apple/Spotify 自动同步（RSS 更新即触发）
  └─ 船长手动：B站投稿 + 视频号发布

Day 3
  └─ 小红书 第一图（早9点）

Day 5
  └─ 小红书 第二图 + X Thread（英文）

Day 7
  └─ 小红书 第三图
```

---

## 六、Melody 声音重新克隆（⚠️ 需人工操作）

新音源已就位：`audio/melody-voice-0304.m4a`

**步骤**：
1. 打开 [https://platform.minimax.io](https://platform.minimax.io)
2. 导航：「声音克隆」→「新建克隆」
3. 上传 `audio/melody-voice-0304.m4a`（约120秒的干净人声）
4. 命名建议：`melody_captaincast_v2`
5. 点击克隆，等待完成（约3-5分钟）
6. 复制新的 `Voice ID`
7. 打开 `.env` 文件，修改：
   ```
   MELODY_VOICE_ID=新的voice_id
   ```
8. 告诉我："麦洛克隆完了，ID 是 xxx"
9. 我运行：`python3 scripts/gen_voice.py --ep 001` 重新合成 EP.001 + EP.002

---

*整理时间：2026-03-05 · 执行人：小安*
