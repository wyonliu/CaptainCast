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
# 船长原语速 0.82-0.95，x1.05 → 实际 0.86-1.0，自然不急促
# 麦洛 x1.0 保持原速
CAPTAIN_SPEED_MULT = float(os.getenv('CAPTAIN_SPEED_MULT', '1.05'))
MELODY_SPEED_MULT  = float(os.getenv('MELODY_SPEED_MULT',  '1.0'))

# 麦洛音量补偿（dB，合并阶段应用，不需重新TTS）
# 麦洛声音克隆音源偏小，+4dB 与船长平衡
MELODY_VOL_DB = float(os.getenv('MELODY_VOL_DB', '4.0'))


def get_ep() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == '--ep' and i + 1 < len(sys.argv):
            return sys.argv[i + 1].zfill(3)
    eps = sorted(Path("episodes").glob("ep*/input/script.md"))
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


def tts(text, voice_id, speed, out_path, retries=3):
    """调用 MiniMax TTS，带重试（3次）和更长超时（120s）"""
    import json as _json
    for attempt in range(1, retries + 1):
        try:
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
                timeout=120
            )
            data = _json.loads(resp.content.decode("utf-8"))
            if data.get("base_resp", {}).get("status_code") != 0:
                print(f"  ✗ {data.get('base_resp',{}).get('status_msg', data)}")
                return False
            audio_hex = data.get("data", {}).get("audio", "")
            if not audio_hex:
                print(f"  ✗ 未返回音频")
                return False
            Path(out_path).write_bytes(bytes.fromhex(audio_hex))
            return True
        except Exception as e:
            if attempt < retries:
                print(f"  ⚠️  第{attempt}次失败({type(e).__name__})，3秒后重试...")
                time.sleep(3)
            else:
                print(f"  ✗ 连续{retries}次失败: {e}")
                return False
    return False


def main():
    if not MM_KEY or MM_KEY.startswith("sk-api-你"):
        print("❌ 请先在 .env 填入 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID")
        return

    ep = get_ep()
    script_path = Path(f"episodes/ep{ep}/input/script.md")
    if not script_path.exists():
        print(f"❌ 未找到 {script_path}")
        return

    script = parse_script(script_path)
    if not script:
        print(f"❌ script.md 中未找到对话行（格式：[船长 speed=0.95] 文本）")
        return

    seg_dir = Path(f"episodes/ep{ep}/output/audio_segments")
    seg_dir.mkdir(parents=True, exist_ok=True)
    final = Path(f"episodes/ep{ep}/output/audio_podcast.mp3")

    print(f"🎙  EP.{ep} 声音合成，共 {len(script)} 段\n")
    seg_files = []
    for i, (role, speed, text) in enumerate(script):
        voice_id = CAP_ID if role == "captain" else MEL_ID
        label = "船长" if role == "captain" else "麦洛"
        # 应用全局速度倍乘器（上限 2.0）
        mult = CAPTAIN_SPEED_MULT if role == "captain" else MELODY_SPEED_MULT
        actual_speed = round(min(2.0, speed * mult), 3)
        out = seg_dir / f"seg_{i:02d}_{role}.mp3"
        # 断点续传：跳过已存在的有效段
        if out.exists() and out.stat().st_size > 1024:
            seg_files.append(out)
            print(f"[{i+1:02d}/{len(script)}] ⏭️  已存在，跳过: {out.name} ({out.stat().st_size//1024} KB)")
            continue
        print(f"[{i+1:02d}/{len(script)}] {label}  x{mult}={actual_speed}  {text[:40]}...")
        if tts(text, voice_id, actual_speed, out):
            seg_files.append(out)
            print(f"  ✅ {out.stat().st_size//1024} KB")
        time.sleep(0.5)

    if not seg_files:
        print("❌ 没有成功的音频段")
        return

    print(f"\n🔗 合并 {len(seg_files)} 段（麦洛音量 +{MELODY_VOL_DB}dB）...")
    try:
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=700)
        combined = AudioSegment.empty()
        for f in seg_files:
            seg = AudioSegment.from_mp3(str(f))
            # 麦洛段根据文件名识别，应用音量补偿
            if "_melody.mp3" in f.name and MELODY_VOL_DB != 0:
                seg = seg + MELODY_VOL_DB
            combined += seg + silence
        combined.export(str(final), format="mp3", bitrate="128k")
        mins = len(combined) / 1000 / 60
        mb = final.stat().st_size // 1024 // 1024
        print(f"✅ {final}  {mins:.1f}分钟 / {mb}MB")

        # 生成 64k 压缩版 → 直接到 media/ 供 GitHub Pages + 微信用
        final_64k = Path(f"media/ep{ep}_podcast_64k.mp3")
        final_64k.parent.mkdir(parents=True, exist_ok=True)
        combined.export(str(final_64k), format="mp3", bitrate="64k")
        kb = final_64k.stat().st_size // 1024
        print(f"✅ {final_64k}  {kb} KB（GitHub Pages / 微信上传用）")
    except ImportError:
        print("⚠️  pip install pydub 后再合并，各段已在:", seg_dir)


if __name__ == "__main__":
    main()
