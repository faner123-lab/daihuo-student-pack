# 3D 剧情带货 · 竖屏 1080x1920 30fps 渲染（画面 + 字幕 + 贴卡 + 转场）
# 用法：
#   python3 render.py 项目文件夹                      没有配音：按字数估算时间轴，出“无配音预览”
#   python3 render.py 项目文件夹 --dur vo/dur.txt     有配音：按 dur.txt 每句时长对点（秒，已含变速）
#   python3 render.py 项目文件夹 --quick S05,S06      只渲染指定镜头，快速看效果
# 项目文件夹里要有：project.json、clips/（H3 片段，如 S01.mp4）、可选 cards/（贴图原图）
# 干货科普用的可选项（都不写就是原来的带货效果）：
#   project.json 顶层  "style": {"accent":[255,90,40], "highlight":["核心","腹肌"]}   强调色、字幕里要染成强调色的词
#                     "lines_en": ["英文第1句", ...]                                   有就出中英双语字幕（和 lines 一一对应）
#                     "progress": {"total": 6, "label": "ROUND"}                       有就在带 step 的镜头显示进度条
#                     "transition_scale": 1.8                                           转场放慢（默认 1.0；干货建议 1.8）
#   每个镜头里        "title":"钩子标题"  "step":2  "numcard":{"text":"30","label":"秒 / 组","delay":0.3,"y":700}
#                     "keywords":[{"text":"核心","at":0.6,"dur":1.3,"y":560}]
import sys, os, re, math, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import design_cards as DC

W, H, FPS = 1080, 1920, 30
GAP = 0.10          # 句间空隙（秒），要和 mix.py 一致
args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
WORK = os.path.abspath(args[0]); OUT = os.path.join(WORK, "out"); os.makedirs(OUT, exist_ok=True)
CFG = json.load(open(os.path.join(WORK, "project.json"), encoding="utf-8"))
LINES = CFG["lines"]; N = len(LINES)
TS = float(CFG.get("transition_scale", 1.0))   # 转场速度倍率，干货片建议 1.8（单个转场约 0.35–0.4 秒）
STYLE = CFG.get("style", {}); ACC = tuple(STYLE.get("accent", [255, 90, 40])); HL = STYLE.get("highlight", [])
LINES_EN = CFG.get("lines_en"); PROG = CFG.get("progress")
if LINES_EN and len(LINES_EN) != N: sys.exit("lines_en 的句数要和 lines 一样（%d 句）" % N)
DUR_FILE = args[args.index("--dur") + 1] if "--dur" in args else None
ONLY = args[args.index("--quick") + 1].split(",") if "--quick" in args else None

# ---------- 时间轴 ----------
def est_len(t):  # 没有配音时按字数估算：约每秒 5.6 字
    return len(re.sub(r"[，。、！？,.!?]", "", t)) / 5.6 + 0.15

if DUR_FILE:
    d = {}
    for l in open(os.path.join(WORK, DUR_FILE) if not os.path.isabs(DUR_FILE) else DUR_FILE):
        if l.strip():
            k, v = l.split(); d[int(k)] = float(v)
    durs = [d[i + 1] for i in range(N)]
else:
    durs = [est_len(l) for l in LINES]
ls, le, t = [], [], 0.0
for x in durs:
    ls.append(t); le.append(t + x); t += x + GAP
seg = list(zip(ls, le)); END = le[-1] + CFG.get("tail", 1.0)

def win(k):  # 第 k 句（0 起）的画面窗口
    a = 0.0 if k == 0 else ls[k] - 0.08
    b = END if k == N - 1 else ls[k + 1] - 0.08
    return a, b

# ---------- 镜头表 ----------
SHOTS = []
for sh in CFG["shots"]:
    a, b = win(sh["line"])
    SHOTS.append(dict(name=sh["name"], k=sh["line"], t0=a + (b - a) * sh.get("frac", 0), clip=sh.get("clip", sh["name"]),
                      ss=sh.get("ss", 0.0), enter=sh.get("enter", "hard"), card=sh.get("card"), design=sh.get("design"),
                      arrow=sh.get("arrow", False), sfx=sh.get("sfx", []), title=sh.get("title"), step=sh.get("step"),
                      numcard=sh.get("numcard"), keywords=sh.get("keywords", [])))
for i, s in enumerate(SHOTS):
    s["t1"] = SHOTS[i + 1]["t0"] if i + 1 < len(SHOTS) else END
    s["dur"] = s["t1"] - s["t0"]
    s["nextenter"] = SHOTS[i + 1]["enter"] if i + 1 < len(SHOTS) else None

# ---------- 字幕：白字黑边，只用一行，底边距 290 ----------
MAXW = 11.0
def tw_units(t): return sum(0.55 if c.isascii() and c.strip() else 1.0 for c in t)
def chunks(p):
    if tw_units(p) <= MAXW: return [p]
    toks = re.findall(r"[A-Za-z0-9]+|.", p); n = math.ceil(tw_units(p) / MAXW); tgt = tw_units(p) / n
    out, cur = [], ""
    for tk in toks:
        if cur and tw_units(cur + tk) > tgt + 0.6 and len(out) < n - 1: out.append(cur); cur = ""
        cur += tk
    out.append(cur); return out
def phrases(k):
    # 字幕写用户原文（LINES），不用发音修正后的字
    parts = [c for p in re.split(r"[，。！？]", LINES[k]) if p for c in chunks(p.replace("、", " "))]
    a, b = seg[k]; tot = sum(tw_units(p) for p in parts); out = []; t0 = a
    for p in parts:
        d = (b - a) * tw_units(p) / tot; out.append((t0, t0 + d + (0.1 if p == parts[-1] else 0), p, LINES_EN[k] if LINES_EN else None)); t0 += d
    return out
SUBS = [x for k in range(N) for x in phrases(k)]
FS = DC.load_font(80, black=False)
SUB_BOTTOM = 290
_subcache = {}
FE = {}
def _hl_mask(txt):
    m = [False] * len(txt)
    for w in HL:
        i = txt.find(w)
        while i >= 0:
            for j in range(i, i + len(w)): m[j] = True
            i = txt.find(w, i + len(w))
    return m
def sub_img(txt, en=None):
    key = (txt, en)
    if key in _subcache: return _subcache[key]
    im = Image.new("RGBA", (W, 130 + (80 if en else 0)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); tw = d.textlength(txt, font=FS)
    x0 = (W - tw) / 2
    d.text((x0 + 3, 13), txt, font=FS, fill=(0, 0, 0, 150), stroke_width=8, stroke_fill=(0, 0, 0, 150))
    d.text((x0, 10), txt, font=FS, fill=(255, 255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))   # 先画黑边
    m = _hl_mask(txt)
    for i, ch in enumerate(txt):                                   # 再逐字上色：重点词染成强调色
        col = tuple(ACC) + (255,) if m[i] else (255, 255, 255, 255)
        d.text((x0 + d.textlength(txt[:i], font=FS), 10), ch, font=FS, fill=col)
    if en:
        size = 46
        while size > 28:
            if size not in FE: FE[size] = DC.load_font(size, black=False)
            if d.textlength(en, font=FE[size]) <= W - 90: break
            size -= 2
        if size not in FE: FE[size] = DC.load_font(size, black=False)
        f = FE[size]; ew = d.textlength(en, font=f)
        d.text(((W - ew) / 2, 142), en, font=f, fill=(255, 255, 255, 235), stroke_width=6, stroke_fill=(0, 0, 0, 255))
    _subcache[key] = im; return im

# ---------- 贴图 ----------
def card(path, width):
    im = Image.open(os.path.join(WORK, path)).convert("RGB"); r = width / im.width
    im = im.resize((width, int(im.height * r)), Image.LANCZOS)
    pad = 10; c = Image.new("RGBA", (im.width + 2 * pad + 40, im.height + 2 * pad + 40), (0, 0, 0, 0))
    sh = Image.new("L", c.size, 0); ImageDraw.Draw(sh).rounded_rectangle((20, 26, c.width - 20, c.height - 14), 28, fill=140)
    c.putalpha(sh.filter(ImageFilter.GaussianBlur(12)))
    base = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (255, 255, 255, 255))
    base.paste(im, (pad, pad)); m = Image.new("L", base.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, base.width - 1, base.height - 1), 26, fill=255); base.putalpha(m)
    c.alpha_composite(base, (20, 14)); return c
def eo(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def eb(x):
    x = min(max(x, 0), 1); c1 = 1.7; c3 = c1 + 1; return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def paste_c(fr, im, cx, cy, sc=1.0, al=1.0):
    if sc != 1: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BICUBIC)
    if al < 1: a = im.getchannel("A").point(lambda v: int(v * al)); im = im.copy(); im.putalpha(a)
    fr.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ---------- 画面 ----------
def read_clip(path, ss, n):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-i", path, "-vf",
           f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS}",
           "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    fs = [Image.frombytes("RGB", (W, H), raw[i * W * H * 3:(i + 1) * W * H * 3]) for i in range(len(raw) // (W * H * 3))]
    if not fs: sys.exit("读不到片段：" + path)
    while len(fs) < n: fs.append(fs[-1])
    return fs[:n]
def zoomc(im, z, dx=0):
    if abs(z - 1) < 1e-3 and dx == 0: return im
    w, h = int(W * z), int(H * z); r = im.resize((w, h), Image.BICUBIC)
    l = int(min(max((w - W) / 2 + dx, 0), w - W)); t = (h - H) // 2
    return r.crop((l, t, l + W, t + H))
def enter_fx(fr, kind, t):
    """进场转场：hard/open 硬切；zoom 放大冲击；push 推近模糊；hwhip 甩镜；white/longwhite 白闪；black 黑场亮起"""
    if kind in ("hard", "open"): return fr
    t = t / TS      # 转场整体放慢：TS=1.8 时 0.2 秒的转场变成约 0.36 秒
    if kind == "zoom" and t < 0.2: return zoomc(fr, 1.10 - 0.10 * eo(t / 0.2))
    if kind == "push" and t < 0.22:
        k = eo(t / 0.22); fr = zoomc(fr, 1.38 - 0.38 * k)
        return fr.filter(ImageFilter.GaussianBlur(8 * (1 - k))) if t < 0.16 else fr
    if kind == "hwhip" and t < 0.16:
        k = eo(t / 0.16); fr = zoomc(fr, 1.22 - 0.22 * k, dx=-260 * (1 - k))
        a = np.asarray(fr, np.float32); acc = np.zeros_like(a)
        for s in range(7): acc += np.roll(a, int(-60 * (1 - k) * s / 7), axis=1)
        return Image.fromarray((acc / 7).astype(np.uint8))
    if kind in ("white", "longwhite"):
        d = 0.22 if kind == "longwhite" else 0.14
        if t < d: return Image.blend(Image.new("RGB", (W, H), "white"), fr, t / d)
    if kind == "black" and t < 0.22: return Image.blend(Image.new("RGB", (W, H), "black"), fr, t / 0.22)
    return fr

def render(s, enc, is_last):
    n = int(round(s["t1"] * FPS)) - int(round(s["t0"] * FPS)); dur = s["dur"]
    frames = read_clip(os.path.join(WORK, "clips", s["clip"] + ".mp4"), s["ss"], n)
    cd = s["card"]; ds = s["design"]
    c_im = card(cd["img"], cd.get("width", 820)) if cd else None
    d_im = DC.build(ds) if ds else None
    d_tag = bool(ds) and ds["type"] == "timejump"       # 时间跳转标题放左上，其余居中弹出
    t_im = DC.title_banner(s["title"], accent=ACC) if s.get("title") else None
    p_im = DC.progress_bar(s["step"], PROG["total"], PROG.get("label", "ROUND"), accent=ACC) if (s.get("step") and PROG) else None
    n_im = DC.numcard(s["numcard"]["text"], s["numcard"].get("label", ""), accent=ACC) if s.get("numcard") else None
    k_ims = [(k, DC.keyword(k["text"], accent=ACC)) for k in s.get("keywords", [])]
    for i in range(n):
        t = i / FPS; rem = dur - t
        fr = zoomc(frames[i], 1.0 + 0.06 * t / max(dur, 0.5))   # 每镜 6% 缓推
        fr = ImageEnhance.Contrast(fr).enhance(1.05); fr = ImageEnhance.Color(fr).enhance(1.08)
        fr = enter_fx(fr, s["enter"], t)
        if s["nextenter"] in ("hwhip", "push") and rem < 0.1: fr = zoomc(fr, 1.0 + 0.12 * (1 - rem / 0.1))
        fr = fr.convert("RGBA")
        if c_im is not None and t > cd.get("delay", 0.15):          # 贴卡：画面上部，淡入上滑
            k = eo((t - cd.get("delay", 0.15)) / 0.25); al = k * (min(1, rem / 0.15) if rem < 0.15 else 1)
            paste_c(fr, c_im, W / 2, 150 + c_im.height / 2 + 50 * (1 - k), 1.0, al)
        if d_im is not None:
            dl = ds.get("delay", 0.4)
            if d_tag and t > dl:
                k = eo((t - dl) / 0.3); paste_c(fr, d_im, 60 + d_im.width / 2 - 120 * (1 - k), ds.get("y", 300), 1.0, k)
            elif not d_tag and t > dl:
                lt = t - dl; paste_c(fr, d_im, W / 2, ds.get("y", 820), 0.5 + 0.5 * eb(lt / 0.28), min(1, lt / 0.08))
        if p_im is not None: paste_c(fr, p_im, W / 2, 120 + p_im.height / 2, 1.0, min(1, t / 0.2))       # 进度条：顶部
        if t_im is not None:                                                                          # 钩子标题：进度条下面，淡入下滑
            k = eo(t / 0.3); paste_c(fr, t_im, W / 2, 330 + (0 if p_im is None else 0) - 30 * (1 - k), 0.8 + 0.2 * eb(t / 0.35), k * (min(1, rem / 0.15) if rem < 0.15 else 1))
        if n_im is not None and t > s["numcard"].get("delay", 0.3):                                   # 数字卡：弹出
            lt = t - s["numcard"].get("delay", 0.3); paste_c(fr, n_im, W / 2, s["numcard"].get("y", 760), 0.5 + 0.5 * eb(lt / 0.3), min(1, lt / 0.08))
        for kw, im_k in k_ims:                                                                        # 关键词跳出：弹出、停留、淡出
            a0 = kw.get("at", 0.5); dd = kw.get("dur", 1.3); lt = t - a0
            if 0 <= lt < dd:
                fade = min(1, (dd - lt) / 0.2); paste_c(fr, im_k, W / 2, kw.get("y", 560), 0.5 + 0.5 * eb(lt / 0.25), min(1, lt / 0.08) * fade)
        if s["arrow"] and t > 0.3:                                    # 红色向下箭头（放在字幕上方）
            k = eo((t - 0.3) / 0.25); lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
            y = 960 + 14 * math.sin(t * 8); x = 150
            dd.rectangle((x - 30, y - 120, x + 30, y), fill=(235, 30, 30, int(255 * k)))
            dd.polygon([(x - 80, y), (x + 80, y), (x, y + 110)], fill=(235, 30, 30, int(255 * k))); fr.alpha_composite(lay)
        T = s["t0"] + t
        for (a, b, txt, en) in SUBS:
            if a <= T < b:
                im = sub_img(txt, en); fr.alpha_composite(im, (0, int(H - SUB_BOTTOM - 130))); break
        if is_last and rem < 0.6: fr = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), fr, max(0, rem / 0.6))
        enc.stdin.write(fr.convert("RGB").tobytes())

if __name__ == "__main__":
    name = os.path.join(OUT, "quick.mp4" if ONLY else "video_noaudio.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", name], stdin=subprocess.PIPE)
    print("总时长", round(END, 2), "秒，镜头", len(SHOTS), "个")
    for i, s in enumerate(SHOTS):
        if ONLY and s["name"] not in ONLY: continue
        print(s["name"], round(s["t0"], 2), round(s["dur"], 2), flush=True); render(s, enc, i == len(SHOTS) - 1)
    enc.stdin.close(); enc.wait()
    json.dump(dict(END=END, seg=seg, GAP=GAP, shots=[{k: s[k] for k in ("name", "t0", "t1", "enter", "sfx")} for s in SHOTS]),
              open(os.path.join(OUT, "marks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("完成", name)
