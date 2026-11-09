import json, subprocess, os, sys
import numpy as np
from scipy.io import wavfile
os.chdir(os.environ["WORK"])
SR = 44100
tl = json.load(open("out/timeline.json"))
T = tl["T0"]; END = tl["END"]; ls = {int(k): v for k, v in tl["ls"].items()}; TR = tl["T_REVEAL"]
def rd(p):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)
def wr(p, a): wavfile.write(p, SR, a.astype(np.float32))
def env(x):
    hop = int(SR * .01); n = len(x) // hop
    return np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)), hop
mix = np.zeros(int(END * SR) + SR)
def add(name, t, mode, g):
    x = rd(f"sfx/{name}.wav"); e, hop = env(x); e = np.convolve(e, np.ones(3) / 3, "same")
    a = int(np.argmax(e)) * hop if mode == "peak" else int(np.argmax(e > e.max() * 0.12)) * hop
    st = int(t * SR) - a
    if st < 0: x = x[-st:]; st = 0
    x = x / (np.abs(x).max() + 1e-9) * g
    end = min(len(mix), st + len(x)); mix[st:end] += x[:end - st]
    print(f"{name:12s} {mode:5s} at {t:6.2f}")
add("呼_转场音效", 0.10, "peak", 0.40)
add("咻的一声", tl["t_line2"], "peak", 0.50)
add("砰_拳击", T["S02"] + 0.00, "onset", 0.45)
add("齿轮_0.36", T["S02"] + 0.10, "onset", 0.45)
add("字幕音效_嘭", tl["t_key"], "onset", 0.50)
add("嗖_转场2", T["S05"] - 0.04, "peak", 0.55)
add("砰_拳击", T["S06"] + 0.02, "onset", 0.45)
add("呼_转场音效", T["S07"] - 0.04, "peak", 0.50)
add("重击_短促", tl["tf9"], "onset", 0.30)
add("仙尘音效", TR - 0.04, "peak", 0.65); add("重击_短促", TR, "onset", 0.45)
add("嗖_转场1", T["S12"] - 0.04, "peak", 0.50)
add("咻的一声", T["G1"] - 0.04, "peak", 0.55); add("冲击_带低频", T["G1"] + 0.05, "onset", 0.50)
add("字幕音效_嘭", tl["t_d"], "onset", 0.45)
add("砰_拳击", T["S16"] + 0.00, "onset", 0.40)
add("呼_转场音效", T["S18"] - 0.04, "peak", 0.50)
mix = mix[:int(END * SR)]; pk = np.abs(mix).max()
if pk > 0.95: mix = mix / pk * 0.95
wr("out/sfx.wav", mix)
vo = np.zeros(int(END * SR) + SR)
for i in range(1, 20):
    x = rd(f"vo/{i:02d}.wav"); st = int(ls[i] * SR); vo[st:st + len(x)] += x
vo = vo[:int(END * SR)]; vo = vo / np.abs(vo).max() * 0.85; wr("out/vo.wav", vo)
BAR = 1.705; DROP = 17.95
m = round(TR / BAR)
while DROP - m * BAR < 0: m -= 1
SS = DROP - m * BAR; ratio = (DROP - SS) / TR
print("bgm start", round(SS, 3), "bars", m, "atempo", round(ratio, 4), "reveal", round(TR, 2))
assert 0.96 < ratio < 1.04
flt = (f"[2:a]atempo={ratio:.5f},aformat=sample_rates=44100:channel_layouts=stereo,"
       f"volume='if(lt(t,2.0),0.30,if(lt(t,{TR - 0.04:.3f}),0.5,0.85))':eval=frame,afade=t=in:st=0:d=0.3,afade=t=out:st={END - 1.5:.3f}:d=1.5,atrim=0:{END:.3f}[bgm];"
       "[0:a]asplit[vo1][vo2];[bgm][vo1]sidechaincompress=threshold=0.04:ratio=3:attack=20:release=350[bgd];"
       "[vo2]aformat=channel_layouts=stereo[vos];[1:a]aformat=channel_layouts=stereo[sfx];"
       f"[vos][sfx][bgd]amix=inputs=3:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=9,atrim=0:{END:.3f}[a]")
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", "out/vo.wav", "-i", "out/sfx.wav", "-ss", f"{SS}", "-i", "bgm/full.wav",
                "-filter_complex", flt, "-map", "[a]", "-ar", "44100", "out/audio.wav"], check=True)
N = "CG014_视觉张力_成片_v1.mp4"
subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", "out/video_noaudio.mp4", "-i", "out/audio.wav", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "out/" + N], check=True)
print("mixed", N)
