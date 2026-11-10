# 自检：用合成的假素材跑一遍“渲染 + 混音”，确认你的电脑环境能出片。
# 用法：python3 selftest.py        （约 1–2 分钟，会在系统临时目录里生成测试项目，跑完自动清理）
import os, sys, json, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp(prefix="selftest_")
def run(cmd): subprocess.run(cmd, check=True)
try:
    cfg = json.load(open(os.path.join(HERE, "project.example.json"), encoding="utf-8"))
    os.makedirs(tmp + "/clips"); os.makedirs(tmp + "/vo"); os.makedirs(tmp + "/cards"); os.makedirs(tmp + "/bgm")
    for i, sh in enumerate(cfg["shots"]):     # 假片段：彩色测试画面，5 秒
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
    run([sys.executable, os.path.join(HERE, "render.py"), tmp, "--dur", "vo/dur.txt"])
    run([sys.executable, os.path.join(HERE, "mix.py"), tmp, "selftest.mp4"])
    out = tmp + "/out/selftest.mp4"
    info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", out], capture_output=True, text=True).stdout
    print("\n自检通过，成片信息：", info.replace("\n", " | "))
    print("渲染和混音环境正常，可以开始做正式项目。")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
