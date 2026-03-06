"""
CaptainCast · X (Twitter) 英文 Thread 发布脚本
内容从 episodes/ep{N}/input/x_thread.json 加载（内容与工具分离）

用法：
  env http_proxy=http://127.0.0.1:1087 https_proxy=http://127.0.0.1:1087 \
  python3 scripts/publish_x.py --ep 001 [--dry-run]
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


def load_thread(ep: str):
    """从 episodes/ep{N}/input/x_thread.json 加载 Thread 内容"""
    path = Path(f"episodes/ep{ep}/input/x_thread.json")
    if not path.exists():
        print(f"❌ 找不到 {path}")
        print(f"   请创建该文件，格式：{{\"tweets\": [\"推文1\", \"推文2\", ...]}}")
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    tweets = data.get("tweets", [])
    if not tweets:
        print(f"❌ {path} 中没有 tweets 内容")
        return None
    return tweets


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
    tweets = load_thread(ep)
    if not tweets:
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
        print(f"\n✅ Dry run 完成，确认内容无误后去掉 --dry-run 正式发布")


if __name__ == "__main__":
    main()
