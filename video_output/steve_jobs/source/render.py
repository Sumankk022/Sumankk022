"""Steve Jobs story — 1080p renderer (PIL + numpy -> ffmpeg).
python3 render.py [--preview t0 t1] [--still t ...]
"""
import json, subprocess, sys, os, math, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1920, 1080, 30
TL = json.load(open("out/timeline.json"))
WORDS = TL["words"]
for w in WORDS:                      # whisper glued "And" onto the tail of "beginning."
    if w["w"] == "And": w["s"], w["e"] = 34.30, 34.40
TOTAL = TL["total"]; IMPACT = TL["impact"]; LAST = TL["last_word"]
END_T0 = LAST + 0.45

GOLD = (242, 193, 91); RED = (235, 72, 60); WHITE = (255, 255, 255)
FD = "/usr/share/fonts/opentype/inter/"
PF = "fonts/pkg/package/files/playfair-display-latin-"
@functools.lru_cache(None)
def font(name, size):
    path = {"xb": FD + "InterDisplay-ExtraBold.otf", "b": FD + "InterDisplay-Bold.otf",
            "sb": FD + "InterDisplay-SemiBold.otf", "l": FD + "InterDisplay-Light.otf",
            "r": FD + "InterDisplay-Regular.otf", "m": FD + "InterDisplay-Medium.otf",
            "pf9": PF + "900-normal.woff", "pf7": PF + "700-normal.woff",
            "pfi": PF + "700-italic.woff", "pfi4": PF + "400-italic.woff"}[name]
    return ImageFont.truetype(path, size)

# ---------------- easing ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3                      # ease-out cubic
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eback(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def win(t, t0, t1, fi=0.25, fo=0.25):
    """0..1 visibility with fade in/out"""
    if t < t0 or t > t1: return 0.0
    return min(eo((t - t0) / fi) if fi else 1, eo((t1 - t) / fo) if fo else 1)

# ---------------- grading ----------------
def curve_lut(contrast=1.0, lift=0, gamma=1.0):
    x = np.arange(256) / 255.0
    x = x ** gamma
    s = 0.5 + (x - 0.5) * contrast                    # linear contrast
    s = s * 0.75 + 0.25 * (3 * x ** 2 - 2 * x ** 3) * (contrast > 1)  # gentle S
    return np.clip(s * 255 + lift, 0, 255)
GRADES = {
    "warm":    dict(c=1.10, sat=1.05, rgb=(1.05, 1.0, 0.92), lift=2),
    "neutral": dict(c=1.06, sat=1.0, rgb=(1.0, 1.0, 1.0), lift=0),
    "cool":    dict(c=1.08, sat=0.75, rgb=(0.94, 1.0, 1.07), lift=4),
    "teal":    dict(c=1.12, sat=0.95, rgb=(0.95, 1.02, 1.06), lift=0),
    "bw":      dict(c=1.18, sat=0.0, rgb=(1.0, 1.0, 1.0), lift=0),
    "faded":   dict(c=1.0, sat=0.55, rgb=(1.02, 1.0, 0.96), lift=10),
}
def grade(arr, g):
    p = GRADES[g]; a = arr.astype(np.float32)
    lut = curve_lut(p["c"], p["lift"])
    a = lut[np.clip(a, 0, 255).astype(np.uint8)]
    if p["sat"] != 1.0:
        lum = (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114)[..., None]
        a = lum + (a - lum) * p["sat"]
    a = a * np.array(p["rgb"], np.float32)
    return np.clip(a, 0, 255).astype(np.uint8)

# vignette + bottom gradient for caption legibility
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIG = 1 - 0.42 * np.clip((r - 0.55) / 0.9, 0, 1) ** 1.6
VIG *= 1 - 0.45 * np.clip((yy - H * 0.62) / (H * 0.38), 0, 1) ** 1.5
VIG = VIG[..., None].astype(np.float32)
rng = np.random.default_rng(7)
GRAIN = [rng.normal(0, 5.0, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]

# ---------------- sources ----------------
@functools.lru_cache(None)
def load_img(key):
    return Image.open(f"img/{key}.jpg").convert("RGB")

@functools.lru_cache(None)
def graded(key, g):
    return Image.fromarray(grade(np.array(load_img(key)), g))

def kb_crop(img, z, px, py, out=(W, H)):
    """Ken Burns: crop window at zoom z, pan px/py in [-1,1]."""
    Wi, Hi = img.size; ow, oh = out
    c = min(Wi / ow, Hi / oh)
    ww, wh = ow * c / z, oh * c / z
    cx = Wi / 2 + px * (Wi - ww) / 2; cy = Hi / 2 + py * (Hi - wh) / 2
    box = (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2)
    return img.transform(out, Image.EXTENT, box, Image.BILINEAR)

@functools.lru_cache(None)
def blurred_bg(key, g, dark=0.45):
    im = graded(key, g)
    c = max(W / im.width, H / im.height) * 1.15
    im = im.resize((int(im.width * c / 4), int(im.height * c / 4)), Image.BILINEAR)
    im = im.filter(ImageFilter.GaussianBlur(14)).resize((int(im.width * 4), int(im.height * 4)), Image.BILINEAR)
    a = (np.array(im).astype(np.float32) * dark).astype(np.uint8)
    return Image.fromarray(a)

@functools.lru_cache(None)
def feather_mask(w, h, edge=140):
    m = np.ones((h, w), np.float32)
    ramp = np.linspace(0, 1, edge) ** 1.4
    m[:, :edge] *= ramp; m[:, -edge:] *= ramp[::-1]
    m[:60, :] *= np.linspace(0, 1, 60)[:, None]; m[-60:, :] *= np.linspace(1, 0, 60)[:, None]
    return Image.fromarray((m * 255).astype(np.uint8))

class Vid:
    def __init__(self, src, offset=0.0, slow=1.0, g="neutral"):
        self.src, self.offset, self.slow, self.g = src, offset, slow, g
        self.p = None; self.idx = -1; self.last = None
    def frame(self, k):
        if self.p is None:
            vf = (f"setpts={self.slow}*PTS,fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                  f"crop={W}:{H}")
            self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(self.offset), "-i", self.src, "-vf", vf,
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        while self.idx < k:
            b = self.p.stdout.read(W * H * 3)
            if len(b) < W * H * 3: break
            self.last = grade(np.frombuffer(b, np.uint8).reshape(H, W, 3), self.g); self.idx += 1
        return self.last

# ---------------- text helpers ----------------
@functools.lru_cache(None)
def text_img(txt, fname, size, color=WHITE, track=0, shadow=True):
    f = font(fname, size)
    if track:
        widths = [f.getlength(ch) for ch in txt]; tw = int(sum(widths) + track * (len(txt) - 1))
    else:
        tw = int(f.getlength(txt))
    asc, desc = f.getmetrics(); th = asc + desc
    pad = 30
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def draw(dd, fill):
        if track:
            x = pad
            for ch, wch in zip(txt, widths): dd.text((x, pad), ch, font=f, fill=fill); x += wch + track
        else:
            dd.text((pad, pad), txt, font=f, fill=fill)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (0, 0, 0, 170))
        sh = sh.filter(ImageFilter.GaussianBlur(max(4, size // 9)))
        im = Image.alpha_composite(im, sh)
        d = ImageDraw.Draw(im)
    draw(d, color + (255,))
    return np.array(im)

def put(layer, arr, x, y, alpha=1.0, anchor="lt", scale=1.0):
    """composite RGBA numpy image onto PIL RGBA layer. x,y refer to the text box w/o padding."""
    if alpha <= 0.003: return
    im = arr
    if scale != 1.0:
        pil = Image.fromarray(arr); pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))), Image.BILINEAR)
        im = np.array(pil)
    h, w = im.shape[:2]; pad = int(30 * scale)
    bw, bh = w - 2 * pad, h - 2 * pad
    if anchor[0] == "m": x -= bw / 2
    elif anchor[0] == "r": x -= bw
    if anchor[1] == "m": y -= bh / 2
    elif anchor[1] == "b": y -= bh
    x, y = int(round(x - pad)), int(round(y - pad))
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    crop = im[y0 - y:y1 - y, x0 - x:x1 - x].copy()
    if alpha < 1: crop[..., 3] = (crop[..., 3] * alpha).astype(np.uint8)
    layer.alpha_composite(Image.fromarray(crop), (x0, y0))

def text_w(txt, fname, size, track=0):
    f = font(fname, size)
    return sum(f.getlength(c) for c in txt) + track * (len(txt) - 1) if track else f.getlength(txt)

# ---------------- captions ----------------
GROUPS = [
    "Imagine building a company from *nothing,*",
    "turning it into one of the most *exciting*",
    "businesses in the world,",
    "and then being ^pushed^ ^out^ of it.",
    "That is exactly what happened to",
    "# Steve Jobs.",
    "He helped create *Apple*",
    "in a small *garage.*",
    "He helped turn it into a *technology* *giant.*",
    "But after a ^power^ ^struggle,^",
    "the company he built",
    "no longer ^wanted^ ^him^ in charge.",
    "Most people would have treated that",
    "# as the end.",
    "Jobs treated it as",
    "# a new beginning.",
    "And when he *returned,*",
    "he didn't just *save* *Apple.*",
    "He *changed* the way the world",
    "listens to *music,* *communicates*",
    "and uses *technology.*",
    "# This is the story of Steve Jobs.",
    "The man who ^lost^ ^Apple,^",
    "found *success* elsewhere",
    "and came back to build a *legacy.*",
]
CAPS = []
wi = 0
for g in GROUPS:
    hidden = g.startswith("#"); toks = g.lstrip("# ").split()
    items = []
    for tk in toks:
        col = GOLD if tk.startswith("*") else RED if tk.startswith("^") else WHITE
        txt = tk.strip("*^"); w = WORDS[wi]
        assert w["w"].lower().strip(",.") == txt.lower().strip(",."), (w["w"], txt)
        items.append((txt, col, w["s"], w["e"])); wi += 1
    CAPS.append(dict(hidden=hidden, items=items, t0=items[0][2] - 0.08, t1=items[-1][3]))
assert wi == len(WORDS)
for i, c in enumerate(CAPS):
    nxt = CAPS[i + 1]["t0"] if i + 1 < len(CAPS) else 1e9
    c["t1"] = min(c["t1"] + 0.7, nxt - 0.02)
CAP_SIZE = 64; CAP_Y = 930
def caption_layout(c):
    if "lay" in c: return c["lay"]
    sp = font("xb", CAP_SIZE).getlength(" ")
    ws = [text_w(t, "xb", CAP_SIZE) for t, *_ in c["items"]]
    total = sum(ws) + sp * (len(ws) - 1)
    x = W / 2 - total / 2; lay = []
    for (t, col, s, e), w_ in zip(c["items"], ws):
        lay.append((x, t, col, s)); x += w_ + sp
    c["lay"] = lay; return lay
def draw_captions(layer, t):
    for c in CAPS:
        if c["hidden"] or not (c["t0"] <= t <= c["t1"]): continue
        out = clamp((c["t1"] - t) / 0.15)
        gin = eo((t - c["t0"]) / 0.22)
        for x, txt, col, s in caption_layout(c):
            k = eo((t - (s - 0.05)) / 0.12)          # word lights up as it is spoken
            a = (0.38 + 0.62 * k) * gin * out
            colr = tuple(int(255 + (cc - 255) * k) for cc in col)   # highlight colour fades in on the word
            put(layer, text_img(txt, "xb", CAP_SIZE, colr if k >= 1 else (WHITE if col == WHITE else colr)),
                x, CAP_Y + 14 * (1 - gin) - 5 * math.sin(math.pi * clamp((t - s + 0.05) / 0.2)), a, "lb")

# ---------------- graphics ----------------
def chapter_tag(layer, t, t0, t1, text):
    v = win(t, t0, t1, 0.4, 0.3)
    if v <= 0: return
    d = ImageDraw.Draw(layer)
    k = eo((t - t0) / 0.45)
    d.rectangle([90, 86, 90 + 5, 86 + int(40 * k)], fill=GOLD + (int(255 * v),))
    put(layer, text_img(text, "sb", 30, WHITE, track=5), 116 - 30 * (1 - k), 87, v * k)

def credit(layer, t, t0, t1, text):
    v = win(t, t0, t1, 0.4, 0.3) * 0.72
    put(layer, text_img(text, "r", 19, WHITE, shadow=True), W - 36, H - 26, v, "rb")

def big_title(layer, t, t0, t1, text, fname, size, y, color=WHITE, track0=46, track1=10, wipe=False):
    v = win(t, t0, t1, 0.5, 0.35)
    if v <= 0: return
    k = eo((t - t0) / 1.1)
    tr = track0 + (track1 - track0) * k
    f = font(fname, size); ws = [f.getlength(ch) for ch in text]
    total = sum(ws) + tr * (len(text) - 1); x = W / 2 - total / 2
    for i, (ch, wch) in enumerate(zip(text, ws)):
        if ch != " ":
            ck = eo((t - t0 - i * 0.035) / 0.45)
            if wipe: ck = clamp((t - t0) * 2.2 - i / len(text) * 1.0)
            put(layer, text_img(ch, fname, size, color), x, y + 20 * (1 - ck), v * ck, "lm")
        x += wch + tr
    return total

def gold_rules(layer, t, t0, t1, y, half):
    v = win(t, t0, t1, 0.6, 0.35)
    if v <= 0: return
    k = eio((t - t0 - 0.2) / 0.8); d = ImageDraw.Draw(layer)
    L = 180 * k
    d.rectangle([W / 2 - half - 40 - L, y - 1, W / 2 - half - 40, y + 1], fill=GOLD + (int(230 * v),))
    d.rectangle([W / 2 + half + 40, y - 1, W / 2 + half + 40 + L, y + 1], fill=GOLD + (int(230 * v),))

# ---------------- shots ----------------
def nt(t): return t
S = []   # each: dict(t0, kind, xf, ...)
def shot(t0, kind, xf=0.35, **kw): S.append(dict(t0=t0, kind=kind, xf=xf, **kw))

shot(0.00, "vid", xf=0.0, src="vid/47051.mp4", off=1.0, slow=1.25, g="teal")
shot(1.80, "img", key="jobs1972", layout="side", side="right", g="neutral", z=(1.0, 1.08), xf=0.25,
     credit="Photo: Homestead High School yearbook, 1972 · Public domain")
shot(3.00, "img", key="mac1984", layout="side", side="right", g="warm", z=(1.02, 1.10), xf=0.3,
     credit="Photo: Bernard Gotfryd, 1984 · Library of Congress · Public domain", tag="1984  ·  THE MACINTOSH")
shot(7.15, "img", key="jobs1984b", layout="side", side="left", g="warm", z=(1.10, 1.0), bw_at=(7.6, 9.4), xf=0.3,
     credit="Photo: Bernard Gotfryd, 1984 · Library of Congress · Public domain")
shot(10.75, "img", key="headshot2010", layout="cover", g="neutral", z=(1.0, 1.12), pan=((0, 0), (0.15, -0.2)),
     dark=(1.0, 0.45, 12.7, 13.3), xf=0.2, credit="Photo: Matthew Yohe · CC BY-SA 3.0 · Wikimedia Commons")
shot(14.75, "img", key="garage", layout="cover", g="warm", z=(1.05, 1.15), pan=((-0.6, 0), (0.6, 0)),
     credit="Photo: Mathieu Thouvenin · CC BY-SA 2.0 · Wikimedia Commons", tag="1976  ·  LOS ALTOS, CALIFORNIA")
shot(17.85, "img", key="apple1", layout="cover", g="warm", z=(1.15, 1.02), pan=((0, -0.3), (0, 0.2)),
     credit="Photo: Ed Uthman · CC BY-SA 2.0 · Wikimedia Commons", tag="THE APPLE I")
shot(19.30, "vid", src="vid/30998.mp4", off=0.0, slow=1.0, g="teal", xf=0.3)
shot(21.05, "vid", src="vid/36897.mp4", off=2.0, slow=1.0, g="cool", xf=0.3)
shot(22.80, "img", key="reagan1985", layout="cover", g="bw", z=(1.18, 1.05), pan=((0.3, -0.2), (0.25, -0.1)),
     credit="Photo: White House Photographic Office, 1985 · Public domain", tag="1985")
shot(26.95, "vid", src="vid/15777.mp4", off=1.0, slow=1.15, g="faded", xf=0.4)
shot(30.95, "vid", src="vid/26532.mp4", off=2.0, slow=1.0, g="warm", xf=0.5)
shot(33.75, "img", key="nextcube", layout="cover", g="cool", z=(1.0, 1.1), pan=((0.2, 0), (-0.1, 0)), xf=0.4,
     credit="Photo: Michael Hicks · CC BY 2.0 · Wikimedia Commons", tag="1985  ·  NeXT")
shot(34.20, "img", key="macworld2005", layout="side", side="right", g="warm", z=(1.0, 1.08), xf=0.25,
     credit="Photo: mylerdude · CC BY 2.0 · Wikimedia Commons", tag="1997  ·  THE RETURN")
shot(37.60, "trip", xf=0.35)
shot(42.75, "vid", src="vid/14154.mp4", off=0.0, slow=1.0, g="warm", xf=0.6, dim=0.55)
shot(IMPACT, "img", key="wwdc07", layout="cover", g="neutral", z=(1.12, 1.0), pan=((0, -0.5), (0, -0.4)), xf=0.0,
     dark=(0.5, 0.5, 0, 1), credit="Photo: Acaben · CC BY-SA 2.0 · Wikimedia Commons")
shot(49.05, "img", key="mac1984", layout="cover", g="bw", z=(1.3, 1.45), pan=((0, -0.62), (0, -0.66)), xf=0.25,
     credit="Photo: Bernard Gotfryd, 1984 · Library of Congress · Public domain")
shot(50.85, "img", key="pixar1998", layout="cover", g="warm", z=(1.25, 1.12), pan=((0, 0.2), (0, 0.1)), xf=0.3,
     credit="Photo: Sharon Farmer, White House, 1998 · Public domain", tag="PIXAR  ·  WHITE HOUSE, 1998")
shot(52.75, "img", key="redshawl", layout="side", side="right", g="warm", z=(1.0, 1.07), xf=0.3,
     credit="Photo: Steve Jurvetson · CC BY 2.0 · Wikimedia Commons")
shot(END_T0, "end", xf=0.5)
for i, s_ in enumerate(S):
    s_["t1"] = S[i + 1]["t0"] if i + 1 < len(S) else TOTAL

VIDS = {}
def render_shot(s_, t):
    lt = t - s_["t0"]; dur = s_["t1"] - s_["t0"]; p = clamp(lt / max(dur, 0.01))
    k = s_["kind"]
    if k == "vid":
        key = id(s_)
        if key not in VIDS: VIDS[key] = Vid(s_["src"], s_["off"], s_["slow"], s_["g"])
        fr = VIDS[key].frame(int(lt * FPS)).astype(np.float32)
        if "dim" in s_: fr *= s_["dim"]
        return fr
    if k == "img":
        z0, z1 = s_.get("z", (1.0, 1.1)); z = z0 + (z1 - z0) * eio(p) if False else z0 + (z1 - z0) * p
        (px0, py0), (px1, py1) = s_.get("pan", ((0, 0), (0, 0)))
        px, py = px0 + (px1 - px0) * p, py0 + (py1 - py0) * p
        g = s_["g"]
        if s_.get("layout") == "side":
            bg = kb_crop(blurred_bg(s_["key"], g), 1.0 + 0.05 * p, 0, 0)
            fg_src = graded(s_["key"], g)
            fh = int(H * 1.0 * z); fw = int(fg_src.width * fh / fg_src.height)
            fg = fg_src.resize((fw, fh), Image.BILINEAR)
            cx = W * (0.68 if s_["side"] == "right" else 0.32)
            x = int(cx - fw / 2); y = int(H / 2 - fh / 2 - (fh - H) * 0.15)
            bg.paste(fg, (x, y), feather_mask(fw, fh))
            fr = np.array(bg).astype(np.float32)
            if "bw_at" in s_:
                a0, a1 = s_["bw_at"]; m = eio((t - a0) / (a1 - a0))
                bw = np.array(Image.fromarray(fr.astype(np.uint8)).convert("L").convert("RGB")).astype(np.float32)
                bw = 128 + (bw - 128) * 1.15
                fr = fr * (1 - m) + bw * m
        else:
            fr = np.array(kb_crop(graded(s_["key"], g), z, px, py)).astype(np.float32)
        if "dark" in s_:
            d0, d1, ta, tb = s_["dark"]; m = eio((t - ta) / max(tb - ta, 0.01))
            fr *= d0 + (d1 - d0) * m
        return fr
    if k == "trip": return render_trip(t, lt)
    if k == "end": return render_end(t, lt)

TRIP = [("ipod", "MUSIC", "iPod  ·  2001", 39.10), ("iphone2007", "COMMUNICATION", "iPhone  ·  2007", 40.60),
        ("ipad2010", "TECHNOLOGY", "iPad  ·  2010", 41.80)]
TRIP_LAYER = {}
def render_trip(t, lt):
    bg = np.array(kb_crop(graded("macworld2008", "warm"), 1.05 + 0.08 * lt / 5, 0, 0)).astype(np.float32)
    dk = 1.0 - 0.62 * eio((t - 38.7) / 0.6)
    bg *= dk
    base = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")
    pw, ph = 500, 340
    for i, (key, lab, sub, ts) in enumerate(TRIP):
        k = eo((t - ts + 0.15) / 0.45)
        if k <= 0: continue
        cx = W / 2 + (i - 1) * 580; cy = 470 + 70 * (1 - k)
        im = kb_crop(graded(key, "neutral"), 1.05 + 0.06 * clamp((t - ts) / 3), 0, 0, (pw, ph)).convert("RGBA")
        frame = Image.new("RGBA", (pw + 6, ph + 6), (255, 255, 255, 235)); frame.paste(im, (3, 3))
        a = np.array(frame); a[..., 3] = (a[..., 3] * k).astype(np.uint8)
        sh = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([40, 50, pw + 40, ph + 50], fill=(0, 0, 0, int(160 * k)))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        base.alpha_composite(sh, (int(cx - pw / 2 - 40), int(cy - ph / 2 - 40)))
        base.alpha_composite(Image.fromarray(a), (int(cx - pw / 2 - 3), int(cy - ph / 2 - 3)))
        lk = eo((t - ts - 0.1) / 0.4)
        put(base, text_img(lab, "b", 38, GOLD, track=6), cx, cy + ph / 2 + 40 + 10 * (1 - lk), lk, "mt")
        put(base, text_img(sub, "m", 26, (220, 220, 220)), cx, cy + ph / 2 + 96, lk * 0.85, "mt")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_end(t, lt):
    bg = np.array(kb_crop(blurred_bg("headshot2010", "warm", 0.28), 1.0 + 0.04 * lt / 6, 0, 0)).astype(np.float32)
    key = "endp"
    if key not in VIDS: VIDS[key] = Vid("vid/18142.mp4", 0.0, 1.0, "warm")
    pr = VIDS[key].frame(int(lt * FPS)).astype(np.float32)
    bg = 255 - (255 - bg) * (255 - pr * 0.30) / 255     # screen blend particles
    return bg

def draw_end_overlay(layer, t):
    lt = t - END_T0
    if lt < 0: return
    a1 = win(t, END_T0 + 0.25, TOTAL, 0.6, 0.01)
    put(layer, text_img("Steve Jobs", "pf7", 92, WHITE), W / 2, 300, a1, "mm")
    put(layer, text_img("1955  —  2011", "l", 30, (230, 230, 230), track=8), W / 2, 380, a1 * 0.9, "mm")
    d = ImageDraw.Draw(layer)
    # subscribe button
    tb = END_T0 + 1.1; tc = END_T0 + 2.4
    kb = eback((t - tb) / 0.45) if t >= tb else 0
    if kb > 0:
        clicked = t >= tc + 0.08
        press = 1 - 0.06 * math.sin(math.pi * clamp((t - tc) / 0.16))
        sc = kb * press
        bw_, bh_ = 470 * sc, 112 * sc; cx, cy = W / 2, 560
        col = (62, 62, 66) if clicked else (229, 33, 23)
        btn = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
        bd.rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2 + 10, cx + bw_ / 2, cy + bh_ / 2 + 10], radius=bh_ / 2,
                             fill=(0, 0, 0, 110))
        btn = btn.filter(ImageFilter.GaussianBlur(10)); bd = ImageDraw.Draw(btn)
        bd.rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2, cx + bw_ / 2, cy + bh_ / 2], radius=bh_ / 2, fill=col + (255,))
        layer.alpha_composite(btn)
        lab = "SUBSCRIBED" if clicked else "SUBSCRIBE"
        put(layer, text_img(lab, "b", 46, WHITE, track=4, shadow=False), cx, cy + 2, clamp(kb), "mm", scale=max(0.01, sc))
        if clicked:   # ripple
            rk = clamp((t - tc) / 0.6)
            rr = 14 + 80 * eo(rk)
            d.ellipse([cx + 60 - rr, cy + 10 - rr, cx + 60 + rr, cy + 10 + rr], outline=(255, 255, 255, int(170 * (1 - rk))), width=3)
            # bell
            bk = eback((t - tc - 0.25) / 0.4)
            if bk > 0:
                bx, by, s = cx + 300, cy, 1.0 * bk
                ang = math.sin((t - tc) * 22) * 18 * math.exp(-(t - tc - 0.25) * 3)
                bell = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); bdd = ImageDraw.Draw(bell)
                bdd.ellipse([20, 20, 120, 120], fill=(255, 255, 255, 40), outline=(255, 255, 255, 200), width=3)
                bdd.pieslice([45, 38, 95, 98], 180, 360, fill=WHITE + (255,))
                bdd.rectangle([45, 66, 95, 86], fill=WHITE + (255,))
                bdd.polygon([(38, 92), (102, 92), (95, 82), (45, 82)], fill=WHITE + (255,))
                bdd.ellipse([62, 92, 78, 106], fill=WHITE + (255,))
                bdd.ellipse([66, 30, 74, 40], fill=WHITE + (255,))
                bell = bell.rotate(ang, resample=Image.BICUBIC, center=(70, 30))
                bell = bell.resize((max(1, int(140 * s)), max(1, int(140 * s))), Image.BILINEAR)
                layer.alpha_composite(bell, (int(bx - bell.width / 2), int(by - bell.height / 2)))
        # cursor
        if t >= tc - 0.9:
            ck = eio((t - (tc - 0.9)) / 0.8)
            x = cx + 60 + (420 * (1 - ck)); y = cy + 10 + 260 * (1 - ck)
            ca = win(t, tc - 0.9, tc + 1.1, 0.2, 0.35)
            cur = [(0, 0), (0, 44), (11, 33), (19, 52), (27, 48), (19, 30), (34, 30)]
            pts = [(x + px_, y + py_) for px_, py_ in cur]
            d.polygon([(px_ + 3, py_ + 4) for px_, py_ in pts], fill=(0, 0, 0, int(110 * ca)))
            d.polygon(pts, fill=(255, 255, 255, int(255 * ca)), outline=(20, 20, 20, int(255 * ca)))
    a3 = win(t, END_T0 + 2.9, TOTAL, 0.5, 0.01)
    put(layer, text_img("for more stories of the people who changed the world", "m", 34, (235, 235, 235)), W / 2, 690, a3, "mm")
    put(layer, text_img("LIKE   ·   SHARE   ·   COMMENT", "sb", 28, GOLD, track=4), W / 2, 760, a3 * 0.95, "mm")

def overlays(layer, t):
    for s_ in S:
        if s_.get("tag"): chapter_tag(layer, t, s_["t0"] + 0.35, s_["t1"] - 0.1, s_["tag"])
        if s_.get("credit") and s_["t0"] <= t <= s_["t1"]:
            credit(layer, t, s_["t0"] + 0.2, s_["t1"], s_["credit"])
    if 37.6 <= t <= 42.9:
        credit(layer, t, 38.9, 42.9, "Photos: Tom Coates · Evan-Amos (PD) · Blake Patterson · Matt Buchanan — CC BY 2.0 · Wikimedia Commons")
    # STEVE JOBS reveal
    tw = big_title(layer, t, 12.95, 14.85, "STEVE JOBS", "pf9", 168, 520)
    if tw: gold_rules(layer, t, 12.95, 14.85, 520, tw / 2)
    put(layer, text_img("CO-FOUNDER OF APPLE", "sb", 30, GOLD, track=9), W / 2, 640, win(t, 13.5, 14.85, 0.5, 0.35), "mm")
    # THE END.
    v = win(t, 29.15, 31.05, 0.45, 0.3)
    put(layer, text_img("the end.", "pfi", 150, WHITE), W / 2, 520, v, "mm", scale=1.0 + 0.04 * clamp((t - 29.15) / 1.9))
    # A NEW BEGINNING
    put(layer, text_img("A  NEW", "l", 52, WHITE, track=14), W / 2, 430, win(t, 32.15, 34.0, 0.4, 0.3), "mm")
    big_title(layer, t, 32.35, 34.0, "BEGINNING", "pf9", 150, 545, GOLD, track0=30, track1=8, wipe=True)
    # ONE MORE THING...
    txt = "ONE MORE THING..."
    if 43.15 <= t <= IMPACT:
        n_ = int(clamp((t - 43.25) / 1.1) * len(txt)) + 1
        v = win(t, 43.15, IMPACT, 0.2, 0.12)
        s_ = 1.0 + 0.25 * eio((t - (IMPACT - 0.45)) / 0.45)
        put(layer, text_img(txt[:n_], "l", 64, WHITE, track=16), W / 2 - text_w(txt, "l", 64, 16) * s_ / 2, 540, v, "lm", scale=s_)
    # THE STORY OF STEVE JOBS
    put(layer, text_img("THE STORY OF", "l", 46, WHITE, track=18), W / 2, 420, win(t, 46.3, 49.05, 0.5, 0.3), "mm")
    tw = big_title(layer, t, 46.9, 49.05, "STEVE JOBS", "pf9", 190, 545)
    if tw: gold_rules(layer, t, 46.9, 49.05, 545, tw / 2)
    draw_captions(layer, t)
    draw_end_overlay(layer, t)

def frame_at(t, fi):
    idx = max(i for i, s_ in enumerate(S) if s_["t0"] <= t + 1e-9)
    cur = S[idx]; fr = render_shot(cur, t)
    lt = t - cur["t0"]
    if idx > 0 and cur["xf"] > 0 and lt < cur["xf"]:
        prev = render_shot(S[idx - 1], t)
        m = eio(lt / cur["xf"]); fr = prev * (1 - m) + fr * m
    fr = fr * VIG
    g = GRAIN[fi % len(GRAIN)]
    fr += np.repeat(np.repeat(g, 2, 0), 2, 1)
    # fades / flash
    fr *= clamp(t / 0.5) * clamp((TOTAL - t) / 0.8)
    if IMPACT <= t < IMPACT + 0.45:
        f = 1 - eo((t - IMPACT) / 0.45); fr = fr * (1 - f) + 255 * f
    base = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
    overlays(base, t)
    return base.convert("RGB")

def main():
    args = sys.argv[1:]
    if args and args[0] == "--still":
        for ts in args[1:]:
            t = float(ts); frame_at(t, 0).save(f"out/still_{t:05.2f}.jpg", quality=88); VIDS.clear()
        return
    t0, t1, out = 0.0, TOTAL, "out/video_noaudio.mp4"
    if args and args[0] == "--preview": t0, t1, out = float(args[1]), float(args[2]), "out/preview.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    n0, n1 = int(t0 * FPS), int(t1 * FPS)
    # pre-seek video readers so preview starts mid-shot correctly (readers read from shot start)
    for fi in range(n0, n1):
        t = fi / FPS
        enc.stdin.write(frame_at(t, fi).tobytes())
        if fi % 90 == 0: print(f"{t:5.1f}s", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main()
