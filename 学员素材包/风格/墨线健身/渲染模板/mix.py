# 墨线健身 · 混音并合成成片：配音 + 真实音效 + BGM（人声时压低）+ -14 LUFS，再和画面合成
# 用法：python3 mix.py 项目文件夹 [成片名]
# 要先运行 render.py（会生成 out/marks.json 和 out/video_noaudio.mp4）
# 项目文件夹里：vo/01.wav、02.wav…（裁掉两端静音的逐句配音，序号从 1 开始）、bgm/ 下的音乐文件（可选）
import sys, os, json, subprocess, numpy as np
from scipy.io import wavfile

SR = 48000
args = sys.argv[1:]
if not args: sys.exit(__doc__)
WORK = os.path.abspath(args[0]); OUT = os.path.join(WORK, "out"); FINAL = args[1] if len(args) > 1 else "成片_v1.mp4"
HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.environ.get("PACK") or os.path.abspath(os.path.join(HERE, "..", "..", ".."))   # 学员素材包
SFXDIR = os.path.join(PACK, "音效库")
CFG = json.load(open(os.path.join(WORK, "project.json"), encoding="utf-8"))
M = json.load(open(os.path.join(OUT, "marks.json"), encoding="utf-8")); END = M["END"]
T = {s["name"]: s for s in M["shots"]}; n = int(END * SR)
CACHE = os.path.join(OUT, "_cache"); os.makedirs(CACHE, exist_ok=True)

def load(path, ch=1):
    o = os.path.join(CACHE, os.path.basename(path).rsplit(".", 1)[0] + f"_{ch}.wav")
    if not os.path.exists(o):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-ar", str(SR), "-ac", str(ch), o], check=True)
    _, x = wavfile.read(o); return x.astype(np.float32) / 32768

def peak(x):
    hop = int(SR * .01); m = len(x) // hop
    e = np.sqrt((x[:m * hop].reshape(m, hop) ** 2).mean(1)); return int(np.argmax(np.convolve(e, np.ones(3) / 3, "same"))) * hop

sfx = np.zeros(n + SR, np.float32); LOG = []
def add(name, t, g):
    p = os.path.join(SFXDIR, name)
    if not os.path.exists(p): print("[提示] 音效文件不存在，已跳过：", name); return
    x = load(p); x = x / (np.abs(x).max() + 1e-9) * g; st = int(t * SR) - peak(x)
    if st < 0: x = x[-st:]; st = 0
    e = min(len(sfx), st + len(x)); sfx[st:e] += x[:e - st]; LOG.append((round(t, 2), name, g))

# ---- 转场与音效成对设计（音效都来自素材包 音效库；稀疏、不重复）----
ENTER = {"slide": ("嗖_转场1.wav", .55), "zoom": ("咻的一声.wav", .45), "flash": ("仙尘音效.wav", .5), "dim": ("嗖_转场2.wav", .5)}
for s in M["shots"]:
    if s["enter"] in ENTER and s["t0"] > 0.05: add(*(ENTER[s["enter"]][0], s["t0"] + 0.02, ENTER[s["enter"]][1]))
for sh in CFG["shots"]:
    t0 = T[sh["name"]]["t0"]
    if sh.get("title"): add("重击_短促.wav", t0 + 0.1, .5)
    for lb in sh.get("labels", []):                       # 标签 pop 出现配“嘭”（"sound": false 可关掉）
        if lb.get("sound", True): add("字幕音效_嘭.wav", t0 + lb["at"] + 0.05, .4)
    if sh.get("inset"): add("叮_收银机提示音1.wav", t0 + sh["inset"]["at"] + 0.2, .45)   # 特写章弹出配“叮”
    for x in sh.get("sfx", []):                           # 自定义音效：{"file":..., "at": 相对镜头起点的秒, "gain": 0.6}
        add(x["file"], t0 + x.get("at", 0.0), x.get("gain", 0.6))
sfx = sfx[:n]; fade = int(.5 * SR); sfx[-fade:] *= np.linspace(1, 0, fade)

# ---- 配音：把 vo/01.wav… 按 render.py 的时间轴摆好 ----
vo = np.zeros(n, np.float32); cnt = 0
for i, (a, b) in enumerate(M["seg"]):
    p = os.path.join(WORK, "vo", f"{i + 1:02d}.wav")
    if not os.path.exists(p): continue
    x = load(p); st = int(a * SR); e = min(n, st + len(x)); vo[st:e] += x[:e - st]; cnt += 1
if cnt: vo = vo / (np.abs(vo).max() + 1e-9) * 0.85
else: print("[提示] 没有找到 vo/*.wav，按无配音预览混音")
hop = int(SR * .02); m = n // hop
env = np.sqrt((vo[:m * hop].reshape(m, hop) ** 2).mean(1)); act = (env > 0.02).astype(np.float32)
act = np.convolve(act, np.ones(6) / 6, "same"); rel = np.copy(act)
for i in range(1, len(rel)): rel[i] = max(act[i], rel[i - 1] - hop / SR / 0.25)
act = np.repeat(rel, hop)[:n]; act = np.pad(act, (0, n - len(act)))

# ---- BGM：从头播放，人声时自动压低，结尾淡出 ----
bg = np.zeros((n, 2), np.float32); B = CFG.get("bgm")
if B and os.path.exists(os.path.join(WORK, B["file"])):
    song = load(os.path.join(WORK, B["file"]), ch=2); song = song / (np.abs(song).max() + 1e-9)
    if len(song) < n: song = np.concatenate([song] * (n // len(song) + 1))
    gain = np.full(n, 0.4, np.float32); f2 = int(2 * SR); gain[-f2:] *= np.linspace(1, 0, f2); gain[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
    bg = song[:n].copy() * (gain * (1 - 0.5 * act))[:, None]
else:
    print("[提示] 没有配置 BGM（project.json 里的 bgm.file），成片无背景音乐")

mix = vo[:, None] + (sfx * 0.9 * (1 - 0.62 * act))[:, None] + bg
raw = os.path.join(OUT, "mix_raw.wav"); wavfile.write(raw, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))

# ---- 响度：两遍 loudnorm 到 -14 LUFS，再限幅 ----
r = subprocess.run(["ffmpeg", "-nostdin", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
j = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
ln = os.path.join(OUT, "audio_ln.wav"); au = os.path.join(OUT, "audio.wav")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-af",
                f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
                f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true", "-ar", str(SR), ln], check=True)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", ln, "-af", "alimiter=limit=0.84:level=false", au], check=True)

# ---- 合成成片：1920x1080 H.264，AAC 192k 48kHz 立体声 ----
final = os.path.join(OUT, FINAL)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", os.path.join(OUT, "video_noaudio.mp4"), "-i", au,
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", final], check=True)
json.dump(dict(sfx=LOG), open(os.path.join(OUT, "sfx_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("音效", len(LOG), "个；成片：", final)
print("质检请再跑：ffmpeg -i", final, "-af ebur128 -f null -   （整体应约 -14 LUFS）")
