import sys, os, json, math, subprocess
W13 = os.environ["WORK"].rstrip("/") + "/"   # 工作目录：里面放 clips/ vo/ sfx/ cards/ figs/ stills/ bgm/ grid/ out/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(W13)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import build as B
from build import W, H, FPS, push, enter, exit_fx, subtitle, parse, eb, eo
hz = B.hz
CLIPD = W13 + "clips/"
U_IMG = W13 + "stills/"
GRID = W13 + "grid/动态黑色网格_1280x720_60秒循环.mp4"
OUT = W13 + "out"; os.makedirs(OUT, exist_ok=True)
W10 = W13
REAL = ""; RV = {}

# ---------------- voice timeline ----------------
d = {}
for l in open(W13 + "vo/dur.txt"):
    k, v = l.split(); d[int(k)] = float(v)
GAP = 0.10
ls = {1: 0.15}
for i in range(2, 20): ls[i] = ls[i - 1] + d[i - 1] + GAP
le = {i: ls[i] + d[i] for i in d}
END = le[19] + 0.75
T0 = {"S01": 0.0}
for k, i in (("S02",2),("S03",3),("S04",4),("S05",5),("S06",6),("S07",7),("S08",8),("S09",9),("S11",11),("S12",12),("G1",13),("S14",14),("S15",15),("S16",16),("S17",18),("S18",19)):
    T0[k] = ls[i] - 0.10
T0["S10"] = ls[10] - 0.22
order = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11", "S12", "G1", "S14", "S15", "S16", "S17", "S18"]
for i in range(len(order) - 1): assert T0[order[i]] < T0[order[i + 1]], order[i]
dur = {n: (T0[order[i + 1]] if i + 1 < len(order) else END) - T0[n] for i, n in enumerate(order)}
T_REVEAL = T0["S10"] + 0.55
rel = lambda name, t_abs: t_abs - T0[name]
# ---------------- video reading ----------------
def read_frames(path, ss, dur_, n, speed=1.0):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(ss), "-t", str(dur_ * speed + 0.3), "-i", path,
           "-vf", f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS}",
           "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fs = [Image.frombytes("RGB", (W, H), raw[i * W * H * 3:(i + 1) * W * H * 3]) for i in range(len(raw) // (W * H * 3))]
    if not fs: raise RuntimeError(path)
    while len(fs) < n: fs.append(fs[-1])
    return fs[:n]

def vid_card_frames(path, ss, dur_, w, h, fx=0.5, speed=1.0):
    n = int(dur_ * FPS) + 3
    vf = (f"setpts=PTS/{speed},crop=w=min(iw\\,ih*{w}/{h}):h=min(ih\\,iw*{h}/{w}):x=(iw-ow)*{fx}:y=(ih-oh)/2,"
          f"scale={w}:{h}:flags=lanczos,fps={FPS}")
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(ss), "-t", str(dur_ * speed + 0.5), "-i", path, "-vf", vf,
           "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fs = [Image.frombytes("RGB", (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(len(raw) // (w * h * 3))]
    if not fs: raise RuntimeError(path)
    while len(fs) < n: fs.append(fs[-1])
    return fs

_TPL = {}
def card_tpl(w, h):
    if (w, h) not in _TPL:
        _TPL[(w, h)] = B.make_card(Image.new("RGB", (w, h), (0, 0, 0)), w, h)[0]
        m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 22, fill=255)
        _TPL[(w, h, "m")] = m
    return _TPL[(w, h)], _TPL[(w, h, "m")]

def vid_card(frame, w, h):
    tpl, m = card_tpl(w, h)
    c = tpl.copy(); inner = frame.convert("RGBA"); inner.putalpha(m); c.alpha_composite(inner, (20, 20)); return c

def circ_badge(text, color, size):
    S = size * 2; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    for r, a in ((0.50, 70), (0.46, 120)): dd.ellipse((S / 2 - S * r, S / 2 - S * r, S / 2 + S * r, S / 2 + S * r), fill=color + (a,))
    dd.ellipse((S * 0.12, S * 0.12, S * 0.88, S * 0.88), fill=color + (255,), outline=(255, 255, 255, 255), width=10)
    f = ImageFont.truetype(hz.FONT, int(S * (0.36 if len(text) == 1 else 0.28)), index=hz.FIDX)
    tw = dd.textlength(text, font=f)
    dd.text((S / 2 - tw / 2, S / 2 - f.size * 0.60), text, font=f, fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(40, 30, 10, 255))
    return im.resize((size, size), Image.LANCZOS)

# ---------------- element renderer (gridgrp 的扩展：视频卡片、圆标) ----------------
import gridgrp as G
DIRS = G.DIRS
_FIG = {}
def figimg(src, hgt):
    k = (src, hgt)
    if k not in _FIG:
        im = Image.open(src).convert("RGBA"); s = hgt / im.height
        _FIG[k] = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    return _FIG[k]

_IMGCARD = {}
def imgcard(src, w, h):
    k = (src, w, h)
    if k not in _IMGCARD: _IMGCARD[k] = B.make_card(B.card_img(src), w, h)[0]
    return _IMGCARD[k]

def draw_elems(fr, t, g):
    for e in sorted(g["elems"], key=lambda e: e.get("z", 1)):
        if not (e["t0"] <= t < e["t1"]): continue
        lt = t - e["t0"]; typ = e["k"]
        if typ == "glow":
            im = G.glow(e["color"], e["r"]); a = min(1, lt / 0.4)
            im2 = im.copy(); im2.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
            fr.alpha_composite(im2, (int(e["x"] - e["r"]), int(e["y"] - e["r"]))); continue
        if typ == "fig": im = figimg(e["src"], e["h"])
        elif typ == "card": im = imgcard(e["src"], e["w"], e["h"])
        elif typ == "vid":
            fi = min(int(lt * FPS), len(e["_fr"]) - 1); im = vid_card(e["_fr"][fi], e["w"], e["h"])
        elif typ == "circ": im = e["_im"]
        dur_in = e.get("din", 0.38)
        x, y = e["x"], e["y"]; sc = 1.0; al = 1.0; rot = e.get("rot", 0.0)
        dd = e.get("enter", "pop")
        if lt < dur_in:
            k = lt / dur_in
            if dd in DIRS:
                off = 560 * (1 - eb(k)); dx, dy = DIRS[dd]; x += dx * off; y += dy * off; al = min(1, lt / 0.12)
            else:
                sc = 0.5 + 0.5 * eb(k); al = min(1, lt / 0.1)
        if typ == "fig": sc *= 1 + 0.02 * math.sin(lt * 2 * math.pi / 2.4)
        elif typ == "circ": y += 6 * math.sin(lt * 3.0)
        else:
            y += 5 * math.sin(lt * 2.1 + e["x"] * 0.01); rot += 0.7 * math.sin(lt * 1.6 + e["y"] * 0.01)
        for (p0, p1) in e.get("pops", []):
            if p0 <= t < p1: sc *= 1 + 0.07 * eo((t - p0) / 0.35)
        if sc != 1.0: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
        if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        if al < 1:
            a = im.getchannel("A").point(lambda v: int(v * al)); im = im.copy(); im.putalpha(a)
        fr.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
    return fr

# ---------------- emoji / subtitles ----------------
_EMO = {}
def emoji_img(ch, size):
    k = (ch, size)
    if k not in _EMO:
        f = ImageFont.truetype(os.environ.get("EMOJI_FONT", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"), 109)
        im = Image.new("RGBA", (136, 128), (0, 0, 0, 0)); ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        bb = im.getbbox(); im = im.crop(bb); s = size / im.height
        _EMO[k] = im.resize((max(1, int(im.width * s)), size), Image.LANCZOS)
    return _EMO[k]

def sub2(fr, parts, big=False, ycen=None, pop=1.0):
    """parts: [(text, hl)]，text 以 @ 开头表示 emoji。fr 为 RGB。"""
    f = B.SUBF_BIG if big else B.SUBF
    sw = 7 if big else 6
    dd = ImageDraw.Draw(fr)
    items = []
    for t, hl in parts:
        if t.startswith("@"): items.append(("e", emoji_img(t[1:], int(f.size * 1.0)), 0))
        else: items.append(("t", t, hl))
    tw = sum((dd.textlength(it[1], font=f) if it[0] == "t" else it[1].width + 6) for it in items)
    layer = Image.new("RGBA", (int(tw) + 60, f.size + 50), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer); x = 30
    for k, v, hl in items:
        if k == "t":
            ld.text((x, 15), v, font=f, fill=B.YEL if hl else (255, 255, 255, 255), stroke_width=sw, stroke_fill=(20, 14, 8)); x += ld.textlength(v, font=f)
        else:
            layer.alpha_composite(v, (int(x), 25)); x += v.width + 6
    if pop != 1.0: layer = layer.resize((int(layer.width * pop), int(layer.height * pop)), Image.BICUBIC)
    cy = ycen if ycen else H * 0.905
    fr.paste(layer, (int(W / 2 - layer.width / 2), int(cy - layer.height / 2)), layer)

def parse2(s):
    out = []; hl = False; cur = ""
    for ch in s:
        if ch == "{":
            if cur: out.append((cur, hl))
            cur = ""; hl = True
        elif ch == "}":
            if cur: out.append((cur, hl))
            cur = ""; hl = False
        elif ch == "@":
            if cur: out.append((cur, hl))
            cur = "@"
        else:
            if cur == "@": out.append(("@" + ch, hl)); cur = ""
            else: cur += ch
    if cur: out.append((cur, hl))
    return out

# ---------------- groups (S13 拼贴) ----------------
FIG = W13 + "figs/"
gd = {"G1": dur["G1"]}
GL = lambda t1, x, y, col, r=340: dict(k="glow", t0=0, t1=t1, x=x, y=y, color=col, r=r, z=0)
t_d = rel("G1", ls[13] + 0.50 * d[13])
circD = dict(k="circ", t0=t_d, t1=gd["G1"], x=780, y=135, enter="pop", din=0.4, z=4); circD["_im"] = circ_badge("D3", (150, 90, 235), 130)
GROUPS = {"G1": dict(elems=[
    GL(gd["G1"], 330, 360, (255, 190, 70)),
    dict(k="fig", src=FIG + "L13.png", t0=0.0, t1=gd["G1"], x=1005, y=400, h=500, enter="R", din=0.40, z=2),
    dict(k="card", src=W13 + "cards/prod.jpg", t0=0.06, t1=gd["G1"], x=400, y=340, w=640, h=520, rot=-3, enter="L", z=1, din=0.36, pops=[(t_d, gd["G1"])]),
    circD], subs=[(0.0, gd["G1"], "小分子液体钙堆个{D3}", False)])}
GOFF = {"G1": 20.0}

# ---------------- scenes ----------------
SEGS = []
def sc(name, enter_k, subs, ss, span, z0=1.0, z1=1.05, kind="scene", **kw):
    speed = max(1.0, span / dur[name])
    SEGS.append(dict(kind=kind, name=name, vi=CLIPD + name + ".mp4", ss=ss, speed=speed, enter=enter_k, subs=subs, z0=z0, z1=z1, exit=None, **kw))
D = lambda n: dur[n]
R = rel
sc("S01", "hwhip", [], 0.3, 3.8, z1=1.04, kind="s01")
sc("S02", "hard", [], 0.0, 2.4, z1=1.03, kind="s02")
t3 = R("S03", ls[3] + 0.45 * d[3])
sc("S03", "hard", [(0, t3, "身高{@⬇}", False, None), (t3, D("S03"), "@💪{显大}", False, None)], 0.0, 2.2)
sc("S04", "hard", [(0, D("S04"), "可要说对{妹妹}吸引力", False, None)], 0.3, 3.2, z1=1.04)
sc("S05", "white", [(0, D("S05"), "{180+}更帅了", False, None)], 0.2, 3.4, z1=1.05)
sc("S06", "white", [(0, D("S06"), "{25+}", True, H * 0.88)], 0.2, 3.2, z0=1.0, z1=1.08)
sc("S07", "vwhip", [], 0.3, 3.4)
sc("S08", "hard", [(0, D("S08"), "但这{买对不买贵}", False, None)], 0.3, 3.4, z1=1.04)
tf9 = R("S09", ls[9] + 0.38 * d[9])
sc("S09", "hard", [(0, D("S09"), "市面上品质低的{固体钙}可以丢掉了", False, None)], 0.2, 3.4, ban_t=tf9)
sc("S10", "white", [(0, D("S10"), "{金维他液体钙}", False, None)], 0.6, 3.0, z1=1.04)
tk = R("S11", ls[11] + 0.30 * d[11])
sc("S11", "hard", [(0, D("S11"), "钙元素{小分子液体}形式", False, None)], 0.0, 3.8, z1=1.03, k01_t=tk)
sc("S12", "vwhip", [(0, D("S12"), "@♻{固体钙}三条街", False, None)], 0.1, 3.8)
sc("S14", "hard", [(0, D("S14"), "{效率}这一块", False, None)], 0.2, 3.4, z1=1.03)
sc("S15", "hard", [], 0.2, 3.6)
t17 = R("S16", ls[17] - 0.02)
sc("S16", "black", [(0, t17, "现在{两位数}到手", False, None), (t17, D("S16"), "整整{6大瓶}", False, None)], 0.0, 2.8, z1=1.04)
sc("S17", "hard", [(0, D("S17"), "可以{吃近一年}", False, None)], 0.2, 3.4, z1=1.04)
sc("S18", "hwhip", [(0, D("S18"), "提升自己的兄弟们{直接冲}", False, None)], 0.0, 1.0, z0=1.0, z1=1.2, kind="still", still=U_IMG + "阿炎_S18_v1.png")
SEGOF = {s["name"]: s for s in SEGS}
full = []
for n in order:
    if n == "G1": full.append(dict(kind="group", name=n, enter="white", exit=None))
    else: full.append(SEGOF[n])
for i in range(len(full) - 1):
    if full[i + 1]["enter"] in ("hwhip", "leak"): full[i]["exit"] = full[i + 1]["enter"]
for s_ in full: s_["t0"] = T0[s_["name"]]; s_["dur"] = dur[s_["name"]]
TL = {"T0": T0, "dur": dur, "END": END, "ls": ls, "le": le, "T_REVEAL": T_REVEAL, "d": d,
      "t_line2": 0.0, "t_key": 0.0, "tf9": T0["S09"] + tf9, "t_d": T0["G1"] + t_d, "t3": T0["S03"] + t3,
      "k01": T0["S11"] + tk}
SPLIT_TS = min(0.60, dur["S02"] * 0.52)
TL["t_key"] = T0["S02"] + SPLIT_TS
T_LINE2 = ls[1] + 0.60 * d[1]
TL["t_line2"] = T_LINE2
json.dump(TL, open(OUT + "/timeline.json", "w"), ensure_ascii=False)
# ---------------- special frames ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def iris(fr, t, dd=0.45):
    if t >= dd: return fr
    k = eo(t / dd)
    a_ = W * (0.10 + 1.05 * k); b_ = H * (0.05 + 0.95 * k)
    r = np.sqrt(((xx - W * 0.5) / a_) ** 2 + ((yy - H * 0.5) / b_) ** 2)
    m = np.clip((1.0 - r) / 0.22, 0, 1)[..., None]
    return Image.fromarray((np.asarray(fr, np.float32) * m).clip(0, 255).astype(np.uint8))

L1 = hz.render_line([("你身材的", 70, "white", 0), ("视觉张力", 94, "gold", 0.12)])
L2 = hz.render_line([("来自海拔", 124, "blue", 0.14)])
C1 = (W * 0.46, H * 0.55); C2 = (W * 0.60, H * 0.62 + L1.height * 0.62)
def s01_overlay(fr, t):
    rgba = fr.convert("RGBA")
    k = hz.ease_out((t - 0.12) / 0.22)
    if k > 0: hz.place(rgba, L1, *C1, scale=1.18 - 0.18 * k, alpha=k, blur=10 * (1 - k))
    k2 = (t - T_LINE2) / 0.26
    if k2 > 0:
        e = hz.ease_back(k2)
        hz.place(rgba, L2, C2[0], C2[1], scale=1.25 - 0.25 * min(1, e), alpha=min(1, k2 * 2), blur=8 * max(0, 1 - k2 * 1.6), dx=60 * (1 - min(1, e)))
    return rgba.convert("RGB")

TT = hz.render_word("今天我们讲", 104, "white", stroke=3)
KK = hz.render_word("视觉张力", 104, "gold", stroke=8, shear=0.12)
_half = TT.height // 2
TOP, BOT = TT.crop((0, 0, TT.width, _half)), TT.crop((0, _half, TT.width, TT.height))
GLITCH = {1: 26, 2: -14, 4: 34, 5: 0, 7: 20, 8: -10}
def s02_frame(bg, t, i):
    cx, cy = W / 2, H * 0.30
    fr = bg.convert("RGBA")
    b = 0.15 if t < 0.1 else min(1, 0.15 + (t - 0.1) / 0.40 * 0.85)
    fr = ImageEnhance.Brightness(fr).enhance(b)
    a = min(1, max(0, (t - 0.03) / 0.15))
    if a > 0:
        if t < SPLIT_TS:
            g = GLITCH.get(i)
            if g is None: hz.place(fr, TT, cx, cy, alpha=a)
            elif g == 0: hz.place(fr, TT, cx, cy + 10, alpha=a)
            else:
                hz.place(fr, TOP, cx - 6, cy - _half / 2 - g, alpha=a); hz.place(fr, BOT, cx + 6, cy + _half / 2 + g, alpha=a)
        else:
            k = hz.ease_out((t - SPLIT_TS) / 0.12); gap = int(TT.height * 0.52 * k)
            hz.place(fr, TOP, cx, cy - _half / 2 - gap, alpha=0.95); hz.place(fr, BOT, cx, cy + _half / 2 + gap, alpha=0.95)
            kk = (t - SPLIT_TS - 0.02) / 0.24
            if kk > 0:
                s = 0.2 + 0.8 * hz.ease_back(kk); hz.place(fr, KK, cx + 8, cy, scale=s, alpha=min(1, kk * 3))
    return fr.convert("RGB")

def ban(rgba, t, t0):
    if t < t0: return rgba
    k = (t - t0) / 0.28; e = eb(k); r = 128 * (0.5 + 0.5 * min(1.15, e)); al = min(1, k * 3)
    lay = Image.new("RGBA", rgba.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
    cx, cy = 300, 500
    col = (230, 36, 36, int(255 * al))
    dd.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=18)
    o = r * 0.707
    dd.line((cx - o, cy - o, cx + o, cy + o), fill=col, width=18)
    rgba.alpha_composite(lay); return rgba

K01 = B.make_card(Image.open(W13 + "cards/K01.png").convert("RGB"), 360, 360)[0]
def k01_overlay(rgba, t, t0):
    if t < t0: return rgba
    k = (t - t0) / 0.34; e = eb(k)
    im = K01.resize((int(K01.width * (0.5 + 0.5 * min(1.1, e))), int(K01.height * (0.5 + 0.5 * min(1.1, e)))), Image.BICUBIC)
    im = im.rotate(-4 + 0.7 * math.sin(t * 1.6), resample=Image.BICUBIC, expand=True)
    if k < 0.3: a = im.getchannel("A").point(lambda v: int(v * k / 0.3)); im = im.copy(); im.putalpha(a)
    rgba.alpha_composite(im, (int(1060 - im.width / 2), int(400 + 5 * math.sin(t * 2.1) - im.height / 2))); return rgba

BAD = {n: circ_badge(tx, col, 118) for n, (tx, col) in {"ca": ("Ca", (60, 140, 235)), "mg": ("Mg", (60, 190, 120)), "d": ("D", (240, 170, 20))}.items()}
def badges(rgba, t, t0):
    for j, (key, x, y) in enumerate((("ca", 150, 150), ("mg", 1150, 120), ("d", 1160, 560))):
        lt = t - t0 - 0.12 * j
        if lt < 0: continue
        k = eb(lt / 0.32); im = BAD[key]; sc_ = 0.4 + 0.6 * min(1.1, k)
        im = im.resize((int(im.width * sc_), int(im.height * sc_)), Image.BICUBIC)
        rgba.alpha_composite(im, (int(x - im.width / 2), int(y + 6 * math.sin(t * 3 + j) - im.height / 2)))
    return rgba

ORB = {n: circ_badge(tx, col, 96) for n, (tx, col) in {"ca": ("钙", (60, 140, 235)), "d3": ("D3", (150, 90, 235)), "mg": ("Mg", (60, 190, 120)), "d": ("D", (240, 170, 20))}.items()}
def ring(rgba, t):
    cx, cy, rx, ry = 640, 520, 480, 120
    lay = Image.new("RGBA", rgba.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
    al = int(255 * min(1, t / 0.4))
    dd.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(255, 205, 80, int(al * 0.85)), width=6)
    dd.ellipse((cx - rx - 10, cy - ry - 8, cx + rx + 10, cy + ry + 8), outline=(255, 235, 150, int(al * 0.35)), width=12)
    rgba.alpha_composite(lay)
    for j, key in enumerate(("ca", "d3", "mg", "d")):
        ang = t * 1.5 + j * math.pi / 2; x = cx + rx * math.cos(ang); y = cy + ry * math.sin(ang)
        im = ORB[key]; sc_ = 0.85 + 0.25 * math.sin(ang)
        im = im.resize((int(im.width * sc_), int(im.height * sc_)), Image.BICUBIC)
        if al < 255: a = im.getchannel("A").point(lambda v: int(v * al / 255)); im = im.copy(); im.putalpha(a)
        rgba.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
    return rgba

# ---------------- overlays ----------------
DF = ImageFont.truetype(hz.FONT, 15, index=hz.FIDX)
DT = "视频仅为个人主观感受 非夸大宣传 无前后对比 非医疗产品"
_t = Image.new("RGBA", (int(DF.getlength(DT)) + 16, 28), (0, 0, 0, 0)); _d = ImageDraw.Draw(_t)
_d.text((8, 4), DT, font=DF, fill=(255, 255, 255, 215), stroke_width=2, stroke_fill=(0, 0, 0, 200))
def overlays(fr):
    fr.paste(_t, (W - _t.width - 10, 6), _t); return fr

def render(only=None):
    n_total = int(round(END * FPS))
    out_name = OUT + ("/quick.mp4" if only else "/video_noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out_name], stdin=subprocess.PIPE)
    for si, s in enumerate(full):
        if only and s["name"] not in only: continue
        start_f = int(round(s["t0"] * FPS))
        end_f = int(round((s["t0"] + s["dur"]) * FPS)) if si + 1 < len(full) else n_total
        n = end_f - start_f
        print("seg", s["name"], n, round(s["t0"], 2), round(s["dur"], 2), flush=True)
        if s["kind"] == "still":
            _im = Image.open(s["still"]).convert("RGB").resize((W, H), Image.LANCZOS); frames = [_im] * n
        elif s["kind"] != "group":
            frames = read_frames(s["vi"], s["ss"], s["dur"], n, s["speed"])
        else:
            gg = GROUPS[s["name"]]; gf = read_frames(GRID, GOFF[s["name"]], s["dur"], n)
        for i in range(n):
            t = i / FPS; rem = s["dur"] - t
            if s["kind"] == "group":
                fr = gf[i].convert("RGBA"); fr = draw_elems(fr, t, gg).convert("RGB")
                for (a0, a1, txt, big) in gg["subs"]:
                    if a0 <= t < a1 - 0.04: sub2(fr, parse2(txt), big=big, ycen=H * 0.9)
                fr = enter(fr, s["enter"], t)
                if s["exit"]: fr = exit_fx(fr, s["exit"], rem)
                enc.stdin.write(overlays(fr).tobytes()); continue
            z = s["z0"] + (s["z1"] - s["z0"]) * t / s["dur"]
            fr = push(frames[i], z)
            if s["kind"] == "s02":
                fr = s02_frame(fr, t, i)
            else:
                if s["kind"] == "s01": fr = s01_overlay(fr, t)
                rgba = fr.convert("RGBA")
                if s.get("ban_t") is not None: rgba = ban(rgba, t, s["ban_t"])
                if s.get("k01_t") is not None: rgba = k01_overlay(rgba, t, s["k01_t"])
                if s.get("badges_t") is not None: rgba = badges(rgba, t, s["badges_t"])
                if s.get("ring"): rgba = ring(rgba, t)
                fr = rgba.convert("RGB")
                for (a0, a1, txt, big, yc) in s["subs"]:
                    if a0 <= t < a1 - 0.04: sub2(fr, parse2(txt), big=big, ycen=yc)
                if s["enter"] == "iris": fr = iris(fr, t)
                else: fr = enter(fr, s["enter"], t)
            if s["exit"]: fr = exit_fx(fr, s["exit"], rem)
            enc.stdin.write(overlays(fr).tobytes())
    enc.stdin.close(); enc.wait()
    print("done", END, flush=True)

if __name__ == "__main__":
    print({k: round(v, 2) for k, v in T0.items()}, "END", round(END, 2), "reveal", round(T_REVEAL, 2))
    render(set(sys.argv[1:]) or None)
