"""
CaptainCast · X (Twitter) 英文 Thread 发布脚本
用法：python3 scripts/publish_x.py --ep 001 [--dry-run]
需要系统代理：http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087
或直接：env http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087 python3 scripts/publish_x.py --ep 001
"""
import tweepy, os, sys, json, time
from pathlib import Path
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()

DRY_RUN = "--dry-run" in sys.argv


def get_ep():
    for i, arg in enumerate(sys.argv):
        if arg == "--ep" and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    return "001"


def get_client():
    bearer = unquote(os.getenv("X_BEARER_TOKEN", ""))
    client = tweepy.Client(
        bearer_token=bearer,
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET"),
    )
    return client


def load_episode(ep: str):
    config_path = Path(f"episodes/ep{ep}/config.json")
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


# ─── EP 英文 Thread 模板 ────────────────────────────────────────────────
THREADS = {
    "001": [
        """🚀 EP.001 DROP: "What if you could build a universe for your daughter?"

At 2AM, a father used borrowed money to pay his employees' last salaries.
Then he started writing a sci-fi epic — not to sell, but for his 11-year-old girl.

This is CaptainCast. A father-daughter space opera begins. 🧵""",

        """🧠 The Big Idea: LINGJI THEORY

AI random numbers are FAKE — they're pseudorandom, predictable.

Human brains have quantum coherence states that generate TRUE randomness.

Human irrationality = the universe's ONLY evolutionary engine.

"When you choose to persist against all logic — the universe just got a new variable." ✨""",

        """🌌 The World: SHANHAI (山海)

Not a game. An existence with equal weight to reality.

Your tears inside are real.
Your friendships inside are real.
Your choices have real consequences.

Aesthetic: Dunhuang Cyberpunk × Chinese ink wash × Hard sci-fi logic 🎨""",

        """🔥 The Twist: THE IGNITERS

Humans thought the high-dimensional civilization was harvesting them.

Then their representative appeared in the sky above every city:

"You think we are harvesters."

Wrong.

"We are IGNITERS."

They manufactured humanity's pain — until we burned bright enough to matter. 💫""",

        """🎙️ Listen now:
🍎 Apple: https://podcasts.apple.com/us/podcast/船长时空站/id1882655595
🎵 Spotify: https://open.spotify.com/show/0rkHdRZTYg7ksxN0zhtzNu
🌐 Web: https://wyonliu.github.io/CaptainCast/ep001.html

📻 小宇宙 (CN): https://www.xiaoyuzhoufm.com/podcast/69a942fad7ec33e774506f7c

#SciFi #Podcast #ChineseSciFi #ShanHai #CaptainCast""",
    ],

    "002": [
        """🚀 EP.002 DROP: "Day One of Universe Creation — Every Bug Is a New Variable"

I built an AI-powered podcast from scratch this week.

Voice cloning → Image generation → Automated publishing.

But the most interesting part? The moments it broke. 🧵""",

        """🤖 What we built (in one week):

• 🎙️ Cloned 2 voices (Captain + Melody) from real recordings
• 🖼️ Generated 8 cover images via Gemini
• 📹 Automated B站 & 视频号 video production
• 📡 Published to 5 podcast platforms via RSS

The whole pipeline: idea → publish in ~4 hours.""",

        """💡 The Lingji Insight of the week:

An AI agent that never makes mistakes is just following instructions.

An AI agent that makes mistakes AND learns — that's a new variable.

Every "Connection Reset" error was the universe demanding a better solution. 🌊""",

        """🎙️ Listen now:
🍎 Apple: https://podcasts.apple.com/us/podcast/船长时空站/id1882655595
🎵 Spotify: https://open.spotify.com/show/0rkHdRZTYg7ksxN0zhtzNu
🌐 Web: https://wyonliu.github.io/CaptainCast/ep002.html

#AITools #PodcastAutomation #ChineseSciFi #CaptainCast""",
    ],
}


def post_thread(client, tweets: list):
    """发布 Thread：第一条独立发，后续回复前一条"""
    prev_id = None
    for i, text in enumerate(tweets):
        if DRY_RUN:
            print(f"\n[DRY RUN] Tweet {i+1}/{len(tweets)}:")
            print(text)
            print("-" * 60)
            prev_id = f"fake_id_{i}"
            continue

        kwargs = {"text": text}
        if prev_id:
            kwargs["in_reply_to_tweet_id"] = prev_id

        try:
            resp = client.create_tweet(**kwargs)
            prev_id = resp.data["id"]
            print(f"✅ Tweet {i+1}/{len(tweets)} posted: id={prev_id}")
            if i < len(tweets) - 1:
                time.sleep(2)  # 避免速率限制
        except tweepy.TweepyException as e:
            print(f"❌ Tweet {i+1} failed: {e}")
            return False
    return True


def main():
    ep = get_ep()
    tweets = THREADS.get(ep)
    if not tweets:
        print(f"❌ 没有 EP.{ep} 的 Thread 模板")
        print(f"   当前可用: {list(THREADS.keys())}")
        return

    print(f"🐦 X Thread 发布 · EP.{ep}")
    print(f"   共 {len(tweets)} 条推文")
    if DRY_RUN:
        print("   [DRY RUN 模式 - 不会真实发布]")
    print()

    client = get_client()

    # 验证账号
    try:
        me = client.get_me()
        print(f"✅ 已连接: @{me.data.username}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("   请确认代理已开启：env http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087")
        return

    print()
    result = post_thread(client, tweets)

    if result and not DRY_RUN:
        print(f"\n🎉 EP.{ep} Thread 发布成功！")
    elif DRY_RUN:
        print(f"\n✅ Dry run 完成，内容无误后去掉 --dry-run 正式发布")


if __name__ == "__main__":
    main()
