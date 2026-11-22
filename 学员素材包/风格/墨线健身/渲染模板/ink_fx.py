# 墨线健身 · 绘制小工具：字体、描边字、徽章、缓动。render.py 会引用它。
import os, math
from PIL import Image, ImageDraw, ImageFont

YELLOW = (255, 214, 0); RED = (235, 50, 50); GREEN = (60, 200, 90); GRAY = (110, 110, 110); WHITE = (255, 255, 255)
COLORS = {"yellow": YELLOW, "red": RED, "green": GREEN, "white": WHITE}

_CANDS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
          "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/msyh.ttc", "/System/Library/Fonts/PingFang.ttc"]


def find_font():
    p = os.environ.get("FONT_PATH")          # 可以用环境变量 FONT_PATH 指定一个中文粗体字体文件
    if p and os.path.exists(p): return p
    for c in _CANDS:
        if os.path.exists(c): return c
    raise SystemExit("找不到中文粗体字体：请安装 Noto Sans CJK SC，或设置环境变量 FONT_PATH 指向一个中文粗体字体文件")


_FC = {}
def font(size):
    if size in _FC: return _FC[size]
    path = find_font()
    for idx in (2, 0):                        # .ttc 里简体中文通常是第 3 个（index=2）
        try:
            _FC[size] = ImageFont.truetype(path, size, index=idx); return _FC[size]
        except Exception: continue
    _FC[size] = ImageFont.truetype(path, size); return _FC[size]


def eo(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3                 # 先快后慢
def eb(x):                                                                     # 带回弹（pop 出现）
    x = min(max(x, 0.0), 1.0); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def stroke_text(text, size, fill=WHITE, stroke=8, hl=None, hl_col=YELLOW, pad=12):
    """描边大字（RGBA）。hl 是要染成强调色的词列表。"""
    f = font(size); w = int(f.getlength(text)) + 2 * (pad + stroke); h = int(size * 1.35) + 2 * (pad + stroke)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x0, y0 = pad + stroke, pad + stroke - int(size * 0.06)
    d.text((x0, y0), text, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    for wd in (hl or []):
        i = text.find(wd)
        while i >= 0:
            ox = x0 + int(f.getlength(text[:i]))
            d.text((ox, y0), wd, font=f, fill=hl_col + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            i = text.find(wd, i + len(wd))
    return im


def pill(text, size, col, pad_x=26, pad_y=12, filled=True, radius=None):
    """圆角标签（RGBA）：filled 时彩色底 + 黑字，否则彩色描边 + 彩色字。"""
    f = font(size); tw = int(f.getlength(text)); w = tw + 2 * pad_x; h = int(size * 1.3) + 2 * pad_y
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = radius if radius is not None else h // 2
    if filled:
        d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=col + (255,)); tc = (15, 15, 15)
    else:
        d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=(0, 0, 0, 200), outline=col + (255,), width=4); tc = col
    d.text((pad_x, pad_y - int(size * 0.04)), text, font=f, fill=tc + (255,))
    return im


def circle_badge(text, d_px, col, filled=True, size=None):
    d_px = int(d_px); im = Image.new("RGBA", (d_px, d_px), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if filled: d.ellipse((0, 0, d_px - 1, d_px - 1), fill=col + (255,)); tc = (15, 15, 15)
    else: d.ellipse((2, 2, d_px - 3, d_px - 3), fill=(0, 0, 0, 160), outline=col + (255,), width=3); tc = col
    f = font(size or int(d_px * 0.55)); tw = f.getlength(text)
    d.text(((d_px - tw) / 2, d_px * 0.12), text, font=f, fill=tc + (255,))
    return im


def paste_c(base, im, cx, cy, scale=1.0, alpha=1.0):
    """把 RGBA 小图按中心点贴到 RGBA 底图上，可缩放、可半透明。"""
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1) > 1e-3: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if alpha < 0.99:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2))) if (
        cx - im.width / 2 >= 0 and cy - im.height / 2 >= 0 and cx + im.width / 2 <= base.width and cy + im.height / 2 <= base.height
    ) else base.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)
