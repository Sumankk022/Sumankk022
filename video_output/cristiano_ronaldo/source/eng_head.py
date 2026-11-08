"""Founder File — Cristiano Ronaldo documentary renderer.
python3 engine.py --still t [t ...]            render stills to out/st_<t>.jpg
python3 engine.py --part i n                    render frame-chunk i of n to out/part_i.mp4
"""
import json, subprocess, sys, os, math, functools, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
TL = json.load(open("out/timeline.json"))
SEGS = TL["segs"]; TOTAL = TL["total"]; END0 = TL["end0"]
GOLD = (246, 190, 62); RED = (226, 50, 58); GREEN = (40, 170, 90); WHITE = (255, 255, 255)

# ================= fonts / easing =================
FD = "/usr/share/fonts/opentype/inter/"; PF = "fonts/@fontsource_playfair-display/package/files/playfair-display-latin-"
BB = "fonts/@fontsource_bebas-neue/package/files/bebas-neue-latin-400-normal.woff"; OS = "fonts/@fontsource_oswald/package/files/oswald-latin-"
@functools.lru_cache(None)
def font(name, size):
    return ImageFont.truetype({"xb": FD + "InterDisplay-ExtraBold.otf", "b": FD + "InterDisplay-Bold.otf",
        "sb": FD + "InterDisplay-SemiBold.otf", "l": FD + "InterDisplay-Light.otf", "r": FD + "InterDisplay-Regular.otf",
        "m": FD + "InterDisplay-Medium.otf", "pf9": PF + "900-normal.woff", "pf7": PF + "700-normal.woff",
        "pfi": PF + "700-italic.woff", "pfi4": PF + "400-italic.woff", "bb": BB, "os7": OS + "700-normal.woff", "os5": OS + "500-normal.woff"}[name], size)
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
GRAIN = [np.repeat(np.repeat(_rng.normal(0, 2.6, (H // 2, W // 2, 1)).astype(np.float32), 2, 0), 2, 1) for _ in range(4)]
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
            pre = "crop=1920:810:0:135," if "v_thanks" in self.src else ""
            vf = (f"{pre}setpts={self.slow}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=bicubic,crop={W}:{H}")
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
GOLDW = set("""ronaldo ronaldo's cristiano cr7 football footballer madeira lisbon sporting cp manchester united real madrid juventus
ballon d'or champions league premier nassr saudi arabia portugal portugal's european messi lionel ferguson alex sir record records
seven greatest famous dream legend legends legendary obsession talent discipline ambition courage brand global phenomenon champions
trophy titles goals scorer goalscoring incredible extraordinary unbelievable special impressed emotional surprising nations uefa
founder file files subscribe euros million millions""".split())
REDW = set("""impossible little losing hated challenge challenges disaster injury struck disagreements questioned difficult wasn't easy""".split())
NO_HL = set()
DISP = {"madera.": "Madeira.", "nasser": "Nassr", "nasser.": "Nassr."}
def disp(tok, prev):
    t = tok
    for a_, b_ in DISP.items():
        if t.lower() == a_: t = b_
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
            end_sent = re.search(r"[.?!]$", tk["t"])
            nxt_end = next((k for k in range(j + 1, len(toks)) if re.search(r"[.?!]$", toks[k]["t"])), len(toks) - 1)
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

