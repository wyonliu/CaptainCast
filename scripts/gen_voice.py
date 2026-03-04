"""
CaptainCast · EP.001 声音合成
运行：python scripts/gen_voice.py
依赖：pip install requests python-dotenv pydub
"""
import requests, os, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
MM_KEY   = os.getenv('MINIMAX_API_KEY')
MM_GROUP = os.getenv('MINIMAX_GROUP_ID')
CAP_ID   = os.getenv('CAPTAIN_VOICE_ID', 'captain_captaincast')
MEL_ID   = os.getenv('MELODY_VOICE_ID',  'melody_captaincast')

SEG_DIR = Path("audio/output/ep001_segments")
SEG_DIR.mkdir(parents=True, exist_ok=True)
FINAL   = Path("audio/output/ep001_podcast.mp3")

SCRIPT = [
    ("captain", 0.95, "欢迎来到CaptainCast，我是船长。这是我们的第一期节目。我不打算用一个很酷的开头跟你说宇宙有多大。我想先跟你说一个人的故事。一个爸爸的故事。"),
    ("captain", 0.90, "凌晨两点。窗外是农田，偶尔有犬吠。他坐在电脑前，口袋里的钱是借来的——用来发完最后一个月的工资。但他在写一个故事。不是为了卖钱，是为了他12岁的女儿。"),
    ("captain", 0.90, "她叫米莱。喜欢打击乐，养了两只大乌龟，梦想是做未来世界设计师。他想：如果什么都没有了，但我能给她留下一个世界——那个世界，该长什么样？"),
    ("melody", 1.05, "爸爸，你说的那个世界，我也想去。山海是什么？是游戏吗？"),
    ("captain", 0.90, "不是游戏。是一个和现实等重的存在。你在里面的眼泪是真的，你建立的友情是真的，你做出的选择，会有真正的后果。"),
    ("melody", 1.05, "麦洛是我吗？那她知道自己是谁吗？"),
    ("captain", 0.88, "不知道。她进去的时候，不知道这里是哪里，只知道——这里美得像梦，又疼得像真实。那正是我设计它时的心情。"),
    ("captain", 0.95, "好，现在我要跟你说一个概念，叫做——灵机。听起来像玄学，其实是硬核物理。你知道AI的随机数是假的吗？它叫伪随机——给定同样的输入，输出是可以被预测的。但人类大脑，存在量子相干态，能产生真正的随机性。"),
    ("melody", 1.10, "等一下爸，我听懂了一半。意思是……人类会做一些AI永远算不出来的事情？"),
    ("captain", 0.92, "对。比如——你明知道放弃是最优解，但你选择了死磕。这一秒，宇宙里，多了一个以前从来没有出现过的新信息。这就是灵机：人类的非理性，是宇宙唯一的进化发动机。"),
    ("melody", 1.00, "所以……我的眼泪不是软弱？我的倔强不是Bug？爸，我每次被说太感性了……"),
    ("captain", 0.90, "你的非理性，才是你最贵的东西。记住这句话。"),
    ("captain", 0.85, "在这个宇宙里，有一群高维文明，一直在收割灵机。他们在宇宙里建了一个牧场。牧场里，养着人类。制造灾难，制造战争，制造分离——收割极端情绪产生的高纯度灵机，用作燃料。"),
    ("melody", 1.10, "等等——所以人类是……作物？爸，这个设定也太黑暗了吧！"),
    ("captain", 0.85, "但这个故事，不是一个打败坏人的故事。第二部末尾，当人类用灵机共鸣撑爆了收割程序，以为赢了。然后那个高维文明的代言人，出现在全球的天空。"),
    ("captain", 0.82, "你们以为我们是收割者。错了。我们，是点火者。"),
    ("melody", 0.95, "点火者……他们不是坏人？他们是……用自己的牺牲，给人类点了一把火？"),
    ("captain", 0.85, "是的。他们太聪明了，聪明到再也产生不了新的变量。唯一的出路，是找到一个足够混乱、足够有爱、足够能犯错的文明——亲手制造它的痛苦，直到它燃烧起来。听起来是不是很熟悉？"),
    ("melody", 0.90, "……爸，你说的是你自己吗？"),
    ("captain", 0.85, "故事的最后，在距今一万五千年之后——麦洛和船长，坐在一棵树下。她靠在父亲的肩膀上。什么都没说。但那一刻，宇宙里每一个有意识的存在，都感受到了那一刻的温暖。欢迎来到CaptainCast，关注我们，下一期见。"),
]

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
    print(f"🎙  EP.001 声音合成，共 {len(SCRIPT)} 段\n")
    seg_files = []
    for i, (role, speed, text) in enumerate(SCRIPT):
        voice_id = CAP_ID if role == "captain" else MEL_ID
        label = "船长" if role == "captain" else "麦洛"
        out = SEG_DIR / f"seg_{i:02d}_{role}.mp3"
        print(f"[{i+1:02d}/{len(SCRIPT)}] {label}  {text[:35]}...")
        if tts(text, voice_id, speed, out):
            seg_files.append(out)
            print(f"  ✅ {out.stat().st_size//1024} KB")
        time.sleep(0.5)
    print(f"\n🔗 合并 {len(seg_files)} 段...")
    try:
        from pydub import AudioSegment
        silence = AudioSegment.silent(duration=700)
        combined = sum([AudioSegment.from_mp3(str(f)) + silence for f in seg_files], AudioSegment.empty())
        combined.export(str(FINAL), format="mp3", bitrate="128k")
        print(f"✅ {FINAL}  {len(combined)/1000/60:.1f}分钟 / {FINAL.stat().st_size//1024//1024}MB")
    except ImportError:
        print("⚠️  pip install pydub 后再合并，各段已在:", SEG_DIR)

if __name__ == "__main__":
    main()
