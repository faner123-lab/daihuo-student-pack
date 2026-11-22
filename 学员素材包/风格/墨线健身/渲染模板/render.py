# 墨线健身 · 横屏 1920x1080 30fps 渲染：黑底墨线人物 + 逐子句字幕 + 右侧标签列 + 进度/导航/难度阶梯 + 特写章 + 转场
# 用法：
#   python3 render.py 项目文件夹                      没有配音：按字数估算时间轴（每秒约 7 字）
#   python3 render.py 项目文件夹 --dur vo/dur.txt     有配音：每行「句号 秒数」（1 起），秒数是裁掉两端静音后的句长
#   python3 render.py 项目文件夹 --quick S02,S03      只渲染指定镜头，快速看效果
# 项目文件夹里要有：project.json、imgs/（人物图，黑底墨线 PNG/JPG，或带透明的 PNG）
# project.json 见 project.example.json 和 README.md
import sys, os, re, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import ink_fx as FX

W, H, FPS = 1920, 1080, 30
GAP = 0.22          # 句间空隙（秒），要和 mix.py 一致
V0 = 0.45           # 开场留白（秒）
args = sys.argv[1:]
if not args: sys.exit(__doc__)
WORK = os.path.abspath(args[0]); OUT = os.path.join(WORK, "out"); os.makedirs(OUT, exist_ok=True)
CFG = json.load(open(os.path.join(WORK, "project.json"), encoding="utf-8"))
LINES = CFG["lines"]; N = len(LINES); TS = float(CFG.get("transition_scale", 1.0))
HL = CFG.get("highlight", []); STEPS = CFG.get("steps", 0); MEM = CFG.get("memory", [])
DUR_FILE = args[args.index("--dur") + 1] if "--dur" in args else None
ONLY = args[args.index("--quick") + 1].split(",") if "--quick" in args else None
COLX = 1450          # 右侧标签列的左边界

# ---------- 时间轴 ----------
def est_len(t): return len(re.sub(r"[，。、！？：；,.!?:;]", "", t)) / 7.0 + 0.1
if DUR_FILE:
    d = {}
    for l in open(DUR_FILE if os.path.isabs(DUR_FILE) else os.path.join(WORK, DUR_FILE)):
        if l.strip(): k, v = l.split(); d[int(k)] = float(v)
    durs = [d[i + 1] for i in range(N)]
else:
    durs = [est_len(l) for l in LINES]
ls, le, t = [], [], V0
for x in durs: ls.append(t); le.append(t + x); t += x + GAP
seg = list(zip(ls, le)); END = le[-1] + CFG.get("tail", 1.0)
def win(k):
    a = 0.0 if k == 0 else ls[k] - 0.08
    b = END if k == N - 1 else ls[k + 1] - 0.08
    return a, b

def clauses(text):                    # 按 ，。！？：、； 切子句，每个子句一行字幕
    parts = [p for p in re.findall(r"[^，。！？：、；]+[，。！？：、；]?", text) if p.strip()]
    return [re.sub(r"[，。！？：、；]$", "", p) for p in parts] or [text]
def clause_times(k):                  # 子句起止：按字数比例分配该句时长（有真实时间码时可替换这里）
    cl = clauses(LINES[k]); w = np.array([max(1, len(c)) for c in cl], float); w /= w.sum()
    edges = np.concatenate([[0], np.cumsum(w)]) * durs[k] + ls[k]
    return cl, list(zip(edges[:-1], edges[1:]))

# ---------- 镜头表 ----------
SHOTS = []
for sh in CFG["shots"]:
    a, b = win(sh["line"]); cl, ct = clause_times(sh["line"])
    SHOTS.append(dict(sh, t0=a, t1=b, dur=b - a, cl=cl, ct=ct))
for i, s in enumerate(SHOTS):
    s["nextenter"] = SHOTS[i + 1].get("enter", "slide") if i + 1 < len(SHOTS) else "none"

# ---------- 素材 ----------
_IMG = {}
def stage_layer(path, tall=0.64):
    """人物图 → 1920x1080 黑底画布上的一层（RGB）。黑底图用“变亮”叠加，不会盖出黑框。返回 (层, 贴图左上角, 缩放比, 原图尺寸)"""
    if path in _IMG: return _IMG[path]
    im = Image.open(os.path.join(WORK, path)); alpha = im.convert("RGBA").getchannel("A") if im.mode in ("RGBA", "LA", "P") else None
    im = im.convert("RGB")
    if alpha is not None and np.asarray(alpha).min() < 250:       # 透明底 → 先铺到黑底上
        bg = Image.new("RGB", im.size, (0, 0, 0)); bg.paste(im, mask=alpha); im = bg
    sc = min(H * tall / im.height, 1250 / im.width); nw, nh = int(im.width * sc), int(im.height * sc)
    r = im.resize((nw, nh), Image.LANCZOS); cx, cy = 730, 500
    layer = np.zeros((H, W, 3), np.uint8); x0, y0 = cx - nw // 2, cy - nh // 2
    layer[y0:y0 + nh, x0:x0 + nw] = np.asarray(r)
    _IMG[path] = (layer, (x0, y0), sc, im); return _IMG[path]

_BG = None
def background():
    global _BG
    if _BG is None:                    # 纯黑底 + 很淡的暗角
        yy, xx = np.mgrid[0:H, 0:W]; v = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        _BG = np.clip(10 * (1 - 0.5 * v), 0, 12).astype(np.uint8)[:, :, None].repeat(3, 2)
    return _BG

def zoomc(im, z, dx=0, dy=0):
    if abs(z - 1) < 1e-3 and not dx and not dy: return im
    w, h = int(W * z), int(H * z); r = im.resize((w, h), Image.BILINEAR)
    l = int(min(max((w - W) / 2 + dx, 0), w - W)); tp = int(min(max((h - H) / 2 + dy, 0), h - H))
    return r.crop((l, tp, l + W, tp + H))

def enter_fx(fr, kind, t):
    """进场转场：slide 右侧滑入+压暗亮起；zoom 放大冲击；flash 白闪；dim 黑场亮起；hard 硬切（墨线风格不建议）"""
    t = t / TS
    if kind == "slide" and t < 0.45:
        k = FX.eo(t / 0.45); fr = zoomc(fr, 1.0, dx=int(-260 * (1 - k)))
        a = np.asarray(fr, np.float32) * (0.35 + 0.65 * k); return Image.fromarray(a.astype(np.uint8))
    if kind == "zoom" and t < 0.3: return zoomc(fr, 1.12 - 0.12 * FX.eo(t / 0.3))
    if kind == "flash" and t < 0.25: return Image.blend(Image.new("RGB", (W, H), "white"), fr, FX.eo(t / 0.25))
    if kind == "dim" and t < 0.35: return Image.blend(Image.new("RGB", (W, H), "black"), fr, FX.eo(t / 0.35))
    return fr

# ---------- 叠加层 ----------
SUBS = {}
def sub_img(txt):
    if txt not in SUBS: SUBS[txt] = FX.stroke_text(txt, 66, FX.WHITE, 9, hl=HL)
    return SUBS[txt]
_C = {}
def cached(key, fn):
    if key not in _C: _C[key] = fn()
    return _C[key]

def draw_top(fr, t, s):
    d = ImageDraw.Draw(fr); d.rounded_rectangle((32, 22, W - 32, 32), 5, fill=(45, 45, 45, 255))       # 顶部总进度条
    d.rounded_rectangle((32, 22, 32 + max(8, int((W - 64) * min(1, t / END))), 32), 5, fill=FX.YELLOW + (255,))
    step = s.get("step")
    if STEPS and step:                                                                                      # 动作导航徽章 + 第 n / N 个动作
        x = 52
        for i in range(1, STEPS + 1):
            b = cached(("nav", i, i == step, i < step), lambda i=i: FX.circle_badge(str(i), 54, FX.YELLOW if i <= step else FX.GRAY, filled=(i <= step)))
            fr.paste(b, (x, 56), b); x += 66
        lab = cached(("navt", step), lambda: FX.stroke_text("第 %d / %d 个动作" % (step, STEPS), 34, FX.WHITE, 5)); fr.paste(lab, (x + 6, 50), lab)
    if s.get("level") is not None:                                                                         # 难度阶梯条：新手 → 标准 → 进阶
        x = 52
        for i, nm in enumerate(["新手", "标准", "进阶"]):
            p = cached(("lv", i, i <= s["level"]), lambda i=i, nm=nm: FX.pill(nm, 30, FX.YELLOW if i <= s["level"] else FX.GRAY, 20, 6, filled=(i <= s["level"])))
            fr.paste(p, (x, 126), p); x += p.width + 14
    if s.get("reps"):                                                                                       # 计次徽章
        p = cached(("reps", s["reps"]), lambda: FX.pill(s["reps"], 44, FX.YELLOW, 28, 8, filled=False)); fr.paste(p, (W - p.width - 52, 54), p)

def draw_labels(fr, lt, s):
    act = None
    for lb in s.get("labels", []):                                                                          # 同一时刻只有一个标签，新的出现旧的消失
        if lb["at"] <= lt < lb["at"] + lb.get("dur", 1.8): act = lb
    if act:
        tt = lt - act["at"]; col = FX.COLORS.get(act.get("color", "yellow"), FX.YELLOW)
        im = cached(("lb", act["text"], str(col)), lambda: FX.pill(act["text"], 54, col, 34, 14, filled=True))
        k = FX.eb(tt / 0.28); out = FX.eo((act["at"] + act.get("dur", 1.8) - lt) / 0.15)
        FX.paste_c(fr, im, COLX + im.width / 2, act.get("y", 300), 0.4 + 0.6 * k, min(1, out))

def draw_inset(fr, lt, s, base_xy_sc, pose_img):
    ins = s.get("inset")                                                                                    # 特写章：圆形放大 + 引线，0.4s 弹出、引线 0.4s 画出
    if not ins or not (ins["at"] <= lt < ins["at"] + ins.get("dur", 2.0)): return
    tt = lt - ins["at"]; (x0, y0), sc, src = base_xy_sc; u, v, rr = ins["u"], ins["v"], ins.get("r", 0.12)
    px, py = x0 + u * src.width * sc, y0 + v * src.height * sc                                              # 部位在屏幕上的位置
    R = int(rr * src.width); box = (int(u * src.width - R), int(v * src.height - R), int(u * src.width + R), int(v * src.height + R))
    crop = src.crop(box).resize((300, 300), Image.LANCZOS)
    m = Image.new("L", (300, 300), 0); ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255)
    chip = Image.new("RGBA", (340, 340), (0, 0, 0, 0)); d = ImageDraw.Draw(chip)
    d.ellipse((0, 0, 339, 339), fill=(0, 0, 0, 255), outline=FX.YELLOW + (255,), width=6); chip.paste(crop, (20, 20), m)
    cx, cy = COLX + 170, ins.get("y", 520); k = FX.eb(tt / 0.4)
    d2 = ImageDraw.Draw(fr); kk = FX.eo(max(0, tt - 0.1) / 0.4)
    ex, ey = px + (cx - 170 - px) * kk, py + (cy - py) * kk; d2.line((px, py, ex, ey), fill=FX.YELLOW + (255,), width=5)
    d2.ellipse((px - 14, py - 14, px + 14, py + 14), outline=FX.YELLOW + (255,), width=5)
    FX.paste_c(fr, chip, cx, cy, 0.3 + 0.7 * k, min(1, k))

def draw_memory(fr, s):
    if not MEM: return                                                                                      # 常驻记忆组件：每讲完一个动作，对应部位亮黄
    done = (s.get("step") or 0) if STEPS else 0; y = 730 if len(MEM) <= 4 else 700 - 40 * (len(MEM) - 4)
    for i, nm in enumerate(MEM):
        on = i < done; p = cached(("mem", nm, on), lambda nm=nm, on=on: FX.pill(nm, 28, FX.YELLOW if on else FX.GRAY, 18, 6, filled=on))
        fr.paste(p, (W - p.width - 40, y), p); y += p.height + 10
    t = cached(("memt", done), lambda: FX.stroke_text("已唤醒 %d/%d" % (done, len(MEM)), 30, FX.YELLOW, 5)); fr.paste(t, (W - t.width - 28, y), t)

# ---------- 逐镜渲染 ----------
def render(s, enc, is_last):
    n = int(round(s["t1"] * FPS)) - int(round(s["t0"] * FPS)); dur = s["dur"]; bg = background()
    poses = s.get("poses") or [s["image"]]
    for i in range(n):
        gt = s["t0"] + i / FPS; lt = i / FPS; rem = dur - lt
        ci = next((j for j, (a, b) in enumerate(s["ct"]) if gt < b), len(s["ct"]) - 1)                     # 当前子句
        pose = poses[min(ci, len(poses) - 1)]                                                              # 每个子句换一个姿势 → 画面持续有变化
        layer, xy, sc, src = stage_layer(pose)
        stage = np.maximum(bg, layer)
        fr = Image.fromarray(stage)
        if s.get("tremble"):                                                                                # 静止发力：微颤
            fr = zoomc(fr, 1.02, dx=int(3 * np.sin(lt * 55)), dy=int(3 * np.sin(lt * 43 + 1)))
        fr = zoomc(fr, 1.0 + 0.05 * lt / max(dur, 0.5))                                                     # 每镜 5% 缓推
        fr = enter_fx(fr, s.get("enter", "slide"), lt)
        if s["nextenter"] in ("zoom",) and rem < 0.1: fr = zoomc(fr, 1.0 + 0.1 * (1 - rem / 0.1))
        fr = fr.convert("RGBA")
        draw_top(fr, gt, s); draw_memory(fr, s); draw_labels(fr, lt, s); draw_inset(fr, lt, s, (xy, sc, src), src)
        if s.get("title") and lt < 2.0:                                                                    # 钩子标题：滑入、停留、淡出
            im = cached(("ttl", s["title"]), lambda: FX.stroke_text(s["title"], 92, FX.YELLOW, 12))
            k = FX.eo(lt / 0.35); al = min(1, (2.0 - lt) / 0.3)
            FX.paste_c(fr, im, 730, 170 - 40 * (1 - k), 1.0, k * al)
        sub = sub_img(s["cl"][ci]); fr.paste(sub, (int(W / 2 - sub.width / 2), 905), sub)                     # 字幕一次一行，固定在底部
        enc.stdin.write(fr.convert("RGB").tobytes())

def encoder(path):
    return subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-maxrate", "14M", "-bufsize", "28M",
                             "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

todo = [s for s in SHOTS if not ONLY or s["name"] in ONLY]
out_path = os.path.join(OUT, "video_noaudio.mp4" if not ONLY else "quick.mp4")
enc = encoder(out_path)
for i, s in enumerate(todo): render(s, enc, i == len(todo) - 1)
enc.stdin.close(); enc.wait()
json.dump(dict(END=END, GAP=GAP, seg=seg, shots=[dict(name=s["name"], t0=s["t0"], enter=s.get("enter", "slide")) for s in SHOTS]),
          open(os.path.join(OUT, "marks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("总时长 %.1f 秒，镜头 %d 个" % (END, len(SHOTS)))
for s in SHOTS: print(s["name"], round(s["t0"], 2), round(s["dur"], 2))
print("完成", out_path)
