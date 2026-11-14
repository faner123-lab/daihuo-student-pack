# 自检：用合成的假素材跑一遍“渲染 + 混音”，确认你的电脑环境能出片。带货和干货两种示例都会跑。
# 用法：python3 selftest.py        （约 2–3 分钟，会在系统临时目录里生成测试项目，跑完自动清理）
import os, sys, json, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.environ.get("PACK") or os.path.abspath(os.path.join(HERE, "..", "..", ".."))
def run(cmd): subprocess.run(cmd, check=True)

# 先确认音效库在（转场和音效都靠它）
sfx_dir = os.path.join(PACK, "音效库")
need = ["仙尘音效.wav", "冲击_带低频.wav", "叮_收银机提示音1.wav", "咻的一声.wav", "嗖_转场1.wav", "嗖_转场2.wav", "字幕音效_嘭.wav", "重击_短促.wav"]
miss = [f for f in need if not os.path.exists(os.path.join(sfx_dir, f))]
if miss:
    sys.exit("音效库不完整，缺：" + "、".join(miss) + "\n请确认素材包里的「音效库」文件夹还在原位置（学员素材包/音效库），或设置环境变量 PACK 指向「学员素材包」文件夹。")
print("音效库完整：", sfx_dir)

def one(example):
    tmp = tempfile.mkdtemp(prefix="selftest_")
    try:
        cfg = json.load(open(os.path.join(HERE, example), encoding="utf-8"))
        for d in ("clips", "vo", "cards", "bgm"): os.makedirs(os.path.join(tmp, d))
        for i, sh in enumerate(cfg["shots"]):     # 假片段：彩色测试画面，6 秒
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=576x1024:r=30:d=6,hue=h={i*35}",
                 "-pix_fmt", "yuv420p", f"{tmp}/clips/{sh['name']}.mp4"])
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (800, 600), (240, 240, 240)); ImageDraw.Draw(im).rectangle((100, 100, 700, 500), fill=(200, 80, 60))
        im.save(tmp + "/cards/product.jpg")
        dur = []
        for i, line in enumerate(cfg["lines"]):    # 假配音：不同长度的正弦音
            d = round(0.4 + 0.1 * len(line), 2); dur.append(d)
            run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=f={200+i*20}:d={d}", "-ar", "48000", "-ac", "1", f"{tmp}/vo/{i+1:02d}.wav"])
        open(tmp + "/vo/dur.txt", "w").write("\n".join(f"{i+1} {d}" for i, d in enumerate(dur)))
        run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=110:d=45", "-ar", "44100", tmp + "/bgm/bgm.mp3"])
        json.dump(cfg, open(tmp + "/project.json", "w", encoding="utf-8"), ensure_ascii=False)
        env = dict(os.environ, PACK=PACK)
        subprocess.run([sys.executable, os.path.join(HERE, "render.py"), tmp, "--dur", "vo/dur.txt"], check=True, env=env)
        subprocess.run([sys.executable, os.path.join(HERE, "mix.py"), tmp, "selftest.mp4"], check=True, env=env)
        out = tmp + "/out/selftest.mp4"
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", out], capture_output=True, text=True).stdout
        print(f"\n[{example}] 通过，成片信息：", info.replace("\n", " | "))
        if os.environ.get("KEEP"): shutil.copy(out, os.path.join(os.environ["KEEP"], example.replace(".json", ".mp4")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

for ex in ("project.example.json", "project.example.fitness.json"):
    one(ex)
print("\n自检通过：渲染和混音环境正常（带货、干货两种都能出片），可以开始做正式项目。")
