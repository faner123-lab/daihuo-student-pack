# 画面里的“设计字”：不是通篇花字，只给 3–5 个重点（数字、价格、时间跳转），做成物件。
# 四种：scale 体重秤读数屏 / gold 金色大数字+小签 / coupon 红色优惠券 / timejump 时间跳转标题
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_CANDS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc",
]


def find_font(black=True):
    """优先用环境变量 FONT_PATH（粗体字体文件），否则在常见位置找。"""
    p = os.environ.get("FONT_PATH")
    if p and os.path.exists(p):
        return p
    order = _CANDS if black else _CANDS[1:] + _CANDS[:1]
    for c in order:
        if os.path.exists(c):
            return c
    raise SystemExit("找不到中文粗体字体：请安装 Noto Sans CJK SC，或设置环境变量 FONT_PATH 指向一个中文粗体字体文件")


def load_font(size, black=True):
    path = find_font(black)
    for idx in (2, 0):  # .ttc 里简体中文通常是第 3 个（index=2）；单字体文件用 0
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.truetype(path, size)


def grad(w, h, c1, c2):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(c1)[None, None] * (1 - t) + np.array(c2)[None, None] * t
    return Image.fromarray(np.repeat(a, w, 1).astype(np.uint8), "RGB")


def grad_text(txt, size, c1, c2, stroke=0, stroke_col=(30, 15, 5), shadow=True, black=True):
    f = load_font(size, black)
    bb = f.getbbox(txt, stroke_width=stroke)
    pad = int(size * .3)
    w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
    ox, oy = pad - bb[0], pad - bb[1]
    fm = Image.new("L", (w, h)); ImageDraw.Draw(fm).text((ox, oy), txt, font=f, fill=255)
    sm = Image.new("L", (w, h)); ImageDraw.Draw(sm).text((ox, oy), txt, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh.putalpha(sm.filter(ImageFilter.GaussianBlur(size * .06)).point(lambda v: int(v * .6)))
        out.alpha_composite(sh, (int(size * .03), int(size * .06)))
    if stroke:
        st = Image.new("RGBA", (w, h), stroke_col + (255,)); st.putalpha(sm); out.alpha_composite(st)
    top = bb[1] + oy; bot = bb[3] + oy
    g2 = Image.new("RGBA", (w, h), c2 + (255,))
    g2.paste(grad(w, max(1, bot - top), c1, c2), (0, top)); g2.putalpha(fm)
    out.alpha_composite(g2)
    return out


def shear(im, k):
    w, h = im.size
    return im.transform((w + int(h * abs(k)), h), Image.AFFINE, (1, k, -h * k if k > 0 else 0, 0, 1, 0), Image.BICUBIC)


def glow(im, col, r):
    a = im.getchannel("A").filter(ImageFilter.GaussianBlur(r))
    g = Image.new("RGBA", im.size, col + (0,)); g.putalpha(a.point(lambda v: min(255, int(v * 1.6))))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(im)
    return out


def _tw(txt, font):
    return int(ImageDraw.Draw(Image.new("RGB", (2, 2))).textlength(txt, font=font))


# 1) 体重秤读数屏：number="60"，unit="KG"
def scale(number="60", unit="KG", **_):
    W, H = 560, 230
    im = Image.new("RGBA", (W + 60, H + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sh = Image.new("L", im.size); ImageDraw.Draw(sh).rounded_rectangle((34, 40, W + 34, H + 40), 40, fill=150)
    s2 = Image.new("RGBA", im.size, (0, 0, 0, 0)); s2.putalpha(sh.filter(ImageFilter.GaussianBlur(14))); im.alpha_composite(s2)
    d.rounded_rectangle((30, 30, W + 30, H + 30), 40, fill=(18, 24, 30, 235), outline=(190, 200, 210, 255), width=6)
    d.rounded_rectangle((52, 52, W + 8, H + 8), 28, fill=(8, 40, 44, 255))
    num = glow(grad_text(str(number), 170, (200, 255, 250), (60, 230, 210), shadow=False), (40, 255, 220), 10)
    im.alpha_composite(num, (70, 30 + (H - num.height) // 2 + 6))
    kg = glow(grad_text(unit, 84, (200, 255, 250), (60, 230, 210), shadow=False), (40, 255, 220), 6)
    im.alpha_composite(kg, (70 + num.width - 30, 30 + H - kg.height - 6))
    return im


# 2) 金色渐变斜体大数字 + 白底小签：text="300g"，label="优质碳水"（label 只写文案里有的词）
def gold(text="300g", label="", **_):
    n = shear(grad_text(text, 200, (255, 250, 210), (255, 170, 30), stroke=12, stroke_col=(70, 30, 5)), -0.12)
    if not label:
        return n
    f = load_font(56, black=True)
    chip = Image.new("RGBA", (_tw(label, f) + 64, 92), (0, 0, 0, 0)); d = ImageDraw.Draw(chip)
    d.rounded_rectangle((0, 0, chip.width - 1, 91), 46, fill=(255, 255, 255, 245), outline=(70, 30, 5, 255), width=5)
    d.text((32, 6), label, font=f, fill=(150, 70, 10))
    W = max(n.width, chip.width) + 20
    im = Image.new("RGBA", (W, n.height + chip.height - 30), (0, 0, 0, 0))
    im.alpha_composite(n, ((W - n.width) // 2, 0))
    im.alpha_composite(chip.rotate(4, expand=True, resample=Image.BICUBIC), (W - chip.width - 30, n.height - 60))
    return im


# 3) 红色优惠券：label="立减"，number="100"
def coupon(label="立减", number="100", **_):
    W, H = 640, 250
    im = Image.new("RGBA", (W + 60, H + 60), (0, 0, 0, 0))
    m = Image.new("L", im.size); dm = ImageDraw.Draw(m); dm.rounded_rectangle((30, 30, W + 30, H + 30), 34, fill=255)
    for cx in (30, W + 30):
        dm.ellipse((cx - 30, 30 + H / 2 - 30, cx + 30, 30 + H / 2 + 30), fill=0)
    for y in range(52, H + 20, 26):
        dm.ellipse((236 - 6, y - 6, 236 + 6, y + 6), fill=0)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(m.filter(ImageFilter.GaussianBlur(12)).point(lambda v: int(v * .55)))
    im.alpha_composite(sh, (6, 12))
    body = grad(im.width, im.height, (255, 70, 60), (200, 10, 25)).convert("RGBA"); body.putalpha(m); im.alpha_composite(body)
    d = ImageDraw.Draw(im); d.rounded_rectangle((44, 44, W + 16, H + 16), 26, outline=(255, 210, 120, 255), width=4)
    d.text((72, 30 + H / 2 - 62), label, font=load_font(78), fill=(255, 255, 255))
    num = shear(grad_text(str(number), 190, (255, 255, 200), (255, 200, 40), stroke=10, stroke_col=(120, 0, 10)), -0.1)
    im.alpha_composite(num, (262, 30 + (H - num.height) // 2 + 4))
    return im.rotate(-4, expand=True, resample=Image.BICUBIC)


# 4) 时间跳转标题：title="一个月后"，subtitle="O N E   M O N T H   L A T E R"
def timejump(title="一个月后", subtitle="O N E   M O N T H   L A T E R", **_):
    t = grad_text(title, 110, (255, 255, 255), (235, 235, 240), stroke=8, stroke_col=(20, 20, 25))
    f = load_font(34, black=False)
    W = max(t.width, _tw(subtitle, f) + 40) + 20
    im = Image.new("RGBA", (W, t.height + 90), (0, 0, 0, 0)); im.alpha_composite(t, (0, 0)); d = ImageDraw.Draw(im)
    im.alpha_composite(grad(W - 40, 10, (255, 230, 140), (230, 160, 30)).convert("RGBA"), (30, t.height - 22))
    d.text((34, t.height + 2), subtitle, font=f, fill=(0, 0, 0, 160)); d.text((32, t.height), subtitle, font=f, fill=(255, 225, 140))
    return im


BUILDERS = {"scale": scale, "gold": gold, "coupon": coupon, "timejump": timejump}


def build(spec):
    """spec 例：{"type":"coupon","label":"立减","number":"100"}"""
    kw = {k: v for k, v in spec.items() if k not in ("type", "delay", "y")}
    return BUILDERS[spec["type"]](**kw)


# ================= 干货科普用的元素（accent 是强调色 (R,G,B)，每个项目可以自己定）=================
def _stroke_text(text, size, fill, stroke, stroke_col=(0, 0, 0, 255), black=True, pad=14):
    f = load_font(size, black=black)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w = int(tmp.textlength(text, font=f)) + 2 * (stroke + pad)
    h = int(size * 1.3) + 2 * (stroke + pad)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((stroke + pad + 3, stroke + pad + 4), text, font=f, fill=(0, 0, 0, 120), stroke_width=stroke, stroke_fill=(0, 0, 0, 120))
    d.text((stroke + pad, stroke + pad), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_col)
    return im


def title_banner(text, accent=(255, 90, 40), **_):
    """钩子标题：顶部一条强调色底的大标题。text 太长会自动缩小字号，保证不出画面（宽度上限 1000）。"""
    size = 96
    while size > 48:
        f = load_font(size)
        if ImageDraw.Draw(Image.new("RGBA", (10, 10))).textlength(text, font=f) <= 900: break
        size -= 6
    t = _stroke_text(text, size, (255, 255, 255, 255), 8)
    im = Image.new("RGBA", (t.width + 80, t.height + 36), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 30, fill=tuple(accent) + (235,))
    d.rounded_rectangle((6, 6, im.width - 7, im.height - 7), 26, outline=(255, 255, 255, 110), width=3)
    im.alpha_composite(t, (40, 18)); return im


def numcard(text="3", label="", accent=(255, 90, 40), **_):
    """数字卡：大数字（强调色渐变）+ 下方小标签，例：text="30"，label="秒 / 组"。"""
    lite = tuple(min(255, c + 90) for c in accent)
    big = shear(grad_text(str(text), 230, lite, tuple(accent), stroke=12, stroke_col=(0, 0, 0)), -0.08)
    if not label: return big
    lab = _stroke_text(label, 64, (255, 255, 255, 255), 8, black=False)
    im = Image.new("RGBA", (max(big.width, lab.width), big.height + lab.height - 10), (0, 0, 0, 0))
    im.alpha_composite(big, ((im.width - big.width) // 2, 0)); im.alpha_composite(lab, ((im.width - lab.width) // 2, big.height - 10))
    return im


def keyword(text, accent=(255, 90, 40), size=118, **_):
    """关键词跳出：强调色大字加黑边，出现时弹一下。"""
    return _stroke_text(text, size, tuple(accent) + (255,), 10)


def progress_bar(step, total, label="ROUND", accent=(255, 90, 40), **_):
    """进度条：左上文字 “ROUND 2/6”，下面一条细进度条（宽 760）。step 从 1 开始。"""
    Wb = 760
    t = _stroke_text(f"{label} {step}/{total}", 50, (255, 255, 255, 255), 6, black=False, pad=8)
    im = Image.new("RGBA", (Wb + 40, t.height + 34), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    im.alpha_composite(t, (14, 0)); y = t.height + 4
    d.rounded_rectangle((20, y, 20 + Wb, y + 16), 8, fill=(0, 0, 0, 150))
    fw = max(16, int(Wb * min(step, total) / float(total)))
    d.rounded_rectangle((20, y, 20 + fw, y + 16), 8, fill=tuple(accent) + (255,))
    d.rounded_rectangle((20, y, 20 + Wb, y + 16), 8, outline=(255, 255, 255, 120), width=2)
    return im
