# 阿三参考 · 转场复刻样片：6 种转场 + 配对音效（音效库原声）
import os, sys, json, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

S = os.environ.get("WORK", ".")
D = S + "/stills"
OUT = f"{S}/trans"; FR = f"{OUT}/frames"; os.makedirs(FR, exist_ok=True)
W, H, FPS = 1280, 720, 30
FONT = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", 34, index=2)

def load(p):
    im = Image.open(p).convert("RGB"); r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r + .5), int(im.height * r + .5)), Image.BICUBIC)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((l, t, l + W, t + H))

def push(img, k, z0=1.0, z1=1.07):  # 镜头内慢推
    z = z0 + (z1 - z0) * k; w, h = int(W * z), int(H * z)
    im = img.resize((w, h), Image.BICUBIC); l, t = (w - W) // 2, (h - H) // 2
    return im.crop((l, t, l + W, t + H))

def motion(im, px, axis):  # 方向模糊（边缘延伸的箱式模糊，无重影）
    if px < 2: return im
    from scipy.ndimage import uniform_filter1d
    a = np.asarray(im, np.float32)
    a = uniform_filter1d(a, size=int(px), axis=axis, mode="nearest")
    a = uniform_filter1d(a, size=max(1, int(px * 0.5)), axis=axis, mode="nearest")
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def zoomblur(im, strength):  # 放射状推近模糊
    if strength < 0.01: return im
    a = np.zeros((H, W, 3), np.float32); n = 7
    for i in range(n):
        z = 1 + strength * i / (n - 1); w, h = int(W * z), int(H * z)
        r = im.resize((w, h), Image.BILINEAR); l, t = (w - W) // 2, (h - H) // 2
        a += np.asarray(r.crop((l, t, l + W, t + H)), np.float32)
    return Image.fromarray((a / n).clip(0, 255).astype(np.uint8))

def bright(im, b): return ImageEnhance.Brightness(im).enhance(b)
def eo(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3

shots = ["阿炎_S03_v2.png", "阿炎_S04_v1.png", "阿炎_S05_v1.png", "阿炎_S06_v1.png",
         "阿炎_S07_v1.png", "阿炎_S08_v1.png", "阿炎_S09_v1.png"]
imgs = [load(f"{D}/{s}") for s in shots]
SHOT = 1.7
# 每个转场：名称、进入时长、出场预糊时长、音效文件、音效对齐方式
TR = [
    ("甩镜糊入（竖向）", "vwhip", 0.35, "呼啸_1800_1800.wav", "peak"),
    ("推近缩放糊入", "zoom", 0.35, "呼啸_1795_1795.wav", "peak"),
    ("闪白糊入", "white", 0.35, "嗖_转场2.wav", "peak"),
    ("黑场亮起", "black", 0.45, "冲击_带低频.wav", "onset"),
    ("漏光扫过", "leak", 0.45, "嗖_转场1.wav", "peak"),
    ("横向甩糊（出+入）", "hwhip", 0.40, "呼啸_1797_1797.wav", "peak"),
]
frames_per_shot = int(SHOT * FPS)
idx = 0; cuts = []
for si, img in enumerate(imgs):
    tin = TR[si - 1] if si > 0 else None
    tout = TR[si] if si < len(TR) else None
    for f in range(frames_per_shot):
        t = f / FPS; k = f / frames_per_shot
        fr = push(img, k)
        # ---- 入场 ----
        if tin:
            name, kind, dur = tin[0], tin[1], tin[2]
            p = t / dur
            if p < 1:
                e = eo(p)
                if kind == "vwhip":
                    fr = motion(fr, 260 * (1 - e), 0); fr = bright(fr, 1 + 0.45 * (1 - e))
                elif kind == "zoom":
                    fr = push(img, 0, 1.30 - 0.30 * e, 1.30 - 0.30 * e)
                    fr = zoomblur(fr, 0.28 * (1 - e)); fr = bright(fr, 1 + 0.25 * (1 - e))
                elif kind == "white":
                    fr = fr.filter(ImageFilter.GaussianBlur(22 * (1 - e)))
                    fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 250, 240)), 0.75 * (1 - e))
                elif kind == "black":
                    fr = bright(fr, 0.0 if t < 0.1 else eo((t - 0.1) / (dur - 0.1)))
                elif kind == "leak":
                    pass  # 漏光在出场一侧处理（跨切点）
                elif kind == "hwhip":
                    fr = motion(fr, 300 * (1 - e), 1); fr = bright(fr, 1 + 0.3 * (1 - e))
        # ---- 出场预处理（仅横向甩糊 / 漏光） ----
        if tout:
            rem = SHOT - t
            if tout[1] == "hwhip" and rem < 0.18:
                e = 1 - rem / 0.18; fr = motion(fr, 300 * e, 1); fr = bright(fr, 1 + 0.3 * e)
            if tout[1] == "vwhip" and rem < 0.07:
                fr = motion(fr, 80, 0)
        # 漏光：跨越切点，前 0.25s 光带从右上扫入，后 0.25s 扫出
        def leak(frm, q):
            a = np.asarray(frm, np.float32)
            yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
            c = (1.4 - 1.8 * q) * W  # 光带中心从右往左
            d = (xx + yy * 0.6) - c
            band = np.exp(-(d / (W * 0.18)) ** 2)[..., None]
            col = np.array([255, 214, 120], np.float32)
            a = a * (1 - 0.85 * band) + col * band * 0.85 + 60 * band
            return Image.fromarray(a.clip(0, 255).astype(np.uint8))
        if tout and tout[1] == "leak" and SHOT - t < 0.25:
            fr = leak(fr, (0.25 - (SHOT - t)) / 0.25 * 0.5)
        if tin and tin[1] == "leak" and t < 0.25:
            fr = leak(fr, 0.5 + t / 0.25 * 0.5)
        # 标签：转场名在切点后显示 1 秒
        if tin and t < 1.0:
            dr = ImageDraw.Draw(fr); txt = f"转场 {si}：{tin[0]}"
            dr.rectangle((24, 20, 24 + 30 + len(txt) * 34, 76), fill=(0, 0, 0))
            dr.text((40, 26), txt, font=FONT, fill=(255, 210, 60))
        fr.save(f"{FR}/f{idx:05d}.png"); idx += 1
    if si < len(TR): cuts.append(idx / FPS)
json.dump({"cuts": cuts, "frames": idx}, open(f"{OUT}/cuts.json", "w"))
print(cuts, idx)
