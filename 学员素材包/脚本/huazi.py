# 阿炎带货 · 开场花字 + "今天阿炎讲" 裂开标题 —— 模板脚本
# 用法: python3 huazi.py <开场背景图> <标题背景图> <输出帧目录>
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H, FPS = 1280, 720, 30
FONT = os.environ.get("FONT_PATH", "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc")  # 换机器时用环境变量 FONT_PATH 指向中文粗体字体
FIDX = 2  # SC

# 颜色方案（上→下渐变）
GRAD = {
    "white": [(255, 255, 255), (222, 226, 232)],
    "blue":  [(225, 246, 255), (52, 150, 255)],
    "gold":  [(255, 248, 190), (255, 176, 20)],
    "pink":  [(255, 214, 236), (255, 72, 150)],
    "green": [(220, 255, 200), (40, 210, 60)],
}

def font(sz):
    return ImageFont.truetype(FONT, sz, index=FIDX)

def gradient(w, h, c1, c2):
    t = np.linspace(0, 1, h)[:, None]
    a = np.array(c1)[None, None, :] * (1 - t[..., None]) + np.array(c2)[None, None, :] * t[..., None]
    a = np.repeat(a, w, axis=1)
    return Image.fromarray(a.astype(np.uint8), "RGB")

def render_word(text, size, color, stroke=None, shear=0.0, shadow=True):
    """单个词：渐变填充 + 深色描边 + 柔和投影，返回 RGBA"""
    f = font(size)
    sw = stroke if stroke is not None else max(2, int(size * 0.06))
    bbox = f.getbbox(text, stroke_width=sw)
    pad = int(size * 0.35)
    w, h = bbox[2] - bbox[0] + pad * 2, bbox[3] - bbox[1] + pad * 2
    ox, oy = pad - bbox[0], pad - bbox[1]
    fill_m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(fill_m).text((ox, oy), text, font=f, fill=255)
    stroke_m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(stroke_m).text((ox, oy), text, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = stroke_m.filter(ImageFilter.GaussianBlur(size * 0.07))
        sh_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh_img.putalpha(sh.point(lambda v: int(v * 0.65)))
        out.alpha_composite(sh_img, (int(size * 0.04), int(size * 0.06)))
    st = Image.new("RGBA", (w, h), (24, 16, 10, 255)); st.putalpha(stroke_m)
    out.alpha_composite(st)
    top, bot = bbox[1] + oy, bbox[3] + oy
    g = gradient(w, max(1, bot - top), *GRAD[color])
    gfull = Image.new("RGB", (w, h), GRAD[color][1]); gfull.paste(g, (0, top))
    fl = gfull.convert("RGBA"); fl.putalpha(fill_m)
    out.alpha_composite(fl)
    if shear:
        out = out.transform((w + int(h * abs(shear)), h), Image.AFFINE,
                            (1, shear, -h * shear if shear > 0 else 0, 0, 1, 0), Image.BICUBIC)
    return out

def render_line(parts, baseline_gap=0):
    """parts: [(文字, 字号, 颜色, 斜切)] 底部对齐拼成一行"""
    ims = [render_word(t, s, c, shear=sh) for (t, s, c, sh) in parts]
    sizes = [p[1] for p in parts]
    pads = [int(s * 0.35) for s in sizes]
    widths = [im.width - 2 * p for im, p in zip(ims, pads)]
    tw = sum(widths) + max(pads) * 2
    th = max(im.height for im in ims)
    line = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    x = max(pads) - pads[0]
    for im, p, wd in zip(ims, pads, widths):
        line.alpha_composite(im, (x, th - im.height))
        x += wd
    return line

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_back(t):
    t = min(max(t, 0), 1); c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def place(canvas, im, cx, cy, scale=1.0, alpha=1.0, blur=0.0, dx=0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if blur > 0.3:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2 + dx), int(cy - im.height / 2)))

def bg_frame(img, t, dur, zoom=(1.0, 1.06)):
    z = zoom[0] + (zoom[1] - zoom[0]) * (t / dur)
    w, h = int(W * z), int(H * z)
    im = img.resize((w, h), Image.BICUBIC)
    l, tp = (w - W) // 2, (h - H) // 2
    return im.crop((l, tp, l + W, tp + H)).convert("RGBA")

def load_bg(p):
    im = Image.open(p).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r + .5), int(im.height * r + .5)), Image.BICUBIC)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((l, t, l + W, t + H))

# ---------- 段1：开场两行花字 ----------
def opening(bg, out, start_idx, dur=2.4, line1=None, line2=None):
    L1 = render_line(line1); L2 = render_line(line2)
    c1 = (W * 0.44, H * 0.56); c2 = (W * 0.60, H * 0.60 + L1.height * 0.62)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        fr = bg_frame(bg, t, dur)
        if t < 0.2:  # 画面模糊进入（承接上一镜的糊切）
            fr = fr.filter(ImageFilter.GaussianBlur(18 * (1 - t / 0.2)))
        # 第1行：缩小+去模糊+淡入  0.12~0.34s
        k = ease_out((t - 0.12) / 0.22)
        if k > 0:
            place(fr, L1, *c1, scale=1.18 - 0.18 * k, alpha=k, blur=10 * (1 - k))
        # 第2行：从右侧滑入+回弹  0.62~0.88s
        k2 = (t - 0.62) / 0.26
        if k2 > 0:
            e = ease_back(k2)
            place(fr, L2, c2[0], c2[1], scale=1.25 - 0.25 * min(1, e), alpha=min(1, k2 * 2),
                  blur=8 * max(0, 1 - k2 * 1.6), dx=60 * (1 - min(1, e)))
        # 结尾 0.22s 横向甩糊（接“嗖”）
        tail = t - (dur - 0.22)
        if tail > 0:
            k3 = tail / 0.22
            arr = fr.convert("RGB")
            arr = arr.filter(ImageFilter.BoxBlur(1))
            m = Image.new("RGB", (W, H))
            steps = 9; shift = int(160 * k3)
            acc = np.zeros((H, W, 3), np.float32); a0 = np.asarray(arr, np.float32)
            for s in range(steps):
                acc += np.roll(a0, int(-shift * s / steps), axis=1)
            fr = Image.fromarray((acc / steps).clip(0, 255).astype(np.uint8)).convert("RGBA")
            fr = ImageEnhance.Brightness(fr).enhance(1 + 0.5 * k3)
        fr.convert("RGB").save(f"{out}/f{start_idx + i:05d}.png")
    return start_idx + n

# ---------- 段2：今天阿炎讲 → 关键词 裂开 ----------
def split_title(bg, out, start_idx, dur=2.0, title="今天阿炎讲", key="形象优先", key_color="gold"):
    T = render_word(title, 104, "white", stroke=3)            # 白字：细描边+投影
    K = render_word(key, 100, key_color, stroke=8, shear=0.12)  # 关键词：粗描边渐变+斜体
    cx, cy = W / 2, H * 0.74
    half = T.height // 2
    top, bot = T.crop((0, 0, T.width, half)), T.crop((0, half, T.width, T.height))
    glitch = {2: 26, 3: -14, 5: 34, 6: 0, 8: 20, 9: -10}   # 帧号 → 上下错位像素（故障抖动）
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        fr = bg_frame(bg, t, dur, zoom=(1.04, 1.10))
        b = 0.15 if t < 0.1 else min(1, 0.15 + (t - 0.1) / 0.45 * 0.85)  # 先压黑再亮起
        fr = ImageEnhance.Brightness(fr).enhance(b)
        a = min(1, max(0, (t - 0.03) / 0.18))
        if a > 0:
            if t < 0.72:
                g = glitch.get(i, None)
                if g is None:
                    place(fr, T, cx, cy, alpha=a)
                elif g == 0:
                    place(fr, T, cx, cy + 10, alpha=a)
                else:  # 上半往上、下半往下，瞬间错开
                    place(fr, top, cx - 6, cy - half / 2 - g, alpha=a)
                    place(fr, bot, cx + 6, cy + half / 2 + g, alpha=a)
            else:
                k = ease_out((t - 0.72) / 0.12)
                gap = int(T.height * 0.30 * k)
                place(fr, top, cx, cy - half / 2 - gap, alpha=0.95)
                place(fr, bot, cx, cy + half / 2 + gap, alpha=0.95)
                kk = (t - 0.74) / 0.24
                if kk > 0:
                    s = 0.2 + 0.8 * ease_back(kk)
                    place(fr, K, cx + 8, cy, scale=s, alpha=min(1, kk * 3))
        fr.convert("RGB").save(f"{out}/f{start_idx + i:05d}.png")
    return start_idx + n

if __name__ == "__main__":
    bg1, bg2, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    A, B = load_bg(bg1), load_bg(bg2)
    idx = opening(A, out, 0, 2.4,
                  line1=[("25岁之前的", 70, "white", 0), ("主线任务", 94, "blue", 0.12)],
                  line2=[("变帅", 132, "gold", 0.14)])
    split_title(B, out, idx, 2.0)
    print("frames", idx + 60)
