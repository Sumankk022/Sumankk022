"""Founder Files — Vijay Mallya documentary renderer.
python3 engine.py --still t [t ...]            render stills to out/st_<t>.jpg
python3 engine.py --part i n                    render frame-chunk i of n to out/part_i.mp4
"""
import json, subprocess, sys, os, math, functools, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
TL = json.load(open("out/timeline.json"))
SEGS = TL["segs"]; TOTAL = TL["total"]; END0 = TL["end0"]
GOLD = (242, 193, 91); RED = (235, 72, 60); WHITE = (255, 255, 255)

# ================= fonts / easing =================
FD = "/usr/share/fonts/opentype/inter/"; PF = "fonts/pkg/package/files/playfair-display-latin-"
@functools.lru_cache(None)
def font(name, size):
    return ImageFont.truetype({"xb": FD + "InterDisplay-ExtraBold.otf", "b": FD + "InterDisplay-Bold.otf",
        "sb": FD + "InterDisplay-SemiBold.otf", "l": FD + "InterDisplay-Light.otf", "r": FD + "InterDisplay-Regular.otf",
        "m": FD + "InterDisplay-Medium.otf", "pf9": PF + "900-normal.woff", "pf7": PF + "700-normal.woff",
        "pfi": PF + "700-italic.woff", "pfi4": PF + "400-italic.woff"}[name], size)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eback(x): x = clamp(x); c1 = 1.70158; return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2
def win(t, t0, t1, fi=0.25, fo=0.25):
    if t < t0 or t > t1: return 0.0
    return min(eo((t - t0) / fi) if fi else 1, eo((t1 - t) / fo) if fo else 1)

# ================= grading =================
GRADES = {"warm": (1.10, 1.05, (1.05, 1.0, 0.92), 2), "neutral": (1.06, 1.0, (1, 1, 1), 0),
          "cool": (1.08, 0.75, (0.94, 1.0, 1.07), 4), "teal": (1.12, 0.95, (0.95, 1.02, 1.06), 0),
          "bw": (1.18, 0.0, (1, 1, 1), 0), "faded": (1.0, 0.55, (1.02, 1.0, 0.96), 10),
          "sepia": (1.08, 0.0, (1.08, 0.98, 0.84), 6)}
@functools.lru_cache(None)
def lut_for(c, lift):
    x = np.arange(256) / 255.0; s = 0.5 + (x - 0.5) * c
    if c > 1: s = s * 0.75 + 0.25 * (3 * x ** 2 - 2 * x ** 3)
    return np.clip(s * 255 + lift, 0, 255).astype(np.float32)
def grade(arr, g):
    if g == "none": return np.array(arr)
    c, sat, rgb, lift = GRADES[g]
    a = lut_for(c, lift)[arr]
    if sat != 1.0:
        lum = (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114)[..., None]; a = lum + (a - lum) * sat
    return np.clip(a * np.array(rgb, np.float32), 0, 255).astype(np.uint8)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIG = (1 - 0.42 * np.clip((_r - 0.55) / 0.9, 0, 1) ** 1.6) * (1 - 0.45 * np.clip((yy - H * 0.62) / (H * 0.38), 0, 1) ** 1.5)
VIG = VIG[..., None].astype(np.float32)
_rng = np.random.default_rng(7)
GRAIN = [np.repeat(np.repeat(_rng.normal(0, 5.0, (H // 2, W // 2, 1)).astype(np.float32), 2, 0), 2, 1) for _ in range(4)]
RADIAL = (np.clip(1 - _r * 0.75, 0, 1)[..., None] * np.array([34, 30, 40], np.float32) + 6).astype(np.float32)

# ================= sources =================
@functools.lru_cache(None)
def load_img(key):
    f = [x for x in os.listdir("img") if x.split(".")[0] == key][0]
    im = Image.open("img/" + f)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (0, 0, 0, 255)); bg.alpha_composite(im); im = bg
    return im.convert("RGB")
@functools.lru_cache(None)
def graded(key, g): return Image.fromarray(grade(np.array(load_img(key)), g))
def kb_crop(img, z, px, py, out=(W, H)):
    Wi, Hi = img.size; ow, oh = out; c = min(Wi / ow, Hi / oh); ww, wh = ow * c / z, oh * c / z
    cx = Wi / 2 + px * (Wi - ww) / 2; cy = Hi / 2 + py * (Hi - wh) / 2
    return img.transform(out, Image.EXTENT, (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2), Image.BILINEAR)
@functools.lru_cache(None)
def blurred_bg(key, g, dark=0.45):
    im = graded(key, g); c = max(W / im.width, H / im.height) * 1.15
    im = im.resize((int(im.width * c / 4), int(im.height * c / 4)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(14))
    im = im.resize((im.width * 4, im.height * 4), Image.BILINEAR)
    return Image.fromarray((np.array(im).astype(np.float32) * dark).astype(np.uint8))
@functools.lru_cache(None)
def feather_mask(w, h, edge=140):
    m = np.ones((h, w), np.float32); ramp = np.linspace(0, 1, edge) ** 1.4
    m[:, :edge] *= ramp; m[:, -edge:] *= ramp[::-1]
    m[:60, :] *= np.linspace(0, 1, 60)[:, None]; m[-60:, :] *= np.linspace(1, 0, 60)[:, None]
    return Image.fromarray((m * 255).astype(np.uint8))

class Vid:
    def __init__(self, src, off=0.0, slow=1.0, g="neutral"):
        self.src, self.off, self.slow, self.g = src, off, slow, g; self.p = None; self.idx = -1; self.last = None; self.base = 0
    def frame(self, k):
        if self.p is None:
            self.base = k; self.idx = k - 1
            ss = self.off + k / FPS / self.slow
            vf = (f"setpts={self.slow}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,crop={W}:{H}")
            self.p = subprocess.Popen(["ffmpeg", "-v", "quiet", "-ss", f"{ss:.3f}", "-i", self.src, "-vf", vf, "-f", "rawvideo",
                                       "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while self.idx < k:
            b = self.p.stdout.read(W * H * 3)
            if len(b) < W * H * 3:
                if self.last is None: self.last = np.zeros((H, W, 3), np.uint8)
                self.idx = k; break
            self.last = grade(np.frombuffer(b, np.uint8).reshape(H, W, 3), self.g); self.idx += 1
        return self.last
    def close(self):
        if self.p: self.p.kill(); self.p = None

# ================= text =================
@functools.lru_cache(maxsize=4096)
def text_img(txt, fname, size, color=WHITE, track=0, shadow=True):
    f = font(fname, size)
    widths = [f.getlength(ch) for ch in txt] if track else None
    tw = int(sum(widths) + track * (len(txt) - 1)) if track else int(f.getlength(txt))
    asc, desc = f.getmetrics(); pad = 30
    im = Image.new("RGBA", (max(1, tw) + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    def draw(dd, fill):
        if track:
            x = pad
            for ch, wch in zip(txt, widths): dd.text((x, pad), ch, font=f, fill=fill); x += wch + track
        else: dd.text((pad, pad), txt, font=f, fill=fill)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (0, 0, 0, 170))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(max(4, size // 9))))
    draw(ImageDraw.Draw(im), tuple(color) + (255,))
    return np.array(im)
def put(layer, arr, x, y, alpha=1.0, anchor="lt", scale=1.0):
    if alpha <= 0.003: return
    im = arr
    if scale != 1.0:
        p = Image.fromarray(arr); im = np.array(p.resize((max(1, int(p.width * scale)), max(1, int(p.height * scale))), Image.BILINEAR))
    h, w = im.shape[:2]; pad = int(30 * scale); bw, bh = w - 2 * pad, h - 2 * pad
    if anchor[0] == "m": x -= bw / 2
    elif anchor[0] == "r": x -= bw
    if anchor[1] == "m": y -= bh / 2
    elif anchor[1] == "b": y -= bh
    x, y = int(round(x - pad)), int(round(y - pad))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    crop = im[y0 - y:y1 - y, x0 - x:x1 - x].copy()
    if alpha < 1: crop[..., 3] = (crop[..., 3] * alpha).astype(np.uint8)
    layer.alpha_composite(Image.fromarray(crop), (x0, y0))
def text_w(txt, fname, size, track=0):
    f = font(fname, size); return (sum(f.getlength(c) for c in txt) + track * (len(txt) - 1)) if track else f.getlength(txt)

# ================= words / anchors =================
def norm(w): return re.sub(r"[^a-z0-9']", "", w.lower())
WORDS = []
for si, s in enumerate(SEGS):
    for w in s["words"]: WORDS.append(dict(w=w["w"], s=w["s"], e=w["e"], ch=si))
def A(phrase, ch, occ=0, edge="s", d=0.0):
    """time of a spoken phrase in chapter ch (0 = intro, 1..7)"""
    toks = [norm(x) for x in phrase.split()]
    ws = [w for w in WORDS if w["ch"] == ch]; seen = 0
    for i in range(len(ws) - len(toks) + 1):
        if all(norm(ws[i + j]["w"]) == toks[j] for j in range(len(toks))):
            if seen == occ:
                return (ws[i]["s"] if edge == "s" else ws[i + len(toks) - 1]["e"]) + d
            seen += 1
    raise KeyError(f"anchor not found: {phrase!r} in ch{ch}")
def CARD(ch): return SEGS[ch]["card"][0]

# ================= captions =================
GOLDW = set("""kingfisher kingfisher's mallya mallya's vijay vittal formula cricket beer brands brand luxury luxurious premium glamorous
celebrity empire empires ambition ambitions airline airlines airline's breweries united deccan gopinath mangalore karnataka jets yachts
mansions parties lifestyle visionary success successful recognizable founder files crores comebacks restored recovery special
famous expand expanded growing""".split())
REDW = set("""collapsed collapse apart controversy controversial debts debt crisis trouble troubles suspended struggling delayed cancelled
frustrated arrested fugitive offender fraud laundering irregularities bankruptcy wrong disastrous downfall failures risks pressure
problem expensive unpaid protests lost stopped dispute extradition rejected allegations criminal wrongdoing heavily tight
impossible bail""".split())
NO_HL = set()
ABBR = re.compile(r"^[A-Z]\.$")
def disp(tok, prev):
    t = re.sub(r"Malia", "Mallya", tok)
    return t
def build_caps():
    caps = []
    for si, s in enumerate(SEGS):
        ws = s["words"]; i = 0
        # display tokens (merge "-1990s" style fragments into the previous token)
        toks = []
        for j, w in enumerate(ws):
            t = w["w"]
            if t.startswith("-") and toks: toks[-1]["t"] += t; continue
            toks.append(dict(t=disp(t, ws[j - 1]["w"] if j else None), s=w["s"], e=w["e"]))
        group = []
        def flush():
            if group: caps.append(dict(items=list(group))); group.clear()
        for j, tk in enumerate(toks):
            group.append(tk)
            end_sent = re.search(r"[.?!]$", tk["t"]) and not ABBR.match(tk["t"])
            nxt_end = next((k for k in range(j + 1, len(toks)) if re.search(r"[.?!]$", toks[k]["t"]) and not ABBR.match(toks[k]["t"])), len(toks) - 1)
            remain = nxt_end - j
            width = sum(text_w(g["t"], "xb", 64) for g in group) + 16 * len(group)
            if end_sent: flush()
            elif remain >= 2 and (len(group) >= 5 or width > 1250 or (tk["t"].endswith(",") and len(group) >= 3)): flush()
        flush()
    for c in caps:
        its = []
        prevtok = None
        for g in c["items"]:
            n_ = norm(g["t"])
            col = WHITE
            if re.search(r"\d", g["t"]) or (n_ in GOLDW and n_ not in NO_HL): col = GOLD
            if n_ in REDW: col = RED
            its.append((g["t"], col, g["s"], g["e"])); prevtok = n_
        c["items"] = its; c["t0"] = its[0][2] - 0.08; c["t1"] = its[-1][3]
    for i, c in enumerate(caps):
        nxt = caps[i + 1]["t0"] if i + 1 < len(caps) else 1e9
        c["t1"] = min(c["t1"] + 0.7, nxt - 0.02)
    return caps
CAPS = build_caps()
HIDE = []          # caption-free windows (big graphics say the words)
CAP_Y = 930
def caption_layout(c):
    if "lay" not in c:
        sp = font("xb", 64).getlength(" "); ws = [text_w(t, "xb", 64) for t, *_ in c["items"]]
        x = W / 2 - (sum(ws) + sp * (len(ws) - 1)) / 2; lay = []
        for (t, col, s, e), w_ in zip(c["items"], ws): lay.append((x, t, col, s)); x += w_ + sp
        c["lay"] = lay
    return c["lay"]
def draw_captions(layer, t):
    for c in CAPS:
        if not (c["t0"] <= t <= c["t1"]): continue
        mid = (c["t0"] + c["t1"]) / 2
        if any(a <= mid <= b for a, b in HIDE): continue
        out = clamp((c["t1"] - t) / 0.15); gin = eo((t - c["t0"]) / 0.22)
        for x, txt, col, s in caption_layout(c):
            k = eo((t - (s - 0.05)) / 0.12); a = (0.38 + 0.62 * k) * gin * out
            colr = col if k >= 1 else (WHITE if col == WHITE else tuple(int(255 + (cc - 255) * k) for cc in col))
            put(layer, text_img(txt, "xb", 64, colr), x, CAP_Y + 14 * (1 - gin) - 5 * math.sin(math.pi * clamp((t - s + 0.05) / 0.2)), a, "lb")

# ================= overlay graphics =================
EV = []     # (t0, t1, fn)
def ev(t0, t1, fn): EV.append((t0, t1, fn))
def chapter_tag(layer, t, t0, t1, text):
    v = win(t, t0, t1, 0.4, 0.3)
    if v <= 0: return
    k = eo((t - t0) / 0.45); d = ImageDraw.Draw(layer)
    d.rectangle([90, 86, 95, 86 + int(40 * k)], fill=GOLD + (int(255 * v),))
    put(layer, text_img(text, "sb", 30, WHITE, track=5), 116 - 30 * (1 - k), 87, v * k)
def credit(layer, t, t0, t1, text):
    put(layer, text_img(text, "r", 19, WHITE), W - 36, H - 26, win(t, t0, t1, 0.4, 0.3) * 0.72, "rb")
def big_title(layer, t, t0, t1, text, fname, size, y, color=WHITE, track0=46, track1=10, wipe=False):
    v = win(t, t0, t1, 0.5, 0.35)
    if v <= 0: return None
    k = eo((t - t0) / 1.1); tr = track0 + (track1 - track0) * k
    f = font(fname, size); ws = [f.getlength(ch) for ch in text]; total = sum(ws) + tr * (len(text) - 1); x = W / 2 - total / 2
    for i, (ch, wch) in enumerate(zip(text, ws)):
        if ch != " ":
            ck = clamp((t - t0) * 2.2 - i / len(text)) if wipe else eo((t - t0 - i * 0.035) / 0.45)
            put(layer, text_img(ch, fname, size, color), x, y + 20 * (1 - ck), v * ck, "lm")
        x += wch + tr
    return total
def gold_rules(layer, t, t0, t1, y, half):
    v = win(t, t0, t1, 0.6, 0.35)
    if v <= 0: return
    L = 180 * eio((t - t0 - 0.2) / 0.8); d = ImageDraw.Draw(layer)
    d.rectangle([W / 2 - half - 40 - L, y - 1, W / 2 - half - 40, y + 1], fill=GOLD + (int(230 * v),))
    d.rectangle([W / 2 + half + 40, y - 1, W / 2 + half + 40 + L, y + 1], fill=GOLD + (int(230 * v),))
def TITLE(t0, t1, text, size=168, y=520, sub=None, above=None, color=WHITE, hide=True):
    def fn(layer, t):
        if above: put(layer, text_img(above, "l", 46, WHITE, track=18), W / 2, y - 125, win(t, t0 - 0.4, t1, 0.5, 0.3), "mm")
        tw = big_title(layer, t, t0, t1, text, "pf9", size, y, color)
        if tw: gold_rules(layer, t, t0, t1, y, tw / 2)
        if sub: put(layer, text_img(sub, "sb", 30, GOLD, track=9), W / 2, y + 120, win(t, t0 + 0.5, t1, 0.5, 0.35), "mm")
    ev(t0 - 0.5, t1, fn)
    if hide: HIDE.append((t0 - 0.3, t1))
def YEAR(t0, text, dur=2.6):
    def fn(layer, t):
        v = win(t, t0, t0 + dur, 0.35, 0.5)
        k = eo((t - t0) / 0.6)
        put(layer, text_img(text, "pf9", 170, WHITE), 110, 760 + 30 * (1 - k), v * 0.95, "lb")
        d = ImageDraw.Draw(layer); L = int(220 * eio((t - t0 - 0.15) / 0.7))
        d.rectangle([114, 782, 114 + L, 787], fill=GOLD + (int(255 * v),))
    ev(t0 - 0.05, t0 + dur, fn)
def ITALIC(t0, t1, text, size=150, y=520):
    def fn(layer, t):
        put(layer, text_img(text, "pfi", size, WHITE), W / 2, y, win(t, t0, t1, 0.45, 0.3), "mm", scale=1.0 + 0.04 * clamp((t - t0) / (t1 - t0)))
    ev(t0, t1, fn); HIDE.append((t0 - 0.2, t1))
def WORDPOP(items, t1, y=470, size=110):
    """items: list of (t, text, color) shown stacked/side by side centrally"""
    def fn(layer, t):
        n = len(items); gap = 110 if n > 1 else 0
        for i, (ta, txt, col) in enumerate(items):
            k = eback((t - ta) / 0.45) if t >= ta else 0
            v = win(t, ta, t1, 0.2, 0.35)
            yy_ = y + (i - (n - 1) / 2) * (size + 20)
            put(layer, text_img(txt, "pf9", size, col), W / 2, yy_, v, "mm", scale=0.85 + 0.15 * clamp(k, 0, 1.2))
    ev(items[0][0] - 0.05, t1, fn)
def COUNTER(t0, t1, target, label):
    def fn(layer, t):
        v = win(t, t0, t1, 0.3, 0.4); k = eio((t - t0) / 1.0)
        put(layer, text_img(str(int(round(target * k))), "pf9", 300, GOLD), W / 2, 470, v, "mm")
        put(layer, text_img(label, "sb", 44, WHITE, track=14), W / 2, 650, v * eo((t - t0 - 0.5) / 0.5), "mm")
    ev(t0, t1, fn); HIDE.append((t0, t1))


# ================= new motion graphics =================
def _panel(layer, x0, y0, x1, y1, a, r=22, fill=(8, 8, 12)):
    if a <= 0: return
    p = Image.new("RGBA", (int(x1 - x0) + 80, int(y1 - y0) + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    d.rounded_rectangle([40, 48, 40 + x1 - x0, 48 + y1 - y0], radius=r, fill=(0, 0, 0, int(120 * a)))
    p = p.filter(ImageFilter.GaussianBlur(16)); d = ImageDraw.Draw(p)
    d.rounded_rectangle([40, 40, 40 + x1 - x0, 40 + y1 - y0], radius=r, fill=fill + (int(185 * a),), outline=(255, 255, 255, int(40 * a)), width=2)
    layer.alpha_composite(p, (int(x0 - 40), int(y0 - 40)))

@functools.lru_cache(None)
def left_shade():
    g = np.zeros((H, W, 4), np.uint8); ramp = np.clip(1 - np.linspace(0, 1, W) / 0.62, 0, 1) ** 1.3
    g[..., 3] = (ramp * 205).astype(np.uint8)[None, :]; return Image.fromarray(g)
@functools.lru_cache(None)
def right_shade():
    return left_shade().transpose(Image.FLIP_LEFT_RIGHT)

def LIST(items, t1, title=None, x=120, y0=300, gap=104, size=62, hide=True):
    """luxury list: items = [(t, text)], newest item gold"""
    t0 = items[0][0]
    def fn(layer, t):
        v = win(t, t0 - 0.3, t1, 0.4, 0.35)
        sh = left_shade().copy(); a_ = np.array(sh); a_[..., 3] = (a_[..., 3] * v).astype(np.uint8); layer.alpha_composite(Image.fromarray(a_))
        if title: put(layer, text_img(title, "sb", 28, GOLD, track=10), x, y0 - 80, v, "lm")
        d = ImageDraw.Draw(layer)
        last = max(i for i, (ta, _) in enumerate(items) if ta - 0.1 <= t) if t >= t0 - 0.1 else -1
        for i, (ta, txt) in enumerate(items):
            k = eo((t - ta + 0.1) / 0.45)
            if k <= 0: continue
            y = y0 + i * gap
            put(layer, text_img(f"{i + 1:02d}", "sb", 26, GOLD, track=4), x, y + 4, v * k, "lm")
            d.rectangle([x + 58, y - 26, x + 62, y - 26 + int(56 * k)], fill=GOLD + (int(255 * v),))
            col = GOLD if i == last else WHITE
            put(layer, text_img(txt, "pf9", size, col), x + 86 - 40 * (1 - k), y, v * k * (1.0 if i == last else 0.82), "lm")
    ev(t0 - 0.3, t1, fn)
    if hide: HIDE.append((t0 - 0.2, t1))

def FALL(t0, t1, top, word, t_fall):
    """headline whose letters appear, then drop out of frame one by one"""
    rng = np.random.default_rng(11); order = rng.permutation(len(word)); delay = {int(j): 0.055 * i for i, j in enumerate(order)}
    def fn(layer, t):
        v = win(t, t0, t1, 0.3, 0.25)
        put(layer, text_img(top, "l", 50, WHITE, track=16), W / 2, 420, v * eo((t - t0) / 0.5), "mm")
        f = font("pf9", 150); ws = [f.getlength(ch) for ch in word]; tr = 10; total = sum(ws) + tr * (len(word) - 1); x = W / 2 - total / 2
        for i, (ch, wch) in enumerate(zip(word, ws)):
            if ch != " ":
                ck = eo((t - t0 - 0.25 - i * 0.03) / 0.4)
                tf = t_fall + delay[i]; dy = 0.0; a = 1.0
                if t > tf: dt = t - tf; dy = 0.5 * 2600 * dt * dt; a = clamp(1 - dt / 0.7)
                put(layer, text_img(ch, "pf9", 150, RED), x, 545 + 20 * (1 - ck) + dy, v * ck * a, "lm")
            x += wch + tr
        d = ImageDraw.Draw(layer); L = int(total / 2 * eio((t - t0 - 0.4) / 0.6) * clamp(1 - (t - t_fall) / 0.4))
        if L > 0: d.rectangle([W / 2 - L, 640, W / 2 + L, 644], fill=RED + (int(220 * v),))
    ev(t0 - 0.05, t1, fn); HIDE.append((t0 - 0.1, t1))

def ROUTE(t0, t1, a_lab="INDIA", b_lab="UNITED KINGDOM", sub=None, dur=2.0):
    A_ = np.array([1390.0, 700.0]); B_ = np.array([560.0, 360.0]); C_ = np.array([1030.0, 150.0])
    def bez(u): return (1 - u) ** 2 * A_ + 2 * (1 - u) * u * C_ + u ** 2 * B_
    def fn(layer, t):
        v = win(t, t0, t1, 0.35, 0.35); d = ImageDraw.Draw(layer)
        u = eio((t - t0 - 0.35) / dur)
        for j in range(60):                                 # dashed arc
            ua, ub = j / 60, (j + 0.55) / 60
            if ua > u: break
            p, q = bez(ua), bez(min(ub, u)); d.line([*p, *q], fill=(255, 255, 255, int(220 * v)), width=4)
        for P, lab, ta in ((A_, a_lab, t0), (B_, b_lab, t0 + 0.2 + dur)):
            k = eback((t - ta) / 0.4) if t >= ta else 0
            if k <= 0: continue
            r = 13 * clamp(k, 0, 1.2); col = GOLD if P is A_ else RED
            pr = ((t - ta) * 0.9) % 1.0; rr = 14 + 46 * pr
            d.ellipse([P[0] - rr, P[1] - rr, P[0] + rr, P[1] + rr], outline=col + (int(200 * (1 - pr) * v),), width=3)
            d.ellipse([P[0] - r, P[1] - r, P[0] + r, P[1] + r], fill=col + (int(255 * v),), outline=(255, 255, 255, int(255 * v)), width=3)
            put(layer, text_img(lab, "b", 40, WHITE, track=8), P[0], P[1] + 52, v * clamp(k), "mt")
        if 0 < u < 1:                                       # plane marker
            p = bez(u); q = bez(min(1, u + 0.01)); ang = math.atan2(q[1] - p[1], q[0] - p[0])
            pts = [(18, 0), (-12, -11), (-6, 0), (-12, 11)]
            pts = [(p[0] + x * math.cos(ang) - y * math.sin(ang), p[1] + x * math.sin(ang) + y * math.cos(ang)) for x, y in pts]
            d.polygon(pts, fill=(255, 255, 255, int(255 * v)))
        if sub: put(layer, text_img(sub, "sb", 30, GOLD, track=10), W / 2, 150, win(t, t0 + 0.6, t1, 0.4, 0.3), "mm")
    ev(t0, t1, fn)

def CHECK(items, t1, title, x0=1120, y0=290):
    t0 = items[0][0]
    def fn(layer, t):
        v = win(t, t0 - 0.4, t1, 0.4, 0.35)
        sh = right_shade().copy(); a_ = np.array(sh); a_[..., 3] = (a_[..., 3] * v).astype(np.uint8); layer.alpha_composite(Image.fromarray(a_))
        put(layer, text_img(title, "sb", 28, GOLD, track=10), x0, y0 - 70, v, "lm")
        d = ImageDraw.Draw(layer)
        for i, (ta, txt) in enumerate(items):
            y = y0 + i * 92; k = eo((t - ta + 0.15) / 0.4)
            ba = v * clamp((t - t0 + 0.4) / 0.4 - i * 0.15)
            d.rounded_rectangle([x0, y - 24, x0 + 48, y + 24], radius=10, outline=(255, 255, 255, int(200 * ba)), width=3,
                                fill=GOLD + (int(255 * v * k),) if k > 0 else None)
            if k > 0:
                c = eio((t - ta) / 0.3); p1, p2, p3 = (x0 + 11, y + 1), (x0 + 21, y + 12), (x0 + 38, y - 12)
                if c < 0.4: d.line([p1, (p1[0] + (p2[0] - p1[0]) * c / 0.4, p1[1] + (p2[1] - p1[1]) * c / 0.4)], fill=(20, 20, 24, 255), width=6)
                else:
                    c2 = (c - 0.4) / 0.6; d.line([p1, p2, (p2[0] + (p3[0] - p2[0]) * c2, p2[1] + (p3[1] - p2[1]) * c2)], fill=(20, 20, 24, 255), width=6)
            put(layer, text_img(txt, "b", 46, WHITE if k <= 0 else GOLD), x0 + 76, y, ba * (0.55 + 0.45 * clamp(k)), "lm")
    ev(t0 - 0.4, t1, fn); HIDE.append((t0 - 0.3, t1))

def COSTS(items, t1, title="RUNNING AN AIRLINE", x0=130, y0=300):
    t0 = items[0][0]
    def fn(layer, t):
        v = win(t, t0 - 0.4, t1, 0.4, 0.35)
        sh = left_shade().copy(); a_ = np.array(sh); a_[..., 3] = (a_[..., 3] * v).astype(np.uint8); layer.alpha_composite(Image.fromarray(a_))
        put(layer, text_img(title, "sb", 28, GOLD, track=10), x0, y0 - 80, v, "lm")
        d = ImageDraw.Draw(layer); n_ = sum(1 for ta, _ in items if t >= ta - 0.1)
        for i, (ta, txt) in enumerate(items):
            k = eback((t - ta + 0.1) / 0.4) if t >= ta - 0.1 else 0
            if k <= 0: continue
            y = y0 + i * 88
            put(layer, text_img("₹", "b", 40, RED), x0, y, v * clamp(k), "lm")
            put(layer, text_img(txt, "b", 48, WHITE), x0 + 50, y, v * clamp(k), "lm", scale=0.9 + 0.1 * clamp(k, 0, 1.1))
        bx, by0, by1 = 760, y0 - 30, y0 + 88 * len(items) - 50                 # cost meter
        d.rounded_rectangle([bx, by0, bx + 34, by1], radius=17, outline=(255, 255, 255, int(170 * v)), width=3)
        prog = 0.0
        for i, (ta, _) in enumerate(items): prog += eio((t - ta) / 0.5) / len(items)
        if prog > 0: d.rounded_rectangle([bx + 6, by1 - 6 - (by1 - by0 - 12) * prog, bx + 28, by1 - 6], radius=11, fill=RED + (int(255 * v),))
        put(layer, text_img("COSTS", "sb", 24, RED, track=8), bx + 17, by0 - 34, v, "mm")
    ev(t0 - 0.4, t1, fn); HIDE.append((t0 - 0.3, t1))

FLAP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
def BOARD(t0, t1, rows):
    """split-flap departures board. rows: (flight, city, status, colour, t_status)"""
    cw, x0, y0 = 34, 330, 300
    def flapline(layer, txt, x, y, ts, t, col, a):
        for j, ch in enumerate(txt):
            settle = ts + j * 0.035
            if t < ts - 0.05: continue
            if t < settle and ch != " ":
                ch = FLAP[(int(t * 30) * 7 + j * 13) % len(FLAP)]; c_ = (200, 200, 200)
            else: c_ = col
            d = ImageDraw.Draw(layer); d.rounded_rectangle([x + j * cw, y - 25, x + j * cw + cw - 4, y + 25], radius=4, fill=(28, 28, 32, int(235 * a)))
            d.line([x + j * cw, y, x + j * cw + cw - 4, y], fill=(0, 0, 0, int(200 * a)), width=2)
            if ch != " ": put(layer, text_img(ch, "b", 36, c_, shadow=False), x + j * cw + (cw - 4) / 2, y + 1, a, "mm")
    def fn(layer, t):
        v = win(t, t0, t1, 0.35, 0.35)
        _panel(layer, x0 - 50, y0 - 140, W - x0 + 50, y0 + 92 * len(rows) + 10, v, fill=(10, 10, 14))
        put(layer, text_img("DEPARTURES", "b", 40, GOLD, track=12), x0, y0 - 88, v, "lm")
        for lab, xx in (("FLIGHT", x0), ("TO", x0 + 300), ("STATUS", x0 + 820)):
            put(layer, text_img(lab, "sb", 22, (180, 180, 180), track=6), xx, y0 - 40, v, "lm")
        for i, (fl, city, st, col, ts) in enumerate(rows):
            y = y0 + 20 + i * 92; tr = t0 + 0.15 + i * 0.12
            flapline(layer, fl.ljust(7), x0, y, tr, t, WHITE, v)
            flapline(layer, city.ljust(13), x0 + 300, y, tr + 0.1, t, WHITE, v)
            flapline(layer, (st if t >= ts else "ON TIME").ljust(9), x0 + 820, y, ts if t >= ts else tr + 0.2, t,
                     col if t >= ts else (120, 220, 140), v)
    ev(t0, t1, fn); HIDE.append((t0, t1))

@functools.lru_cache(None)
def stamp_img(text, col=RED, size=120):
    f = font("xb", size); tw = int(f.getlength(text)); pad = 34
    im = Image.new("RGBA", (tw + pad * 2 + 20, size + pad * 2 + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, im.width - 10, im.height - 10], radius=14, outline=col + (255,), width=10)
    d.text((pad + 10, pad - size * 0.12 + 10), text, font=f, fill=col + (255,))
    rng = np.random.default_rng(5); a = np.array(im); m = rng.random(a.shape[:2]) < 0.13; a[m, 3] = (a[m, 3] * 0.35).astype(np.uint8)
    return Image.fromarray(a).rotate(-11, resample=Image.BICUBIC, expand=True)
@functools.lru_cache(None)
def permit_card():
    w_, h_ = 760, 470; im = Image.new("RGBA", (w_, h_), (246, 243, 236, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w_, 16], fill=(170, 30, 30, 255))
    d.text((48, 52), "OPERATING PERMIT", font=font("xb", 50), fill=(25, 25, 30, 255))
    d.text((48, 120), "KINGFISHER AIRLINES", font=font("sb", 30), fill=(150, 30, 30, 255))
    for i, ww in enumerate([620, 560, 640, 480, 600, 380]):
        d.rounded_rectangle([48, 190 + i * 38, 48 + ww, 202 + i * 38], radius=6, fill=(205, 200, 192, 255))
    return im
def STAMP(t0, t1, ts, text="SUSPENDED", card=True, y=520):
    def fn(layer, t):
        v = win(t, t0, t1, 0.35, 0.3)
        if card:
            k = eo((t - t0) / 0.6); c = permit_card(); arr = np.array(c); arr[..., 3] = (arr[..., 3] * v * k).astype(np.uint8)
            sh = Image.new("RGBA", (c.width + 100, c.height + 100), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rectangle([50, 64, 50 + c.width, 64 + c.height], fill=(0, 0, 0, int(150 * v * k)))
            cx, cy = W / 2, y + 40 * (1 - k)
            layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(20)), (int(cx - c.width / 2 - 50), int(cy - c.height / 2 - 50)))
            layer.alpha_composite(Image.fromarray(arr), (int(cx - c.width / 2), int(cy - c.height / 2)))
        if t >= ts:
            k = clamp((t - ts) / 0.18); sc = 2.4 - 1.4 * eo(k)
            s_ = stamp_img(text); s2 = s_.resize((max(1, int(s_.width * sc)), max(1, int(s_.height * sc))), Image.BILINEAR)
            a = np.array(s2); a[..., 3] = (a[..., 3] * v * clamp(k * 1.5)).astype(np.uint8)
            jx = math.sin((t - ts) * 90) * 10 * math.exp(-(t - ts) * 9) if t > ts + 0.18 else 0
            layer.alpha_composite(Image.fromarray(a), (int(W / 2 - s2.width / 2 + 60 + jx), int(y + 50 - s2.height / 2)))
    ev(t0, t1, fn); HIDE.append((t0, t1))

def VS(t0, t1, left, right, t_right, top=None):
    def fn(layer, t):
        v = win(t, t0, t1, 0.4, 0.3); kl = eo((t - t0) / 0.5); kr = eo((t - t_right) / 0.5)
        if top: put(layer, text_img(top, "sb", 28, GOLD, track=10), W / 2, 370, v, "mm")
        fs_ = 74
        while max(text_w(left, "pf9", fs_), text_w(right, "pf9", fs_)) > W / 2 - 190: fs_ -= 2
        put(layer, text_img(left, "pf9", fs_, WHITE), W / 2 - 90 - 40 * (1 - kl), 520, v * kl, "rm")
        put(layer, text_img("≠", "b", 110, GOLD), W / 2, 515, v * kr, "mm", scale=0.6 + 0.4 * clamp(eback((t - t_right) / 0.45), 0, 1.2))
        put(layer, text_img(right, "pf9", fs_, GOLD), W / 2 + 90 + 40 * (1 - kr), 520, v * kr, "lm")
    ev(t0, t1, fn); HIDE.append((t0, t1))

def QUOTE(t0, t1, l1, l2, tm, size=76):
    def fn(layer, t):
        put(layer, text_img(l1, "pfi", size, WHITE), W / 2, 455, win(t, t0, t1, 0.5, 0.4), "mm")
        put(layer, text_img(l2, "pfi", size, GOLD), W / 2, 565, win(t, tm, t1, 0.5, 0.4), "mm")
    ev(t0, t1, fn); HIDE.append((t0, t1))

def HEAD(t0, t1, text, sub=None, color=WHITE, size=150, y=520, above=None, hide=True):
    def fn(layer, t):
        if above: put(layer, text_img(above, "sb", 30, GOLD, track=10), W / 2, y - 120, win(t, t0, t1, 0.4, 0.3), "mm")
        tw = big_title(layer, t, t0, t1, text, "pf9", size, y, color, 36, 6)
        if tw: gold_rules(layer, t, t0, t1, y, tw / 2)
        if sub: put(layer, text_img(sub, "sb", 30, WHITE, track=9), W / 2, y + 115, win(t, t0 + 0.5, t1, 0.5, 0.35), "mm")
    ev(t0 - 0.05, t1, fn)
    if hide: HIDE.append((t0 - 0.2, t1))

def LOWER(t0, t1, title, sub):
    """lower-third name strap"""
    def fn(layer, t):
        v = win(t, t0, t1, 0.4, 0.35); k = eo((t - t0) / 0.55); d = ImageDraw.Draw(layer)
        x, y = 110, 735
        d.rectangle([x, y - 6, x + int(520 * k), y + 74], fill=(10, 10, 14, int(170 * v)))
        d.rectangle([x, y - 6, x + 6, y + 74], fill=GOLD + (int(255 * v),))
        put(layer, text_img(title, "xb", 42, WHITE), x + 26 - 20 * (1 - k), y + 18, v * k, "lm")
        put(layer, text_img(sub, "sb", 22, GOLD, track=6), x + 26 - 20 * (1 - k), y + 54, v * k, "lm")
    ev(t0, t1, fn)

# ================= shots =================
S = []
def shot(t0, kind, xf=0.35, **kw): S.append(dict(t0=t0, kind=kind, xf=xf, **kw))
INFO = json.load(open("imginfo.json"))
IMGS = {x.split(".")[0] for x in os.listdir("img")}
ART = {"mallya_wef": "World Economic Forum / Dana Smillie", "mallya_goa1": "PIB, Ministry of I&B, Govt. of India",
       "mallya_goa2": "PIB, Ministry of I&B, Govt. of India", "gopinath": "Ranjit Bhaskar / Al Jazeera English",
       "wmc2": "Mike Peel", "rcj": "David Castor", "f1parc": "Oahiyeel", "yacht2": "VerTego", "kftowers": "SerChevalerie",
       "ubcity2": "Wikimedia Commons user", "n4ub": "Eddie Maloney", "tewin": "Peter O'Connor", "rupee": "Monito",
       "delhit": "V Malik", "a320": "airbus777", "kfmeal2": "Andy Mitchell"}
def CR_(k):
    if k not in INFO: return None
    i = INFO[k]; a = ART.get(k) or re.sub(r"\s+", " ", i["artist"]).strip() or "Wikimedia Commons user"
    return f"Photo: {a} · {i['lic']} · Wikimedia Commons"
def pick(keys):
    for k in keys.split("|"):
        if k in IMGS: return k
    return None
def IMG(t0, key, layout="cover", g="warm", z=(1.02, 1.12), pan=((0, 0), (0, 0)), xf=0.35, tag=None, side="right", fb=None, **kw):
    k = pick(key)
    if k is None:
        if fb: VID(t0, *fb, xf=xf, tag=tag if kw.get("keep_tag") else None)
        return
    shot(t0, "img", xf=xf, key=k, layout=layout, g=g, z=z, pan=pan, tag=tag, side=side, credit=CR_(k), **kw)
def VID(t0, n, off=0.0, slow=1.0, g="neutral", xf=0.35, tag=None, **kw):
    shot(t0, "vid", xf=xf, src=f"vid/{n}.mp4", off=off, slow=slow, g=g, tag=tag, **kw)
def CARDSHOT(ch, bgkey, bgg="warm"):
    c = TL["chapters"][ch - 1]
    shot(CARD(ch), "card", xf=0.6, n=ch, title=c["title"], years=c["years"], bgkey=pick(bgkey) or "ubcity", bgg=bgg)

# ---------------------------------------------------------------- INTRO (ch 0)
a = lambda p, occ=0, edge="s", d=0.0: A(p, 0, occ, edge, d)
VID(0.0, 7138, off=2.0, g="teal", xf=0.0)
VID(a("luxury", d=-0.12), 4446, off=1.0, g="warm", xf=0.25)
VID(a("expensive", d=-0.12), 51629, off=2.0, g="warm", xf=0.25)
IMG(a("beautiful", d=-0.12), "kftowers", g="warm", z=(1.0, 1.0), pan=((0, 0.75), (0, -0.95)), xf=0.25, tag="KINGFISHER TOWERS  ·  BENGALURU")
IMG(a("and one of", d=-0.1), "a330c", g="neutral", z=(1.05, 1.15), pan=((-0.4, 0), (0.3, -0.1)), xf=0.25)
LIST([(a("private"), "Private jets"), (a("luxury"), "Luxury yachts"), (a("expensive"), "Expensive parties"),
      (a("beautiful"), "Beautiful mansions"), (a("glamorous"), "A glamorous airline")], a("at one point", d=-0.15), title="THE GOOD LIFE")
IMG(a("at one point", d=-0.15), "mallya_wef", g="neutral", z=(1.12, 1.0), pan=((0.25, -0.35), (0.25, -0.3)), xf=0.4,
    dark=(0.55, 1.0, a("at one point"), a("vijay malia", d=0.2)))
HEAD(a("vijay malia", d=-0.05), a("he was known", d=-0.2), "VIJAY MALLYA", sub="CHAIRMAN  ·  UNITED BREWERIES GROUP", size=160, y=700)
IMG(a("he was known", d=-0.15), "beerad", g="warm", z=(1.0, 1.35), pan=((-0.15, -0.5), (-0.15, -0.55)), xf=0.3)
ITALIC(a("king of good", d=-0.25), a("he owned", d=-0.15), "“The King of Good Times”", size=110, y=900)
VID(a("he owned", d=-0.12), 8697, off=2.0, g="warm")
LOWER(a("liquor", d=-0.3), a("entered formula", d=-0.2), "UNITED BREWERIES", "KINGFISHER  ·  SPIRITS  ·  BEER")
IMG(a("entered formula", d=-0.12), "f1sing|f1vjm01|f1parc|f1car2017", g="neutral", z=(1.04, 1.16), pan=((0.3, 0), (-0.2, 0)),
    tag="FORCE INDIA  ·  FORMULA ONE", fb=(615, 0.0, 1.0, "teal"))
VID(a("owned a cricket", d=-0.12), 12233, off=2.0, g="faded", tag="ROYAL CHALLENGERS BANGALORE  ·  IPL")
IMG(a("and launched", d=-0.12), "a330", g="neutral", z=(1.0, 1.12), pan=((0.3, 0), (-0.3, 0)), tag="KINGFISHER AIRLINES")
VID(a("completely different", d=-0.15), 40102, off=3.0, g="warm")
IMPACT0 = a("but then", d=-0.1)
VID(IMPACT0, 22387, off=14.0, g="cool", xf=0.0, flash=True, dim=0.55)
FALL(a("but then", d=0.05), a("kingfisher airlines collapsed", d=-0.1), "EVERYTHING STARTED", "FALLING APART", a("apart", edge="e", d=0.55))
IMG(a("kingfisher airlines collapsed", d=-0.1), "kfclosed|kfcounter", g="faded", z=(1.0, 1.12), pan=((0.2, 0), (0.0, 0)), xf=0.15,
    tag="GOA AIRPORT  ·  2013", fb=(36351, 0.0, 1.0, "cool"))
VID(a("thousands of crores", d=-0.15), 47005, off=1.0, g="warm", dim=0.6)
WORDPOP([(a("thousands of crores"), "Thousands of crores", GOLD), (a("in bank loans"), "in bank loans", WHITE)],
        a("became the center", d=-0.1), y=520, size=100)
HIDE.append((a("thousands of crores", d=-0.1), a("a massive", d=-0.1)))
VID(a("became the center", d=-0.12), 23225, off=4.0, g="cool")
VID(a("and malia eventually", d=-0.12), 26852, off=1.0, g="cool", dim=0.55)
ROUTE(a("and malia eventually", d=0.1), a("so how did", d=-0.15))
IMG(a("so how did", d=-0.15), "mallya_goa2", "side", side="right", g="warm", z=(1.0, 1.06))
IMG(a("go from building", d=-0.12), "ubcity", g="warm", z=(1.0, 1.12), pan=((0, 0.2), (0, -0.2)), tag="UB CITY  ·  BENGALURU")
IMG(a("to becoming", d=-0.12), "mallya_wef", g="bw", z=(1.3, 1.45), pan=((0.2, -0.4), (0.22, -0.42)), xf=0.25)
ITALIC(a("let's find out", d=-0.1), a("let's find out", edge="e", d=0.9), "Let’s find out.", size=120)

# ---------------------------------------------------------------- channel ident (user's intro.mp4)
IDENT = TL["ident"]
shot(IDENT[0], "ext", xf=0.35, src="vid/intro.mp4")

# ---------------------------------------------------------------- CH1 Born Into Business
a = lambda p, occ=0, edge="s", d=0.0: A(p, 1, occ, edge, d)
CARDSHOT(1, "mangalore2")
IMG(a("vijay malia was born", d=-0.1), "mangalore2", g="warm", z=(1.0, 1.12), xf=0.6, tag="MANGALORE  ·  KARNATAKA")
YEAR(a("1955", d=-0.1), "1955")
IMG(a("his father vittal", d=-0.15), "vittal2", g="warm", z=(1.0, 1.18), pan=((0, -0.3), (0.0, -0.4)), tag="VITTAL MALLYA  ·  1924 – 1983")
VID(a("who built a strong", d=-0.12), 33006, off=1.0, g="warm")
IMG(a("when his father passed", d=-0.15), "vittal1", "side", side="left", g="bw", z=(1.0, 1.06))
YEAR(a("1983", d=-0.1), "1983")
IMG(a("vijay malia took over", d=-0.15), "mallya_goa2", g="warm", z=(1.15, 1.28), pan=((-0.25, -0.2), (-0.3, -0.25)))
COUNTER(a("just 28", d=-0.1), a("instead of simply", d=-0.15), 28, "YEARS OLD")
VID(a("just 28", d=-0.15), 1433, off=1.0, g="warm", dim=0.4, xf=0.25)
VID(a("instead of simply", d=-0.12), 1421, off=2.0, g="warm")
IMG(a("he focused on growing", d=-0.15), "ubcity2|ubcity", g="warm", z=(1.0, 1.12), tag="UNITED BREWERIES GROUP")
IMG(a("which became famous", d=-0.12), "beer", "side", side="right", g="warm", z=(1.0, 1.06), tag="KINGFISHER BEER")
VID(a("he also expanded", d=-0.12), 52410, off=3.0, g="warm", dim=0.5)
WORDPOP([(a("spirits"), "Spirits", WHITE), (a("chemicals"), "Chemicals", WHITE), (a("and several other"), "& more industries", GOLD)],
        a("over time", d=-0.15), y=520, size=96)
HIDE.append((a("spirits", d=-0.1), a("over time", d=-0.15)))
IMG(a("over time", d=-0.12), "beerstand", "side", side="left", g="warm", z=(1.0, 1.06))
VID(a("one of india's most", d=-0.15), 8706, off=1.0, g="warm")
IMG(a("malia was becoming more", d=-0.15), "mallya_goa1", g="warm", z=(1.0, 1.1), pan=((0, -0.2), (0.1, -0.2)), tag="GOA  ·  2010")
VID(a("he was becoming a celebrity", d=-0.15), 4043, off=2.0, g="warm")
IMG(a("and he loved the lifestyle", d=-0.15), "yacht|yacht2", g="warm", z=(1.0, 1.12), tag="INDIAN EMPRESS  ·  HIS SUPERYACHT",
    fb=(4446, 4.0, 1.0, "warm"))
VID(a("but his biggest ambition", d=-0.15), 2684, off=1.0, g="teal")

# ---------------------------------------------------------------- CH2 The Airline Dream
a = lambda p, occ=0, edge="s", d=0.0: A(p, 2, occ, edge, d)
CARDSHOT(2, "a330c", "neutral")
VID(a("in 2005", d=-0.1), 27989, off=0.0, g="warm", xf=0.6)
YEAR(a("2005", d=-0.1), "2005")
IMG(a("launched kingfisher airlines", d=-0.1), "a320", g="neutral", z=(1.05, 1.15), pan=((-0.3, 0), (0.1, 0)), tag="KINGFISHER AIRLINES  ·  2005")
IMG(a("and this wasn't", d=-0.1), "a330c", g="neutral", z=(1.15, 1.02), pan=((0.2, 0), (0.0, 0)))
VID(a("he wanted to create", d=-0.15), 40102, off=8.0, g="warm")
IMG(a("comfortable seats", d=-0.15), "kfgood|deccanint", g="warm", z=(1.0, 1.1), fb=(4196, 1.0, 1.0, "warm"))
IMG(a("stylish branding", d=-0.15), "kftail|kflogo|a330b", g="warm", z=(1.0, 1.1))
IMG(a("good food", d=-0.15), "kfmeal|kfmeal2", g="warm", z=(1.0, 1.1), fb=(5227, 2.0, 1.0, "warm"))
VID(a("premium service", d=-0.15), 4065, off=4.0, g="warm")
CHECK([(a("comfortable seats"), "Comfortable seats"), (a("attractive cabin"), "Stylish cabins"), (a("stylish branding"), "Bold red branding"),
       (a("good food"), "Good food"), (a("premium service"), "Premium service")], a("the airline was designed", d=-0.15), "THE KINGFISHER EXPERIENCE")
VID(a("the airline was designed", d=-0.12), 11303, off=2.0, g="warm")
IMG(a("and its marketing", d=-0.12), "beerad", g="warm", z=(1.1, 1.0), pan=((0, -0.4), (0, -0.3)))
IMG(a("the red kingfisher branding", d=-0.12), "a330b", g="neutral", z=(1.0, 1.15))
IMG(a("for a while", d=-0.12), "a330", g="warm", z=(1.12, 1.0), pan=((0.2, 0), (-0.2, 0)))
VID(a("passengers loved", d=-0.12), 4008, off=1.0, g="teal")
IMG(a("and the airline quickly", d=-0.12), "kfhyd|a321", g="warm", z=(1.0, 1.1), tag="HYDERABAD AIRPORT  ·  2008")
VID(a("but there was one", d=-0.12), 7030, off=3.0, g="cool", flash=True, xf=0.0, dim=0.5)
HEAD(a("one major problem", d=-0.05), a("running an airline", d=-0.2), "ONE MAJOR PROBLEM", color=RED, size=130)
VID(a("running an airline", d=-0.12), 4003, off=6.0, g="cool")
VID(a("fuel", d=-0.2), 4389, off=2.0, g="cool", xf=0.25)
COSTS([(a("fuel"), "Fuel"), (a("aircraft leases"), "Aircraft leases"), (a("airport charges"), "Airport charges"),
       (a("maintenance"), "Maintenance"), (a("employee salaries"), "Employee salaries")], a("and kingfisher was trying", d=-0.15))
VID(a("and kingfisher was trying", d=-0.12), 9535, off=1.0, g="neutral")
VID(a("where profit margins", d=-0.12), 49219, off=2.0, g="neutral")
VID(a("but instead of slowing", d=-0.12), 3044, off=0.0, g="warm")
IMG(a("malia decided to expand", d=-0.12), "a321|a330c", g="neutral", z=(1.0, 1.12), pan=((0.2, 0), (-0.2, 0)))

# ---------------------------------------------------------------- CH3 The Big Gamble
a = lambda p, occ=0, edge="s", d=0.0: A(p, 3, occ, edge, d)
CARDSHOT(3, "deccana320|deccanatr|a320")
IMG(a("in 2007", d=-0.1), "deccana320|deccanatr", g="warm", z=(1.0, 1.12), xf=0.6, tag="AIR DECCAN", fb=(4083, 1.0, 1.0, "warm"))
YEAR(a("2007", d=-0.1), "2007")
IMG(a("founded by captain", d=-0.15), "gopinath", "side", side="right", g="warm", z=(1.0, 1.06), tag="CAPT. G. R. GOPINATH  ·  FOUNDER, AIR DECCAN")
shot(a("now think about", d=-0.15), "split",
     items=[(pick("a330c|a330"), "KINGFISHER", "PREMIUM", a("kingfisher was a premium")),
            (pick("deccanatr|deccana320|deccanint") or "ubcity", "AIR DECCAN", "LOW-COST", a("air deccan was built"))],
     credit="Photos: Jakkrit Prasertwit · Sean d'Silva / Aeroprints — GFDL / CC BY-SA · Wikimedia Commons")
VID(a("on paper", d=-0.12), 42648, off=0.0, g="warm")
VID(a("but combining two", d=-0.12), 22827, off=1.0, g="cool")
VID(a("kingfisher continued expanding", d=-0.12), 47016, off=2.0, g="cool")
VID(a("rising fuel prices", d=-0.2), 47018, off=4.0, g="cool", xf=0.25)
VID(a("the airline was spending", d=-0.12), 45702, off=2.0, g="cool")
VID(a("but its business", d=-0.12), 49219, off=5.0, g="cool")
VID(a("and slowly", d=-0.12), 39854, off=1.0, g="cool")
VID(a("the airline began struggling", d=-0.12), 18299, off=3.0, g="cool")
VID(a("flights were delayed", d=-0.15), 36351, off=0.0, g="cool", dim=0.35, slow=1.4)
BOARD(a("flights were delayed", d=-0.1), a("passengers were frustrated", d=-0.1),
      [("IT 2401", "MUMBAI", "DELAYED", (245, 175, 60), a("delayed")), ("IT 0305", "DELHI", "CANCELLED", RED, a("cancelled")),
       ("IT 5110", "BENGALURU", "CANCELLED", RED, a("cancelled", d=0.25)), ("IT 0742", "GOA", "DELAYED", (245, 175, 60), a("delayed", d=0.3)),
       ("IT 2011", "KOLKATA", "CANCELLED", RED, a("cancelled", d=0.5))])
VID(a("passengers were frustrated", d=-0.12), 23269, off=3.0, g="cool")
IMG(a("and the airline that once", d=-0.12), "a330c", g="neutral", z=(1.0, 1.1), bw_at=(a("financial troubles", d=-0.6), a("financial troubles", edge="e")))

# ---------------------------------------------------------------- CH4 Grounded
a = lambda p, occ=0, edge="s", d=0.0: A(p, 4, occ, edge, d)
CARDSHOT(4, "kfclosed|kfcounter|a330", "faded")
IMG(a("by 2012", d=-0.1), "kfclosed|a330", g="faded", z=(1.0, 1.12), xf=0.6, tag="2012")
YEAR(a("2012", d=-0.1), "2012")
IMG(a("its operations were suspended", d=-0.12), "kfcounter|kfclosed", g="faded", z=(1.12, 1.0), pan=((0.3, 0), (0, 0)),
    tag="A CLOSED KINGFISHER COUNTER  ·  GOA", fb=(4625, 2.0, 1.0, "cool"))
VID(a("the directorate general", d=-0.12), 38512, off=1.0, g="neutral", dim=0.4)
STAMP(a("the directorate general", d=0.1), a("just think about that", d=-0.15), a("suspended its", d=0.1))
VID(a("just think about that", d=-0.12), 36351, off=2.0, g="cool")
IMG(a("an airline that was once", d=-0.12), "a330c", g="neutral", z=(1.0, 1.08), xf=0.3,
    bw_at=(a("had stopped flying", d=-0.2), a("had stopped flying", edge="e")))
STAMP(a("had stopped flying", d=-0.2), a("thousands of employees", d=-0.15), a("stopped flying", d=0.05), text="GROUNDED", card=False, y=480)
VID(a("thousands of employees", d=-0.12), 4008, off=4.0, g="cool")
VID(a("passengers were left", d=-0.12), 27760, off=1.0, g="cool")
IMG(a("and banks were trying", d=-0.12), "sbi", "side", side="right", g="neutral", z=(1.0, 1.06), tag="STATE BANK OF INDIA", fb=(24604, 0.0, 1.0, "cool"))
VID(a("a consortium of lenders", d=-0.12), 46977, off=2.0, g="cool", dim=0.6)
WORDPOP([(a("a consortium of lenders"), "A consortium of lenders", WHITE), (a("thousands of crores"), "Thousands of crores", GOLD)],
        a("malia's business empire", d=-0.15), y=520, size=90)
HIDE.append((a("a consortium of lenders", d=-0.1), a("malia's business empire", d=-0.15)))
IMG(a("malia's business empire", d=-0.12), "mallya_wef", g="bw", z=(1.0, 1.15), pan=((0.25, -0.2), (0.25, -0.35)))
VID(a("but the story didn't", d=-0.12), 27496, off=10.0, g="cool")
VID(a("it was about to become", d=-0.12), 47602, off=0.0, g="cool", slow=1.3)

# ---------------------------------------------------------------- CH5 The Legal Battle
a = lambda p, occ=0, edge="s", d=0.0: A(p, 5, occ, edge, d)
CARDSHOT(5, "wmc|rcj", "cool")
VID(a("kingfisher's collapse left", d=-0.1), 14126, off=2.0, g="cool", xf=0.6)
VID(a("indian investigating agencies", d=-0.12), 47732, off=3.0, g="cool", dim=0.45)
WORDPOP([(a("financial irregularities"), "Financial irregularities", WHITE), (a("fraud"), "Fraud", WHITE),
         (a("and money laundering"), "Money laundering", WHITE)], a("malia denied", d=-0.1), y=540, size=84)
def _alleg(layer, t, t0=a("indian investigating agencies"), t1=a("malia denied", d=-0.1)):
    put(layer, text_img("ALLEGED BY INDIAN INVESTIGATING AGENCIES", "sb", 28, GOLD, track=8), W / 2, 330, win(t, t0, t1, 0.4, 0.3), "mm")
ev(a("indian investigating agencies"), a("malia denied", d=-0.1), _alleg)
HIDE.append((a("financial irregularities", d=-0.1), a("malia denied", d=-0.1)))
IMG(a("malia denied", d=-0.12), "mallya_goa2", "side", side="left", g="warm", z=(1.0, 1.06))
LOWER(a("malia denied", d=0.2), a("but the pressure", d=-0.2), "VIJAY MALLYA", "DENIED ANY WRONGDOING")
VID(a("but the pressure", d=-0.12), 4331, off=2.0, g="cool")
VID(a("on march 2", d=-0.12), 23146, off=8.0, g="cool")
YEAR(a("on march 2", d=0.0), "2 March 2016", dur=3.0)
VID(a("malia left india", d=-0.15), 26853, off=1.0, g="cool", dim=0.5)
ROUTE(a("malia left india", d=-0.05), a("soon afterwards", d=-0.1), sub="2 MARCH 2016", dur=1.4)
VID(a("soon afterwards", d=-0.12), 46820, off=4.0, g="cool")
IMG(a("in 2017", d=-0.12), "wmc|wmc2|rcj", g="cool", z=(1.0, 1.12), tag="WESTMINSTER MAGISTRATES' COURT  ·  LONDON", fb=(4079, 0.0, 1.0, "cool"))
YEAR(a("2017", d=-0.1), "2017")
VID(a("but was released on bail", d=-0.15), 4495, off=3.0, g="cool")
VID(a("in 2019", d=-0.12), 47686, off=2.0, g="cool", dim=0.4)
YEAR(a("2019", d=-0.1), "2019", dur=1.6)
HEAD(a("fugitive economic offender", d=-0.1), a("the legal battle continued", d=-0.1), "FUGITIVE ECONOMIC OFFENDER",
     above="DECLARED BY A SPECIAL COURT IN INDIA", size=92, y=540)
VID(a("the legal battle continued", d=-0.12), 46820, off=10.0, g="cool")
shot(a("a uk court approved", d=-0.15), "ltl", bg=pick("wmc|rcj|ubcity"),
     items=[("2017", "ARRESTED IN THE UK", "RELEASED ON BAIL", a("a uk court approved", d=0.05)),
            ("2018", "UK COURT APPROVES", "EXTRADITION", a("approved")),
            ("2019", "DECLARED FUGITIVE", "ECONOMIC OFFENDER", a("a uk court approved", d=0.35)),
            ("2020", "HIS APPEAL", "REJECTED", a("rejected")),
            ("TODAY", "EXTRADITION", "NOT CARRIED OUT", a("still not been"))])
IMG(a("malia remains in the uk", d=-0.12), "tewin", g="cool", z=(1.0, 1.1), tag="LADYWALK  ·  TEWIN, HERTFORDSHIRE", fb=(4457, 2.0, 1.0, "cool"))

# ---------------------------------------------------------------- CH6 Unfinished Business
a = lambda p, occ=0, edge="s", d=0.0: A(p, 6, occ, edge, d)
CARDSHOT(6, "rcj|wmc", "cool")
VID(a("and here's an important", d=-0.1), 45702, off=6.0, g="warm", xf=0.6)
VID(a("the financial recovery", d=-0.12), 47005, off=4.0, g="warm")
IMG(a("indian authorities have reported", d=-0.12), "rupee|sbi", g="warm", z=(1.0, 1.15), pan=((0.2, 0), (-0.1, 0)), fb=(24584, 1.0, 1.0, "warm"))
HEAD(a("thousands of crores", d=-0.05), a("but recovering money", d=-0.15), "ASSETS RESTORED", above="THOUSANDS OF CRORES", sub="BACK TO THE BANKS", size=120, color=GOLD)
VID(a("but recovering money", d=-0.12), 47602, off=0.0, g="cool", dim=0.35, slow=1.6)
VS(a("but recovering money", d=0.05), a("in 2025", d=-0.15), "RECOVERING MONEY", "RESOLVING ALLEGATIONS", a("resolving criminal"))
IMG(a("in 2025", d=-0.12), "rcj|wmc", g="cool", z=(1.0, 1.12), tag="ROYAL COURTS OF JUSTICE  ·  LONDON", fb=(33823, 0.0, 1.0, "cool"))
YEAR(a("2025", d=-0.1), "2025")
LOWER(a("lost an appeal", d=-0.1), a("and in 2026", d=-0.2), "APPEAL LOST", "UK BANKRUPTCY ORDER")
VID(a("and in 2026", d=-0.12), 47686, off=8.0, g="warm")
YEAR(a("2026", d=-0.1), "2026")
IMG(a("with malia saying", d=-0.12), "mallya_wef", "side", side="right", g="neutral", z=(1.0, 1.06))
VID(a("so even after", d=-0.12), 4457, off=2.0, g="warm")
ITALIC(a("the story is not", d=-0.1), a("the story is not", edge="e", d=2.6), "The story is not over.", size=110)

# ---------------------------------------------------------------- CH7 The Lesson + CTA
a = lambda p, occ=0, edge="s", d=0.0: A(p, 7, occ, edge, d)
CARDSHOT(7, "ubcity")
IMG(a("vijay malia's story", d=-0.1), "mallya_wef", g="neutral", z=(1.0, 1.1), pan=((0.2, -0.2), (0.2, -0.3)), xf=0.6)
shot(a("both the power", d=-0.2), "split",
     items=[(pick("a330c"), "THE POWER", "", a("both the power")), (pick("kfclosed|kfcounter|a330"), "THE RISKS", "", a("the risks of"))],
     bw_right=True, credit="Photos: Jakkrit Prasertwit (GFDL) · Arne Hückelheim (CC BY-SA 3.0) · Wikimedia Commons")
shot(a("he built successful", d=-0.15), "trip", bg=pick("ubcity"), dark_at=a("he built successful"),
     items=[(pick("ubcity2|ubcity"), "UB GROUP", "", a("successful businesses")), (pick("beer"), "KINGFISHER BEER", "", a("beer brands")),
            (pick("a330c"), "KINGFISHER AIRLINES", "", a("premium airline"))],
     credit="Photos via Wikimedia Commons — CC BY-SA / GFDL (see description)")
VID(a("but his expansion", d=-0.12), 22387, off=24.0, g="cool")
IMG(a("kingfisher's collapse became", d=-0.12), "kfcounter|kfclosed", g="bw", z=(1.0, 1.12), fb=(36351, 0.0, 1.0, "cool"))
WORDPOP([(a("business ambition"), "Ambition", GOLD), (a("debt"), "+ Debt", RED), (a("and financial planning"), "− Planning", WHITE)],
        a("and perhaps", d=-0.15), y=520, size=96)
HIDE.append((a("business ambition", d=-0.1), a("and perhaps", d=-0.15)))
shot(a("and perhaps", d=-0.12), "vid", xf=0.5, src="vid/12496.mp4", off=2.0, slow=1.0, g="warm", dim=0.7, tag=None)
QUOTE(a("building a business", d=-0.2), a("you can have", d=-0.2), "“Building an empire is difficult.", "Managing it responsibly matters more.”",
      a("but managing", d=-0.1))
VID(a("you can have", d=-0.12), 8706, off=3.0, g="warm")
VID(a("a luxurious lifestyle", d=-0.12), 4446, off=6.0, g="warm")
VID(a("and massive business", d=-0.12), 41541, off=2.0, g="warm")
VID(a("but at the end", d=-0.12), 9535, off=3.0, g="neutral")
IMPACT7 = SEGS[7]["impact"]
VID(a("sense.", edge="e", d=0.35), 14154, off=0.0, g="warm", xf=0.6, dim=0.6)
def _yt(layer, t, t0=a("sense.", edge="e", d=0.8), t1=IMPACT7):
    txt = "NOW, YOUR TURN..."; n_ = int(clamp((t - t0 - 0.1) / 1.0) * len(txt)) + 1
    s_ = 1.0 + 0.25 * eio((t - (t1 - 0.45)) / 0.45)
    if t0 <= t <= t1:
        put(layer, text_img(txt[:n_], "l", 64, WHITE, track=16), W / 2 - text_w(txt, "l", 64, 16) * s_ / 2, 540, win(t, t0, t1, 0.2, 0.12), "lm", scale=s_)
ev(a("sense.", edge="e", d=0.8), IMPACT7, _yt)
shot(IMPACT7, "poll", xf=0.0, flash=True,
     items=[(pick("mallya_wef"), "A VISIONARY", "who built iconic brands", a("a visionary")),
            (pick("kfclosed|kfcounter|a330"), "DISASTROUS DECISIONS", "that grounded an airline", a("disastrous decisions")),
            (pick("mallya_goa2|mallya_300"), "MORE TO THE STORY?", "you decide", a("or is there more"))],
     t_comment=a("share your thoughts"), credit="Photos: World Economic Forum (CC BY-SA 2.0) · Arne Hückelheim (CC BY-SA 3.0) · PIB (GODL-India)")
HIDE.append((IMPACT7, a("and if you enjoy", d=-0.2)))
shot(a("and if you enjoy", d=-0.15), "subscribe", xf=0.5, t_click=a("subscribe", d=0.35))
shot(END0, "end", xf=0.6)


S.sort(key=lambda s_: s_["t0"])
for i, s_ in enumerate(S): s_["t1"] = S[i + 1]["t0"] if i + 1 < len(S) else TOTAL

# ================= shot rendering =================
VIDS = {}
def vid_for(key, src, off, slow, g):
    if key not in VIDS: VIDS[key] = Vid(src, off, slow, g)
    return VIDS[key]
def paste_panel(base, key, cx, cy, pw, ph, k, t_rel, g="neutral", border=True):
    im = kb_crop(graded(key, g), 1.04 + 0.05 * clamp(t_rel / 4), 0, 0, (pw, ph)).convert("RGBA")
    fr = Image.new("RGBA", (pw + 6, ph + 6), (255, 255, 255, 235 if border else 0)); fr.paste(im, (3, 3))
    arr = np.array(fr); arr[..., 3] = (arr[..., 3] * clamp(k)).astype(np.uint8)
    sh = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 50, pw + 40, ph + 50], fill=(0, 0, 0, int(160 * clamp(k))))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (int(cx - pw / 2 - 40), int(cy - ph / 2 - 40)))
    base.alpha_composite(Image.fromarray(arr), (int(cx - pw / 2 - 3), int(cy - ph / 2 - 3)))

def render_shot(s_, t):
    lt = t - s_["t0"]; dur = max(s_["t1"] - s_["t0"], 0.01); p = clamp(lt / dur); k = s_["kind"]
    if k == "vid":
        fr = vid_for(id(s_), s_["src"], s_["off"], s_["slow"], s_["g"]).frame(int(lt * FPS)).astype(np.float32)
        if "dim" in s_: fr *= s_["dim"]
        return fr
    if k == "img":
        z0, z1 = s_["z"]; z = z0 + (z1 - z0) * p
        (px0, py0), (px1, py1) = s_["pan"]; px, py = px0 + (px1 - px0) * p, py0 + (py1 - py0) * p
        if s_["layout"] == "side":
            bg = kb_crop(blurred_bg(s_["key"], s_["g"]), 1.0 + 0.05 * p, 0, 0)
            src = graded(s_["key"], s_["g"]); fh = int(H * z); fw = int(src.width * fh / src.height)
            if fw > W * 0.75: fw = int(W * 0.75); fh = int(src.height * fw / src.width)
            fg = src.resize((fw, fh), Image.BILINEAR)
            cx = W * (0.68 if s_["side"] == "right" else 0.32)
            bg.paste(fg, (int(cx - fw / 2), int(H / 2 - fh / 2 - (fh - H) * 0.15)), feather_mask(fw, fh))
            fr = np.array(bg).astype(np.float32)
            if "bw_at" in s_:
                a0, a1 = s_["bw_at"]; m = eio((t - a0) / (a1 - a0))
                lum = fr @ np.array([0.299, 0.587, 0.114], np.float32)
                bw = np.repeat((128 + (lum - 128) * 1.15)[..., None], 3, 2); fr = fr * (1 - m) + bw * m
        else:
            fr = np.array(kb_crop(graded(s_["key"], s_["g"]), z, px, py)).astype(np.float32)
            if "bw_at" in s_:
                a0, a1 = s_["bw_at"]; m = eio((t - a0) / (a1 - a0))
                if m > 0:
                    lum = fr @ np.array([0.299, 0.587, 0.114], np.float32)
                    bw = np.repeat((128 + (lum - 128) * 1.15)[..., None], 3, 2); fr = fr * (1 - m) + bw * m * 0.85
        if "dark" in s_:
            d0, d1, ta, tb = s_["dark"]; fr *= d0 + (d1 - d0) * eio((t - ta) / max(tb - ta, 0.01))
        return fr
    if k == "ext":
        return vid_for(id(s_), s_["src"], 0.0, 1.0, "none").frame(int(lt * FPS)).astype(np.float32)
    if k == "dark":
        return vid_for(id(s_), f"vid/{s_['bg']}.mp4", 0, 1.0, "warm").frame(int(lt * FPS)).astype(np.float32) * 0.8
    if k == "card": return render_card(s_, t, lt)
    if k == "trip": return render_trip(s_, t, lt)
    if k == "split": return render_split(s_, t, lt)
    if k == "simplify": return render_simplify(s_, t, lt)
    if k == "timeline": return render_timeline(s_, t, lt)
    if k == "ltl": return render_ltl(s_, t, lt)
    if k == "poll": return render_poll(s_, t, lt)
    if k == "subscribe": return render_subscribe(s_, t, lt)
    if k == "end": return render_end(s_, t, lt)

def particles_bg(s_, lt, key, g="warm", dark=0.3, amt=0.35):
    bg = np.array(kb_crop(blurred_bg(key, g, dark), 1.0 + 0.012 * lt, 0, 0)).astype(np.float32)
    pr = vid_for(("p", id(s_)), "vid/18142.mp4", 0.0, 1.0, "warm").frame(int(lt * FPS) % 290).astype(np.float32)
    return 255 - (255 - bg) * (255 - pr * amt) / 255

def render_card(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, s_["bgkey"], s_["bgg"], 0.32), 0, 255).astype(np.uint8)).convert("RGBA")
    t0, t1 = s_["t0"], s_["t1"]
    put(base, text_img(f"CHAPTER  {s_['n']:02d}", "sb", 30, GOLD, track=12), W / 2, 395, win(t, t0 + 0.25, t1 + 0.6, 0.5, 0.5), "mm")
    tw = big_title(base, t, t0 + 0.45, t1 + 0.6, s_["title"], "pf7", 118, 520, WHITE, 26, 4)
    if tw: gold_rules(base, t, t0 + 0.5, t1 + 0.6, 520, tw / 2)
    put(base, text_img(s_["years"], "l", 34, (225, 225, 225), track=10), W / 2, 640, win(t, t0 + 1.0, t1 + 0.6, 0.5, 0.5), "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_trip(s_, t, lt):
    bg = np.array(kb_crop(graded(s_["bg"], "warm"), 1.05 + 0.016 * lt, 0, 0)).astype(np.float32)
    bg *= 1.0 - 0.65 * eio((t - s_["dark_at"]) / 0.6)
    base = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")
    for i, (key, lab, sub, ts) in enumerate(s_["items"]):
        k = eo((t - ts + 0.15) / 0.45)
        if k <= 0: continue
        cx = W / 2 + (i - 1) * 580; cy = 460 + 70 * (1 - k)
        paste_panel(base, key, cx, cy, 500, 340, k, t - ts)
        lk = eo((t - ts - 0.1) / 0.4)
        put(base, text_img(lab, "b", 36, GOLD, track=6), cx, cy + 210 + 10 * (1 - lk), lk, "mt")
        if sub: put(base, text_img(sub, "m", 26, (220, 220, 220)), cx, cy + 264, lk * 0.85, "mt")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_split(s_, t, lt):
    base = Image.fromarray(RADIAL.astype(np.uint8)).convert("RGBA")
    for i, (key, lab, sub, ts) in enumerate(s_["items"]):
        k = eo((t - s_["t0"] - i * 0.35) / 0.6)
        if k <= 0: continue
        g = "bw" if (i == 1 and s_.get("bw_right")) else "warm"
        im = kb_crop(graded(key, g), 1.04 + 0.03 * clamp((t - ts) / 4), 0, -0.2 if key in ("redshawl", "jobs1984b") else 0, (W // 2 - 4, H)).convert("RGBA")
        arr = np.array(im); arr[..., 3] = int(255 * k)
        x = 0 if i == 0 else W // 2 + 4
        base.alpha_composite(Image.fromarray(arr), (x + int((-60 if i == 0 else 60) * (1 - k)), 0))
    d = ImageDraw.Draw(base); d.rectangle([W // 2 - 2, 0, W // 2 + 2, H], fill=GOLD + (220,))
    dk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(dk)
    for yy_ in range(560, H, 4): dd.rectangle([0, yy_, W, yy_ + 4], fill=(0, 0, 0, int(min(200, (yy_ - 560) * 0.5))))
    base.alpha_composite(dk)
    for i, (key, lab, sub, ts) in enumerate(s_["items"]):
        lk = eo((t - ts - 0.15) / 0.45)
        cx = W / 4 if i == 0 else 3 * W / 4
        fs_ = 76
        while text_w(lab, "pf9", fs_) > W / 2 - 120: fs_ -= 4
        put(base, text_img(lab, "pf9", fs_, GOLD if i == 0 else WHITE), cx, 690 + 15 * (1 - lk), lk, "mm")
        if sub: put(base, text_img(sub, "sb", 26, WHITE, track=8), cx, 770, lk * 0.9, "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_simplify(s_, t, lt):
    base = Image.fromarray(RADIAL.astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(base)
    ts = s_["t_simple"]; m = eio((t - ts) / 0.9)
    cols, rows, sz, gap = 8, 3, 92, 26; keep = {(1, 1), (6, 1), (3, 1), (4, 1)}
    gw = cols * sz + (cols - 1) * gap; x0 = W / 2 - gw / 2; y0 = 300
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c; ka = eo((t - s_["t0"] - 0.15 - i * 0.025) / 0.35)
            if (c, r) in keep:
                j = sorted(keep).index((c, r)); tx = W / 2 + (j - 1.5) * 250 - 100; ty = 380
                x = (x0 + c * (sz + gap)) * (1 - m) + tx * m; y = (y0 + r * (sz + gap)) * (1 - m) + ty * m; s2 = sz + (200 - sz) * m
                col = tuple(int(150 + (cc - 150) * m) for cc in GOLD)
                d.rounded_rectangle([x, y, x + s2, y + s2], radius=18, fill=col + (int(255 * ka),))
            else:
                a_ = ka * (1 - m)
                if a_ > 0.01: d.rounded_rectangle([x0 + c * (sz + gap), y0 + r * (sz + gap), x0 + c * (sz + gap) + sz, y0 + r * (sz + gap) + sz], radius=14, fill=(150, 150, 160, int(200 * a_)))
    put(base, text_img("FROM DOZENS OF PRODUCTS", "sb", 34, WHITE, track=10), W / 2, 230, win(t, s_["t0"] + 0.3, ts + 0.2, 0.4, 0.3), "mm")
    put(base, text_img("TO A FEW, DONE EXCEPTIONALLY WELL", "sb", 34, GOLD, track=10), W / 2, 230, win(t, ts + 0.5, s_["t1"] + 1, 0.4, 0.3), "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_timeline(s_, t, lt):
    bg = np.array(kb_crop(blurred_bg(s_["bg"], "warm", 0.35), 1.02 + 0.01 * lt, 0, 0)).astype(np.float32)
    base = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(base)
    y = 520; xL, xR = 220, W - 220; n = len(s_["items"])
    first = s_["items"][0][2]; L = eio((t - first + 0.6) / 1.2)
    d.rectangle([xL, y - 2, xL + (xR - xL) * L, y + 2], fill=(255, 255, 255, 200))
    pts = []
    for i, (lab, yrs, ts) in enumerate(s_["items"]):
        x = xL + (xR - xL) * (i + 0.5) / n; k = eback((t - ts) / 0.45) if t >= ts else 0
        dip = 110 if lab == "A PUBLIC FALL" else (-60 if lab in ("HIGHS",) else (40 if lab == "REBUILDING" else -120))
        pts.append((x, y + dip, k, lab, yrs, ts))
    for i in range(1, len(pts)):
        x0_, y0_, k0, *_ = pts[i - 1]; x1_, y1_, k1, *_ = pts[i]
        if k1 > 0:
            f = clamp(k1); d.line([x0_, y0_, x0_ + (x1_ - x0_) * f, y0_ + (y1_ - y0_) * f], fill=GOLD + (255,), width=5)
    for x, yy_, k, lab, yrs, ts in pts:
        if k <= 0: continue
        r = 16 * clamp(k, 0, 1.2); col = RED if lab == "A PUBLIC FALL" else GOLD
        d.ellipse([x - r, yy_ - r, x + r, yy_ + r], fill=col + (255,), outline=(255, 255, 255, 255), width=3)
        above = yy_ < y
        put(base, text_img(lab, "b", 34, WHITE, track=5), x, yy_ + (-70 if above else 62), clamp(k), "mm")
        put(base, text_img(yrs, "m", 26, (220, 220, 220)), x, yy_ + (-30 if above else 102), clamp(k) * 0.85, "mm")
    return np.array(base.convert("RGB")).astype(np.float32)


def render_ltl(s_, t, lt):
    """legal timeline: evenly spaced nodes, line grows to the latest revealed node"""
    bg = np.array(kb_crop(blurred_bg(s_["bg"], "cool", 0.33), 1.02 + 0.01 * lt, 0, 0)).astype(np.float32)
    base = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(base)
    put(base, text_img("THE LEGAL BATTLE", "sb", 30, GOLD, track=12), W / 2, 200, eo(lt / 0.5), "mm")
    y = 560; xL, xR = 200, W - 200; n_ = len(s_["items"])
    xs = [xL + (xR - xL) * i / (n_ - 1) for i in range(n_)]
    d.rectangle([xL, y - 2, xR, y + 2], fill=(255, 255, 255, 60))
    L = xL
    for i, (yr, l1, l2, ts) in enumerate(s_["items"]):
        k = eio((t - ts + 0.3) / 0.6)
        if k <= 0: continue
        st = xs[i - 1] if i else xL; L = max(L, st + (xs[i] - st) * k)
    d.rectangle([xL, y - 3, L, y + 3], fill=GOLD + (255,))
    for i, (yr, l1, l2, ts) in enumerate(s_["items"]):
        k = eback((t - ts) / 0.45) if t >= ts else 0
        if k <= 0: continue
        x = xs[i]; last = i == n_ - 1; col = RED if last else GOLD
        r = 17 * clamp(k, 0, 1.2)
        if last:
            pr = ((t - ts) * 0.8) % 1.0; rr = 18 + 40 * pr
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=RED + (int(200 * (1 - pr)),), width=3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,), outline=(255, 255, 255, 255), width=3)
        above = i % 2 == 0; a_ = clamp(k)
        put(base, text_img(yr, "pf9", 64, col), x, y + (-120 if above else 105), a_, "mm")
        put(base, text_img(l1, "b", 28, WHITE, track=4), x, y + (-62 if above else 160), a_, "mm")
        put(base, text_img(l2, "m", 26, (225, 225, 225), track=3), x, y + (-30 if above else 195), a_ * 0.9, "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_poll(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, pick("a330c|ubcity"), "warm", 0.22, 0.3), 0, 255).astype(np.uint8)).convert("RGBA")
    put(base, text_img("WHAT DO YOU THINK?", "b", 54, WHITE, track=8), W / 2, 170, eo(lt / 0.5), "mm")
    put(base, text_img("ABOUT VIJAY MALLYA", "sb", 28, GOLD, track=12), W / 2, 235, eo((lt - 0.3) / 0.5), "mm")
    for i, (key, lab, sub, ts) in enumerate(s_["items"]):
        k = eo((t - ts + 0.15) / 0.45)
        if k <= 0 or key is None: continue
        cx = W / 2 + (i - 1) * 580; cy = 470 + 60 * (1 - k)
        paste_panel(base, key, cx, cy, 480, 320, k, t - ts, g="bw" if i == 1 else "warm")
        fs_ = 50
        while text_w(lab, "pf9", fs_) > 470: fs_ -= 2
        put(base, text_img(lab, "pf9", fs_, GOLD if i != 1 else RED), cx, cy + 200, k, "mt")
        put(base, text_img(sub, "m", 26, (225, 225, 225)), cx, cy + 262, k * 0.85, "mt")
    tc = s_["t_comment"]
    if t >= tc - 0.1:
        kb = eback((t - tc) / 0.45); d = ImageDraw.Draw(base); cx, cy = W / 2, 905
        w_, h_ = 560 * clamp(kb, 0, 1.1), 92 * clamp(kb, 0, 1.1)
        d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], radius=h_ / 2, fill=(255, 255, 255, 240))
        d.polygon([(cx - 40, cy + h_ / 2 - 2), (cx - 10, cy + h_ / 2 - 2), (cx - 46, cy + h_ / 2 + 26 * clamp(kb))], fill=(255, 255, 255, 240))
        put(base, text_img("TELL US IN THE COMMENTS", "b", 34, (20, 20, 24), track=4, shadow=False), cx, cy + 2, clamp(kb), "mm", scale=max(0.05, clamp(kb, 0, 1.1)))
    return np.array(base.convert("RGB")).astype(np.float32)

def button(layer, t, cx, cy, tb, tc, label="SUBSCRIBE"):
    d = ImageDraw.Draw(layer)
    kb = eback((t - tb) / 0.45) if t >= tb else 0
    if kb <= 0: return
    clicked = t >= tc + 0.08
    sc = kb * (1 - 0.06 * math.sin(math.pi * clamp((t - tc) / 0.16)))
    bw_, bh_ = 470 * sc, 112 * sc; col = (62, 62, 66) if clicked else (229, 33, 23)
    btn = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2 + 10, cx + bw_ / 2, cy + bh_ / 2 + 10], radius=bh_ / 2, fill=(0, 0, 0, 110))
    btn = btn.filter(ImageFilter.GaussianBlur(10)); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2, cx + bw_ / 2, cy + bh_ / 2], radius=bh_ / 2, fill=col + (255,))
    layer.alpha_composite(btn)
    put(layer, text_img("SUBSCRIBED" if clicked else label, "b", 46, WHITE, track=4, shadow=False), cx, cy + 2, clamp(kb), "mm", scale=max(0.01, sc))
    if clicked:
        rk = clamp((t - tc) / 0.6); rr = 14 + 80 * eo(rk)
        d.ellipse([cx + 60 - rr, cy + 10 - rr, cx + 60 + rr, cy + 10 + rr], outline=(255, 255, 255, int(170 * (1 - rk))), width=3)
        bk = eback((t - tc - 0.25) / 0.4)
        if bk > 0:
            ang = math.sin((t - tc) * 22) * 18 * math.exp(-max(0, t - tc - 0.25) * 3)
            bell = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); bdd = ImageDraw.Draw(bell)
            bdd.ellipse([20, 20, 120, 120], fill=(255, 255, 255, 40), outline=(255, 255, 255, 200), width=3)
            bdd.pieslice([45, 38, 95, 98], 180, 360, fill=WHITE + (255,)); bdd.rectangle([45, 66, 95, 86], fill=WHITE + (255,))
            bdd.polygon([(38, 92), (102, 92), (95, 82), (45, 82)], fill=WHITE + (255,)); bdd.ellipse([62, 92, 78, 106], fill=WHITE + (255,))
            bell = bell.rotate(ang, resample=Image.BICUBIC, center=(70, 30))
            s2 = max(1, int(140 * clamp(bk, 0, 1.2))); bell = bell.resize((s2, s2), Image.BILINEAR)
            layer.alpha_composite(bell, (int(cx + 300 - s2 / 2), int(cy - s2 / 2)))
    if t >= tc - 0.9:
        ck = eio((t - (tc - 0.9)) / 0.8); x = cx + 60 + 420 * (1 - ck); y = cy + 10 + 260 * (1 - ck)
        ca = win(t, tc - 0.9, tc + 1.1, 0.2, 0.35)
        pts = [(x + a_, y + b_) for a_, b_ in [(0, 0), (0, 44), (11, 33), (19, 52), (27, 48), (19, 30), (34, 30)]]
        d.polygon([(a_ + 3, b_ + 4) for a_, b_ in pts], fill=(0, 0, 0, int(110 * ca)))
        d.polygon(pts, fill=(255, 255, 255, int(255 * ca)), outline=(20, 20, 20, int(255 * ca)))

def brand(layer, t, t0, y=300, a_=1.0):
    v = win(t, t0, 1e9, 0.6, 0.01) * a_
    put(layer, text_img("FOUNDER FILES", "pf9", 96, WHITE, track=10), W / 2, y, v, "mm")
    d = ImageDraw.Draw(layer); L = int(260 * eio((t - t0 - 0.3) / 0.8))
    d.rectangle([W / 2 - L, y + 72, W / 2 + L, y + 75], fill=GOLD + (int(255 * v),))


def render_subscribe(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, pick("a330c|ubcity"), "warm", 0.24), 0, 255).astype(np.uint8)).convert("RGBA")
    brand(base, t, s_["t0"] + 0.2, 330)
    put(base, text_img("stories of business empires, ambition, failures and comebacks", "m", 36, (235, 235, 235)), W / 2, 450,
        win(t, s_["t0"] + 0.9, 1e9, 0.5, 0.01), "mm")
    button(base, t, W / 2, 600, s_["t0"] + 1.0, s_["t_click"])
    return np.array(base.convert("RGB")).astype(np.float32)

def render_end(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, pick("ubcity|a330c"), "warm", 0.22), 0, 255).astype(np.uint8)).convert("RGBA")
    brand(base, t, s_["t0"] + 0.1, 170)
    d = ImageDraw.Draw(base)
    for i, (x, lab) in enumerate([(W / 2 - 430, "WATCH NEXT"), (W / 2 + 430, "MORE FOUNDER STORIES")]):
        k = eo((t - s_["t0"] - 0.5 - i * 0.2) / 0.6); w_, h_ = 760, 428
        d.rounded_rectangle([x - w_ / 2, 560 - h_ / 2, x + w_ / 2, 560 + h_ / 2], radius=18, outline=(255, 255, 255, int(150 * k)), width=3,
                            fill=(0, 0, 0, int(90 * k)))
        put(base, text_img(lab, "sb", 30, GOLD, track=8), x, 560 + h_ / 2 + 50, k, "mm")
    put(base, text_img("Thanks for watching.", "pfi", 44, WHITE), W / 2, 1000, win(t, s_["t0"] + 1.0, 1e9, 0.6, 0.01), "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def overlays(layer, t):
    for s_ in S:
        if not (s_["t0"] - 1 <= t <= s_["t1"] + 1): continue
        if s_.get("tag"): chapter_tag(layer, t, s_["t0"] + 0.35, s_["t1"] - 0.1, s_["tag"])
        if s_.get("credit") and s_["t0"] <= t <= s_["t1"]: credit(layer, t, s_["t0"] + 0.2, s_["t1"], s_["credit"])
    for t0, t1, fn in EV:
        if t0 <= t <= t1: fn(layer, t)
    draw_captions(layer, t)

FLASHES = [s_["t0"] for s_ in S if s_.get("flash")]
CUR = {"idx": None}
def frame_at(t, fi):
    idx = max(i for i, s_ in enumerate(S) if s_["t0"] <= t + 1e-9)
    if CUR["idx"] is not None and idx != CUR["idx"]:     # free finished video readers
        keep = {id(S[idx]), id(S[idx - 1]) if idx else None, ("p", id(S[idx])), ("p", id(S[idx - 1])) if idx else None}
        for k_ in list(VIDS):
            if k_ not in keep: VIDS.pop(k_).close()
    CUR["idx"] = idx
    cur = S[idx]; fr = render_shot(cur, t); lt = t - cur["t0"]
    if idx > 0 and cur["xf"] > 0 and lt < cur["xf"]:
        m = eio(lt / cur["xf"]); fr = render_shot(S[idx - 1], t) * (1 - m) + fr * m
    if not (cur["kind"] == "ext" and lt >= cur["xf"]):      # the ident plays untouched
        fr = fr * VIG + GRAIN[fi % 4]
    fr *= clamp(t / 0.5) * clamp((TOTAL - t) / 1.0)
    for ft in FLASHES:
        if ft <= t < ft + 0.45: f = 1 - eo((t - ft) / 0.45); fr = fr * (1 - f) + 255 * f
    base = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
    overlays(base, t)
    return base.convert("RGB")

def main():
    a_ = sys.argv[1:]
    if a_ and a_[0] == "--still":
        for ts in a_[1:]:
            t = float(ts); frame_at(t, 0).save(f"out/st_{t:06.2f}.jpg", quality=88)
            for v in VIDS.values(): v.close()
            VIDS.clear(); CUR["idx"] = None
        return
    i, n = int(a_[1]), int(a_[2])
    N = int(TOTAL * FPS); n0, n1 = N * i // n, N * (i + 1) // n
    if len(a_) > 3:      # sub-split chunk i into a_[3] pieces, render piece a_[4]
        m, j = int(a_[3]), int(a_[4]); L_ = n1 - n0; n0, n1 = n0 + L_ * j // m, n0 + L_ * (j + 1) // m; i = i * 10 + j
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                            "-threads", "2", f"out/part_{i:02d}.mp4"], stdin=subprocess.PIPE)
    for fi in range(n0, n1):
        enc.stdin.write(frame_at(fi / FPS, fi).tobytes())
        if fi % 300 == 0: print(f"part {i}: {fi/FPS:6.1f}s / {n1/FPS:.1f}", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main()
