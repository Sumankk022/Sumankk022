"""Founder File: vertical news-style reels (1080x1920, 30 fps) for the Razorpay IPO and BYJU'S stories.

  python3 reel.py retime  NAME           re-time the narration (pauses) -> out/NAME_voice.wav, out/NAME_tl.json
  python3 reel.py mix     NAME           music + SFX + intro ident + CTA       -> out/NAME_mix.wav
  python3 reel.py introv                 vertical version of the channel intro -> out/intro_v.mp4
  python3 reel.py still   NAME t [t..]   preview stills                        -> out/NAME_<t>.jpg
  python3 reel.py part    NAME i n       render frame-chunk i of n             -> out/NAME_part_i.mp4
NAME is razorpay or byjus.  ASSETS env var points at the asset folder (vid/ img/ music/ sfx/ voice/ intro.mp4).
"""
import sys, os, json, math, re, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, SR = 1080, 1920, 30, 48000
AS = os.environ.get("ASSETS", "assets")
OUT = os.environ.get("OUT", "out"); os.makedirs(OUT, exist_ok=True)
GOLD, RED, WHITE, BLACK, GREEN = (255, 196, 46), (238, 58, 52), (255, 255, 255), (0, 0, 0), (52, 211, 120)
db = lambda x: 10 ** (x / 20)

# ============================================================ basics
FD = "/usr/share/fonts/opentype/inter/"
@functools.lru_cache(None)
def font(name, size):
    return ImageFont.truetype(FD + {"bk": "InterDisplay-Black.otf", "xb": "InterDisplay-ExtraBold.otf", "b": "InterDisplay-Bold.otf",
                                     "sb": "InterDisplay-SemiBold.otf", "m": "InterDisplay-Medium.otf"}[name], size)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def eback(x, s=1.70158): x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2
def spring(x):
    x = max(0.0, x); return 1 - math.exp(-6 * x) * math.cos(9 * x)
def win(t, t0, t1, fi=0.2, fo=0.2):
    if t < t0 or t > t1: return 0.0
    return min(eo((t - t0) / fi) if fi else 1, eo((t1 - t) / fo) if fo else 1)
def norm(w): return re.sub(r"[^a-z0-9$']", "", w.lower().replace("’", "'"))

GRADES = {"warm": (1.10, 1.05, (1.05, 1.0, 0.93), 2), "neutral": (1.06, 1.0, (1, 1, 1), 0), "cool": (1.08, 0.8, (0.94, 1.0, 1.07), 3),
          "teal": (1.12, 0.95, (0.94, 1.02, 1.07), 0), "dark": (1.15, 0.55, (0.95, 0.98, 1.05), -6), "red": (1.12, 0.7, (1.12, 0.92, 0.9), -4),
          "bw": (1.18, 0.0, (1, 1, 1), 0)}
@functools.lru_cache(None)
def lut(g):
    c, sat, rgb, lift = GRADES[g]; x = np.arange(256) / 255.0; s = 0.5 + (x - 0.5) * c
    if c > 1: s = s * 0.75 + 0.25 * (3 * x ** 2 - 2 * x ** 3)
    return np.stack([np.clip(s * 255 * k + lift, 0, 255) for k in rgb], 1).astype(np.uint8), sat
def grade(a, g):
    L, sat = lut(g); o = np.empty_like(a)
    for c in range(3): o[..., c] = L[a[..., c], c]
    if sat != 1.0:
        f = o.astype(np.float32); lum = (f[..., 0] * .299 + f[..., 1] * .587 + f[..., 2] * .114)[..., None]
        o = np.clip(lum + (f - lum) * sat, 0, 255).astype(np.uint8)
    return o

# ---------- text / shapes (RGBA numpy sprites, cached)
@functools.lru_cache(maxsize=6000)
def stext(txt, fname, size, color=WHITE, stroke=0, track=0, shadow=True, sc=None):
    f = font(fname, size); pad = 40 + stroke
    widths = [f.getlength(c) for c in txt] if track else None
    tw_ = int(sum(widths) + track * (len(txt) - 1)) if track else int(f.getlength(txt))
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (max(1, tw_) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    def draw(d, fill, sw=0, sf=None):
        if track:
            x = pad
            for c, wc in zip(txt, widths): d.text((x, pad), c, font=f, fill=fill, stroke_width=sw, stroke_fill=sf); x += wc + track
        else: d.text((pad, pad), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=sf)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (0, 0, 0, 190), stroke, (0, 0, 0, 190))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(max(5, size // 9))))
    draw(ImageDraw.Draw(im), tuple(color) + (255,), stroke, tuple(sc or (0, 0, 0)) + (255,))
    return np.array(im)
def tw(txt, fname, size, track=0):
    f = font(fname, size); return (sum(f.getlength(c) for c in txt) + track * (len(txt) - 1)) if track else f.getlength(txt)
def put(layer, arr, x, y, a=1.0, anchor="lt", scale=1.0, pad=None, rot=0.0):
    """composite sprite (cropped pad of 40+stroke around text). anchor: l/m/r + t/m/b on the text box."""
    if a <= 0.003 or scale <= 0.01: return
    im = arr; pd0 = 40 if pad is None else pad
    if scale != 1.0 or rot:
        p = Image.fromarray(arr)
        if scale != 1.0: p = p.resize((max(1, int(p.width * scale)), max(1, int(p.height * scale))), Image.BICUBIC)
        if rot:
            w0, h0 = p.size; p = p.rotate(rot, Image.BICUBIC, expand=True)
            x -= 0; y -= 0
            dx, dy = (p.width - w0) / 2, (p.height - h0) / 2
        im = np.array(p)
    else: dx = dy = 0
    if not rot: dx = dy = 0
    h, w = im.shape[:2]; pd = pd0 * scale; bw, bh = w - 2 * pd - 2 * dx, h - 2 * pd - 2 * dy
    if anchor[0] == "m": x -= bw / 2
    elif anchor[0] == "r": x -= bw
    if anchor[1] == "m": y -= bh / 2
    elif anchor[1] == "b": y -= bh
    x, y = int(round(x - pd - dx)), int(round(y - pd - dy))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(layer.width, x + w), min(layer.height, y + h)
    if x1 <= x0 or y1 <= y0: return
    c = im[y0 - y:y1 - y, x0 - x:x1 - x].copy()
    if a < 1: c[..., 3] = (c[..., 3] * a).astype(np.uint8)
    layer.alpha_composite(Image.fromarray(c), (x0, y0))
@functools.lru_cache(maxsize=2000)
def rrect(w, h, r, fill=(0, 0, 0, 255), outline=None, width=0, ss=3):
    """anti-aliased rounded rect sprite, padded by 40 like text sprites"""
    w, h = max(2, int(w)), max(2, int(h))
    im = Image.new("RGBA", ((w + 80) * ss, (h + 80) * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40 * ss, 40 * ss, (40 + w) * ss - 1, (40 + h) * ss - 1], radius=r * ss, fill=fill,
                        outline=outline, width=width * ss)
    return np.array(im.resize((w + 80, h + 80), Image.LANCZOS))
@functools.lru_cache(maxsize=200)
def glow(w, h, r, color, blur=26, alpha=150):
    im = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + w, 40 + h], radius=r, fill=tuple(color) + (alpha,))
    return np.array(im.filter(ImageFilter.GaussianBlur(blur)))

# ============================================================ audio helpers
def load(path, ch=1, af=None, sr=SR):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    return a.reshape(-1, ch).copy() if ch > 1 else a.copy()
def save(path, a):
    ch = 1 if a.ndim == 1 else a.shape[1]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", str(ch), "-i", "-", "-c:a", "pcm_s24le", path],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)

# ============================================================ REEL CONFIG
REELS = {
 "razorpay": dict(series="RAZORPAY IPO", head=("RAZORPAY IS", "GOING PUBLIC"), box=GOLD, bed="34", bed_off=2.0,
                  pauses={"online,": 0.36, "market.": 0.95, "part.": 0.85, "planning.": 0.45, "billion.": 0.5},
                  default_gap=0.45, last_q="chapter?"),
 "byjus": dict(series="THE BYJU'S STORY", head=("HOW BYJU'S", "FELL APART"), box=RED, bed="32", bed_off=0.0,
               pauses={"apart.": 1.0, "startup.": 0.68, "building.": 0.55, "crisis.": 0.5, "survival.": 0.6},
               default_gap=0.45, last_q="wrong?"),
}

# ============================================================ 1) RE-TIME NARRATION
def words_raw(name):
    W_ = [dict(w=w["w"].strip(), s=w["s"], e=w["e"]) for s in json.load(open(f"{AS}/voice/{name}_words.json")) for w in s["words"]]
    out = []                                          # merge "-based", ".5" into the previous token
    for w in W_:
        if out and re.match(r"^[-.]\w", w["w"]): out[-1]["w"] += w["w"]; out[-1]["e"] = w["e"]
        else: out.append(dict(w))
    return out

def retime(name):
    R = REELS[name]; words = words_raw(name)
    v = load(f"{AS}/voice/{name}.mp3")
    hop = int(0.01 * SR); env = np.sqrt(np.convolve(v ** 2, np.ones(hop) / hop, "same")[::hop]); edb = 20 * np.log10(env + 1e-9)
    sil = edb < -52
    ci = next(i for i, w in enumerate(words) if norm(w["w"]) == "follow" and i > len(words) * 0.7)   # CTA start
    pieces, shifts = [], []          # pieces: (src_a, src_b) or ("sil", seconds); shifts: (src_time, delta)
    pos, delta = 0.0, 0.0
    for i in range(ci - 1):
        a_, b_ = words[i]["e"] - 0.25, words[i + 1]["s"] + 0.25
        fa, fb = int(a_ * 100), int(b_ * 100); best, run, bs = (0, 0), 0, 0
        for f in range(fa, fb):
            if 0 <= f < len(sil) and sil[f]:
                if run == 0: bs = f
                run += 1
                if run > best[1] - best[0]: best = (bs, f + 1)
            else: run = 0
        if best[1] - best[0] >= 3: ra, rb = best[0] / 100, best[1] / 100
        else:
            seg = edb[fa:fb]; m = fa + int(np.argmin(seg)); ra = rb = m / 100
        L = rb - ra; key = words[i]["w"]
        T = R["pauses"].get(key, min(L, R["default_gap"]) if L > R["default_gap"] else L)
        if abs(T - L) < 0.02: continue
        keep = min(L, T)
        pieces.append((pos, ra + keep / 2)); pieces.append(("sil", T - keep)); pos = rb - keep / 2
        delta += T - L; shifts.append((rb, delta))
    # main part ends after the question (+ small tail), CTA kept separately
    qe = words[ci - 1]["e"]; tail_end = qe + 0.12
    k = int(qe * 100)
    while k < len(sil) and not sil[k]: k += 1
    tail_end = max(tail_end, k / 100 + 0.03)
    pieces.append((pos, tail_end))
    out = []
    for p in pieces:
        if p[0] == "sil": out.append(np.zeros(int(p[1] * SR), np.float32))
        else:
            seg = v[int(p[0] * SR):int(p[1] * SR)].copy(); f = min(len(seg) // 2, int(0.006 * SR))
            if f: seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
            out.append(seg)
    main = np.concatenate(out)
    def mapt(t):
        d = 0.0
        for s_, dl in shifts:
            if t >= s_ - 0.001: d = dl
        return t + d
    cs = words[ci]["s"] - 0.06
    k = int(cs * 100)
    while k > 0 and not sil[k]: k -= 1                     # back up into silence
    cs = min(cs, k / 100 + 0.02)
    cta = v[int(cs * SR):]
    nz = np.where(np.abs(cta) > 1e-3)[0]; cta = cta[:nz[-1] + int(0.15 * SR)] if len(nz) else cta
    nw = [dict(w=w["w"], s=round(mapt(w["s"]), 3), e=round(mapt(w["e"]), 3)) for w in words[:ci]]
    cw = [dict(w=w["w"], s=round(w["s"] - cs, 3), e=round(w["e"] - cs, 3)) for w in words[ci:]]
    save(f"{OUT}/{name}_main.wav", main); save(f"{OUT}/{name}_cta.wav", cta)
    json.dump(dict(words=nw, cta_words=cw, main_len=len(main) / SR, cta_len=len(cta) / SR, q_end=mapt(qe)),
              open(f"{OUT}/{name}_rt.json", "w"), indent=1)
    print(f"{name}: main {len(v)/SR:.2f}s -> {len(main)/SR:.2f}s (+{delta:.2f}), cta {len(cta)/SR:.2f}s")

# ============================================================ timeline
V0 = 0.15                     # voice offset
IDENT_LEN = 4.55              # we cut the 5 s intro just before its fade-to-black
def timeline(name):
    rt = json.load(open(f"{OUT}/{name}_rt.json"))
    words = [dict(w, s=w["s"] + V0, e=w["e"] + V0) for w in rt["words"]]
    q_end = rt["q_end"] + V0
    t_imp = q_end + 0.8                               # short beat after the last question, then the hit
    t_ec = t_imp + IDENT_LEN
    cta0 = t_ec + 0.35
    cta_words = [dict(w, s=w["s"] + cta0, e=w["e"] + cta0) for w in rt["cta_words"]]
    total = cta0 + rt["cta_len"] + 1.6
    return dict(words=words, cta_words=cta_words, q_end=q_end, t_imp=t_imp, t_ec=t_ec, cta0=cta0, total=total)

def anchor_fn(words):
    def A(phrase, d=0.0, edge="s", occ=0):
        toks = [norm(x) for x in phrase.split()]; seen = 0
        for i in range(len(words) - len(toks) + 1):
            if all(norm(words[i + j]["w"]) == toks[j] for j in range(len(toks))):
                if seen == occ: return (words[i]["s"] if edge == "s" else words[i + len(toks) - 1]["e"]) + d
                seen += 1
        raise KeyError(phrase)
    return A

# ============================================================ SPEC (shots + overlay events), shared by audio + video
def spec(name, A, TL):
    S, EV = [], []
    def vid(t, num, off=0.0, g="neutral", tr="whip", z=(1.0, 1.1), dim=1.0, label=None, rate=1.0):
        S.append(dict(t0=t, kind="vid", src=f"{AS}/vid/{num}.mp4", off=off, g=g, tr=tr, z=z, dim=dim, label=label, rate=rate, key=None))
    def img(t, key, g="warm", tr="whip", z=(1.04, 1.16), px=(0, 0), py=(0, 0), dim=1.0, label=None, fit=False):
        S.append(dict(t0=t, kind="img", key=key, g=g, tr=tr, z=z, px=px, py=py, dim=dim, label=label, fit=fit))
    def ev(kind, t0, t1, **kw): EV.append(dict(kind=kind, t0=t0, t1=t1, **kw))
    if name == "razorpay":
        vid(0.0, 47412, off=1.0, g="warm", tr="none")
        vid(A("helps millions", -0.08), 21780, off=1.5, g="warm", tr="punch")
        vid(A("collect money", -0.08), 35902, off=3.0, g="warm", tr="punch")
        vid(A("and then taking", -0.08), 9607, off=1.0, g="teal")
        ev("pop", A("stock market"), A("that's exactly", -0.15), text="STOCK MARKET", sub="NEXT STOP", color=GOLD, size=118)
        img(A("that's exactly", -0.12), "ubnight", g="cool", tr="flash", z=(1.05, 1.2), px=(0.0, 0.1), label="BENGALURU")
        ev("logo", A("razorpay is", -0.05), A("founded in", -0.2), key="rzplogo")
        vid(A("founded in", -0.1), 42652, off=1.0, g="warm")
        ev("pop", A("2014", -0.05), A("razorpay started", -0.1), text="2014", sub="FOUNDED", color=GOLD, size=190)
        vid(A("razorpay started", -0.1), 18264, off=1.0, g="warm", tr="punch")
        vid(A("online payments", -0.1), 15914, off=2.0, g="warm", tr="punch")
        vid(A("today,", -0.12), 6367, off=1.0, g="warm", dim=0.5)
        ev("chips", A("payment processing", -0.05), A("now,", -0.15), items=[
            ("PAYMENTS", A("payment processing", -0.05)), ("PAYROLL", A("payroll", -0.05)),
            ("BANKING", A("banking", -0.05)), ("LENDING", A("lending", -0.05))], color=GOLD, style="grid")
        vid(A("payroll", -0.08), 22827, off=1.0, g="warm", tr="punch", dim=0.5)
        img(A("banking", -0.08), "rupee", g="warm", tr="punch", dim=0.5, z=(1.1, 1.2))
        vid(A("lending", -0.08), 23168, off=0.5, g="warm", tr="punch", dim=0.5)
        vid(A("now,", -0.1), 47792, off=2.0, g="dark", tr="glitch", dim=0.8)
        ev("banner", A("here's the", -0.05), A("razorpay has", -0.2), text="THE INTERESTING PART", color=RED)
        img(A("razorpay has", -0.08), "sebi", g="cool", tr="flash", z=(1.05, 1.18), py=(0.2, -0.1), label="SEBI BHAVAN · MUMBAI")
        ev("stamp", A("approval", -0.02), A("for its", 0.25), text="SEBI APPROVED", color=GREEN, rot=-8)
        img(A("for its", -0.05), "bse", g="warm", tr="punch", z=(1.05, 1.15), py=(-0.3, -0.3), label="BOMBAY STOCK EXCHANGE")
        ev("pop", A("ipo,", -0.05), A("targeting", 0.05), text="IPO", sub=None, color=GOLD, size=230)
        vid(A("targeting", -0.05), 47012, off=2.0, g="teal", dim=0.6)
        ev("counter", A("valuation", 0.0), A("but back", -0.15), pre="~$", target=5.0, dec=0, suf="B", label="TARGET VALUATION",
           land=A("billion.", 0.0), color=GOLD)
        vid(A("but back", -0.08), 47213, off=3.0, g="teal", tr="glitch", dim=0.35)
        ev("bars", A("2021", -0.05), A("so,", -0.15), b1=("2021", 7.5, A("$7.5", -0.1)), b2=("IPO TARGET", 5.0, A("billion.", 0.25, occ=1)))
        img(A("so,", -0.08), "bsehall", g="warm", tr="whip", z=(1.0, 1.12), py=(-0.4, -0.2), label="DALAL STREET · MUMBAI")
        vid(A("buy into", -0.08), 45706, off=2.0, g="teal", tr="punch", dim=0.55)
        ev("question", A("next big", -0.05), TL["t_imp"] - 0.02, text=("WILL INVESTORS", "BUY IN?"), color=GOLD)
    if name == "byjus":
        vid(0.0, 30873, off=0.5, g="neutral", tr="none", dim=0.55)
        ev("counter", A("worth", -0.05), A("and then", -0.1), pre="$", target=22, dec=0, suf=" BILLION", label="STARTUP VALUATION",
           land=A("22", 0.6), color=GOLD, crash=None)
        vid(A("and then", -0.08), 26759, off=1.0, g="red", tr="glitch", dim=0.6)
        ev("crash", A("and then", -0.08), A("that's the", -0.15), text="$22 BILLION", fall=A("fall", -0.02))
        img(A("that's the", -0.1), "byju2", g="warm", tr="flash", z=(1.05, 1.18), px=(-0.3, -0.2))
        ev("logo", A("baiju's.", -0.02), A("founded by", -0.15), key="byjulogo")
        img(A("founded by", -0.1), "byju1", g="warm", tr="punch", z=(1.0, 1.12), px=(0.0, 0.0), py=(-0.5, -0.5), label="BYJU RAVEENDRAN · FOUNDER")
        vid(A("the company changed", -0.1), 48860, off=1.0, g="warm")
        img(A("indian students", -0.1), "byjuclass", g="warm", tr="punch", z=(1.05, 1.2), label="LIVE CLASS · BENGALURU, 2020")
        vid(A("during the", -0.1), 47186, off=2.0, g="warm", tr="whip")
        ev("pop", A("pandemic,", -0.05), A("demand", 0.0), text="2020", sub="THE PANDEMIC HITS", color=WHITE, size=200)
        vid(A("demand", -0.08), 47184, off=3.0, g="warm", tr="punch", dim=0.55)
        ev("growth", A("demand", -0.05), A("investors poured", -0.15), text="DEMAND")
        vid(A("investors poured", -0.1), 45703, off=2.0, g="warm", tr="punch")
        vid(A("the company acquired", -0.1), 23042, off=3.0, g="warm", tr="punch")
        ev("pop", A("acquired", 0.0), A("and baiju's", -0.15), text="ACQUISITIONS", sub="BUYING COMPANIES", color=GOLD, size=110)
        img(A("and baiju's", -0.1), "byjuann3", g="warm", tr="flash", z=(1.05, 1.2), px=(-0.2, 0.0), dim=0.85)
        ev("badge", A("most valuable", -0.05), A("but behind", -0.2), text=("INDIA'S MOST", "VALUABLE STARTUP"), sub="$22B")
        vid(A("but behind", -0.06), 9704, off=1.0, g="dark", tr="glitch")
        vid(A("financial troubles", -0.1), 47948, off=0.5, g="dark", tr="flash")
        vid(A("delayed", -0.1), 45923, off=1.0, g="red", tr="punch", dim=0.5)
        ev("chips", A("delayed", -0.05), A("pushed the", -0.1), items=[
            ("DELAYED FINANCIALS", A("delayed", -0.05)), ("INVESTOR DISPUTES", A("investor disputes", -0.05)),
            ("MOUNTING DEBT", A("mounting", -0.05)), ("LEGAL BATTLES", A("and legal", 0.0))], color=RED, style="list")
        vid(A("investor disputes", -0.08), 46677, off=2.0, g="red", tr="punch", dim=0.5)
        vid(A("mounting", -0.08), 18305, off=1.0, g="red", tr="punch", dim=0.5)
        vid(A("and legal", -0.06), 46820, off=2.0, g="red", tr="punch", dim=0.5)
        vid(A("pushed the", -0.08), 26758, off=2.0, g="red", tr="glitch", dim=0.55)
        ev("stamp", A("insolvency", -0.02), A("and the company", -0.15), text="INSOLVENCY", color=RED, rot=-7)
        vid(A("and the company", -0.1), 15478, off=4.0, g="dark", tr="flash")
        vid(A("fighting for", -0.1), 5601, off=1.0, g="dark", tr="punch")
        vid(A("so what", -0.08), 4701, off=2.0, g="dark", tr="glitch", dim=0.45)
        ev("question", A("so what", -0.02), TL["t_imp"] - 0.02, text=("WHAT WENT", "WRONG?"), color=RED)
    S.sort(key=lambda s: s["t0"])
    for i, s in enumerate(S): s["t1"] = S[i + 1]["t0"] if i + 1 < len(S) else TL["t_imp"]
    return S, EV

HL = {"razorpay": {"razorpay": GOLD, "2014": GOLD, "ipo": GOLD, "sebi": GOLD, "approval": GREEN, "$5": GOLD, "$75": GOLD, "billion": GOLD,
                   "2021": GOLD, "stock": GOLD, "market": GOLD, "interesting": RED, "millions": GOLD, "bengalurubased": GOLD,
                   "payroll": GOLD, "banking": GOLD, "lending": GOLD, "payment": GOLD, "processing": GOLD, "chapter": GOLD},
      "byjus": {"22": GOLD, "billion": GOLD, "dollars": GOLD, "empire": GOLD, "fall": RED, "apart": RED, "baiju's": GOLD, "ravindran": GOLD,
                "millions": GOLD, "pandemic": GOLD, "exploded": GREEN, "valuable": GOLD, "troubles": RED, "delayed": RED, "disputes": RED,
                "debt": RED, "legal": RED, "battles": RED, "insolvency": RED, "crisis": RED, "survival": RED, "wrong": RED, "unstoppable": GOLD}}

# ============================================================ 2) MIX
def synth_pop(f0=900, dur=0.09):
    t = np.arange(int(dur * SR)) / SR; f = f0 * np.exp(-t * 18)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40)).astype(np.float32)
def synth_tick():
    t = np.arange(int(0.02 * SR)) / SR; n = np.random.default_rng(3).normal(0, 1, len(t))
    return (np.diff(np.concatenate([[0], n])) * np.exp(-t * 300) * 0.5 + np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 400) * 0.6).astype(np.float32)
def synth_click():
    t = np.arange(int(0.05 * SR)) / SR
    return (np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 220) * 0.7 + np.sin(2 * np.pi * 420 * t) * np.exp(-t * 90) * 0.5).astype(np.float32)
def synth_bell():
    t = np.arange(int(1.6 * SR)) / SR; o = np.zeros_like(t)
    for fr, a, d in ((1318, 1.0, 2.2), (2637, 0.45, 3.5), (3520, 0.25, 4.5), (1975, 0.3, 3.0), (5274, 0.12, 6)):
        o += a * np.sin(2 * np.pi * fr * t) * np.exp(-t * d)
    return (o / 2.1 * np.minimum(1, t / 0.003)).astype(np.float32)
def synth_heart(n):
    t = np.arange(int(0.35 * SR)) / SR; f = 62 * np.exp(-t * 6) + 38
    k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)
    return (k * n).astype(np.float32)
def drone(dur, seed=5):
    t = np.arange(int(dur * SR)) / SR; rng = np.random.default_rng(seed)
    o = np.zeros((len(t), 2), np.float32)
    for fr, a in ((55.0, 0.5), (65.41, 0.32), (82.41, 0.3), (110.0, 0.12), (130.8, 0.06)):
        for c, det in ((0, 0.997), (1, 1.003)):
            o[:, c] += a * np.sin(2 * np.pi * fr * det * t + rng.uniform(0, 6)) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t + c))
    noise = rng.normal(0, 1, (len(t), 2)).astype(np.float32)
    k = 400; noise = np.apply_along_axis(lambda x: np.convolve(x, np.ones(k) / k, "same"), 0, noise) * 6
    o += noise * (0.1 + 0.5 * (t / dur) ** 2)[:, None]                    # tension rises
    beat = 0.86; hs = synth_heart(1.0)
    for b in np.arange(0.4, dur - 0.5, beat):
        for off, g in ((0, 1.0), (0.2, 0.6)):
            i = int((b + off) * SR); seg = hs[:max(0, len(o) - i)] * g * (0.6 + 0.6 * b / dur)
            o[i:i + len(seg)] += seg[:, None]
    fi = int(0.4 * SR); o[:fi] *= np.linspace(0, 1, fi)[:, None]
    return o * 0.55

def tape_stop(x, dur):
    n = int(dur * SR); seg = x[-n:]; rate = np.linspace(1, 0, n) ** 1.6
    idx = np.cumsum(rate); idx = idx[idx < n - 1]
    out = np.stack([np.interp(idx, np.arange(n), seg[:, c]) for c in range(2)], 1)
    out *= np.linspace(1, 0, len(out))[:, None] ** 0.5
    return np.concatenate([x[:-n], out]), len(x) - n + len(out)

def mix(name):
    R = REELS[name]; TL = timeline(name); words = TL["words"]; A = anchor_fn(words); S, EV = spec(name, A, TL)
    total = TL["total"]; N = int(total * SR)
    vf = "highpass=f=75,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=1.5,equalizer=f=3200:t=q:w=1.2:g=2,loudnorm=I=-16:TP=-2:LRA=7"
    main = load(f"{OUT}/{name}_main.wav", af=vf); cta = load(f"{OUT}/{name}_cta.wav", af=vf)
    voice = np.zeros(N, np.float32)
    i0 = int(V0 * SR); voice[i0:i0 + len(main)] = main[:N - i0]
    ic = int(TL["cta0"] * SR); voice[ic:ic + len(cta)] = cta[:N - ic]
    m = np.zeros((N, 2), np.float32)
    def place(clip, t, gain):
        i = int(t * SR)
        if clip.ndim == 1: clip = np.repeat(clip[:, None], 2, 1)
        if i < 0: clip = clip[-i:]; i = 0
        clip = clip[:max(0, N - i)]; m[i:i + len(clip)] += clip * gain
    env = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
    env = np.clip(env / (np.percentile(env[env > 1e-4], 90) + 1e-9) * 1.3, 0, 1)
    def bed(track, t0, t1, off, hi, lo, fi=0.05, fo=0.6, af=None):
        mus = load(f"{AS}/music/{track}.mp3", ch=2, af="loudnorm=I=-14:TP=-1.5" + ("," + af if af else ""))[int(off * SR):]
        n = int((t1 - t0) * SR)
        while len(mus) < n: mus = np.concatenate([mus, mus])
        mus = mus[:n].copy(); i = int(t0 * SR)
        g = db(hi) + (db(lo) - db(hi)) * env[i:i + n]
        k = int(fi * SR); g[:k] *= np.linspace(0, 1, k) if k else 1
        k = int(fo * SR); g[-k:] *= np.linspace(1, 0, k)
        m[i:i + n] += mus * g[:len(mus), None]
        return mus
    sfx = lambda nm: load(f"{AS}/sfx/{nm}.mp3", ch=2)
    t_imp, t_ec = TL["t_imp"], TL["t_ec"]
    # ---- music beds
    if name == "razorpay":
        tl0, tl1 = A("now,", -0.12), A("razorpay has", -0.05)
        bed(R["bed"], 0.0, tl0 + 0.05, R["bed_off"], -15, -22, fi=0.02, fo=0.12)
        bed(R["bed"], tl0, tl1 + 0.08, R["bed_off"] + tl0, -17, -23, fi=0.1, fo=0.1, af="lowpass=f=420,lowpass=f=420")   # muffled "twist"
        bed(R["bed"], tl1, t_imp - 0.25, R["bed_off"] + tl1, -15, -22, fi=0.03, fo=1.4)
    else:
        tb = A("but behind", -0.08)
        mus = load(f"{AS}/music/{R['bed']}.mp3", ch=2, af="loudnorm=I=-14:TP=-1.5")[int(R["bed_off"] * SR):]
        n = int(tb * SR) + int(0.05 * SR); mus = mus[:n]
        g = db(-15) + (db(-22) - db(-15)) * env[:n]; mus = mus * g[:, None]; mus[:int(0.02 * SR)] *= 0
        mus, ln = tape_stop(mus, 0.75)                        # tape-stop into the downfall
        m[:ln] += mus[:N]
        dr = drone(t_imp - tb + 0.2); place(dr, tb + 0.1, db(-6))
    # ---- intro ident + finale
    intro = load(f"{AS}/intro.mp4", ch=2)[:int(IDENT_LEN * SR)]
    k = int(0.12 * SR); intro[-k:] *= np.linspace(1, 0, k)[:, None]
    place(intro, t_imp, db(-2.5))
    bed("31", t_ec - 0.05, total, 74.0, -12, -19, fi=0.05, fo=1.2)
    # transition: riser -> whoosh -> impact
    rs = sfx("788")[:int(2.17 * SR)]; rs *= np.linspace(0.2, 1, len(rs))[:, None] ** 1.5
    place(rs, t_imp - 2.17, db(-6))
    place(sfx("1714"), t_imp - 1.09, db(-9))
    place(sfx("2782"), t_imp - 0.40, db(-3))
    place(sfx("1143"), t_imp - 0.55, db(-8))
    # ---- per-shot / per-event SFX
    wh = ["1491", "1489"]
    for j, s in enumerate(S):
        if s["t0"] < 0.2: continue
        if s["tr"] == "whip": place(sfx(wh[j % 2]), s["t0"] - (0.3 if wh[j % 2] == "1491" else 0.7), db(-19))
        elif s["tr"] == "punch": place(sfx("1492"), s["t0"] - 1.0, db(-22))
        elif s["tr"] == "flash": place(sfx("1489"), s["t0"] - 0.7, db(-18)); place(sfx("498"), s["t0"], db(-20))
        elif s["tr"] == "glitch": place(sfx("1143"), s["t0"] - 0.5, db(-17))
    for e in EV:
        k_ = e["kind"]
        if k_ in ("pop", "logo", "question"): place(synth_pop(), e["t0"], db(-16)); place(sfx("498"), e["t0"], db(-20))
        if k_ == "banner": place(sfx("1492"), e["t0"] - 1.0, db(-16)); place(sfx("498"), e["t0"], db(-14))
        if k_ == "stamp": place(sfx("2782"), e["t0"] - 0.38, db(-9)); place(sfx("498"), e["t0"], db(-12))
        if k_ == "chips":
            for _, tt in e["items"]: place(synth_pop(700 if e["color"] == RED else 1100), tt, db(-15)); \
                (place(sfx("1143"), tt - 0.5, db(-20)) if e["color"] == RED else None)
        if k_ == "counter":
            t = e["t0"]
            while t < e["land"]: place(synth_tick(), t, db(-22)); t += 0.055
            place(sfx("498"), e["land"], db(-14))
        if k_ == "bars": place(synth_pop(600), e["b1"][2], db(-16)); place(synth_pop(500), e["b2"][2], db(-16)); place(sfx("498"), e["b2"][2] + 0.5, db(-16))
        if k_ == "crash": place(sfx("2782"), e["fall"] - 0.38, db(-8)); place(sfx("1143"), e["fall"] - 0.5, db(-10))
        if k_ in ("badge", "growth"): place(synth_pop(1300), e["t0"], db(-16)); place(sfx("498"), e["t0"] + 0.05, db(-18))
    # pause hits after the hooks
    hook_end = A("market.", edge="e") if name == "razorpay" else A("apart.", edge="e")
    place(sfx("1143"), hook_end + 0.02 - 0.5, db(-12))
    # ---- end card: click + bell
    ec = t_ec
    place(synth_click(), ec + 1.25, db(-8)); place(synth_click(), ec + 2.05, db(-8)); place(synth_bell(), ec + 2.08, db(-12))
    place(sfx("498"), ec + 0.02, db(-12))
    mixd = m + voice[:, None]
    save(f"{OUT}/_{name}.wav", mixd)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{OUT}/_{name}.wav", "-af", "loudnorm=I=-14:TP=-1.0:LRA=9",
                    "-ar", "48000", "-c:a", "pcm_s24le", f"{OUT}/{name}_mix.wav"], check=True)
    print(f"{name}: total {total:.2f}s, ident @ {t_imp:.2f}, end card @ {t_ec:.2f}")

# ============================================================ 3) VIDEO
CX, CY, CW, CH = 40, 470, 1000, 900          # media card
CAP_Y = 1520
@functools.lru_cache(None)
def card_mask():
    m = Image.new("L", (CW * 3, CH * 3), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, CW * 3 - 1, CH * 3 - 1], radius=34 * 3, fill=255)
    return m.resize((CW, CH), Image.LANCZOS)
@functools.lru_cache(None)
def card_shadow():
    im = Image.new("RGBA", (CW + 160, CH + 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([80, 95, 80 + CW, 95 + CH], radius=34, fill=(0, 0, 0, 200))
    return im.filter(ImageFilter.GaussianBlur(28))
@functools.lru_cache(None)
def card_border():
    return Image.fromarray(rrect(CW, CH, 34, (0, 0, 0, 0), (255, 255, 255, 40), 2))
@functools.lru_cache(None)
def vignette_layer():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return (1 - 0.35 * np.clip((r - 0.7) / 0.7, 0, 1) ** 1.5)[..., None].astype(np.float32)
_rng = np.random.default_rng(11)
GRAIN = [np.repeat(np.repeat(_rng.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32), 2, 0), 2, 1) for _ in range(3)]

ZB = 1.18          # video decode oversize for push-ins
class Vid:
    def __init__(self, src, off, g, size=(int(CW * ZB), int(CH * ZB))):
        self.src, self.off, self.g, self.size = src, off, g, size; self.p = None; self.idx = -1; self.last = None
        self.dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                        capture_output=True, text=True).stdout or 10)
    def frame(self, k):
        w, h = self.size
        if self.p is None:
            self.idx = k - 1; ss = self.off + k / FPS
            ss = ss % max(0.5, self.dur - 0.2)
            vf = f"fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},unsharp=5:5:0.6"
            self.p = subprocess.Popen(["ffmpeg", "-v", "quiet", "-stream_loop", "-1", "-ss", f"{ss:.3f}", "-i", self.src, "-vf", vf,
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while self.idx < k:
            b = self.p.stdout.read(w * h * 3)
            if len(b) < w * h * 3:
                if self.last is None: self.last = np.zeros((h, w, 3), np.uint8)
                self.idx = k; break
            self.last = grade(np.frombuffer(b, np.uint8).reshape(h, w, 3), self.g); self.idx += 1
        return self.last
    def close(self):
        if self.p: self.p.kill(); self.p.wait(); self.p = None

@functools.lru_cache(None)
def load_img(key):
    f = [x for x in os.listdir(f"{AS}/img") if x.split(".")[0] == key][0]
    im = Image.open(f"{AS}/img/" + f)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg
    im = im.convert("RGB")
    if key == "bsehall": im = im.crop((0, 0, im.width, int(im.height * 0.88)))      # drop the date stamp
    return im
@functools.lru_cache(None)
def graded(key, g): return Image.fromarray(grade(np.array(load_img(key)), g))
def kb_crop(img, z, px, py, out):
    Wi, Hi = img.size; ow, oh = out; c = min(Wi / ow, Hi / oh); ww, wh = ow * c / z, oh * c / z
    cx = Wi / 2 + px * (Wi - ww) / 2; cy = Hi / 2 + py * (Hi - wh) / 2
    return img.transform(out, Image.EXTENT, (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2), Image.BICUBIC)

@functools.lru_cache(None)
def intro_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.5)) ** 2)
    v = 4 + 22 * np.clip(1 - r, 0, 1) ** 1.3
    return np.repeat(v[..., None], 3, 2).astype(np.float32)

def introv():
    """vertical version of the 16:9 channel intro: logo scaled to fit, extended dark background"""
    sc = 0.68; w2, h2 = int(1920 * sc), int(1080 * sc); x0 = int(1020.5 * sc - W / 2)
    y_logo = 503 * sc; top = int(H / 2 - y_logo)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", f"{AS}/intro.mp4", "-vf", f"scale={w2}:{h2}:flags=lanczos,crop={W}:{h2}:{x0}:0",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                            "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", f"{OUT}/intro_v.mp4"], stdin=subprocess.PIPE)
    m = np.ones((h2, 1), np.float32); fe = 140; m[:fe] = np.linspace(0, 1, fe)[:, None] ** 1.5; m[-fe:] = np.linspace(1, 0, fe)[:, None] ** 1.5
    m = m[..., None]; bg = intro_bg()
    while True:
        b = p.stdout.read(W * h2 * 3)
        if len(b) < W * h2 * 3: break
        fr = np.frombuffer(b, np.uint8).reshape(h2, W, 3).astype(np.float32)
        lvl = fr.mean() / 21.0                          # follow the intro's own fade in/out
        canvas = bg * min(1.0, lvl)
        canvas[top:top + h2] = np.maximum(canvas[top:top + h2] * (1 - m) + fr * m, fr)
        enc.stdin.write(np.clip(canvas, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()
    json.dump(dict(top=top, h=h2), open(f"{OUT}/intro_v.json", "w"))

class Reel:
    def __init__(self, name):
        self.name = name; self.R = REELS[name]; self.TL = TL = timeline(name)
        self.words = TL["words"]; self.total = TL["total"]; A = anchor_fn(self.words); self.A = A
        self.S, self.EV = spec(name, A, TL)
        self.vids = {}; self.caps = self.build_caps(); self.HL = HL[name]
        self.ident = None
    # ---------------- captions
    def build_caps(self):
        caps, cur = [], []; words = self.words
        for i, w in enumerate(words):
            cur.append(w); end = bool(re.search(r"[.?!,]$", w["w"]))
            width = sum(tw(self.disp(x["w"]), "bk", 84) for x in cur) + 30 * len(cur)
            nxt = words[i + 1] if i + 1 < len(words) else None
            if end or len(cur) >= 3 or width > 780 or (nxt and nxt["s"] - w["e"] > 0.3) or \
               (nxt and width + tw(self.disp(nxt["w"]), "bk", 84) > 860):
                caps.append(cur); cur = []
        if cur: caps.append(cur)
        out = []
        for i, c in enumerate(caps):
            nx = caps[i + 1][0]["s"] - 0.03 if i + 1 < len(caps) else self.TL["t_imp"] - 0.1
            out.append(dict(items=c, t0=c[0]["s"] - 0.06, t1=min(c[-1]["e"] + 0.35, nx)))
        return out
    def disp(self, w):
        t = w.upper().replace("BAIJU'S", "BYJU'S").replace("BAIJU", "BYJU").replace("RAVINDRAN", "RAVEENDRAN")
        return t if t.endswith("?") else re.sub(r"[.,!]+$", "", t)
    def draw_caps(self, layer, t):
        for c in self.caps:
            if not (c["t0"] <= t <= c["t1"]): continue
            gin = eback((t - c["t0"]) / 0.2); out = clamp((c["t1"] - t) / 0.08)
            toks = [self.disp(w["w"]) for w in c["items"]]; fs = 84
            while sum(tw(x_, "bk", fs) for x_ in toks) + 28 * (len(toks) - 1) > W - 140: fs -= 4
            ws = [tw(x_, "bk", fs) for x_ in toks]; sp = 28
            x = W / 2 - (sum(ws) + sp * (len(ws) - 1)) / 2
            for w, txt, wd in zip(c["items"], toks, ws):
                active = w["s"] - 0.04 <= t
                hl = self.HL.get(norm(w["w"]))
                col = (hl or WHITE) if active else (255, 255, 255)
                sc = (1.0 + 0.08 * math.sin(math.pi * clamp((t - w["s"] + 0.04) / 0.22))) * clamp(gin, 0, 1.15)
                a = (1.0 if active else 0.5) * out
                put(layer, stext(txt, "bk", fs, col, stroke=7), x + wd / 2, CAP_Y, a, "mm", scale=max(0.05, sc), pad=47)
                x += wd + sp
    # ---------------- media
    def vid(self, s):
        k = id(s)
        if k not in self.vids: self.vids[k] = Vid(s["src"], s["off"], s["g"])
        return self.vids[k]
    def card(self, s, t):
        """RGB PIL image CW x CH for shot s at time t (with push-in + punch)"""
        lt = t - s["t0"]; dur = max(s["t1"] - s["t0"], 0.01); p = clamp(lt / dur)
        punch = 1.0 + (0.16 * (1 - eo(lt / 0.35)) if s["tr"] == "punch" else 0.0)
        if s["kind"] == "vid":
            fr = self.vid(s).frame(int(round(lt * FPS)))
            z = (s["z"][0] + (s["z"][1] - s["z"][0]) * p) * punch
            z = clamp(z, 1.0, ZB * 1.4)
            hh, ww = fr.shape[:2]; cw_, ch_ = ww / (ZB / min(z, ZB)) * (1 / ZB) * ZB, 0
            vw, vh = CW * ZB / z, CH * ZB / z
            x0, y0 = (ww - vw) / 2, (hh - vh) / 2
            im = Image.fromarray(fr)
            if abs(vw - CW) < 0.5: return im.crop((int(x0), int(y0), int(x0) + CW, int(y0) + CH))
            return im.transform((CW, CH), Image.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.BILINEAR)
        z = (s["z"][0] + (s["z"][1] - s["z"][0]) * (eio(p) * 0.5 + p * 0.5)) * punch
        px = s["px"][0] + (s["px"][1] - s["px"][0]) * p; py = s["py"][0] + (s["py"][1] - s["py"][0]) * p
        return kb_crop(graded(s["key"], s["g"]), z, px, py, (CW, CH))
    def bg_from(self, card):
        sm = card.resize((96, 86), Image.BILINEAR)
        c = sm.crop((24, 0, 72, 86)).filter(ImageFilter.GaussianBlur(3)).resize((W // 4, H // 4), Image.BILINEAR)
        a = np.array(c.resize((W, H), Image.BILINEAR)).astype(np.float32) * 0.34
        return a
    # ---------------- overlays
    def header(self, layer, t, ek):
        d = ImageDraw.Draw(layer)
        d.rectangle([0, 0, W, 10], fill=(255, 255, 255, 50)); d.rectangle([0, 0, int(W * t / self.TL["t_imp"]), 10], fill=GOLD + (255,))
        a = eo(t / 0.4) * ek
        pill = f"FOUNDER FILE  •  {self.R['series']}"
        pw = tw(pill, "b", 28, 3) + 64
        put(layer, rrect(pw, 54, 27, (0, 0, 0, 150), GOLD + (170,), 2), W / 2, 112, a, "mm")
        put(layer, stext(pill, "b", 28, WHITE, track=3, shadow=False), W / 2, 112, a, "mm")
        h1, h2 = self.R["head"]; box = self.R["box"]
        k1 = eback((t - 0.05) / 0.45); k2 = eo((t - 0.2) / 0.4)
        put(layer, stext(h1, "bk", 86, WHITE, stroke=0), W / 2, 228 + 30 * (1 - clamp(k1)), clamp(k1 * 1.4) * ek, "mm")
        bw = tw(h2, "bk", 86) + 56
        if k2 > 0:
            put(layer, rrect(bw * k2, 112, 16, box + (255,)), W / 2, 340, ek, "mm")
            if k2 > 0.5: put(layer, stext(h2, "bk", 86, BLACK if box == GOLD else WHITE, shadow=False), W / 2, 338, clamp((k2 - 0.5) * 2) * ek, "mm")
    def label(self, layer, s, t):
        if not s.get("label"): return
        lk = eo((t - s["t0"] - 0.2) / 0.3) * clamp((s["t1"] - t) / 0.15)
        if lk <= 0: return
        lab = s["label"]; lw = tw(lab, "b", 30, 4) + 52; y = CY + CH - 46
        put(layer, rrect(lw * lk, 58, 10, (0, 0, 0, 175)), CX + 26, y, 1, "lm")
        put(layer, rrect(6, 58, 2, GOLD + (255,)), CX + 26, y, lk, "lm")
        put(layer, stext(lab, "b", 30, WHITE, track=4, shadow=False), CX + 50, y, lk, "lm")
    def credit(self, layer, s, t):
        key = s.get("key") if s["kind"] == "img" else None
        if not key or key not in CREDITS: return
        c = CREDITS[key]
        put(layer, stext(c, "m", 19, (240, 240, 240)), CX + CW - 22, CY + 26, 0.75 * clamp((t - s["t0"]) / 0.3), "rt", pad=40)
    def events(self, layer, t):
        mx, my = CX + CW / 2, CY + CH / 2
        for e in self.EV:
            if not (e["t0"] - 0.05 <= t <= e["t1"] + 0.3): continue
            lt = t - e["t0"]; out = clamp((e["t1"] - t) / 0.2 + 0) if t <= e["t1"] else 0
            k = e["kind"]
            if k == "pop":
                kk = spring(lt / 0.55); a = clamp(lt / 0.12) * out
                put(layer, stext(e["text"], "bk", e["size"], e["color"], stroke=0), mx, my - 10, a, "mm", scale=max(0.05, 0.6 + 0.4 * kk))
                if e.get("sub"):
                    sw = tw(e["sub"], "b", 34, 6) + 50; ks = eo((lt - 0.2) / 0.3)
                    put(layer, rrect(sw * ks, 58, 29, GOLD + (235,) if e["color"] != GOLD else (0, 0, 0, 170)), mx, my + e["size"] * 0.62 + 10, a, "mm")
                    put(layer, stext(e["sub"], "b", 34, BLACK if e["color"] != GOLD else WHITE, track=6, shadow=False), mx, my + e["size"] * 0.62 + 10, a * ks, "mm")
            elif k == "logo":
                kk = spring(lt / 0.6); a = clamp(lt / 0.12) * out
                lg = logo_sprite(e["key"]); sc = max(0.05, 0.55 + 0.45 * kk)
                pw, ph = lg.width + 90, lg.height + 70
                put(layer, glow(pw, ph, 30, GOLD, 30, 140), mx, my + 230, a * 0.8, "mm", scale=sc)
                put(layer, rrect(pw, ph, 30, (255, 255, 255, 255)), mx, my + 230, a, "mm", scale=sc)
                arr = np.zeros((lg.height + 80, lg.width + 80, 4), np.uint8); arr[40:-40, 40:-40] = np.array(lg)
                put(layer, arr, mx, my + 230, a, "mm", scale=sc)
            elif k == "banner":
                kin = eo(lt / 0.3); a = out
                bw = W * kin
                put(layer, rrect(bw, 130, 0, e["color"] + (245,)), W / 2, my, a, "mm", pad=40)
                put(layer, stext(e["text"], "bk", 78, WHITE, shadow=False), W / 2 - 60 * (1 - kin), my - 2, a * clamp((lt - 0.12) / 0.2), "mm")
            elif k == "stamp":
                kk = clamp(lt / 0.22); sc = 2.4 - 1.4 * eo(kk); a = clamp(lt / 0.08) * out
                txt = e["text"]; tw_ = tw(txt, "bk", 92) + 80
                spr = stamp_sprite(txt, e["color"])
                put(layer, spr, mx, my, a, "mm", scale=sc, rot=e["rot"], pad=40)
            elif k == "chips": self.draw_chips(layer, e, t, lt, out)
            elif k == "counter":
                p = eo(clamp(lt / max(0.3, e["land"] - e["t0"]))); v = e["target"] * p
                txt = f"{e['pre']}{v:.{e['dec']}f}{e['suf']}" if p < 1 else f"{e['pre']}{e['target']:g}{e['suf']}"
                a = clamp(lt / 0.15) * out; land = clamp((t - e["land"]) / 0.25)
                sc = 1.0 + 0.12 * math.sin(math.pi * land) if 0 < land < 1 else 1.0
                size = 150 if len(txt) < 8 else 118
                put(layer, stext(e["label"], "b", 36, WHITE, track=6), mx, my - size * 0.75, a, "mm")
                put(layer, stext(txt, "bk", size, e["color"]), mx, my + 20, a, "mm", scale=sc)
            elif k == "crash": self.draw_crash(layer, e, t, lt)
            elif k == "bars": self.draw_bars(layer, e, t, lt, out)
            elif k == "question":
                l1, l2 = e["text"]; a = clamp(lt / 0.1)
                k1 = spring(lt / 0.5); k2 = spring((lt - 0.25) / 0.5)
                put(layer, stext(l1, "bk", 96, WHITE), mx, my - 70, a, "mm", scale=max(0.05, 0.6 + 0.4 * k1))
                if lt > 0.25:
                    wob = 1 + 0.03 * math.sin(lt * 6)
                    put(layer, stext(l2, "bk", 150, e["color"]), mx, my + 70, a, "mm", scale=max(0.05, (0.6 + 0.4 * k2) * wob))
            elif k == "growth":
                a = clamp(lt / 0.15) * out; p = eo(lt / 0.9)
                pts = [(0, 0.1), (0.2, 0.15), (0.35, 0.22), (0.5, 0.3), (0.62, 0.45), (0.75, 0.6), (0.88, 0.8), (1.0, 1.0)]
                gx0, gy0, gw, gh = CX + 110, CY + CH - 150, CW - 220, CH - 330
                d = ImageDraw.Draw(layer); n = int(p * 60)
                xs = [gx0 + gw * (i / 60) for i in range(n + 1)]
                ys = [gy0 - gh * np.interp(i / 60, [q[0] for q in pts], [q[1] for q in pts]) for i in range(n + 1)]
                if n > 1:
                    poly = list(zip(xs, ys)) + [(xs[-1], gy0), (xs[0], gy0)]
                    ov = Image.new("RGBA", layer.size, (0, 0, 0, 0)); ImageDraw.Draw(ov).polygon(poly, fill=GREEN + (int(70 * a),))
                    layer.alpha_composite(ov)
                    d.line(list(zip(xs, ys)), fill=GREEN + (int(255 * a),), width=12, joint="curve")
                    d.ellipse([xs[-1] - 16, ys[-1] - 16, xs[-1] + 16, ys[-1] + 16], fill=WHITE + (int(255 * a),))
                put(layer, stext(e["text"], "bk", 110, WHITE), mx, CY + 120, a, "mm", scale=max(0.05, 0.7 + 0.3 * spring(lt / 0.5)))
                put(layer, stext("▲ EXPLODED", "bk", 56, GREEN), mx, CY + 215, a * clamp((t - self.A("exploded.", 0)) / 0.2), "mm")
            elif k == "badge":
                l1, l2 = e["text"]; kk = spring(lt / 0.6); a = clamp(lt / 0.12) * out; sc = max(0.05, 0.5 + 0.5 * kk)
                bw_, bh_ = 820, 300
                put(layer, glow(bw_, bh_, 40, GOLD, 34, 120), mx, my + 120, a, "mm", scale=sc)
                put(layer, rrect(bw_, bh_, 40, (14, 12, 8, 235), GOLD + (255,), 4), mx, my + 120, a, "mm", scale=sc)
                put(layer, stext(l1, "bk", 70, WHITE, shadow=False), mx, my + 120 - 70 * sc, a, "mm", scale=sc)
                put(layer, stext(l2, "bk", 70, GOLD, shadow=False), mx, my + 120 + 10 * sc, a, "mm", scale=sc)
                put(layer, stext("VALUED AT " + e["sub"], "b", 36, WHITE, track=5, shadow=False), mx, my + 120 + 88 * sc, a * clamp((lt - 0.35) / 0.3), "mm", scale=sc)
    def draw_chips(self, layer, e, t, lt, out):
        items = e["items"]; col = e["color"]
        if e["style"] == "grid":
            cw_, ch_ = 430, 120; pos = [(CX + CW / 2 - 225, CY + 360), (CX + CW / 2 + 225, CY + 360), (CX + CW / 2 - 225, CY + 520), (CX + CW / 2 + 225, CY + 520)]
        else:
            cw_, ch_ = 760, 112; pos = [(CX + CW / 2, CY + 230 + i * 150) for i in range(4)]
        put(layer, stext("WHAT IT OFFERS" if col == GOLD else "WARNING SIGNS", "b", 34, WHITE, track=7), CX + CW / 2, CY + (230 if col == GOLD else 130),
            clamp(lt / 0.2) * out, "mm")
        for i, (txt, ts) in enumerate(items):
            if t < ts - 0.02: continue
            kk = spring((t - ts) / 0.5); a = clamp((t - ts) / 0.1) * out; sc = max(0.05, 0.6 + 0.4 * kk)
            x, y = pos[i]
            latest = i == max(j for j, (_, tt) in enumerate(items) if t >= tt - 0.02)
            put(layer, rrect(cw_, ch_, 24, (12, 12, 14, 225), col + (255 if latest else 150,), 4 if latest else 2), x, y, a, "mm", scale=sc)
            ic = (CX + CW / 2 - cw_ / 2 + 62) if e["style"] == "list" else (x - cw_ / 2 + 58)
            icx = x - (cw_ / 2 - 58) * sc
            put(layer, rrect(64, 64, 32, col + (255,)), icx, y, a, "mm", scale=sc)
            put(layer, stext("!" if col == RED else "✓", "bk", 44, BLACK if col == GOLD else WHITE, shadow=False), icx, y - 2, a, "mm", scale=sc)
            put(layer, stext(txt, "bk", 50 if e["style"] == "grid" else 54, WHITE, shadow=False), icx + 56 * sc, y - 2, a, "lm", scale=sc)
    def draw_crash(self, layer, e, t, lt):
        mx, my = CX + CW / 2, CY + CH / 2 + 20; tf = e["fall"]
        if t < tf:
            jit = 4 * math.sin(t * 90) if t > tf - 0.4 else 0
            put(layer, stext("STARTUP VALUATION", "b", 36, WHITE, track=6), mx, my - 150, 1, "mm")
            put(layer, stext(e["text"], "bk", 118, GOLD), mx + jit, my + 20, 1, "mm")
            return
        ft = t - tf
        spr = stext(e["text"], "bk", 118, RED); h_, w_ = spr.shape[:2]
        left, right = spr[:, : w_ // 2], spr[:, w_ // 2:]
        g = 2400 * ft ** 2
        put(layer, left, mx - w_ / 4 + 40 - 120 * ft, my + 20 + g * 0.8, clamp(1 - ft / 1.4), "mm", rot=18 * ft * 2, pad=0)
        put(layer, right, mx + w_ / 4 - 40 + 140 * ft, my + 20 + g, clamp(1 - ft / 1.4), "mm", rot=-24 * ft * 2, pad=0)
        put(layer, stext("STARTUP VALUATION", "b", 36, WHITE, track=6), mx, my - 150, clamp(1 - ft / 0.3), "mm")
    def draw_bars(self, layer, e, t, lt, out):
        a = clamp(lt / 0.2) * out
        px0, py0, pw_, ph_ = CX + 120, CY + 100, CW - 240, CH - 200
        put(layer, rrect(pw_, ph_, 30, (10, 12, 16, 210), (255, 255, 255, 40), 2), px0, py0, a, "lt")
        put(layer, stext("VALUATION", "b", 32, WHITE, track=7, shadow=False), px0 + pw_ / 2, py0 + 52, a, "mm")
        base = py0 + ph_ - 90; maxh = ph_ - 250
        for i, (lab, val, ts) in enumerate((e["b1"], e["b2"])):
            if t < ts - 0.05: continue
            p = eo((t - ts) / 0.6); bh = maxh * val / 7.5 * p
            bx = px0 + pw_ * (0.3 if i == 0 else 0.7); bw = 210
            col = GOLD if i == 0 else (235, 235, 235)
            put(layer, rrect(bw, max(4, bh), 14, col + (255,)), bx, base, a, "mb")
            vt = f"${val * p:.1f}B" if p < 1 else (f"${val:g}B" if i == 0 else f"~${val:g}B")
            put(layer, stext(vt, "bk", 64, col), bx, base - bh - 50, a, "mm")
            put(layer, stext(lab, "b", 32, WHITE, track=4, shadow=False), bx, base + 44, a, "mm")
            if i == 1 and t > ts + 0.6:
                kk = spring((t - ts - 0.6) / 0.5)
                put(layer, rrect(210, 84, 42, RED + (255,)), bx + 10, base - maxh * 0.95, a, "mm", scale=max(0.05, kk))
                put(layer, stext("▼ 33%", "bk", 50, WHITE, shadow=False), bx + 10, base - maxh * 0.95 - 2, a, "mm", scale=max(0.05, kk))
    # ---------------- ident + end card
    def ident_frame(self, t):
        if self.ident is None: self.ident = Vid(f"{OUT}/intro_v.mp4", 0.0, "neutral", size=(W, H))
        return self.ident.frame(int(round((t - self.TL["t_imp"]) * FPS))).astype(np.float32)
    def endcard(self, t):
        lt = t - self.TL["t_ec"]
        base = intro_bg().copy()
        # drifting gold particles
        img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
        for (x, y, r, sp, ph) in PARTS:
            yy = (y - sp * (lt + 3)) % (H + 100) - 50; xx = x + 18 * math.sin(lt * 0.8 + ph)
            put(img, dot_sprite(r), xx, yy, 0.55 * clamp(lt / 0.5), "mm", pad=0)
        lg = ident_logo(); mv = eio((lt - 0.15) / 0.55)
        y = 960 + (690 - 960) * mv; sc = 1.0 - 0.12 * mv
        l2 = lg.resize((int(lg.width * sc), int(lg.height * sc)), Image.BICUBIC)
        img.alpha_composite(l2, (int(W / 2 - l2.width / 2 + IDENT_DX * sc), int(y - l2.height / 2)))
        # subscribe + bell
        bk = spring((lt - 0.55) / 0.6)
        if lt > 0.55:
            sub_done = lt > 1.28; bx, by = W / 2 - 75, 1060
            col = (64, 64, 66) if sub_done else (229, 32, 26)
            press = 1 - 0.07 * math.sin(math.pi * clamp((lt - 1.18) / 0.18))
            s_ = max(0.05, bk) * press
            put(img, glow(600, 132, 66, col, 30, 120), bx, by, 1, "mm", scale=s_)
            put(img, rrect(600, 132, 66, col + (255,)), bx, by, 1, "mm", scale=s_)
            txt = "SUBSCRIBED" if sub_done else "SUBSCRIBE"
            put(img, stext(txt, "bk", 58, WHITE if not sub_done else (220, 220, 220), shadow=False), bx + (22 if sub_done else 0) * s_, by - 2, 1, "mm", scale=s_)
            if sub_done: put(img, stext("✓", "bk", 54, WHITE, shadow=False), bx - 205 * s_, by - 2, 1, "mm", scale=s_)
            # bell
            bb = spring((lt - 0.75) / 0.6); bxx = W / 2 + 315
            ring = lt > 2.08
            put(img, rrect(132, 132, 66, (40, 40, 42, 255), GOLD + (255,) if ring else (90, 90, 90, 255), 3), bxx, by, 1, "mm", scale=max(0.05, bb))
            ang = 22 * math.sin((lt - 2.08) * 28) * math.exp(-(lt - 2.08) * 3) if ring else 0
            put(img, bell_sprite(GOLD if ring else WHITE), bxx, by, 1, "mm", scale=max(0.05, bb), rot=ang, pad=10)
            if ring:
                for i in range(8):
                    r_ = 80 + 260 * eo((lt - 2.08) / 0.7); aa = clamp(1 - (lt - 2.08) / 0.8)
                    an = i * math.pi / 4 + 0.3
                    put(img, dot_sprite(7), bxx + r_ * math.cos(an), by + r_ * math.sin(an), aa, "mm", pad=0)
            if lt > 1.2:   # click ripple
                rp = clamp((lt - 1.25) / 0.45)
                if 0 < rp < 1:
                    d = ImageDraw.Draw(img); r_ = 30 + 120 * eo(rp)
                    d.ellipse([bx - r_, by - r_, bx + r_, by + r_], outline=(255, 255, 255, int(200 * (1 - rp))), width=5)
        tk = eo((lt - 0.9) / 0.4)
        put(img, stext("FOR MORE BUSINESS STORIES", "b", 38, WHITE, track=6), W / 2, 1230, tk, "mm")
        put(img, stext("REAL STORIES  •  REAL BUILDERS", "sb", 28, GOLD, track=6), W / 2, 1290, tk * 0.85, "mm")
        # cursor path: in -> subscribe (click 1.25) -> bell (click 2.05) -> out
        if 0.7 < lt < 3.6:
            pts = [(0.7, (980, 1650)), (1.2, (W / 2 - 40, 1085)), (1.35, (W / 2 - 40, 1085)), (1.95, (W / 2 + 330, 1085)),
                   (2.2, (W / 2 + 330, 1085)), (3.0, (1150, 1500)), (3.6, (1300, 1700))]
            for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
                if t0 <= lt <= t1:
                    q = eio((lt - t0) / (t1 - t0)); cx_, cy_ = p0[0] + (p1[0] - p0[0]) * q, p0[1] + (p1[1] - p0[1]) * q; break
            press = 1 - 0.18 * max(math.sin(math.pi * clamp((lt - 1.17) / 0.16)), math.sin(math.pi * clamp((lt - 1.97) / 0.16)), 0)
            put(img, cursor_sprite(), cx_, cy_, clamp((lt - 0.7) / 0.15), "lt", scale=press, pad=10)
        fr = np.array(img.convert("RGB")).astype(np.float32)
        if lt < 0.25: fr = fr * (1 - (1 - eo(lt / 0.25))) + 255 * (1 - eo(lt / 0.25)) * 0.6
        return fr
    # ---------------- frame
    def shot_at(self, t):
        idx = max([i for i, s in enumerate(self.S) if s["t0"] <= t + 1e-9] or [0]); return idx
    def frame(self, t, fi):
        TL = self.TL
        if t >= TL["t_ec"]: return Image.fromarray(np.clip(self.endcard(t) + GRAIN[fi % 3], 0, 255).astype(np.uint8))
        if t >= TL["t_imp"]:
            fr = self.ident_frame(t); lt = t - TL["t_imp"]
            if lt < 0.3: fr = fr * eo(lt / 0.3) + 255 * (1 - eo(lt / 0.3))       # impact flash into the ident
            return Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8))
        i = self.shot_at(t); s = self.S[i]; lt = t - s["t0"]
        cd = self.card(s, t); dim = s.get("dim", 1.0)
        bg = self.bg_from(cd)
        tr = s["tr"]; TR = 0.26
        if tr == "whip" and i > 0 and lt < TR:
            prev = self.S[i - 1]; pc = self.card(prev, t)
            p = eio(lt / TR); comb = Image.new("RGB", (CW, CH))
            comb.paste(pc, (int(-p * CW), 0)); comb.paste(cd, (int((1 - p) * CW), 0))
            blur = math.sin(math.pi * p)
            if blur > 0.05:
                k = max(2, int(CW / (1 + 30 * blur)))
                comb = comb.resize((k, CH), Image.BILINEAR).resize((CW, CH), Image.BILINEAR)
            cd = comb; pdim = prev.get("dim", 1.0); dim = pdim + (dim - pdim) * p
        cda = np.array(cd).astype(np.float32) * dim
        if tr == "glitch" and lt < 0.35:
            g = 1 - lt / 0.35; rng = np.random.default_rng(int(t * 1000))
            sh = int(26 * g); cda[..., 0] = np.roll(cda[..., 0], sh, 1); cda[..., 2] = np.roll(cda[..., 2], -sh, 1)
            for _ in range(int(7 * g) + 1):
                y0 = rng.integers(0, CH - 40); hh = rng.integers(10, 60); cda[y0:y0 + hh] = np.roll(cda[y0:y0 + hh], rng.integers(-80, 80), 1)
        if tr == "flash" and lt < 0.28: f = 1 - eo(lt / 0.28); cda = cda * (1 - f) + 255 * f
        frame = bg.copy()
        # shadow + card
        base = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).convert("RGBA")
        base.alpha_composite(card_shadow(), (CX - 80, CY - 80))
        base.paste(Image.fromarray(np.clip(cda, 0, 255).astype(np.uint8)), (CX, CY), card_mask())
        put(base, np.array(card_border()), CX, CY, 1, "lt")
        # card-local overlays
        self.label(base, s, t); self.credit(base, s, t)
        self.header(base, t, 1.0)
        self.events(base, t)
        self.draw_caps(base, t)
        arr = np.array(base.convert("RGB")).astype(np.float32) * vignette_layer() + GRAIN[fi % 3]
        # camera shake on stamps / crash
        shk = 0.0
        for e in self.EV:
            if e["kind"] == "stamp": shk = max(shk, 1 - clamp((t - e["t0"] - 0.2) / 0.35) if t >= e["t0"] + 0.2 else 0)
            if e["kind"] == "crash": shk = max(shk, 1 - clamp((t - e["fall"]) / 0.45) if t >= e["fall"] else 0)
        if shk > 0:
            r_ = np.random.default_rng(fi); arr = np.roll(arr, (int(r_.integers(-14, 14) * shk), int(r_.integers(-14, 14) * shk)), (0, 1))
        if t < 0.12: arr *= t / 0.12
        # flash out of the last shot into the ident (riser peak)
        tp = TL["t_imp"] - t
        if tp < 0.12: arr = arr * (tp / 0.12) + 255 * (1 - tp / 0.12)
        # cleanup finished readers
        for k_, v in list(self.vids.items()):
            if not any(id(s_) == k_ and s_["t1"] + 0.4 > t for s_ in self.S): v.close(); del self.vids[k_]
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

# ---------- sprites
CREDITS = {}
@functools.lru_cache(None)
def logo_sprite(key):
    im = Image.open([f"{AS}/img/{x}" for x in os.listdir(f"{AS}/img") if x.split(".")[0] == key][0]).convert("RGBA")
    a = np.array(im); rgb = a[..., :3].astype(int)
    white = (rgb.min(2) > 240); a[..., 3] = np.where(white, 0, a[..., 3])         # knock out white
    im = Image.fromarray(a); bb = im.getbbox(); im = im.crop(bb)
    s = min(560 / im.width, 150 / im.height); return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
@functools.lru_cache(None)
def stamp_sprite(txt, col):
    f = font("bk", 96); w_ = int(f.getlength(txt)) + 90; h_ = 170
    im = Image.new("RGBA", (w_ + 80, h_ + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 40, 40 + w_, 40 + h_], radius=18, fill=(0, 0, 0, 120), outline=col + (255,), width=10)
    d.rounded_rectangle([56, 56, 24 + w_, 24 + h_], radius=10, outline=col + (200,), width=3)
    d.text((40 + w_ / 2, 40 + h_ / 2), txt, font=f, fill=col + (255,), anchor="mm")
    a = np.array(im); rng = np.random.default_rng(4)
    mask = rng.random(a.shape[:2]) < 0.06; a[..., 3] = np.where(mask, (a[..., 3] * 0.35).astype(np.uint8), a[..., 3])   # ink texture
    return a
@functools.lru_cache(None)
def dot_sprite(r):
    s = int(r * 4); im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r], fill=GOLD + (230,))
    return np.array(im.filter(ImageFilter.GaussianBlur(r * 0.45)))
_pr = np.random.default_rng(21)
PARTS = [(_pr.uniform(0, W), _pr.uniform(0, H), _pr.uniform(2, 7), _pr.uniform(20, 70), _pr.uniform(0, 6)) for _ in range(46)]
@functools.lru_cache(None)
def bell_sprite(col):
    ss = 4; s = 84 * ss; im = Image.new("RGBA", (s + 20 * ss, s + 20 * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = 10 * ss
    c = col + (255,)
    d.pieslice([o + 14 * ss, o + 8 * ss, o + 70 * ss, o + 76 * ss], 180, 360, fill=c)
    d.polygon([(o + 14 * ss, o + 42 * ss), (o + 70 * ss, o + 42 * ss), (o + 78 * ss, o + 62 * ss), (o + 6 * ss, o + 62 * ss)], fill=c)
    d.rounded_rectangle([o + 4 * ss, o + 60 * ss, o + 80 * ss, o + 68 * ss], radius=4 * ss, fill=c)
    d.ellipse([o + 33 * ss, o + 66 * ss, o + 51 * ss, o + 82 * ss], fill=c)
    d.ellipse([o + 37 * ss, o + 0, o + 47 * ss, o + 10 * ss], fill=c)
    return np.array(im.resize((im.width // ss, im.height // ss), Image.LANCZOS))
@functools.lru_cache(None)
def cursor_sprite():
    ss = 4; im = Image.new("RGBA", (90 * ss, 110 * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(10, 10), (10, 82), (28, 66), (40, 94), (52, 89), (40, 62), (64, 62)]
    P = [(x * ss, y * ss) for x, y in pts]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(x + 4 * ss, y + 5 * ss) for x, y in P], fill=(0, 0, 0, 140))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(4 * ss))); d = ImageDraw.Draw(im)
    d.polygon(P, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=4 * ss)
    return np.array(im.resize((90, 110), Image.LANCZOS))
IDENT_DX = 0
@functools.lru_cache(None)
def ident_logo():
    """logo layer lifted from the vertical intro (frame at 4.0 s): alpha from brightness over the dark bg"""
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", "4.0", "-i", f"{OUT}/intro_v.mp4", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True).stdout
    fr = np.frombuffer(p, np.uint8).reshape(H, W, 3).astype(np.float32)
    band = fr[700:1220]; bgb = intro_bg()[700:1220]
    lum = band.max(2); a = np.clip((lum - bgb[..., 0] - 3) / 70, 0, 1)
    rgb = np.clip((band - bgb * (1 - a[..., None])) / np.maximum(a[..., None], 1e-3), 0, 255)
    out = np.dstack([rgb, a * 255]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA"); bb = im.getbbox(); im = im.crop(bb)
    global IDENT_DX; IDENT_DX = (bb[0] + bb[2]) / 2 - W / 2
    return im

def load_credits():
    p = f"{AS}/img/credits.json"
    if not os.path.exists(p): return
    for k, v in json.load(open(p)).items():
        lic = v["license"]
        if lic in ("Public domain", "CC0"): continue
        CREDITS[k] = f"{v['artist']} · {lic}"
load_credits()

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "retime": retime(sys.argv[2])
    elif cmd == "mix": mix(sys.argv[2])
    elif cmd == "introv": introv()
    elif cmd == "still":
        r = Reel(sys.argv[2])
        for ts in sys.argv[3:]:
            t = float(ts); r.frame(t, 0).save(f"{OUT}/{sys.argv[2]}_{t:05.2f}.jpg", quality=88)
            for v in r.vids.values(): v.close()
            r.vids.clear()
            if r.ident: r.ident.close(); r.ident = None
    elif cmd == "part":
        name, i, n = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        r = Reel(name); N = int(round(r.total * FPS)); a, b = N * i // n, N * (i + 1) // n
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", f"{OUT}/{name}_part{i}.mp4"],
                               stdin=subprocess.PIPE)
        for fi in range(a, b):
            enc.stdin.write(r.frame(fi / FPS, fi).tobytes())
            if (fi - a) % 150 == 0: print(f"{name} part {i}: {fi - a}/{b - a}", flush=True)
        enc.stdin.close(); enc.wait()
