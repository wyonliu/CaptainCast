"""
CaptainCast · 声音合成（通用，支持任意集数）
运行：python3 scripts/gen_voice.py --ep 001
     python3 scripts/gen_voice.py --ep 002
脚本格式（episodes/ep00X/script.md）：
  [船长 speed=0.95] 文本内容
  [麦洛 speed=1.05] 文本内容
依赖：pip install requests python-dotenv pydub
"""
import requests, os, re, time, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
MM_KEY   = os.getenv('MINIMAX_API_KEY')
MM_GROUP = os.getenv('MINIMAX_GROUP_ID')
CAP_ID   = os.getenv('CAPTAIN_VOICE_ID', 'captain_captaincast')
MEL_ID   = os.getenv('MELODY_VOICE_ID',  'melody_captaincast')

# 全局语速倍乘（.env 可覆盖）
# 船长原语速 0.82-0.95 偏慢，x1.15 → 实际 0.94-1.09，明快不失沉稳
# 麦洛待重新克隆后视效果调整，默认不变
CAPTAIN_SPEED_MULT = float(os.getenv('CAPTAIN_SPEED_MULT', '1.15'))
MELODY_SPEED_MULT  = float(os.getenv('MELODY_SPEED_MULT',  '1.0'))


def get_ep() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == '--ep' and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    eps = sorted(Path("episodes").glob("ep*/script.md"))
    if eps:
        return eps[-1].parent.name.replace("ep", "")
    return "001"


def parse_script(script_path: Path):
    """解析 script.md，返回 [(role, speed, text), ...]"""
    pattern = re.compile(r'^\[(船长|麦洛)\s+speed=([\d.]+)\]\s*(.+)$')
    lines = []
    for line in script_path.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line.strip())
        if m:
            role_cn, speed, text = m.groups()
            role = "captain" if role_cn == "船长" else "melody"
            lines.append((role, float(speed), text.strip()))
    return lines


def tts(text, voice_id, speed, out_path):
    resp = requests.post(
        f"https://api.minimax.chat/v1/t2a_v2?GroupId={MM_GROUP}",
        headers={"Authorization": f"Bearer {MM_KEY}", "Content-Type": "application/json"},
        json={
            "model": "speech-01-hd",
            "text": text,
            "stream": False,
            "voice_setting": {"voice_id": voice_id, "speed": speed, "vol": 1.0, "pitch": 0},
            "audio_setting": {"format": "mp3", "sample_rate": 44100}
        },
        timeout=60
    )
    data = resp.json()
    if data.get("base_resp", {}).get("status_code") != 0:
        print(f"  ✗ {data.get('base_resp',{}).get('status_msg', data)}")
        return False
    audio_hex = data.get("data", {}).get("audio", "")
    if not audio_hex:
        print(f"  ✗ 未返回音频")
        return False
    Path(out_path).write_bytes(bytes.fromhex(audio_hex))
    return True


def main():
    if not MM_KEY or MM_KEY.startswith("sk-api-你"):
        print("❌ 请先在 .env 填入 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID")
        return

    ep = get_ep()
    script_path = Path(f"episodes/ep{ep}/script.md")
    if not script_path.exists():
        print(f"❌ 未找到 {script_path}")
        return

    script = parse_script(script_path)
    if not script:
        print(f"❌ script.md 中未找到对话行（格式：[船长 speed=0.95] 文本）")
        return

    seg_dir = Path(f"audio/output/ep{ep}_segments")
    seg_dir.mkdir(parents=True, exist_ok=True)
    final = Path(f"audio/output/ep{ep}_podcast.mp3")

    print(f"🎙  EP.{ep} 声音合成，共 {len(script)} 段\n")
    seg_files = []
    for i, (role, speed, text) in enumerate(script):
        voice_id = CAP_ID if role == "captain" else MEL_ID
        label = "船长" if role == "captain" else "麦洛"
        # 应用全局速度倍乘器（上限 2.0）
        mult = CAPTAIN_SPEED_MULT if role == "captain" else MELODY_SPEED_MULT
        actual_speed = round(min(2.0, speed * mult), 3)
        out = seg_dir / f"seg_{i:02d}_{role}.mp3"
        print(f"[{i+1:02d}/{len(script)}] {label}  x{mult}={actual_speed}  {text[:40]}...")
        if tts(text, voice_id, actual_speed, out):
            seg_files.append(out)
            print(f"  ✅ {out.stat().st_size//1024} KB")
        time.sleep(0.5)

    if not seg_files:
        print("❌ 没有成功的音频段")
        return

    print(f"\n🔗 合并 {len(seg_files)} 段...")
    try:
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=700)
        combined = sum(
            [AudioSegment.from_mp3(str(f)) + silence for f in seg_files],
            AudioSegment.empty()
        )
        combined.export(str(final), format="mp3", bitrate="128k")
        mins = len(combined) / 1000 / 60
        mb = final.stat().st_size // 1024 // 1024
        print(f"✅ {final}  {mins:.1f}分钟 / {mb}MB")

        # 生成 64k 压缩版（用于微信上传）
        final_64k = Path(f"audio/output/ep{ep}_podcast_64k.mp3")
        combined.export(str(final_64k), format="mp3", bitrate="64k")
        kb = final_64k.stat().st_size // 1024
        print(f"✅ {final_64k}  {kb} KB（微信上传用）")
    except ImportError:
        print("⚠️  pip install pydub 后再合并，各段已在:", seg_dir)


if __name__ == "__main__":
    main()
