"""
CaptainCast · AI 生图（通用，支持任意集数）
运行：python3 scripts/gen_image.py --ep 001
     python3 scripts/gen_image.py --ep 002
依赖：pip3 install requests python-dotenv
"""
import requests, os, base64, re, json, sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
OR_KEY = os.getenv('OPENROUTER_API_KEY')


def get_ep() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == '--ep' and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    # 默认用最新的有 prompts.json 的集数（新目录 input/，旧目录兼容）
    eps = sorted(Path("episodes").glob("ep*/input/prompts.json"))
    if eps:
        return eps[-1].parent.parent.name.replace("ep", "")
    eps = sorted(Path("episodes").glob("ep*/prompts.json"))
    if eps:
        return eps[-1].parent.name.replace("ep", "")
    return "001"


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

    # Gemini via OpenRouter: images in message["images"]
    for images_field in [msg.get("images", []),
                         msg.get("content") if isinstance(msg.get("content"), list) else []]:
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

    ep = get_ep()
    ep_dir = Path(f"episodes/ep{ep}")

    # 新目录结构：input/prompts.json → output/images/
    # 旧目录结构（兼容）：prompts.json → images/
    prompts_file = ep_dir / "input" / "prompts.json"
    if not prompts_file.exists():
        prompts_file = ep_dir / "prompts.json"
    if not prompts_file.exists():
        print(f"❌ 未找到 prompts.json，请先创建 episodes/ep{ep}/input/prompts.json")
        return

    raw = json.loads(prompts_file.read_text(encoding="utf-8"))

    # 支持两种格式：
    # 新格式：{"images": [{"filename": "xx.png", "description": "...", "prompt": "..."}]}
    # 旧格式：[{"name": "xx", "label": "...", "prompt": "..."}]
    if isinstance(raw, dict) and "images" in raw:
        prompts = [
            {"name": Path(p["filename"]).stem,
             "label": p.get("description", p["filename"]),
             "filename": p["filename"],
             "prompt": p["prompt"]}
            for p in raw["images"]
        ]
        out_dir = ep_dir / "output" / "images"
    else:
        prompts = raw
        for p in prompts:
            if "filename" not in p:
                p["filename"] = f"{p['name']}.png"
        out_dir = ep_dir / "images"

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🎨 EP.{ep} 生图开始，共 {len(prompts)} 张")
    print(f"   输出目录: {out_dir}\n")
    for i, p in enumerate(prompts):
        out_path = out_dir / p["filename"]
        if out_path.exists() and out_path.stat().st_size > 10240:
            print(f"[{i+1}/{len(prompts)}] ⏭️  已存在，跳过: {p['filename']}")
            continue
        print(f"[{i+1}/{len(prompts)}] {p['label']}")
        data = generate(p["prompt"])
        if data:
            out_path.write_bytes(data)
            print(f"  ✅ {out_path}  ({len(data)//1024} KB)\n")
        else:
            print(f"  ⚠️  跳过\n")

    success = len(list(out_dir.glob("*.png")))
    print(f"✨ 完成！{success} 张图片在 {out_dir}")


if __name__ == "__main__":
    main()
