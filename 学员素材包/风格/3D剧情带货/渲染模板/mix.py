# 3D 剧情带货 · 混音并合成成片：配音 + 真实音效 + BGM（爆点对产品登场）+ 闪避 + -14 LUFS，再和画面合成
# 用法：python3 mix.py 项目文件夹 [成片名]
# 要先运行 render.py（会生成 out/marks.json 和 out/video_noaudio.mp4）
# 项目文件夹里：vo/01.wav、02.wav…（处理后的逐句配音，序号从 1 开始）、bgm/ 下的音乐文件
import sys, os, json, subprocess, numpy as np
from scipy.io import wavfile

SR = 48000
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
WORK = os.path.abspath(args[0]); OUT = os.path.join(WORK, "out")
FINAL = args[1] if len(args) > 1 else "成片_v1.mp4"
HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.environ.get("PACK") or os.path.abspath(os.path.join(HERE, "..", "..", ".."))   # 学员素材包
SFXDIR = os.path.join(PACK, "音效库")
CFG = json.load(open(os.path.join(WORK, "project.json"), encoding="utf-8"))
M = json.load(open(os.path.join(OUT, "marks.json"), encoding="utf-8")); END = M["END"]; GAP = M["GAP"]
T = {s["name"]: s for s in M["shots"]}; n = int(END * SR)
CACHE = os.path.join(OUT, "_cache"); os.makedirs(CACHE, exist_ok=True)

def load(path, ch=1):
    o = os.path.join(CACHE, os.path.basename(path).rsplit(".", 1)[0] + f"_{ch}.wav")
    if not os.path.exists(o):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", path, "-ar", str(SR), "-ac", str(ch), o], check=True)
    _, x = wavfile.read(o); return x.astype(np.float32) / 32768

def peak(x):  # 音效最响处的位置，用来和画面节拍对齐
    hop = int(SR * .01); m = len(x) // hop
    e = np.sqrt((x[:m * hop].reshape(m, hop) ** 2).mean(1)); return int(np.argmax(np.convolve(e, np.ones(3) / 3, "same"))) * hop

sfx = np.zeros(n + SR, np.float32); LOG = []
def add(name, t, g):
    p = os.path.join(SFXDIR, name)
    if not os.path.exists(p): print("[提示] 音效文件不存在，已跳过：", name); return
    x = load(p); x = x / (np.abs(x).max() + 1e-9) * g; st = int(t * SR) - peak(x)
    if st < 0: x = x[-st:]; st = 0
    e = min(len(sfx), st + len(x)); sfx[st:e] += x[:e - st]; LOG.append((round(t, 2), name, g))

# ---- 转场与音效成对设计（默认映射，音效都来自素材包 音效库；硬切不配）----
ENTER = {"zoom": ("咻的一声.wav", .45), "hwhip": ("嗖_转场1.wav", .55), "white": ("仙尘音效.wav", .5),
         "push": ("嗖_转场2.wav", .6), "open": ("冲击_带低频.wav", .6), "black": ("重击_短促.wav", .45),
         "longwhite": ("仙尘音效.wav", .7)}
for s in M["shots"]:
    t0, en = s["t0"], s["enter"]
    if en in ENTER:
        f, g = ENTER[en]; add(f, t0 + (0.02 if en in ("open", "black") else 0), g)
    if en == "longwhite": add("重击_短促.wav", t0 + 0.04, .7)
    for x in s.get("sfx", []):                       # 镜头里自定义音效：{"file":..., "at": 相对镜头起点的秒, "gain": 0.6}
        add(x["file"], t0 + x.get("at", 0.0), x.get("gain", 0.6))
for sh in CFG["shots"]:                              # 贴卡出现配“叮”，大数字出现配“嘭”
    t0 = T[sh["name"]]["t0"]
    if sh.get("card"): add("叮_收银机提示音1.wav", t0 + sh["card"].get("delay", 0.15) + 0.05, .5)
    if sh.get("design"): add("字幕音效_嘭.wav", t0 + sh["design"].get("delay", 0.4) + 0.05, .55)
    if sh.get("arrow"): add("重击_短促.wav", t0 + 0.3, .6)
    if sh.get("title"): add("咻的一声.wav", t0 + 0.05, .35)                                   # 干货：钩子标题滑入
    if sh.get("numcard"): add("字幕音效_嘭.wav", t0 + sh["numcard"].get("delay", 0.3) + 0.05, .5)   # 数字卡弹出
    for kw in sh.get("keywords", []):                                                          # 关键词弹出（"sound": false 可关掉）
        if kw.get("sound", True): add("字幕音效_嘭.wav", t0 + kw.get("at", 0.5) + 0.05, .4)
sfx = sfx[:n]; fade = int(.5 * SR); sfx[-fade:] *= np.linspace(1, 0, fade)

# ---- 配音：把 vo/01.wav… 按 render.py 的时间轴摆好 ----
vo = np.zeros(n, np.float32); cnt = 0
for i, (a, b) in enumerate(M["seg"]):
    p = os.path.join(WORK, "vo", f"{i + 1:02d}.wav")
    if not os.path.exists(p): continue
    x = load(p); st = int(a * SR); e = min(n, st + len(x)); vo[st:e] += x[:e - st]; cnt += 1
if cnt:
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.85
else:
    print("[提示] 没有找到 vo/*.wav，按无配音预览混音")
hop = int(SR * .02); m = n // hop
env = np.sqrt((vo[:m * hop].reshape(m, hop) ** 2).mean(1)); act = (env > 0.02).astype(np.float32)
act = np.convolve(act, np.ones(6) / 6, "same"); rel = np.copy(act)
for i in range(1, len(rel)): rel[i] = max(act[i], rel[i - 1] - hop / SR / 0.25)   # 说话时压 BGM 和音效，释放 0.25s
act = np.repeat(rel, hop)[:n]; act = np.pad(act, (0, n - len(act)))

# ---- BGM：从第 1 秒到结尾；爆点对到 drop_shot 镜头开头后 0.1 秒（拼整小节 + 微调速）----
bg = np.zeros((n, 2), np.float32); DT = None
B = CFG.get("bgm")
if B and os.path.exists(os.path.join(WORK, B["file"])):
    song = load(os.path.join(WORK, B["file"]), ch=2)
    if "bar" in B and "drop" in B and B.get("drop_shot") in T:
        BAR, DROP = B["bar"], B["drop"]; DT = T[B["drop_shot"]]["t0"] + 0.1
        kk = int(round((DT - DROP) / BAR)); ratio = (DROP + kk * BAR) / DT; Q = DROP - 2 * BAR
        loop = song[int((Q - 4 * BAR) * SR):int(Q * SR)]
        if kk >= 0:
            ext = np.concatenate([loop] * (kk // 4 + 1))[:int(kk * BAR * SR)]
            a1 = np.concatenate([song[:int(Q * SR)], ext]); a2 = song[int(Q * SR):].copy()
        else:
            a1 = song[:int((Q + kk * BAR) * SR)].copy(); a2 = song[int(Q * SR):].copy()
        cf = int(.03 * SR); w = np.linspace(0, 1, cf)[:, None]; a1[-cf:] = a1[-cf:] * (1 - w) + a2[:cf] * w
        song = np.concatenate([a1, a2[cf:]])
        wavfile.write(os.path.join(CACHE, "bgm_sp.wav"), SR, (np.clip(song, -1, 1) * 32767).astype(np.int16))
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", os.path.join(CACHE, "bgm_sp.wav"), "-af", f"atempo={ratio:.5f}",
                        "-ar", str(SR), os.path.join(CACHE, "bgm_t.wav")], check=True)
        _, song = wavfile.read(os.path.join(CACHE, "bgm_t.wav")); song = song.astype(np.float32) / 32768
        print("BGM 爆点对齐到", round(DT, 2), "秒，整小节", kk, "个，变速", round(ratio, 4))
    song = song / (np.abs(song).max() + 1e-9)
    if len(song) < n: song = np.concatenate([song] * (n // len(song) + 1))   # 不够长就循环
    bg = song[:n].copy()
    gain = np.where(np.arange(n) / SR < (DT or 0) - 0.05, 0.32, 0.45).astype(np.float32)
    f2 = int(2 * SR); gain[-f2:] *= np.linspace(1, 0, f2); gain[:int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
    bg = bg * (gain * (1 - 0.45 * act))[:, None]
else:
    print("[提示] 没有配置 BGM（project.json 里的 bgm.file），成片无背景音乐")

mix = vo[:, None] + (sfx * 0.9 * (1 - 0.62 * act))[:, None] + bg
raw = os.path.join(OUT, "mix_raw.wav"); wavfile.write(raw, SR, (np.clip(mix, -1, 1) * 32767).astype(np.int16))

# ---- 响度：两遍 loudnorm 到 -14 LUFS，再限幅 ----
r = subprocess.run(["ffmpeg", "-nostdin", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
j = json.loads(r[r.rindex("{"):r.rindex("}") + 1])
ln = os.path.join(OUT, "audio_ln.wav"); au = os.path.join(OUT, "audio.wav")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", raw, "-af",
                f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
                f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true", "-ar", str(SR), ln], check=True)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", ln, "-af", "alimiter=limit=0.84:level=false", au], check=True)

# ---- 合成成片：1080x1920 H.264 约 4 Mbps，AAC 192k 48kHz 立体声 ----
final = os.path.join(OUT, FINAL)
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", os.path.join(OUT, "video_noaudio.mp4"), "-i", au,
                "-c:v", "libx264", "-preset", "medium", "-b:v", "4M", "-maxrate", "5M", "-bufsize", "8M", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", final], check=True)
json.dump(dict(sfx=LOG, drop_target=DT), open(os.path.join(OUT, "sfx_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("音效", len(LOG), "个；成片：", final)
print("质检请再跑：ffmpeg -i", final, "-af ebur128 -f null -   （整体应约 -14 LUFS）")
