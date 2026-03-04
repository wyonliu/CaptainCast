"""
CaptainCast · EP.001 AI 生图
运行：python3 scripts/gen_image.py
依赖：pip3 install requests python-dotenv
"""
import requests, os, base64, re, json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
OR_KEY  = os.getenv('OPENROUTER_API_KEY')
OUT_DIR = Path("episodes/ep001/images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = [
    {
        "name": "01_cover",
        "label": "封面·麦洛&小墨",
        "prompt": "A 14-year-old Chinese girl standing at the threshold of a vast fantasy portal, a small ink-black dragon curled around her wrist. Nine-colored glowing pools, floating stone pillars defying gravity. Sky deep indigo and amber gold. Dunhuang cyberpunk meets Chinese ink wash painting. Cinematic 4K vertical composition.",
    },
    {
        "name": "02_lingji_vs_jicheng",
        "label": "灵机vs寂熵",
        "prompt": "Split composition. Left half: warm chaotic human light, ember particles, organic flowing curves, fire and tears. Right half: cold blue crystalline AI lattice, geometric rigid order. Center: a spiral vortex where chaos meets order, gold and blue swirling. Dark cosmic background. Chinese ink wash meets hard sci-fi. Square composition.",
    },
    {
        "name": "03_father_daughter",
        "label": "父女·送别",
        "prompt": "A father silhouette standing in darkness watching his young daughter walk through a glowing portal into fantastical mountains and seas. Warm amber light from the portal. Father in shadow, daughter bathed in golden light. Ancient Chinese ink landscape meets science fiction. Deeply emotional cinematic scene. Vertical composition.",
    },
    {
        "name": "04_jianyi_reveal",
        "label": "减一·显现",
        "prompt": "Vast sky over Earth at dusk. A massive translucent holographic ancient entity hovers above clouds, sorrowful and wise. Tiny humans below in awe looking up. Gold and purple cosmic light. Epic science fiction meets Chinese ink painting. Widescreen landscape composition.",
    },
]


def generate(prompt: str) -> Optional[bytes]:
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OR_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://wyonliu.github.io/CaptainCast/",
            "X-Title": "CaptainCast"
        },
        json={
            "model": "google/gemini-3.1-flash-image-preview",
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        },
        timeout=120
    )
    data = resp.json()
    if "error" in data:
        print(f"  ✗ {data['error'].get('message', data['error'])}")
        return None
    msg = data["choices"][0]["message"]

    # Gemini via OpenRouter returns images in message["images"]
    for images_field in [msg.get("images", []), msg.get("content") if isinstance(msg.get("content"), list) else []]:
        if not images_field:
            continue
        for part in images_field:
            if not isinstance(part, dict):
                continue
            url = part.get("image_url", {}).get("url", "")
            if url.startswith("data:"):
                return base64.b64decode(url.split(",")[1])
            elif url.startswith("http"):
                return requests.get(url, timeout=30).content

    content = msg.get("content", "")
    if isinstance(content, str):
        m = re.search(r'data:image/\w+;base64,([A-Za-z0-9+/=]+)', content)
        if m:
            return base64.b64decode(m.group(1))
    print(f"  ✗ 未找到图像，响应: {json.dumps(data)[:200]}")
    return None


def main():
    if not OR_KEY or OR_KEY.startswith("sk-or-v1-你"):
        print("❌ 请先在 .env 填入 OPENROUTER_API_KEY")
        return
    print(f"🎨 EP.001 生图开始，共 {len(PROMPTS)} 张\n")
    for i, p in enumerate(PROMPTS):
        print(f"[{i+1}/{len(PROMPTS)}] {p['label']}")
        data = generate(p["prompt"])
        if data:
            path = OUT_DIR / f"{p['name']}.png"
            path.write_bytes(data)
            print(f"  ✅ {path}  ({len(data)//1024} KB)\n")
        else:
            print(f"  ⚠️  跳过\n")
    success = len(list(OUT_DIR.glob("*.png")))
    print(f"✨ 完成！{success} 张图片在 episodes/ep001/images/")


if __name__ == "__main__":
    main()
