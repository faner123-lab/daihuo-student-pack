import sys, os, math, subprocess, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import huazi as hz

W, H, FPS = 1280, 720, 30
# 本文件当作工具库用（push/enter/exit_fx/make_card/card_img/subtitle 等）；下面这些路径只给文件末尾的旧项目示例用，新项目不用管
WORK = os.environ.get("WORK", ".")
U = WORK + "/"
P = IMG = PRD = U
GRID = U + "grid/动态黑色网格_1280x720_60秒循环.mp4"
V = U + "clips/v%02d.mp4"
OUT = U + "out_build"
os.makedirs(OUT, exist_ok=True)
QUICK = len(sys.argv) > 1 and sys.argv[1] == "quick"

SUBF = ImageFont.truetype(hz.FONT, 50, index=hz.FIDX)
SUBF_BIG = ImageFont.truetype(hz.FONT, 76, index=hz.FIDX)
YEL = (255, 222, 40)

def eo(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
eb = hz.ease_back

# ---------------- video readers ----------------
def read_frames(path, ss, dur, n):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", str(dur + 0.2), "-i", path,
           "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fs = [Image.frombytes("RGB", (W, H), raw[i * W * H * 3:(i + 1) * W * H * 3]) for i in range(len(raw) // (W * H * 3))]
    while len(fs) < n: fs.append(fs[-1])
    return fs[:n]

# ---------------- effects ----------------
def push(im, z):
    if z == 1.0: return im
    w, h = int(W * z), int(H * z)
    r = im.resize((w, h), Image.BICUBIC); l, t = (w - W) // 2, (h - H) // 2
    return r.crop((l, t, l + W, t + H))

def motion(im, px, axis):
    if px < 2: return im
    a = np.asarray(im, np.float32)
    a = uniform_filter1d(a, size=int(px), axis=axis, mode="nearest")
    a = uniform_filter1d(a, size=max(1, int(px * 0.5)), axis=axis, mode="nearest")
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

def zoomblur(im, s):
    if s < 0.01: return im
    a = np.zeros((H, W, 3), np.float32); n = 7
    for i in range(n):
        z = 1 + s * i / (n - 1); w, h = int(W * z), int(H * z)
        r = im.resize((w, h), Image.BILINEAR); l, t = (w - W) // 2, (h - H) // 2
        a += np.asarray(r.crop((l, t, l + W, t + H)), np.float32)
    return Image.fromarray((a / n).clip(0, 255).astype(np.uint8))

def bright(im, b): return ImageEnhance.Brightness(im).enhance(b)

def leak(frm, q):
    a = np.asarray(frm, np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    c = (1.4 - 1.8 * q) * W
    d = (xx + yy * 0.6) - c
    band = np.exp(-(d / (W * 0.18)) ** 2)[..., None]
    col = np.array([255, 214, 120], np.float32)
    a = a * (1 - 0.85 * band) + col * band * 0.85 + 60 * band
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

TRDUR = {"vwhip": 0.42, "zoom": 0.42, "white": 0.42, "black": 0.45, "leak": 0.5, "hwhip": 0.40, "hard": 0}

def rgbsplit(im, px):
    if px < 1: return im
    a = np.asarray(im); o = a.copy(); px = int(px)
    o[..., 0] = np.roll(a[..., 0], px, axis=1); o[..., 2] = np.roll(a[..., 2], -px, axis=1)
    return Image.fromarray(o)

def enter(fr, kind, t, base=None):
    d = TRDUR.get(kind, 0)
    if d == 0 or t >= d: return fr
    p = t / d; e = eo(p)
    if kind == "vwhip":
        fr = motion(fr, 260 * (1 - e), 0); fr = bright(fr, 1 + 0.45 * (1 - e)); fr = rgbsplit(fr, 14 * (1 - e))
    elif kind == "zoom":
        z = 1.30 - 0.30 * e
        fr = zoomblur(push(fr, z), 0.28 * (1 - e)); fr = bright(fr, 1 + 0.25 * (1 - e)); fr = rgbsplit(fr, 12 * (1 - e))
    elif kind == "white":
        fr = fr.filter(ImageFilter.GaussianBlur(22 * (1 - e)))
        fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 250, 240)), 0.75 * (1 - e))
    elif kind == "black":
        fr = bright(fr, 0.0 if t < 0.1 else eo((t - 0.1) / (d - 0.1)))
    elif kind == "leak":
        if t < 0.25: fr = leak(fr, 0.5 + t / 0.25 * 0.5)
    elif kind == "hwhip":
        fr = motion(fr, 300 * (1 - e), 1); fr = bright(fr, 1 + 0.3 * (1 - e)); fr = rgbsplit(fr, 16 * (1 - e))
    return fr

def exit_fx(fr, kind, rem):
    if kind == "hwhip" and rem < 0.18:
        e = 1 - rem / 0.18; fr = motion(fr, 300 * e, 1); fr = bright(fr, 1 + 0.3 * e)
    if kind == "leak" and rem < 0.25:
        fr = leak(fr, (0.25 - rem) / 0.25 * 0.5)
    return fr

# ---------------- subtitles ----------------
def subtitle(fr, parts, big=False, pop=1.0, ycen=None):
    f = SUBF_BIG if big else SUBF
    sw = 7 if big else 6
    d = ImageDraw.Draw(fr)
    tw = sum(d.textlength(t, font=f) for t, _ in parts)
    layer = Image.new("RGBA", (int(tw) + 60, f.size + 50), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer); x = 30
    for t, hl in parts:
        ld.text((x, 15), t, font=f, fill=YEL if hl else (255, 255, 255, 255), stroke_width=sw, stroke_fill=(20, 14, 8))
        x += ld.textlength(t, font=f)
    if pop != 1.0:
        layer = layer.resize((int(layer.width * pop), int(layer.height * pop)), Image.BICUBIC)
    cy = ycen if ycen else H * 0.905
    fr.paste(layer, (int(W / 2 - layer.width / 2), int(cy - layer.height / 2)), layer)

def parse(s):  # "当你{全勤}" -> parts
    out = []; hl = False; cur = ""
    for ch in s:
        if ch == "{": 
            if cur: out.append((cur, hl))
            cur = ""; hl = True
        elif ch == "}":
            if cur: out.append((cur, hl))
            cur = ""; hl = False
        else: cur += ch
    if cur: out.append((cur, hl))
    return out

# ---------------- collage helpers ----------------
def autocrop(im):
    a = np.asarray(im.convert("L"))
    h, w = a.shape
    b, r = h, w
    while b > h * 0.8 and a[b - 1, : w // 2].mean() < 25: b -= 1
    while r > w * 0.8 and a[: h // 2, r - 1].mean() < 25: r -= 1
    return im.crop((0, 0, r - 2, b - 2))

def card_img(path, crop=None):
    im = Image.open(path).convert("RGB")
    if "产品原图" in path: im = autocrop(im)
    if crop:
        w, h = im.size; im = im.crop((0, int(h * crop[0]), w, int(h * crop[1])))
    return im

def make_card(im, maxw, maxh, border=5, rad=22):
    s = min(maxw / im.width, maxh / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS).convert("RGBA")
    w, h = im.size
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), rad, fill=255)
    im.putalpha(m)
    out = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 170)); sh.putalpha(m.point(lambda v: int(v * 0.6)))
    shb = Image.new("RGBA", out.size, (0, 0, 0, 0)); shb.alpha_composite(sh, (20, 26)); shb = shb.filter(ImageFilter.GaussianBlur(10))
    out.alpha_composite(shb)
    fr = Image.new("RGBA", (w + 2 * border, h + 2 * border), (0, 0, 0, 0))
    mm = Image.new("L", fr.size, 0); ImageDraw.Draw(mm).rounded_rectangle((0, 0, fr.width - 1, fr.height - 1), rad + border, fill=255)
    fr.paste((255, 255, 255, 255), (0, 0), mm)
    out.alpha_composite(fr, (20 - border, 20 - border))
    out.alpha_composite(im, (20, 20))
    return out, (w, h)

def figure(path, height):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im.getchannel("A"))
    bb = Image.fromarray((a > 8).astype(np.uint8) * 255).getbbox()
    im = im.crop(bb)
    s = height / im.height
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)

def paste_c(canvas, im, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def flash_card(im, k):  # k 0..1 白色覆盖
    if k <= 0: return im
    wh = Image.new("RGBA", im.size, (255, 255, 255, int(255 * k)))
    wh.putalpha(ImageChops_mul(im.getchannel("A"), int(255 * k)))
    out = im.copy(); out.alpha_composite(wh); return out

def ImageChops_mul(a, v): return a.point(lambda x: int(x * v / 255))

def red_circle(canvas, cx, cy, w, h, p, wd=7):
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    d.arc(box, -100, -100 + 380 * p, fill=(235, 38, 38, 255), width=wd)
    canvas.alpha_composite(lay)

CARDSRC = {
    "c03": (IMG + "卡片/卡片_03_碗装咀嚼片.png", None), "c01": (IMG + "卡片/卡片_01_手持两瓶.png", None), "c02": (IMG + "卡片/卡片_02_两瓶并排.png", None),
    "p05": (PRD + "05_营养金字塔图.jpg", None), "p05top": (PRD + "05_营养金字塔图.jpg", (0.02, 0.74)),
    "p01": (PRD + "01_产品正面实拍_以此为准.jpg", None), "p02": (PRD + "02_咀嚼片手心实拍.jpg", None),
    "p03": (PRD + "03_开盖手持实拍.jpg", None), "p04": (PRD + "04_21种宣传主图.jpg", None)}
CACHE = {}
def cimg(key, fn):
    if key not in CACHE: CACHE[key] = fn()
    return CACHE[key]

# ---------------- segment definitions ----------------
# kind: scene / open / title / group / still
SEG = []
def scene(vi, ss, dur, enter_k, sub, push_to=1.07, grade=None, out=None, sfx=None, name=None):
    SEG.append(dict(kind="scene", vi=vi, ss=ss, dur=dur, enter=enter_k, sub=sub, push=push_to, grade=grade, out=out, sfx=sfx, name=name))

SEG.append(dict(kind="open", vi=1, ss=0.0, dur=1.4, enter="hard", name="S01"))
SEG.append(dict(kind="title", vi=2, ss=0.3, dur=2.0, enter="hard", name="S02"))
scene(3, 0.0, 2.0, "black", "当你每天晚上都在{全勤}", 1.10, name="S03", sfx=("砰_拳击.wav", "onset", 1.0))
scene(4, 0.3, 1.5, "vwhip", "尤其{健身党}的", 1.07, name="S04", sfx=("呼_转场音效.wav", "peak", 0.9))
scene(5, 0.6, 1.5, "hard", "{消耗与需求}都比普通人要高", name="S05")
scene(6, 0.8, 1.5, "zoom", "{锌镁硒}很容易透支不足", name="S06", sfx=("咻的一声.wav", "peak", 0.9))
scene(7, 0.0, 2.5, "white", "所以基础营养{多维}真要重视起来", name="S07", sfx=("嗖_转场2.wav", "peak", 0.9))
scene(8, 0.5, 2.0, "vwhip", "千万别觉得{年轻}就无所谓", name="S08", sfx=("呼_转场音效.wav", "peak", 0.9))
scene(9, 0.5, 1.0, "hard", "{挂档}更是不可避免", grade=("sat", 0.9), name="S09")
scene(10, 0.5, 2.0, "zoom", "尤其是平时{上班学习忙}", name="S10", sfx=("咻的一声.wav", "peak", 0.9))
scene(11, 0.5, 1.0, "hard", "三餐全靠{外卖}", name="S11")
scene(12, 0.3, 2.5, "leak", "{蔬菜水果}想起来才吃两口的兄弟", grade=("warm", 1.0), name="S12", sfx=("嗖_转场1.mp3", "peak", 0.9))
scene(13, 0.5, 2.0, "vwhip", "不想研究那么多{花里胡哨}的食补", name="S13", sfx=("呼_转场音效.wav", "peak", 0.9))
scene(14, 0.0, 1.5, "white", "直接看{赛霸}这个多维", name="S14", sfx=("仙尘音效.wav", "peak", 1.0))
SEG.append(dict(kind="group", gid=1, dur=7.0, enter="black", name="拼贴A-C", sfx=("冲击_带低频.mp3", "onset", 1.0), grid0=0.0))
scene(15, 0.3, 2.0, "hwhip", "平时{饮食不规律}，{外卖吃的多}", grade=("sat", 0.92), name="S18", sfx=("嗖_转场1.mp3", "peak", 0.9))
scene(16, 0.4, 2.5, "zoom", "想做个{日常基础}营养补充就很方便", name="S19", sfx=("咻的一声.wav", "peak", 0.9), out=None)
SEG.append(dict(kind="group", gid=2, dur=6.0, enter="white", name="拼贴D-E", sfx=("仙尘音效.wav", "peak", 1.0), grid0=10.0))
SEG.append(dict(kind="still", img=IMG + "阿炎_S22_v1.png", dur=1.9, enter="hwhip", name="S22", sfx=("呼_转场音效.wav", "peak", 0.9)))

# previous segment of whip-in gets out blur
for i, s in enumerate(SEG):
    if i + 1 < len(SEG) and SEG[i + 1]["enter"] == "hwhip": s["out"] = "hwhip"
    if i + 1 < len(SEG) and SEG[i + 1]["enter"] == "leak": s["out"] = "leak"

t = 0.0
for s in SEG:
    s["t0"] = t; t += s["dur"]
TOTAL = t
json.dump([{k: v for k, v in s.items() if k in ("name", "t0", "dur")} for s in SEG], open(OUT + "/timeline.json", "w"), ensure_ascii=False)

# ---------------- group layouts ----------------
def gcards():
    L = lambda f, crop=None, mw=360, mh=440: make_card(card_img(f, crop), mw, mh)
    return dict(
        c03=L(IMG + "卡片/卡片_03_碗装咀嚼片.png"), c04=L(IMG + "卡片/卡片_04_倒出咀嚼片.png"),
        c01=L(IMG + "卡片/卡片_01_手持两瓶.png"), c02=L(IMG + "卡片/卡片_02_两瓶并排.png"),
        p05=L(PRD + "05_营养金字塔图.jpg", mw=370, mh=440), p05top=L(PRD + "05_营养金字塔图.jpg", crop=(0.10, 0.76), mw=450, mh=400),
        p01=L(PRD + "01_产品正面实拍_以此为准.jpg", mw=250, mh=330), p01b=L(PRD + "01_产品正面实拍_以此为准.jpg", mw=330, mh=440),
        p02=L(PRD + "02_咀嚼片手心实拍.jpg", mw=360, mh=440), p03=L(PRD + "03_开盖手持实拍.jpg", mw=360, mh=440),
        p04=L(PRD + "04_21种宣传主图.jpg", mw=360, mh=440))

# group spec: figures, left/right slots, circles, flashes, subs
G1 = dict(
    figs=[(IMG + "阿炎_S15_立绘_v1.png", 0.0, 3.0, 640, 560, "R"), (IMG + "阿炎_S16_立绘_v1.png", 3.0, 5.5, 735, 480, "L"), (IMG + "阿炎_S17_立绘_v1.png", 5.5, 7.0, 640, 560, "L")],
    left=[("c03", 0.0, 1.4, 215, 340), ("c04", 1.4, 3.0, 215, 340), ("p05top", 3.0, 5.5, 255, 300), ("p03", 5.5, 7.0, 215, 340)],
    right=[("p05", 0.0, 3.0, 1065, 340), ("p01", 3.0, 5.5, 1120, 440), ("p04", 5.5, 7.0, 1065, 340)],
    circles=[("p05", 1.6, 3.0, 0.70, 0.865, 0.66, 0.12), ("p05top", 3.4, 5.5, 0.62, 0.43, 0.62, 0.11)],
    flashes=[("left", 1.4), ("left", 4.4), ("right", 3.0), ("right", 5.9)],
    pop=[("right", 5.9)],
    subs=[(0.0, 3.0, "一片里面就压进去{锌镁硒}等{9种矿物质}", False), (3.0, 5.5, "还有{ABCDE}等{12种维生素}", False), (5.5, 7.0, "一次覆盖{21种}基础营养", False)])
G2 = dict(
    figs=[(IMG + "阿炎_S20_立绘_v1.png", 0.0, 3.0, 640, 560, "L"), (IMG + "阿炎_S21_立绘_v1.png", 3.0, 6.0, 640, 560, "R")],
    left=[("p02", 0.0, 1.8, 215, 340), ("c03", 1.8, 3.0, 215, 340), ("c01", 3.0, 4.5, 215, 340), ("c02", 4.5, 6.0, 215, 340)],
    right=[("p01b", 0.0, 3.0, 1065, 340), ("c03", 3.0, 6.0, 1065, 340)],
    circles=[], flashes=[("left", 1.8), ("left", 3.0), ("left", 4.5), ("right", 3.0)], pop=[],
    subs=[(0.0, 2.0, "关键是{价格还夯到爆}", False), (2.0, 3.0, "{19块9}一瓶 60粒", True), (3.0, 4.5, "长期健身推荐{拍2瓶}", False), (4.5, 6.0, "{29块9}更划算", True)])
GROUPS = {1: G1, 2: G2}

def slot_at(slots, tl):
    for s in slots:
        if s[1] <= tl < s[2]: return s
    return slots[-1]

def render_group(g, gframes, tl, cards, figs):
    fr = gframes.rgba_at(tl) if False else None

# ---------------- opening / title ----------------
LINE1 = [("戒了还能", 74, "white", 0), ("戒了", 96, "blue", 0.12)]
LINE1 = [("戒了", 92, "blue", 0.12), ("还能", 70, "white", 0)]
LINE2 = [("回来吗", 140, "gold", 0.14)]

def open_frame(bg, t, dur, L1, L2):
    c1 = (W * 0.42, H * 0.56); c2 = (W * 0.60, H * 0.60 + L1.height * 0.62)
    fr = bg.convert("RGBA")
    k = hz.ease_out((t - 0.12) / 0.22)
    if k > 0: hz.place(fr, L1, *c1, scale=1.18 - 0.18 * k, alpha=k, blur=10 * (1 - k))
    k2 = (t - 0.55) / 0.26
    if k2 > 0:
        e = eb(k2)
        hz.place(fr, L2, c2[0], c2[1], scale=1.25 - 0.25 * min(1, e), alpha=min(1, k2 * 2), blur=8 * max(0, 1 - k2 * 1.6), dx=60 * (1 - min(1, e)))
    fr = fr.convert("RGB")
    return fr

def title_frame(bg, t, i, T, K, top, bot, half):
    cx, cy = W / 2, H * 0.74
    glitch = {2: 26, 3: -14, 5: 34, 6: 0, 8: 20, 9: -10}
    fr = bg.convert("RGBA")
    b = 0.15 if t < 0.1 else min(1, 0.15 + (t - 0.1) / 0.45 * 0.85)
    fr = ImageEnhance.Brightness(fr).enhance(b)
    a = min(1, max(0, (t - 0.03) / 0.18))
    if a > 0:
        if t < 0.72:
            g = glitch.get(i)
            if g is None: hz.place(fr, T, cx, cy, alpha=a)
            elif g == 0: hz.place(fr, T, cx, cy + 10, alpha=a)
            else:
                hz.place(fr, top, cx - 6, cy - half / 2 - g, alpha=a)
                hz.place(fr, bot, cx + 6, cy + half / 2 + g, alpha=a)
        else:
            k = hz.ease_out((t - 0.72) / 0.12)
            gap = int(T.height * 0.30 * k)
            hz.place(fr, top, cx, cy - half / 2 - gap, alpha=0.95)
            hz.place(fr, bot, cx, cy + half / 2 + gap, alpha=0.95)
            kk = (t - 0.74) / 0.24
            if kk > 0:
                s = 0.2 + 0.8 * eb(kk)
                hz.place(fr, K, cx + 8, cy, scale=s, alpha=min(1, kk * 3))
    return fr.convert("RGB")

# ---------------- main render ----------------
def main():
    nfr_total = int(round(TOTAL * FPS))
    out_name = OUT + ("/quick.mp4" if QUICK else "/video_noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out_name], stdin=subprocess.PIPE)
    L1 = hz.render_line(LINE1); L2 = hz.render_line(LINE2)
    T = hz.render_word("今天阿炎讲", 104, "white", stroke=3)
    K = hz.render_word("锌镁硒", 118, "gold", stroke=8, shear=0.12)
    half = T.height // 2
    top, bot = T.crop((0, 0, T.width, half)), T.crop((0, half, T.width, T.height))
    gcache = None
    for si, s in enumerate(SEG):
        n = int(round((s["t0"] + s["dur"]) * FPS)) - int(round(s["t0"] * FPS))
        if QUICK and s["name"] not in QUICK_SEGS: 
            continue
        print("seg", s["name"], n, flush=True)
        if s["kind"] in ("scene", "open", "title"):
            frames = read_frames(V % s["vi"], s["ss"], s["dur"], n)
        if s["kind"] == "still":
            still = hz.load_bg(s["img"])
        if s["kind"] == "group":
            g = GROUPS[s["gid"]]
            if gcache is None: gcache = gcards()
            cards = gcache
            gf = read_frames(GRID, s["grid0"], s["dur"], n)
            figs = [(figure(f[0], f[4]),) + f[1:] for f in g["figs"]]
        for i in range(n):
            t = i / FPS; rem = s["dur"] - t
            if s["kind"] == "open":
                bg = push(frames[i], 1.0 + 0.05 * t / s["dur"])
                fr = open_frame(bg, t, s["dur"], L1, L2)
                tail = t - (s["dur"] - 0.22)
                if tail > 0:
                    k3 = tail / 0.22
                    fr = motion(fr, 160 * k3 + 2, 1); fr = bright(fr, 1 + 0.5 * k3)
            elif s["kind"] == "title":
                bg = push(frames[i], 1.04 + 0.06 * t / s["dur"])
                fr = title_frame(bg, t, i, T, K, top, bot, half)
            elif s["kind"] == "scene":
                z = 1.0 + (s["push"] - 1.0) * t / s["dur"]
                fr = push(frames[i], z)
                gr = s["grade"]
                if gr:
                    if gr[0] == "sat": fr = ImageEnhance.Color(fr).enhance(gr[1])
                    if gr[0] == "warm":
                        a = np.asarray(fr, np.float32); k = min(1, t / 1.5) * 0.12
                        a[..., 0] *= 1 + k; a[..., 2] *= 1 - k * 0.8; fr = Image.fromarray(a.clip(0, 255).astype(np.uint8))
                        fr = ImageEnhance.Color(fr).enhance(1.12)
                if s["sub"] and t < s["dur"] - 0.05:
                    subtitle(fr, parse(s["sub"]))
                fr = enter(fr, s["enter"], t)
                if s["out"]: fr = exit_fx(fr, s["out"], rem)
            elif s["kind"] == "still":
                z = 1.13 + 0.05 * t / s["dur"]; ww, hh = int(W * z), int(H * z)
                fr = still.resize((ww, hh), Image.BICUBIC).crop(((ww - W) // 2, 0, (ww - W) // 2 + W, H))
                a_ = np.asarray(fr, np.float32)
                ramp = np.clip((np.arange(H) - H * 0.74) / (H * 0.26), 0, 1)[:, None, None] * 0.6
                fr = Image.fromarray((a_ * (1 - ramp)).clip(0, 255).astype(np.uint8))
                subtitle(fr, parse("需要的兄弟，{左下角}直接冲"))
                lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
                kk = eo((t - 0.4) / 0.25)
                if kk > 0:
                    by = 585 + 8 * math.sin(t * 9)
                    d.polygon([(46, by), (126, by), (86, by + 62)], fill=(255, 200, 30, int(255 * kk)), outline=(40, 20, 0, int(255 * kk)))
                fr = fr.convert("RGBA"); fr.alpha_composite(lay); fr = fr.convert("RGB")
                fr = enter(fr, s["enter"], t)
                if t > s["dur"] - 0.4: fr = bright(fr, max(0.0, (s["dur"] - t) / 0.4))
            elif s["kind"] == "group":
                fr = gf[i].convert("RGBA")
                if 'elems' in g:
                    import gridgrp; fr = gridgrp.draw_elems(fr, t, g)
                # figures
                for (fim, a0, a1, cx, hgt, side) in figs:
                    if a0 <= t < a1:
                        lt = t - a0
                        k = eb(lt / 0.32) if lt < 0.32 else 1.0
                        off = (-380 if side == "L" else 380) * (1 - k)
                        br = 1 + 0.02 * math.sin(lt * 2 * math.pi / 2.4)
                        fy = 690 - 35 - fim.height * br / 2 + 5
                        fy = 360 if fim.height > 520 else 360
                        sh = Image.new("RGBA", (int(fim.width * 0.7), 30), (0, 0, 0, 0))
                        paste_c(fr, fim, cx + off, 345, br, min(1, lt / 0.12))
                for side, slots in (() if "elems" in g else (("left", g["left"]), ("right", g["right"]))):
                    key, a0, a1, cx, cy = slot_at(slots, t)
                    cim, _ = cards[key]
                    lt = t - a0
                    sc = 1.0; al = 1.0
                    if lt < 0.2 and a0 > 0.05 and not (lt < 0 ):
                        pass
                    if a0 == 0.0:
                        sc = 0.92 + 0.08 * eo(lt / 0.2); al = min(1, lt / 0.2)
                    elif lt < 0.2:
                        sc = 0.95 + 0.05 * eo(lt / 0.2)
                    fk = 0.0
                    for ps, pt, pe in g["pop"]:
                        if ps == side and pt <= t < pe:
                            sc *= 1 + 0.07 * eo((t - pt) / 0.35)
                    paste_c(fr, flash_card(cim, fk), cx, cy, sc, al)
                    for (ck, c0, c1, fx, fy, cw, ch) in g["circles"]:
                        if ck == key and c0 <= t < c1:
                            w0, h0 = cards[key][1]
                            ox = cx - w0 * sc / 2; oy = cy - h0 * sc / 2
                            red_circle(fr, ox + w0 * sc * fx, oy + h0 * sc * fy, w0 * sc * cw, h0 * sc * ch, min(1, (t - c0) / 0.4))
                fr = fr.convert("RGB")
                for (a0, a1, txt, big) in g["subs"]:
                    if a0 <= t < a1:
                        pop = 1.0
                        if big: pop = 0.8 + 0.2 * eb((t - a0) / 0.25) if t - a0 < 0.25 else 1.0
                        subtitle(fr, parse(txt), big=big, pop=pop, ycen=H * 0.9)
                fr = enter(fr, s["enter"], t)
            enc.stdin.write(fr.tobytes())
    enc.stdin.close(); enc.wait()
    print("done", TOTAL)

QUICK_SEGS = {"S01","S02","拼贴A-C","拼贴D-E","S22"}
if __name__ == "__main__":
    main()
