"""学员环境检查：
  剪辑环境（Claude 渲染的地方）：python3 check_env.py
  配音三项（必须在学员自己的电脑上跑）：python3 check_env.py --only-tts --test-tts
原说明：运行  python3 check_env.py  （可加 --test-tts 真实合成一句配音）
只检查“有没有”，不会打印任何密钥内容。"""
import os, sys, shutil, subprocess, glob
ok_all = True
def line(ok, name, tip=""):
    global ok_all
    if not ok: ok_all = False
    print(("[OK]   " if ok else "[缺失] ") + name + ("" if ok else "  -> " + tip))
HERE = os.path.dirname(os.path.abspath(__file__)); PACK = os.path.dirname(HERE)
ONLY_TTS = "--only-tts" in sys.argv   # 在学员自己电脑上只检查配音三项，把输出贴给 Claude
if not ONLY_TTS:
  print("== 1. 基础工具 ==")
  line(sys.version_info >= (3, 8), "Python 3.8+", "安装 Python 3")
  for exe in ("ffmpeg", "ffprobe"): line(shutil.which(exe) is not None, exe, "安装 ffmpeg 并加入 PATH")
  for mod in ("numpy", "PIL", "scipy"):
      try: __import__(mod); line(True, "Python 库 " + mod)
      except Exception: line(False, "Python 库 " + mod, "pip install numpy pillow scipy")
  print("== 2. 字体 ==")
  font = os.environ.get("FONT_PATH", "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc")
  line(os.path.exists(font), "中文粗体字体 " + font, "安装 Noto Sans CJK SC Black，或设置环境变量 FONT_PATH 指向它")
  emo = os.environ.get("EMOJI_FONT", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
  line(os.path.exists(emo), "彩色 emoji 字体 " + emo, "安装 Noto Color Emoji，或设置 EMOJI_FONT（不装则字幕里的 emoji 不显示）")
  print("== 3. 素材包文件 ==")
  for f in ("huazi.py", "transitions.py", "sfxmix.py", "gridgrp.py", "build.py", "范例_渲染_CG014.py", "范例_混音_CG014.py"):
      line(os.path.exists(os.path.join(HERE, f)), "脚本/" + f, "重新解压学员素材包")
  need = ["呼_转场音效", "咻的一声", "砰_拳击", "齿轮_0.36", "字幕音效_嘭", "重击_短促", "仙尘音效", "嗖_转场1", "嗖_转场2", "冲击_带低频", "叮_收银机提示音1"]
  for n in need: line(os.path.exists(os.path.join(PACK, "音效库", n + ".wav")), "音效 " + n, "把同名 wav 放进 音效库/")
  line(bool(glob.glob(os.path.join(PACK, "背景", "*.mp4"))), "黑色动态网格背景视频", "放进 背景/")
  line(os.path.exists(os.path.join(PACK, "镜头模板库", "镜头模板库_v0.md")), "镜头模板库", "重新解压学员素材包")
  print("== 4. 背景音乐（自备）==")
  print("[提示] 背景音乐不在素材包里，请准备一首有明显“爆点”的无版权或已授权音乐（mp3/wav）。")
print("== 5. 配音 API（火山语音合成，自备账号）==")
for k, tip in (("VOLC_APPID", "火山控制台里的 AppID"), ("VOLC_TOKEN", "火山控制台里的 Access Token"), ("VOLC_SPEAKER_ID", "你自己克隆的声音的 Speaker ID")):
    line(bool(os.environ.get(k)), "环境变量 " + k, "设置 " + k + "（" + tip + "）")
if "--test-tts" in sys.argv:
    out = os.path.join(HERE, "_tts_test.mp3")
    r = subprocess.run([sys.executable, os.path.join(HERE, "配音示例_volc_tts.py"), "--text", "你好，这是一句测试配音。", "--output", out])
    line(r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 2000, "真实合成一句配音", "检查 AppID / Token / Speaker ID 是否正确、声音是否已在火山开通")
else:
    print("[提示] 想真实测一句配音：python3 check_env.py --test-tts")
print("\n结论：" + ("全部就绪，可以开工。" if ok_all else "有缺失项，请先补上面标 [缺失] 的。配音没配好时，可以先做分镜、出图、写 H3 提示词，配音和剪辑放后面。"))
