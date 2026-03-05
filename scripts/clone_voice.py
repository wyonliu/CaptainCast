"""
CaptainCast · MiniMax 声音克隆脚本
用法：python3 scripts/clone_voice.py
会用 audio/melody-voice-0304.m4a 克隆麦洛新声音
克隆成功后自动更新 .env 中的 MELODY_VOICE_ID
"""
import requests, os, json, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MM_KEY   = os.getenv('MINIMAX_API_KEY')
MM_GROUP = os.getenv('MINIMAX_GROUP_ID')

# 新麦洛声音文件
AUDIO_FILE = Path("audio/melody-voice-0304.m4a")
NEW_VOICE_ID = "melody_captaincast_v2"

def upload_file():
    """第一步：上传音频文件，获取 file_id"""
    print(f"📤 第一步：上传音频文件获取 file_id...")
    url = f"https://api.minimax.chat/v1/files/upload?GroupId={MM_GROUP}"
    headers = {"Authorization": f"Bearer {MM_KEY}"}

    with open(AUDIO_FILE, "rb") as f:
        files = {"file": (AUDIO_FILE.name, f, "audio/mp4")}
        data  = {"purpose": "voice_clone"}
        resp = requests.post(url, headers=headers, files=files, data=data, timeout=120)

    print(f"   HTTP {resp.status_code}")
    try:
        result = json.loads(resp.content.decode("utf-8"))
    except Exception as e:
        print(f"❌ 响应解析失败: {e}\n   原始: {resp.text[:500]}")
        return None

    print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 成功时返回 file_id
    base = result.get("base_resp", {})
    if base.get("status_code") == 0:
        file_id = result.get("file", {}).get("file_id") or result.get("file_id")
        if file_id:
            print(f"   ✅ file_id = {file_id}")
            return str(file_id)
    # 有些版本直接在顶层
    file_id = result.get("file_id") or result.get("id")
    if file_id:
        print(f"   ✅ file_id = {file_id}")
        return str(file_id)

    print(f"❌ 上传失败: {base.get('status_msg', result)}")
    return None


def clone_voice():
    if not MM_KEY or MM_KEY.startswith("sk-api-你"):
        print("❌ 请先在 .env 填入 MINIMAX_API_KEY")
        return None

    if not AUDIO_FILE.exists():
        print(f"❌ 音频文件不存在: {AUDIO_FILE}")
        return None

    print(f"🎤 开始克隆麦洛声音")
    print(f"   音频文件: {AUDIO_FILE} ({AUDIO_FILE.stat().st_size // 1024} KB)")
    print(f"   目标 voice_id: {NEW_VOICE_ID}")
    print()

    # 先上传文件
    file_id_str = upload_file()
    if not file_id_str:
        return None

    print(f"\n🎙  第二步：用 file_id 克隆声音...")
    url = f"https://api.minimax.chat/v1/voice_clone?GroupId={MM_GROUP}"
    headers = {"Authorization": f"Bearer {MM_KEY}", "Content-Type": "application/json"}
    payload = {
        "voice_id": NEW_VOICE_ID,
        "file_id": int(file_id_str),   # 必须是整数！
        "need_noise_reduction": True,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    print(f"   HTTP {resp.status_code}")

    try:
        result = json.loads(resp.content.decode("utf-8"))
    except Exception as e:
        print(f"❌ 响应解析失败: {e}")
        print(f"   原始响应: {resp.text[:500]}")
        return None

    print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 判断成功
    base_resp = result.get("base_resp", {})
    status_code = base_resp.get("status_code", -1)
    status_msg  = base_resp.get("status_msg", "")

    if status_code == 0:
        voice_id = result.get("voice_id", NEW_VOICE_ID)
        print(f"\n✅ 克隆成功！voice_id = {voice_id}")
        return voice_id
    else:
        print(f"\n❌ 克隆失败: [{status_code}] {status_msg}")
        # 如果是 voice_id 已存在，直接用
        if status_code in (1004, 2004) or "already" in status_msg.lower() or "exist" in status_msg.lower():
            print(f"   (voice_id 已存在，直接使用: {NEW_VOICE_ID})")
            return NEW_VOICE_ID
        return None


def update_env(voice_id: str):
    """更新 .env 中的 MELODY_VOICE_ID"""
    env_path = Path(".env")
    if not env_path.exists():
        print("⚠️  .env 文件不存在")
        return

    content = env_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    updated = []
    found = False
    for line in lines:
        if line.startswith("MELODY_VOICE_ID="):
            updated.append(f"MELODY_VOICE_ID={voice_id}")
            found = True
        else:
            updated.append(line)

    if not found:
        updated.append(f"MELODY_VOICE_ID={voice_id}")

    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"✅ .env 已更新: MELODY_VOICE_ID={voice_id}")


def test_tts(voice_id: str):
    """用新 voice_id 合成一句测试音频"""
    print(f"\n🔊 测试新声音 TTS ({voice_id})...")
    url = f"https://api.minimax.chat/v1/t2a_v2?GroupId={MM_GROUP}"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {MM_KEY}", "Content-Type": "application/json"},
        json={
            "model": "speech-01-hd",
            "text": "爸爸，你说的那个世界，我也想去。山海是什么？",
            "stream": False,
            "voice_setting": {"voice_id": voice_id, "speed": 1.05, "vol": 1.0, "pitch": 0},
            "audio_setting": {"format": "mp3", "sample_rate": 44100}
        },
        timeout=60
    )
    data = json.loads(resp.content.decode("utf-8"))
    base = data.get("base_resp", {})
    if base.get("status_code") == 0:
        audio_hex = data.get("data", {}).get("audio", "")
        out = Path("audio/output/melody_test_new.mp3")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(bytes.fromhex(audio_hex))
        print(f"✅ 测试音频已保存: {out} ({out.stat().st_size // 1024} KB)")
        print(f"   请播放确认音质: open {out}")
    else:
        print(f"❌ TTS 测试失败: {base}")


if __name__ == "__main__":
    voice_id = clone_voice()
    if voice_id:
        update_env(voice_id)
        test_tts(voice_id)
        print(f"\n🎉 全部完成！")
        print(f"   下一步：python3 scripts/gen_voice.py --ep 001")
        print(f"         python3 scripts/gen_voice.py --ep 002")
    else:
        print("\n💡 如API克隆失败，也可手动上传到 platform.minimax.io 获取 voice_id，")
        print("   然后手动更新 .env 中的 MELODY_VOICE_ID")
