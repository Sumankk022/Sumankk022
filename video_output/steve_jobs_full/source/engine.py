"""Founder Files — Steve Jobs full documentary renderer.
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
GOLDW = set("""apple apple's macintosh mac mac's next pixar wozniak wozniak's ipod iphone itunes imac toy story reed lucasfilm scully
ceo calligraphy typography garage legacy success comebacks founder files simple perfect accessible public value visionary
graphical mouse oregon francisco smartphone touchscreen apps greater curious electronics commercial technology animation comeback
remarkable extraordinary valuable influential effortless iconic""".split())
REDW = set("""pushed lost struggle struggling conflict disappointing clashed cancer died harsh criticism cost fall failure pressure
demanding declined resigned tensions difficult out disappear expensive confusing tumor""".split())
NO_HL = {"story"}   # 'story' only gold inside 'toy story'
def disp(tok, prev):
    t = tok
    if norm(t) == "scully": t = t.replace("Scully", "Sculley")
    if norm(t) == "next" and t[0] == "N": t = t.replace("Next", "NeXT")
    if prev and norm(prev) == "apple" and norm(t) in ("one", "two"): t = {"one": "I", "two": "II"}[norm(t)] + t[3:]
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
            if n_ == "story" and prevtok == "toy": col = GOLD
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

# ================= shots =================
S = []
def shot(t0, kind, xf=0.35, **kw): S.append(dict(t0=t0, kind=kind, xf=xf, **kw))
C = lambda who, lic: f"Photo: {who} · {lic} · Wikimedia Commons"
CR = {
 "jobs1972": "Photo: Homestead High School yearbook, 1972 · Public domain",
 "woz1968": "Photo: Homestead High School yearbook, 1968 · Public domain",
 "mac1984": "Photo: Bernard Gotfryd, 1984 · Library of Congress · Public domain",
 "jobs1984b": "Photo: Bernard Gotfryd, 1984 · Library of Congress · Public domain",
 "reagan1985": "Photo: White House Photographic Office, 1985 · Public domain",
 "pixar1998": "Photo: Sharon Farmer, White House, 1998 · Public domain",
 "obama2011": "Photo: Pete Souza, The White House, 2011 · Public domain",
 "ipod": "Photo: Evan-Amos · Public domain", "callig": "Malmesbury Bible (1407) · Public domain",
 "homebrew": "Homebrew Computer Club newsletter, 1976 · Public domain",
 "headshot2010": C("Matthew Yohe", "CC BY-SA 3.0"), "garage": C("Mathieu Thouvenin", "CC BY-SA 2.0"),
 "apple1": C("Ed Uthman", "CC BY-SA 2.0"), "nextcube": C("Michael Hicks", "CC BY 2.0"),
 "macworld2005": C("mylerdude", "CC BY 2.0"), "macworld2008": C("Tom Coates", "CC BY 2.0"),
 "iphone2007": C("Blake Patterson", "CC BY 2.0"), "ipad2010": C("Matt Buchanan", "CC BY 2.0"),
 "wwdc07": C("Acaben", "CC BY-SA 2.0"), "redshawl": C("Steve Jurvetson", "CC BY 2.0"),
 "goldengate": C("Chalmers Butterfield", "CC BY 2.5"), "reed": C("Another Believer", "CC BY-SA 4.0"),
 "wozniak": C("Gage Skidmore", "CC BY-SA 3.0"), "apple2": C("The wub", "CC BY-SA 4.0"),
 "apple2b": C("Rama & Musée Bolo", "CC BY-SA 2.0 fr"), "mac128": C("Grm wnr", "CC BY-SA 3.0"),
 "macmouse": C("Marcin Wichary", "CC BY 2.0"), "lisa": C("Timothy Colegrove", "CC BY-SA 4.0"),
 "sculley": C("JD Lasica", "CC BY 2.0"), "nextcube2": C("Rama & Musée Bolo", "CC BY-SA 2.0 fr"),
 "pixarhq": C("Sharon Hahn Darlin", "CC BY 2.0"), "pixarbldg": C("Grendelkhan", "CC BY-SA 3.0"),
 "imac": C("Steve Rainwater", "CC BY-SA 2.0"), "ipod1g": C("Paul Vera", "CC BY 2.0"),
 "iphonemw07": C("ArnoldReinhold", "CC BY-SA 4.0"), "iphonedock": C("Andrew (London)", "CC BY-SA 2.0"),
 "keynote07": C("ArnoldReinhold", "CC BY-SA 4.0"), "jobs07a": C("JD Lasica", "CC BY 2.0"),
 "jobsintel": C("tuchodi", "CC BY-SA 2.0"), "jobs08iphone": C("Tom Coates", "CC BY 2.0"),
 "applepark": C("Daniel L. Lu", "CC BY-SA 4.0"), "infloop": C("InvadingInvader", "CC BY-SA 4.0"),
 "tribute_pa": C("Ed and Eddie", "CC BY-SA 2.0"), "tribute_nyc": C("Doug Belshaw", "CC BY 2.0"),
 "tribute_london": C("Ivan Bandura", "CC BY 2.0"), "wwdc08": C("Erik Pitti", "CC BY 2.0"),
 "ipadevent": C("Matt Buchanan", "CC BY 2.0"),
}
def IMG(t0, key, layout="cover", g="warm", z=(1.02, 1.12), pan=((0, 0), (0, 0)), xf=0.35, tag=None, side="right", **kw):
    shot(t0, "img", xf=xf, key=key, layout=layout, g=g, z=z, pan=pan, tag=tag, side=side, credit=CR.get(key), **kw)
def VID(t0, n, off=0.0, slow=1.0, g="neutral", xf=0.35, tag=None, **kw):
    shot(t0, "vid", xf=xf, src=f"vid/{n}.mp4", off=off, slow=slow, g=g, tag=tag, **kw)
def CARDSHOT(ch, bgkey, bgg="warm"):
    c = TL["chapters"][ch - 1]
    shot(CARD(ch), "card", xf=0.6, n=ch, title=c["title"], years=c["years"], bgkey=bgkey, bgg=bgg)

# ---------------------------------------------------------------- INTRO (ch 0)
a = lambda p, occ=0, edge="s", d=0.0: A(p, 0, occ, edge, d)
VID(0.0, 47051, off=1.0, slow=1.25, g="teal", xf=0.0)
IMG(a("turning"), "mac1984", "side", z=(1.02, 1.10), xf=0.3, tag="1984  ·  THE MACINTOSH")
IMG(a("and then being"), "jobs1984b", "side", side="left", z=(1.10, 1.0), xf=0.3, bw_at=(a("and then being", d=0.4), a("it.", edge="e")))
IMG(a("that is exactly", d=-0.15), "headshot2010", g="neutral", z=(1.0, 1.12), pan=((0, 0), (0.15, -0.2)), xf=0.2,
    dark=(1.0, 0.45, a("steve jobs", d=-0.4), a("steve jobs", d=0.2)))
TITLE(a("steve jobs", d=-0.05), a("he helped create", d=-0.15), "STEVE JOBS", sub="CO-FOUNDER OF APPLE")
IMG(a("he helped create", d=-0.15), "garage", z=(1.05, 1.15), pan=((-0.6, 0), (0.6, 0)), tag="1976  ·  LOS ALTOS, CALIFORNIA")
IMG(a("he helped turn", d=-0.2), "apple1", z=(1.15, 1.02), pan=((0, -0.3), (0, 0.2)), tag="THE APPLE I")
VID(a("technology", d=-0.1), 30998, g="teal", xf=0.3)
VID(a("but after", d=-0.1), 36897, off=2.0, g="cool", xf=0.3)
IMG(a("the company he built", d=-0.1), "reagan1985", g="bw", z=(1.18, 1.05), pan=((0.3, -0.2), (0.25, -0.1)), tag="1985")
VID(a("most people", d=-0.35), 15777, off=1.0, slow=1.15, g="faded", xf=0.4)
ITALIC(a("as the end", d=-0.1), a("jobs treated", d=-0.1), "the end.")
VID(a("jobs treated", d=-0.1), 26532, off=2.0, g="warm", xf=0.5)
def _nb(layer, t, t0=a("a new beginning", d=-0.15), t1=a("and when", d=-0.3)):
    put(layer, text_img("A  NEW", "l", 52, WHITE, track=14), W / 2, 430, win(t, t0, t1, 0.4, 0.3), "mm")
    big_title(layer, t, t0 + 0.2, t1, "BEGINNING", "pf9", 150, 545, GOLD, 30, 8, wipe=True)
ev(a("a new beginning", d=-0.15), a("and when", d=-0.3), _nb); HIDE.append((a("a new beginning", d=-0.2), a("and when", d=-0.3)))
IMG(a("beginning.", edge="e", d=-0.05), "nextcube", g="cool", z=(1.0, 1.1), pan=((0.2, 0), (-0.1, 0)), xf=0.4, tag="1985  ·  NeXT")
IMG(a("and when", d=-0.15), "macworld2005", "side", z=(1.0, 1.08), xf=0.25, tag="1997  ·  THE RETURN")
shot(a("he changed", d=-0.15), "trip", bg="macworld2008", dark_at=a("listens", d=-0.4),
     items=[("ipod", "MUSIC", "iPod  ·  2001", a("listens")), ("iphone2007", "COMMUNICATION", "iPhone  ·  2007", a("communicates")),
            ("ipad2010", "TECHNOLOGY", "iPad  ·  2010", a("uses"))],
     credit="Photos: Tom Coates · Evan-Amos (PD) · Blake Patterson · Matt Buchanan — CC BY 2.0 · Wikimedia Commons")
IMPACT0 = a("this is the story", d=-0.3)
IMG(IMPACT0, "wwdc07", g="neutral", z=(1.12, 1.0), pan=((0, -0.5), (0, -0.4)), xf=0.0, dark=(0.5, 0.5, 0, 1), flash=True)
TITLE(a("the story of", d=0.0), a("the man who", d=-0.15), "STEVE JOBS", size=190, y=545, above="THE STORY OF")
HIDE.append((IMPACT0, a("the man who", d=-0.15)))
IMG(a("the man who", d=-0.15), "mac1984", g="bw", z=(1.3, 1.45), pan=((0, -0.62), (0, -0.66)), xf=0.25)
IMG(a("found success", d=-0.1), "pixar1998", z=(1.25, 1.12), pan=((0, 0.2), (0, 0.1)), tag="PIXAR  ·  WHITE HOUSE, 1998")
IMG(a("and came back", d=-0.15), "redshawl", "side", z=(1.0, 1.07))

# ---------------------------------------------------------------- channel ident (user's intro.mp4)
IDENT = TL["ident"]
shot(IDENT[0], "ext", xf=0.35, src="vid/intro.mp4")

# ---------------------------------------------------------------- CH1 The Curious Kid
a = lambda p, occ=0, edge="s", d=0.0: A(p, 1, occ, edge, d)
CARDSHOT(1, "goldengate")
IMG(a("steve jobs was born", d=-0.1), "goldengate", "side", side="right", z=(1.0, 1.08), xf=0.6, tag="SAN FRANCISCO  ·  1955")
YEAR(a("1955", d=-0.1), "1955")
VID(a("and was adopted", d=-0.1), 11038, off=6.0, slow=1.1, g="warm")
IMG(a("his father encouraged", d=-0.15), "garage", g="warm", z=(1.0, 1.12), pan=((0.5, 0), (-0.4, 0)), tag="THE JOBS FAMILY HOME  ·  LOS ALTOS")
VID(a("experiment with", d=-0.2), 47051, off=4.0, slow=1.3, g="warm")
IMG(a("he was curious", d=-0.15), "jobs1972", "side", side="left", g="sepia", z=(1.0, 1.08), tag="HOMESTEAD HIGH SCHOOL  ·  1972")
VID(a("he wanted things", d=-0.15), 9188, off=3.0, g="faded", dim=0.35)
WORDPOP([(a("simple,"), "Simple.", WHITE), (a("perfect."), "Perfect.", GOLD)], a("after high school", d=-0.2), y=520, size=130)
HIDE.append((a("he wanted things", d=0.1), a("after high school", d=-0.2)))
IMG(a("after high school", d=-0.15), "reed", g="warm", z=(1.0, 1.14), pan=((0, 0.2), (0, -0.2)), tag="REED COLLEGE  ·  PORTLAND, OREGON")
VID(a("he dropped out", d=-0.15), 4519, off=2.0, g="faded")
VID(a("including calligraphy", d=-0.2), 50695, off=0.0, g="warm")
VID(a("at the time", d=-0.15), 50704, off=1.0, g="warm")
IMG(a("years later", d=-0.15), "mac128", g="neutral", z=(1.0, 1.12), pan=((0, -0.1), (0, 0)), tag="1984  ·  MACINTOSH TYPOGRAPHY")
IMG(a("one of the most important", d=-0.15), "woz1968", "side", side="left", g="sepia", z=(1.0, 1.08), tag="STEVE WOZNIAK")
IMG(a("a brilliant engineer", d=-0.1), "wozniak", "side", side="right", g="warm", z=(1.0, 1.06))
IMG(a("jobs saw something", d=-0.15), "homebrew", g="sepia", z=(1.2, 1.35), pan=((0, -0.6), (0, -0.2)), tag="HOMEBREW COMPUTER CLUB  ·  1976")
VID(a("the possibility", d=-0.15), 42749, off=2.0, g="warm")

# ---------------------------------------------------------------- CH2 From Garage to Giant
a = lambda p, occ=0, edge="s", d=0.0: A(p, 2, occ, edge, d)
CARDSHOT(2, "apple1")
IMG(a("in 1976", d=-0.1), "garage", g="cool", z=(1.12, 1.0), pan=((0.3, 0.1), (0, 0)), xf=0.6, tag="1976  ·  THE GARAGE")
YEAR(a("1976"), "1976")
VID(a("make computers", d=-0.2), 1781, off=1.0, g="warm")
IMG(a("their first product", d=-0.15), "apple1", g="warm", z=(1.0, 1.12), tag="APPLE I  ·  1976")
VID(a("circuit board", d=-0.2), 47051, off=0.5, slow=1.2, g="teal")
IMG(a("it was not a polished", d=-0.15), "apple1", g="sepia", z=(1.35, 1.5), pan=((-0.4, 0.3), (0.2, 0.2)))
IMG(a("then came the apple", d=-0.15), "apple2", g="warm", z=(1.0, 1.12), tag="APPLE II  ·  1977")
IMG(a("it was easier", d=-0.15), "apple2b", "side", side="right", g="neutral", z=(1.0, 1.06))
VID(a("apple was no longer", d=-0.15), 23116, off=1.0, g="warm")
VID(a("it was becoming", d=-0.15), 46194, off=2.0, g="teal")
VID(a("in 1980", d=-0.15), 47012, off=2.0, g="neutral", tag="DECEMBER 1980  ·  APPLE GOES PUBLIC")
YEAR(a("1980"), "1980")
IMG(a("jobs was still young", d=-0.15), "jobs1984b", "side", side="right", g="warm", z=(1.0, 1.1))
VID(a("but success brought", d=-0.15), 25251, off=2.0, g="cool")
IMG(a("jobs wanted to create", d=-0.15), "lisa", g="warm", z=(1.0, 1.1), tag="APPLE LISA  ·  1983")
VID(a("he pushed his teams", d=-0.15), 9050, off=1.0, g="cool")
VID(a("that intensity", d=-0.15), 4192, off=1.0, g="teal")
VID(a("but it also created", d=-0.1), 36897, off=6.0, g="cool")

# ---------------------------------------------------------------- CH3 The Fall
a = lambda p, occ=0, edge="s", d=0.0: A(p, 3, occ, edge, d)
CARDSHOT(3, "mac1984")
IMG(a("jobs became deeply", d=-0.1), "mac128", g="neutral", z=(1.0, 1.08), xf=0.6, tag="THE MACINTOSH PROJECT")
IMG(a("graphical interface", d=-0.2), "macmouse", g="neutral", z=(1.05, 1.18), pan=((-0.3, 0), (0.3, 0)))
VID(a("the goal was", d=-0.15), 1781, off=5.0, g="warm")
IMG(a("the macintosh launched", d=-0.15), "mac1984", "side", side="right", g="warm", z=(1.0, 1.08), tag="JANUARY 1984")
YEAR(a("1984"), "1984")
VID(a("with an unforgettable", d=-0.1), 46291, off=1.0, g="cool", dim=0.85, tag="THE  “1984”  SUPER BOWL AD")
IMG(a("it was bold", d=-0.15), "mac128", g="warm", z=(1.25, 1.1), pan=((0, -0.3), (0, -0.2)))
VID(a("but the mac's", d=-0.15), 47018, off=2.0, g="cool")
IMG(a("jobs clashed", d=-0.15), "sculley", "side", side="right", g="neutral", z=(1.0, 1.06), tag="JOHN SCULLEY  ·  APPLE CEO 1983–1993")
IMG(a("in 1985", d=-0.15), "reagan1985", g="bw", z=(1.0, 1.12), pan=((0.3, -0.2), (0.3, -0.2)), tag="1985")
YEAR(a("1985"), "1985")
VID(a("think about that", d=-0.2), 28901, off=1.0, g="warm")
IMG(a("the person most", d=-0.15), "jobs1984b", "side", side="left", g="bw", z=(1.08, 1.0))
VID(a("he was only", d=-0.15), 28901, off=5.0, g="warm", dim=0.3)
COUNTER(a("only", d=0.0), a("the company he had", d=-0.15), 30, "YEARS OLD")
VID(a("the company he had", d=-0.15), 15777, off=4.0, slow=1.15, g="faded")

# ---------------------------------------------------------------- CH4 The Wilderness Years
a = lambda p, occ=0, edge="s", d=0.0: A(p, 4, occ, edge, d)
CARDSHOT(4, "nextcube", "cool")
VID(a("but jobs didn't", d=-0.1), 11038, off=16.0, g="warm", xf=0.6)
IMG(a("he started a new", d=-0.15), "nextcube2", g="cool", z=(1.0, 1.12), tag="1985  ·  NeXT, INC.")
IMG(a("its machines were", d=-0.15), "nextcube", g="cool", z=(1.12, 1.0), pan=((-0.3, 0), (0.2, 0)), tag="NeXTcube  ·  1990")
VID(a("still, next developed", d=-0.15), 4192, off=4.0, g="teal")
VID(a("at around the same", d=-0.15), 99786, off=0.0, g="teal")
IMG(a("he turned it into", d=-0.15), "pixarhq", g="warm", z=(1.0, 1.12), tag="1986  ·  PIXAR")
VID(a("pixar focused", d=-0.15), 4192, off=8.0, g="warm")
shot(a("in 1995", d=-0.15), "dark", bg="18142", xf=0.4)
YEAR(a("1995"), "1995", dur=1.6)
def _toy(layer, t, t0=a("toy story", d=-0.1), t1=a("the film became", d=-0.15), tf=a("the first", d=-0.1)):
    tw = big_title(layer, t, t0, t1, "TOY STORY", "pf9", 170, 500, GOLD)
    if tw: gold_rules(layer, t, t0, t1, 500, tw / 2)
    put(layer, text_img("THE FIRST FEATURE FILM MADE ENTIRELY WITH COMPUTER ANIMATION", "sb", 28, WHITE, track=6), W / 2, 620,
        win(t, tf, t1, 0.5, 0.35), "mm")
ev(a("toy story", d=-0.6), a("the film became", d=-0.15), _toy)
VID(a("the film became", d=-0.15), 17630, off=1.0, g="warm")
IMG(a("and helped establish", d=-0.1), "pixarbldg", g="warm", z=(1.0, 1.1), tag="PIXAR CAMPUS  ·  EMERYVILLE")
IMG(a("jobs had now", d=-0.15), "pixar1998", g="warm", z=(1.1, 1.25), pan=((0, 0.1), (0.1, 0.0)), tag="WHITE HOUSE  ·  1998")
shot(a("one company was", d=-0.15), "split", items=[("nextcube2", "NeXT", "TECHNOLOGY", a("one company was")),
     ("pixarhq", "PIXAR", "ANIMATION & ENTERTAINMENT", a("the other was"))],
     credit="Photos: Rama & Musée Bolo (CC BY-SA 2.0 fr) · Sharon Hahn Darlin (CC BY 2.0) · Wikimedia Commons")

# ---------------------------------------------------------------- CH5 The Comeback
a = lambda p, occ=0, edge="s", d=0.0: A(p, 5, occ, edge, d)
CARDSHOT(5, "macworld2005")
VID(a("by the mid", d=-0.1), 47018, off=8.0, g="cool", xf=0.6, tag="MID-1990s")
VID(a("its product line", d=-0.15), 9188, off=8.0, g="faded")
IMG(a("in 1996", d=-0.15), "infloop", g="warm", z=(1.0, 1.1), tag="1996  ·  APPLE BUYS NeXT")
YEAR(a("1996"), "1996", dur=2.0)
IMG(a("the deal brought", d=-0.15), "macworld2005", "side", side="right", g="warm", z=(1.0, 1.08), tag="THE RETURN")
IMG(a("in 1997", d=-0.15), "jobsintel", g="warm", z=(1.0, 1.12), pan=((-0.2, 0), (0.0, 0)), tag="1997  ·  INTERIM CEO")
YEAR(a("1997"), "1997", dur=2.2)
shot(a("jobs quickly simplified", d=-0.15), "simplify", t_simple=a("smaller number"))
IMG(a("the colorful imac", d=-0.15), "imac", g="warm", z=(1.0, 1.12), tag="1998  ·  iMac")
IMG(a("then came the ipod", d=-0.15), "ipod1g", g="neutral", z=(1.05, 1.18), tag="2001  ·  iPod")
VID(a("music library", d=-0.3), 4855, off=1.0, g="warm")
VID(a("itunes helped", d=-0.15), 51134, off=2.0, g="warm", tag="2003  ·  iTUNES STORE")
IMG(a("but jobs' biggest", d=-0.15), "keynote07", g="neutral", z=(1.0, 1.1), tag="MACWORLD  ·  JANUARY 2007")
YEAR(a("2007"), "2007", dur=2.0)
IMG(a("he walked onto", d=-0.15), "jobs07a", g="neutral", z=(1.0, 1.1), pan=((0.2, 0), (0.25, -0.1)))
shot(a("an ipod, a phone", d=-0.3), "img", xf=0.35, key="iphonemw07", layout="cover", g="cool", z=(1.0, 1.08), pan=((0, 0), (0, 0)),
     credit=CR["iphonemw07"], dark=(0.6, 0.6, 0, 1), tag=None, side="right")
WORDPOP([(a("an ipod,"), "An iPod.", WHITE), (a("a phone,"), "A phone.", WHITE), (a("internet communicator"), "An internet communicator.", GOLD)],
        a("it was the iphone", d=-0.1), size=86)
HIDE.append((a("an ipod, a phone", d=-0.1), a("it was the iphone", d=-0.1)))
IMG(a("it was the iphone", d=-0.2), "iphone2007", g="neutral", z=(1.0, 1.1), xf=0.0, flash=True, tag="JANUARY 9, 2007  ·  THE iPHONE")
IMG(a("the iphone changed", d=-0.2), "iphonedock", "side", side="right", g="neutral", z=(1.0, 1.08))
VID(a("a touchscreen", d=-0.15), 4915, off=1.0, g="warm")
VID(a("an ecosystem", d=-0.2), 41174, off=0.5, g="warm")
VID(a("it didn't just transform", d=-0.15), 4401, off=2.0, g="teal")
IMG(a("the company that had once", d=-0.15), "applepark", g="warm", z=(1.0, 1.15), tag="APPLE PARK  ·  CUPERTINO")

# ---------------------------------------------------------------- CH6 The Cost
a = lambda p, occ=0, edge="s", d=0.0: A(p, 6, occ, edge, d)
CARDSHOT(6, "headshot2010", "bw")
IMG(a("behind the success", d=-0.1), "jobs08iphone", "side", side="right", g="faded", z=(1.0, 1.08), xf=0.6)
VID(a("in 2003", d=-0.15), 46365, off=2.0, g="cool", tag="2003")
IMG(a("he continued working", d=-0.15), "ipad2010", g="faded", z=(1.0, 1.12), pan=((0.3, -0.2), (0.3, -0.3)), tag="2010  ·  iPAD LAUNCH")
IMG(a("in august 2011", d=-0.15), "obama2011", g="faded", z=(1.0, 1.1), tag="FEBRUARY 2011")
VID(a("on october", d=-0.15), 48919, off=3.0, g="warm", xf=0.6)
def _rip(layer, t, t0=a("steve jobs died", d=-0.1), t1=a("age of 56", edge="e", d=1.2)):
    tw = big_title(layer, t, t0, t1, "1955 — 2011", "pf7", 120, 500, WHITE, 30, 12)
    if tw: gold_rules(layer, t, t0, t1, 500, tw / 2)
    put(layer, text_img("STEVE JOBS", "sb", 34, GOLD, track=14), W / 2, 610, win(t, t0 + 0.5, t1, 0.5, 0.35), "mm")
ev(a("steve jobs died", d=-0.6), a("age of 56", edge="e", d=1.2), _rip)
IMG(a("age of 56", edge="e", d=0.3), "tribute_pa", g="faded", z=(1.0, 1.08), xf=0.6, tag="APPLE STORE  ·  PALO ALTO  ·  OCTOBER 2011")
IMG(a("former colleagues", d=-0.15), "headshot2010", g="bw", z=(1.1, 1.2), pan=((0, -0.3), (0.1, -0.35)))
VID(a("his achievements", d=-0.15), 36897, off=8.0, g="cool")
IMG(a("but so were", d=-0.1), "tribute_nyc", g="faded", z=(1.0, 1.1), tag="APPLE STORE  ·  NEW YORK")
shot(a("understanding jobs", d=-0.15), "split", items=[("redshawl", "THE VISIONARY", "", a("the visionary")),
     ("jobs1984b", "THE COMPLICATED PERSON", "", a("the complicated person"))], bw_right=True,
     credit="Photos: Steve Jurvetson (CC BY 2.0) · Bernard Gotfryd / Library of Congress (PD)")

# ---------------------------------------------------------------- CH7 The Lesson + CTA
a = lambda p, occ=0, edge="s", d=0.0: A(p, 7, occ, edge, d)
CARDSHOT(7, "applepark")
shot(a("steve jobs didn't invent", d=-0.1), "trip", bg="keynote07", dark_at=a("steve jobs didn't invent"), xf=0.6,
     items=[("apple2", "PERSONAL COMPUTER", "", a("personal computer")), ("ipod1g", "MUSIC PLAYER", "", a("music player")),
            ("iphonedock", "SMARTPHONE", "", a("smartphone"))],
     credit="Photos: The wub (CC BY-SA 4.0) · Paul Vera (CC BY 2.0) · Andrew (CC BY-SA 2.0) · Wikimedia Commons")
VID(a("but he helped rethink", d=-0.15), 4915, off=6.0, g="warm")
VID(a("fit into", d=-0.3), 15997, off=2.0, g="warm")
shot(a("his journey had", d=-0.15), "timeline", bg="macworld2005",
     items=[("HIGHS", "1976 – 1984", a("extraordinary highs")), ("A PUBLIC FALL", "1985", a("a public fall")),
            ("REBUILDING", "1985 – 1996", a("years of rebuilding")), ("THE COMEBACK", "1997 – 2011", a("most famous comebacks"))])
IMG(a("and perhaps", d=-0.15), "redshawl", "side", side="right", g="warm", z=(1.0, 1.08))
shot(a("being pushed out", d=-0.2), "vid", xf=0.5, src="vid/14428.mp4", off=2.0, slow=1.0, g="cool", dim=0.6, tag=None)
def _quote(layer, t, t0=a("being pushed out", d=-0.1), t1=a("sometimes it gives", d=-0.2), tm=a("doesn't mean", d=-0.1)):
    v1 = win(t, t0, t1, 0.5, 0.4); v2 = win(t, tm, t1, 0.5, 0.4)
    put(layer, text_img("“Being pushed out of one chapter", "pfi", 76, WHITE), W / 2, 450, v1, "mm")
    put(layer, text_img("doesn’t mean your story is over.”", "pfi", 76, GOLD), W / 2, 560, v2, "mm")
ev(a("being pushed out", d=-0.2), a("sometimes it gives", d=-0.2), _quote)
HIDE.append((a("being pushed out", d=-0.2), a("sometimes it gives", d=-0.2)))
VID(a("sometimes it gives", d=-0.15), 26532, off=6.0, g="warm", xf=0.5)
IMPACT7 = SEGS[7]["impact"]
VID(a("greater.", edge="e", d=0.4), 14154, off=0.0, g="warm", xf=0.6, dim=0.6)
def _yt(layer, t, t0=a("greater.", edge="e", d=0.9), t1=IMPACT7):
    txt = "NOW, YOUR TURN..."; n_ = int(clamp((t - t0 - 0.1) / 1.0) * len(txt)) + 1
    s_ = 1.0 + 0.25 * eio((t - (t1 - 0.45)) / 0.45)
    if t0 <= t <= t1:
        put(layer, text_img(txt[:n_], "l", 64, WHITE, track=16), W / 2 - text_w(txt, "l", 64, 16) * s_ / 2, 540, win(t, t0, t1, 0.2, 0.12), "lm", scale=s_)
ev(a("greater.", edge="e", d=0.9), IMPACT7, _yt)
shot(IMPACT7, "poll", xf=0.0, flash=True,
     items=[("mac128", "MACINTOSH", "1984", a("the macintosh")), ("ipod", "iPOD", "2001", a("the ipod")),
            ("iphonedock", "iPHONE", "2007", a("the iphone"))],
     t_comment=a("let us know"), credit="Photos: Grm wnr (CC BY-SA 3.0) · Evan-Amos (PD) · Andrew (CC BY-SA 2.0) · Wikimedia Commons")
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

def render_poll(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, "keynote07", "warm", 0.25, 0.3), 0, 255).astype(np.uint8)).convert("RGBA")
    put(base, text_img("WHAT WAS HIS GREATEST CREATION?", "b", 50, WHITE, track=6), W / 2, 200, eo(lt / 0.5), "mm")
    for i, (key, lab, yr, ts) in enumerate(s_["items"]):
        k = eo((t - ts + 0.15) / 0.45)
        if k <= 0: continue
        cx = W / 2 + (i - 1) * 560; cy = 480 + 60 * (1 - k)
        paste_panel(base, key, cx, cy, 460, 320, k, t - ts)
        put(base, text_img(lab, "pf9", 52, GOLD), cx, cy + 205, k, "mt")
        put(base, text_img(yr, "m", 26, (225, 225, 225)), cx, cy + 270, k * 0.85, "mt")
    tc = s_["t_comment"]
    if t >= tc - 0.1:
        kb = eback((t - tc) / 0.45); d = ImageDraw.Draw(base); cx, cy = W / 2, 860
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
    base = Image.fromarray(np.clip(particles_bg(s_, lt, "headshot2010", "warm", 0.26), 0, 255).astype(np.uint8)).convert("RGBA")
    brand(base, t, s_["t0"] + 0.2, 330)
    put(base, text_img("stories of ambition, failure and incredible comebacks", "m", 36, (235, 235, 235)), W / 2, 450,
        win(t, s_["t0"] + 0.9, 1e9, 0.5, 0.01), "mm")
    button(base, t, W / 2, 600, s_["t0"] + 1.0, s_["t_click"])
    return np.array(base.convert("RGB")).astype(np.float32)

def render_end(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, "applepark", "warm", 0.22), 0, 255).astype(np.uint8)).convert("RGBA")
    brand(base, t, s_["t0"] + 0.1, 170)
    d = ImageDraw.Draw(base)
    # placeholder frames where YouTube end-screen elements go (video + playlist + subscribe)
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
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-threads", "2", f"out/part_{i:02d}.mp4"], stdin=subprocess.PIPE)
    for fi in range(n0, n1):
        enc.stdin.write(frame_at(fi / FPS, fi).tobytes())
        if fi % 300 == 0: print(f"part {i}: {fi/FPS:6.1f}s / {n1/FPS:.1f}", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main()
