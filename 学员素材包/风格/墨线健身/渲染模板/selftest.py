# 墨线健身 · 环境自检：自己生成示例人物图、配音和音乐，跑一遍「渲染 + 混音」，确认环境能出片
# 用法：python3 selftest.py        看到「自检通过」才往下做正式项目
# 可选环境变量：PACK（素材包位置）、KEEP（把示例成片复制到这个文件夹）、FONT_PATH（中文粗体字体文件）
import os, sys, json, math, shutil, subprocess, tempfile, re
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.environ.get("PACK") or os.path.abspath(os.path.join(HERE, "..", "..", ".."))
need = ["咻的一声.wav", "嗖_转场1.wav", "嗖_转场2.wav", "仙尘音效.wav", "重击_短促.wav", "字幕音效_嘭.wav", "叮_收银机提示音1.wav"]
miss = [f for f in need if not os.path.exists(os.path.join(PACK, "音效库", f))]
if miss: sys.exit("音效库不完整，缺：%s（素材包位置：%s）。请重新下载完整的学员素材包。" % ("、".join(miss), PACK))
for tool in ("ffmpeg", "ffprobe"):
    if not shutil.which(tool): sys.exit("找不到 %s，请先安装 ffmpeg" % tool)

def stick(path, pose):
    im = Image.new("RGB", (900, 900), (0, 0, 0)); d = ImageDraw.Draw(im); W = (240, 240, 240); Y = (255, 214, 0)
    d.ellipse((410, 120, 490, 200), outline=W, width=8)                      # 头
    d.line((450, 200, 450, 460), fill=W, width=10)                           # 躯干
    a = [(450, 250, 330, 380), (450, 250, 570, 380)] if pose != 2 else [(450, 250, 330, 160), (450, 250, 570, 160)]
    for x1, y1, x2, y2 in a: d.line((x1, y1, x2, y2), fill=Y, width=10)      # 手臂（黄 = 发力）
    l = [(450, 460, 380, 700), (450, 460, 520, 700)] if pose != 3 else [(450, 460, 330, 640), (450, 460, 590, 640)]
    for x1, y1, x2, y2 in l: d.line((x1, y1, x2, y2), fill=W, width=10)
    im.save(path)

def tone(path, dur, f0):
    sr = 48000; t = np.arange(int(dur * sr)) / sr
    x = 0.4 * np.sin(2 * math.pi * f0 * t) * (0.6 + 0.4 * np.sin(2 * math.pi * 3.5 * t)); x *= np.minimum(1, np.minimum(t / 0.02, (dur - t) / 0.03))
    wavfile.write(path, sr, (x * 32767).astype(np.int16))

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0: sys.exit("运行失败：%s\n%s\n%s" % (" ".join(cmd), r.stdout[-800:], r.stderr[-1500:]))
    return r

work = tempfile.mkdtemp(prefix="inkselftest_")
try:
    os.makedirs(os.path.join(work, "imgs")); os.makedirs(os.path.join(work, "vo")); os.makedirs(os.path.join(work, "bgm"))
    for i in (1, 2, 3): stick(os.path.join(work, "imgs", "pose%d.png" % i), i)
    shutil.copy(os.path.join(HERE, "project.example.json"), os.path.join(work, "project.json"))
    cfg = json.load(open(os.path.join(work, "project.json"), encoding="utf-8")); dur_lines = []
    for i, l in enumerate(cfg["lines"]):
        d = len(re.sub(r"[，。、！？：；]", "", l)) / 7.0 + 0.1; tone(os.path.join(work, "vo", "%02d.wav" % (i + 1)), d, 180 + 25 * i); dur_lines.append("%d %.3f" % (i + 1, d))
    open(os.path.join(work, "vo", "dur.txt"), "w").write("\n".join(dur_lines))
    sr = 48000; t = np.arange(sr * 40) / sr; bgm = 0.5 * np.sin(2 * math.pi * 110 * t) * (0.7 + 0.3 * np.sin(2 * math.pi * 2 * t))
    wavfile.write(os.path.join(work, "bgm", "bgm.wav"), sr, (bgm * 32767).astype(np.int16))
    cfg["bgm"] = {"file": "bgm/bgm.wav"}; json.dump(cfg, open(os.path.join(work, "project.json"), "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ, PACK=PACK)
    print("渲染中…（约一两分钟）")
    r = run([sys.executable, os.path.join(HERE, "render.py"), work, "--dur", "vo/dur.txt"], env=env); print(r.stdout.strip())
    r = run([sys.executable, os.path.join(HERE, "mix.py"), work, "selftest.mp4"], env=env); print(r.stdout.strip())
    out = os.path.join(work, "out", "selftest.mp4")
    info = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", out]).stdout.strip().replace("\n", " | ")
    lu = run(["ffmpeg", "-nostdin", "-i", out, "-af", "ebur128", "-f", "null", "-"]).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", lu)[-1])
    if "1920,1080" not in info: sys.exit("成片尺寸不对：" + info)
    if not -16.5 < lufs < -11.5: sys.exit("响度异常：%.1f LUFS（应约 -14）" % lufs)
    if os.environ.get("KEEP"): shutil.copy(out, os.path.join(os.environ["KEEP"], "ink_selftest.mp4"))
    print("成片信息：", info, "| 响度 %.1f LUFS" % lufs)
    print("\n自检通过：墨线渲染和混音环境正常，可以开始做正式项目。")
finally:
    shutil.rmtree(work, ignore_errors=True)
