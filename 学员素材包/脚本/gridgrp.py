import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import build as B
W, H = B.W, B.H
_C = {}
def eo(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def eb(t): return B.eb(t)

def card(key, mw, mh):
    k = ("c", key, mw, mh)
    if k not in _C:
        spec = B.CARDSRC[key]
        _C[k] = B.make_card(B.card_img(spec[0], spec[1]), mw, mh)[0]
    return _C[k]

def fig(path, hgt):
    k = ("f", path, hgt)
    if k not in _C: _C[k] = B.figure(path, hgt)
    return _C[k]

def glow(color, r):
    k = ("g", color, r)
    if k not in _C:
        yy, xx = np.mgrid[-r:r, -r:r].astype(np.float32)
        d = np.sqrt(xx ** 2 + yy ** 2) / r
        a = np.clip(1 - d, 0, 1) ** 1.6 * 150
        im = np.zeros((2 * r, 2 * r, 4), np.uint8); im[..., :3] = color; im[..., 3] = a.astype(np.uint8)
        _C[k] = Image.fromarray(im, "RGBA")
    return _C[k]

def badge(text, sub, size=250):
    k = ("b", text, sub, size)
    if k not in _C:
        S = size * 2; im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        n = 16; R = S * 0.48; r = S * 0.40; c = S / 2
        pts = []
        for i in range(n * 2):
            a = math.pi * i / n - math.pi / 2; rr = R if i % 2 == 0 else r
            pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
        d.polygon(pts, fill=(235, 40, 40, 255), outline=(255, 255, 255, 255), width=10)
        f1 = ImageFont.truetype(B.hz.FONT, int(S * 0.27), index=B.hz.FIDX)
        f2 = ImageFont.truetype(B.hz.FONT, int(S * 0.115), index=B.hz.FIDX)
        w1 = d.textlength(text, font=f1)
        d.text((c - w1 / 2, c - S * 0.20), text, font=f1, fill=(255, 235, 60), stroke_width=9, stroke_fill=(110, 10, 10))
        w2 = d.textlength(sub, font=f2)
        d.text((c - w2 / 2, c + S * 0.12), sub, font=f2, fill=(255, 255, 255), stroke_width=6, stroke_fill=(110, 10, 10))
        _C[k] = im.resize((size, size), Image.LANCZOS)
    return _C[k]

DIRS = {"L": (-1, 0), "R": (1, 0), "T": (0, -1), "B": (0, 1)}

def draw_elems(fr, t, g):
    for e in sorted(g["elems"], key=lambda e: e.get("z", 1)):
        if not (e["t0"] <= t < e["t1"]): continue
        lt = t - e["t0"]; typ = e["k"]
        if typ == "glow":
            im = glow(e["color"], e["r"]); a = min(1, lt / 0.4)
            im2 = im.copy(); im2.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
            fr.alpha_composite(im2, (int(e["x"] - e["r"]), int(e["y"] - e["r"]))); continue
        if typ == "fig": im = fig(e["src"], e["h"])
        elif typ == "card": im = card(e["src"], e["w"], e["h"])
        elif typ == "badge": im = badge(e["text"], e["sub"], e["w"])
        dur_in = e.get("din", 0.38)
        x, y = e["x"], e["y"]; sc = 1.0; al = 1.0; rot = e.get("rot", 0.0)
        d = e.get("enter", "pop")
        if lt < dur_in:
            k = lt / dur_in
            if d in DIRS:
                off = 560 * (1 - eb(k)); dx, dy = DIRS[d]; x += dx * off; y += dy * off; al = min(1, lt / 0.12)
            else:
                sc = 0.5 + 0.5 * eb(k); al = min(1, lt / 0.1)
                if typ == "badge": rot += -14 * (1 - eo(k))
        if typ == "fig": sc *= 1 + 0.02 * math.sin(lt * 2 * math.pi / 2.4)
        else:
            y += 5 * math.sin(lt * 2.1 + e["x"] * 0.01); rot += 0.7 * math.sin(lt * 1.6 + e["y"] * 0.01)
        for (p0, p1) in e.get("pops", []):
            if p0 <= t < p1: sc *= 1 + 0.08 * eo((t - p0) / 0.35)
        if sc != 1.0: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
        if rot: im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
        if al < 1:
            a = im.getchannel("A").point(lambda v: int(v * al)); im = im.copy(); im.putalpha(a)
        fr.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))
    return fr
