"""Founder Files — vertical reels (1080x1920) from the Vijay Mallya story.
python3 reel.py audio N          build reels/out/rN_mix.wav + rN_words.json
python3 reel.py still N t [t..]  stills
python3 reel.py render N         reels/out/reelN.mp4 (with audio)
"""
import sys, os, json, math, re, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import engine as E                     # reuse fonts, grading, Ken Burns, video reader, text helpers

W, H, FPS = 1080, 1920, 30
E.W, E.H = W, H                        # helpers read these at call time
RD = "../reels"; OUT = RD + "/out"; os.makedirs(OUT, exist_ok=True)
GOLD, RED, WHITE, BLACK = E.GOLD, E.RED, E.WHITE, (0, 0, 0)
clamp, eo, eio, eback, win = E.clamp, E.eo, E.eio, E.eback, E.win
SR = 48000
db = lambda x: 10 ** (x / 20)

# ---------------- vertical vignette / grain ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIG = (1 - 0.35 * np.clip((_r - 0.6) / 0.8, 0, 1) ** 1.6)
VIG *= 1 - 0.35 * np.clip((yy - H * 0.55) / (H * 0.3), 0, 1) * np.clip((H * 0.85 - yy) / (H * 0.15) + 1, 0, 1)   # darker band behind captions
VIG *= 1 - 0.30 * np.clip((H * 0.14 - yy) / (H * 0.14), 0, 1)                                                    # top for header
VIG = VIG[..., None].astype(np.float32)
_rng = np.random.default_rng(11)
GRAIN = [np.repeat(np.repeat(_rng.normal(0, 4.5, (H // 2, W // 2, 1)).astype(np.float32), 2, 0), 2, 1) for _ in range(3)]

# ---------------- stroked text ----------------
@functools.lru_cache(maxsize=4096)
def stext(txt, fname, size, color=WHITE, stroke=0, track=0, shadow=True):
    f = E.font(fname, size); pad = 40 + stroke
    widths = [f.getlength(c) for c in txt] if track else None
    tw = int(sum(widths) + track * (len(txt) - 1)) if track else int(f.getlength(txt))
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (max(1, tw) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    def draw(d, fill, sw=0, sf=None):
        if track:
            x = pad
            for c, wc in zip(txt, widths): d.text((x, pad), c, font=f, fill=fill, stroke_width=sw, stroke_fill=sf); x += wc + track
        else: d.text((pad, pad), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=sf)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); draw(ImageDraw.Draw(sh), (0, 0, 0, 200), stroke, (0, 0, 0, 200))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(max(5, size // 8))))
    draw(ImageDraw.Draw(im), tuple(color) + (255,), stroke, (0, 0, 0, 255))
    arr = np.array(im); return arr
def tw(txt, fname, size, track=0): return E.text_w(txt, fname, size, track)
def put(layer, arr, x, y, a=1.0, anchor="lt", scale=1.0, pad=None):
    """like E.put but for stext padding"""
    if a <= 0.003: return
    im = arr
    if scale != 1.0:
        p = Image.fromarray(arr); im = np.array(p.resize((max(1, int(p.width * scale)), max(1, int(p.height * scale))), Image.BILINEAR))
    h, w = im.shape[:2]; pd = int((pad if pad is not None else 40) * scale); bw, bh = w - 2 * pd, h - 2 * pd
    if anchor[0] == "m": x -= bw / 2
    elif anchor[0] == "r": x -= bw
    if anchor[1] == "m": y -= bh / 2
    elif anchor[1] == "b": y -= bh
    x, y = int(round(x - pd)), int(round(y - pd))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    c = im[y0 - y:y1 - y, x0 - x:x1 - x].copy()
    if a < 1: c[..., 3] = (c[..., 3] * a).astype(np.uint8)
    layer.alpha_composite(Image.fromarray(c), (x0, y0))

def norm(w): return re.sub(r"[^a-z0-9']", "", w.lower())

# ============================================================ REEL SPECS
REELS = {
 1: dict(audio="r1.mp3", music="371", moff=30.0, part="PART 1", hook=("PRIVATE JETS. YACHTS.", "THEN IT FELL APART"),
         thumb_key="mallya_wef", pauses={"you.": 0.3, "times.": 0.2, "twist.": 0.4, "wrong?": 1.0}),
 2: dict(audio="r2.mp3", music="598", moff=60.0, part="PART 2", hook=("WHAT REALLY GROUNDED", "KINGFISHER AIRLINES?"),
         thumb_key="a330c", pauses={"airlines?": 0.2, "perfect.": 0.3, "problem.": 0.4, "flying.": 0.45, "wrong?": 1.0}),
 3: dict(audio="r3.mp3", music="678", moff=0.0, part="PART 3", hook=("HOW DID VIJAY MALLYA", "END UP IN THE UK?"),
         thumb_key="kfclosed", pauses={"begins.": 0.2, "court.": 0.3, "point?": 1.0}),
}
def CREDIT_FOR(key):
    c = E.CR_(key); return c

def shots_for(n, A):
    S, POP, HL = [], [], {}
    def img(t, key, z=(1.06, 1.18), px=(0, 0), py=(0, 0), g="warm", fit=False, flash=False, w=True, label=None):
        k = E.pick(key)
        if k is None: return
        S.append(dict(t0=t, kind="img", key=k, z=z, px=px, py=py, g=g, fit=fit, flash=flash, whoosh=w, label=label))
    def vid(t, num, off=0.0, slow=1.0, g="neutral", flash=False, w=True, dim=1.0, label=None):
        S.append(dict(t0=t, kind="vid", src=f"vid/{num}.mp4", off=off, slow=slow, g=g, flash=flash, whoosh=w, dim=dim, label=label))
    def pop(t, text, color=GOLD, size=170, y=760, sfx=True, sub=None, dur=1.6, font="pf9"):
        POP.append(dict(t=t, text=text, color=color, size=size, y=y, sfx=sfx, sub=sub, dur=dur, font=font))
    if n == 1:
        vid(0.0, 7138, off=2.0, g="teal", w=False)
        vid(A("luxury yachts", -0.1), 4446, off=1.0, g="warm")
        vid(A("expensive parties", -0.1), 51629, off=2.0, g="warm")
        vid(A("and an empire", -0.1), 47005, off=1.0, g="warm", dim=0.8)
        pop(A("thousands of crores", 0.0), "₹ THOUSANDS OF CRORES", GOLD, 84, 760, font="xb", dur=1.4)
        img(A("that's vijay", -0.1), "mallya_wef", z=(1.05, 1.15), px=(0.4, 0.42), py=(-0.3, -0.35), flash=True)
        pop(A("malia for you", 0.0), "VIJAY MALLYA", WHITE, 130, 760, sub="THE KING OF GOOD TIMES", dur=2.6)
        img(A("he built a massive", -0.1), "beerad", z=(1.0, 1.15), px=(0.0, 0.0), py=(-0.5, -0.55), label="KINGFISHER BEER")
        img(A("owned a formula", -0.1), "f1sing", z=(1.0, 1.1), px=(-0.3, 0.1), label="FORCE INDIA · F1")
        vid(A("was associated", -0.1), 12233, off=2.0, g="faded", label="RCB · IPL")
        img(A("and even launched", -0.1), "a330c", z=(1.0, 1.12), px=(0.1, 0.35), label="KINGFISHER AIRLINES")
        vid(A("but here's the twist", -0.1), 22387, off=14.0, g="cool", flash=True, dim=0.7)
        pop(A("the twist", 0.0), "THE TWIST...", RED, 130, 760, font="pf9", dur=1.3)
        img(A("the man who seemed", -0.1), "mallya_wef", g="bw", z=(1.15, 1.25), px=(0.4, 0.42), py=(-0.35, -0.4))
        img(A("eventually watched", -0.1), "kfclosed|kfcounter", g="faded", z=(1.0, 1.12), px=(0.2, -0.1), label="GOA AIRPORT · 2013")
        vid(A("faced massive debt", -0.1), 46820, off=4.0, g="cool")
        vid(A("and left india", -0.1), 26852, off=1.0, g="cool", label="LONDON, UK")
        img(A("how did things", -0.1), "mallya_wef", g="bw", z=(1.3, 1.45), px=(0.45, 0.45), py=(-0.4, -0.45), flash=True)
        HL.update({"jets": GOLD, "yachts": GOLD, "parties": GOLD, "crores": GOLD, "malia": GOLD, "king": GOLD, "good": GOLD, "times": GOLD,
                   "liquor": GOLD, "formula": GOLD, "ipl": GOLD, "glamorous": GOLD, "twist": RED, "collapse": RED, "debt": RED,
                   "uk": GOLD, "wrong": RED, "everything": GOLD})
    if n == 2:
        img(0.0, "a330", z=(1.0, 1.12), px=(0.3, -0.2), w=False)
        pop(A("kingfisher airlines", 0.0), "KINGFISHER", RED, 150, 760, sub="AIRLINES · 2005 – 2012", dur=1.8)
        img(A("it was one", -0.1), "a330c", z=(1.0, 1.12), px=(0.0, 0.35))
        vid(A("stylish interiors", -0.1), 40102, off=6.0, g="warm")
        img(A("great branding", -0.1), "a330b", z=(1.0, 1.1), px=(0, 0))
        vid(A("premium service", -0.1), 4065, off=4.0, g="warm")
        vid(A("everything looked", -0.1), 11303, off=2.0, g="warm")
        pop(A("perfect", 0.0), "PERFECT.", GOLD, 160, 760, dur=1.0)
        vid(A("but there was", -0.1), 7030, off=3.0, g="cool", flash=True, dim=0.6)
        pop(A("one big problem", 0.0), "ONE BIG PROBLEM", RED, 110, 760, dur=1.6)
        vid(A("running an airline", -0.1), 45702, off=2.0, g="cool")
        vid(A("kingfisher kept", -0.1), 3044, off=0.0, g="warm")
        img(A("acquired a stake", -0.1), "deccana320", z=(1.0, 1.1), px=(-0.4, 0.0), label="AIR DECCAN · 2007")
        vid(A("and struggled", -0.1), 49219, off=2.0, g="cool")
        img(A("by 2012", -0.1), "kfclosed|kfcounter", g="faded", z=(1.0, 1.12), px=(0.2, -0.1), flash=True)
        pop(A("2012", 0.0), "2012", WHITE, 230, 700, dur=1.2)
        pop(A("stopped flying", 0.0), "GROUNDED", RED, 150, 760, dur=1.6)
        vid(A("think about it", -0.1), 36351, off=1.0, g="cool")
        img(A("an airline that", -0.1), "a330c", g="bw", z=(1.0, 1.12), px=(0.0, 0.35))
        img(A("couldn't even", -0.1), "kfcounter|kfclosed", g="faded", z=(1.1, 1.0), px=(0.1, 0.0))
        vid(A("so what exactly", -0.1), 27496, off=10.0, g="cool", flash=True)
        HL.update({"kingfisher": RED, "airlines": RED, "glamorous": GOLD, "stylish": GOLD, "branding": GOLD, "premium": GOLD,
                   "perfect": GOLD, "problem": RED, "money": RED, "deccan": GOLD, "costs": RED, "pressure": RED, "2012": GOLD,
                   "stopped": RED, "flying": RED, "luxury": GOLD, "wrong": RED})
    if n == 3:
        vid(0.0, 47005, off=1.0, g="warm", w=False, dim=0.85)
        img(A("and then watching", -0.1), "kfclosed|kfcounter", g="faded", z=(1.0, 1.12), px=(0.2, -0.1))
        img(A("that's where", -0.1), "mallya_wef", z=(1.05, 1.15), px=(0.4, 0.42), py=(-0.3, -0.35), flash=True)
        pop(A("malia controversy", 0.0), "VIJAY MALLYA", WHITE, 130, 760, sub="THE CONTROVERSY", dur=2.0)
        img(A("after kingfisher", -0.1), "kfcounter|kfclosed", g="faded", z=(1.1, 1.0), px=(0.1, 0.0))
        vid(A("banks began", -0.1), 24604, off=0.0, g="cool")
        vid(A("indian investigating", -0.1), 47732, off=3.0, g="cool", label="ALLEGATIONS")
        img(A("which malia", -0.1), "mallya_goa2", z=(1.1, 1.2), px=(-0.3, -0.35), label="MALLYA DENIES WRONGDOING")
        vid(A("then in 2016", -0.1), 23146, off=8.0, g="cool", flash=True)
        pop(A("2016", 0.0), "2016", WHITE, 230, 700, dur=1.2)
        vid(A("he left india", -0.1), 26852, off=1.0, g="cool", label="LONDON, UK")
        vid(A("and in 2019", -0.1), 47686, off=2.0, g="cool", dim=0.6)
        pop(A("2019", 0.0), "2019", WHITE, 230, 600, dur=1.0)
        pop(A("fugitive economic", -0.05), "FUGITIVE ECONOMIC", RED, 80, 720, font="xb", sub="OFFENDER · DECLARED BY AN INDIAN COURT", dur=2.4)
        img(A("but how did", -0.1), "ubcity", z=(1.0, 1.15), px=(0.0, 0.0), label="UB CITY · BENGALURU")
        HL.update({"crores": GOLD, "collapse": RED, "malia": GOLD, "controversy": RED, "kingfisher": GOLD, "unpaid": RED, "loans": RED,
                   "alleged": RED, "wrongdoing": RED, "denied": GOLD, "2016": GOLD, "uk": GOLD, "united": GOLD, "kingdom": GOLD,
                   "2019": GOLD, "fugitive": RED, "offender": RED, "empires": GOLD})
    return S, POP, HL

# ============================================================ AUDIO
def load(path, ch=1, af=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    return a.reshape(-1, ch) if ch > 1 else a.copy()
def save(path, a):
    ch = 1 if a.ndim == 1 else a.shape[1]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", str(ch), "-i", "-", "-c:a", "pcm_s24le", path],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)

V0 = 0.12
def raw_words(n):
    T = json.load(open(RD + "/transcripts.json"))[str(n)]
    return [dict(w=w["w"].strip(), s=w["s"], e=w["e"]) for s in T for w in s["words"]]
def pause_plan(n):
    """[(cut_time_in_original, added_seconds)] — silence inserted at the quietest point after hook sentences"""
    ws = raw_words(n); P = REELS[n]["pauses"]; v = load(RD + "/" + REELS[n]["audio"]); out = []
    for i, w in enumerate(ws[:-1]):
        key = w["w"].lower()
        if key in P:
            t0, t1 = w["e"] - 0.05, max(ws[i + 1]["s"] + 0.05, w["e"] + 0.15); best, bt = 1e9, (t0 + t1) / 2
            for t in np.arange(t0, t1, 0.005):
                x = v[int(t * SR):int((t + 0.02) * SR)]
                if len(x) and np.mean(x ** 2) < best: best, bt = float(np.mean(x ** 2)), t
            out.append((bt, P[key]))
    return out
def words_for(n):
    plan = pause_plan(n)
    sh = lambda t: t + sum(p for c, p in plan if c <= t)
    return [dict(w=w["w"], s=round(sh(w["s"]) + V0, 3), e=round(sh(w["e"]) + V0, 3)) for w in raw_words(n)]
def anchor_fn(words):
    def A(phrase, d=0.0, edge="s", occ=0):
        toks = [norm(x) for x in phrase.split()]; seen = 0
        for i in range(len(words) - len(toks) + 1):
            if all(norm(words[i + j]["w"]) == toks[j] for j in range(len(toks))):
                if seen == occ: return (words[i]["s"] if edge == "s" else words[i + len(toks) - 1]["e"]) + d
                seen += 1
        raise KeyError(phrase)
    return A
def cta_start(words):
    for i, w in enumerate(words):
        if norm(w["w"]) == "watch" and i > len(words) * 0.6: return w["s"]
    raise KeyError("cta")

def build_audio(n):
    R = REELS[n]; words = words_for(n); A = anchor_fn(words)
    v0 = load(RD + "/" + R["audio"], af="loudnorm=I=-15:TP=-2:LRA=7")      # voice as recorded (levelled), hook pauses inserted
    pieces, prev = [], 0.0
    for c, p in pause_plan(n):
        pieces += [v0[int(prev * SR):int(c * SR)], np.zeros(int(p * SR), np.float32)]; prev = c
    pieces.append(v0[int(prev * SR):]); v = np.concatenate(pieces)
    total = V0 + len(v) / SR + 0.9
    N = int(total * SR); voice = np.zeros(N, np.float32); voice[int(V0 * SR):int(V0 * SR) + len(v)] = v
    S, POP, _ = shots_for(n, A)
    mus = load(f"music/{R['music']}.mp3", ch=2, af="loudnorm=I=-14:TP=-1.5")[int(R["moff"] * SR):]
    while len(mus) < N: mus = np.concatenate([mus, mus])
    mus = mus[:N].copy()
    env = np.convolve(np.abs(voice), np.ones(int(0.2 * SR)) / int(0.2 * SR), mode="same")
    env = np.clip(env / (np.percentile(env[env > 1e-4], 95) + 1e-9) * 1.2, 0, 1)
    g = db(-13) + (db(-19) - db(-13)) * env
    k = int(0.3 * SR); g[:k] *= np.linspace(0.3, 1, k)
    ko = int(0.8 * SR); g[-ko:] *= np.linspace(1, 0, ko)
    m = mus * g[:, None]
    def place(clip, t, gain):
        i = int(t * SR); clip = clip[:max(0, N - i)]; m[i:i + len(clip)] += clip * gain
    sfx = lambda name: load(f"sfx/{name}.mp3", ch=2)
    for s in S:
        if s.get("whoosh") and s["t0"] > 0.2: place(sfx("1489"), s["t0"] - 0.12, db(-17))
        if s.get("flash"): place(sfx("1143"), s["t0"], db(-14))
    for p in POP:
        if p["sfx"]: place(sfx("2782"), p["t"] - 0.02, db(-11))
    c0 = cta_start(words)
    place(sfx("788")[:int(2.25 * SR)] * np.linspace(0, 1, int(2.25 * SR))[:, None] ** 0.5, c0 - 2.1, db(-8))
    place(sfx("1714"), c0 - 0.9, db(-11))
    place(sfx("2782"), c0 - 0.02, db(-5))
    place(sfx("1143"), c0 - 0.02, db(-9))
    place(sfx("498"), c0 + 0.9, db(-14))
    mix = m + voice[:, None]
    save(OUT + f"/_r{n}.wav", mix)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", OUT + f"/_r{n}.wav", "-af", "loudnorm=I=-14:TP=-1.0:LRA=9",
                    "-ar", "48000", "-c:a", "pcm_s24le", OUT + f"/r{n}_mix.wav"], check=True)
    json.dump(dict(words=words, total=total, cta=c0), open(OUT + f"/r{n}_tl.json", "w"), indent=1)
    print(f"reel {n}: {total:.1f}s, {len(words)} words, cta @ {c0:.2f}")

# ============================================================ RENDER
class Reel:
    def __init__(self, n):
        self.n = n; self.R = REELS[n]; tl = json.load(open(OUT + f"/r{n}_tl.json"))
        self.words = tl["words"]; self.total = tl["total"]; self.cta = tl["cta"]
        A = anchor_fn(self.words)
        self.S, self.POP, self.HL = shots_for(n, A)
        self.S.append(dict(t0=self.cta, kind="cta", whoosh=False, flash=True))
        self.S.sort(key=lambda s: s["t0"])
        for i, s in enumerate(self.S): s["t1"] = self.S[i + 1]["t0"] if i + 1 < len(self.S) else self.total
        self.vids = {}; self.caps = self.build_caps()
        self.link_t = A("subscribe")
    # ---- captions: 1–3 word groups, karaoke pop
    def build_caps(self):
        caps, cur = [], []
        words = [w for w in self.words if w["s"] < self.cta - 0.05]
        for i, w in enumerate(words):
            cur.append(w); end = bool(re.search(r"[.?!,]$", w["w"]))
            width = sum(tw(x["w"].upper(), "xb", 92) for x in cur) + 25 * len(cur)
            nxt = words[i + 1] if i + 1 < len(words) else None
            if end or len(cur) >= 3 or width > 760 or (nxt and nxt["s"] - w["e"] > 0.35):
                caps.append(cur); cur = []
        if cur: caps.append(cur)
        out = []
        for i, c in enumerate(caps):
            t1 = min(c[-1]["e"] + 0.25, caps[i + 1][0]["s"] - 0.02) if i + 1 < len(caps) else min(c[-1]["e"] + 0.3, self.cta - 0.05)
            out.append(dict(items=c, t0=c[0]["s"] - 0.05, t1=t1))
        return out
    def disp(self, w):
        t = w.upper().replace("MALIA", "MALLYA").replace("SHUTDOWN", "SHUT DOWN")
        return re.sub(r"[.,?!]+$", "", t) if not t.endswith("?") else t
    def draw_caps(self, layer, t):
        for c in self.caps:
            if not (c["t0"] <= t <= c["t1"]): continue
            if any(p["t"] - 0.1 <= t <= p["t"] + p["dur"] and p["y"] > 650 and p["y"] < 1000 for p in self.POP): y = 1330
            else: y = 1180
            gin = eback((t - c["t0"]) / 0.22); out = clamp((c["t1"] - t) / 0.1)
            toks = [self.disp(w["w"]) for w in c["items"]]
            fs = 92
            while sum(tw(x_, "xb", fs) for x_ in toks) + 40 * (len(toks) - 1) > W - 120: fs -= 4
            ws = [tw(x_, "xb", fs) + 14 for x_ in toks]; sp = 40
            x = W / 2 - (sum(ws) + sp * (len(ws) - 1)) / 2
            for w, txt, wd in zip(c["items"], toks, ws):
                active = w["s"] - 0.03 <= t
                hl = self.HL.get(norm(w["w"]))
                col = (hl or WHITE) if active else (230, 230, 230)
                sc = (1.0 + 0.07 * math.sin(math.pi * clamp((t - w["s"] + 0.03) / 0.22))) * clamp(gin, 0, 1.2)
                a = (1.0 if active else 0.55) * out
                put(layer, stext(txt, "xb", fs, col, stroke=6), x + wd / 2, y, a, "mm", scale=max(0.05, sc), pad=46)
                x += wd + sp
    # ---- shots
    def vid(self, key, src, off, slow, g):
        if key not in self.vids: self.vids[key] = E.Vid(src, off, slow, g)
        return self.vids[key]
    def render_shot(self, s, t):
        lt = t - s["t0"]; dur = max(s["t1"] - s["t0"], 0.01); p = clamp(lt / dur); k = s["kind"]
        punch = 1.0 + 0.06 * (1 - eo(lt / 0.3))           # zoom punch on every cut
        if k == "vid":
            fr = self.vid(id(s), s["src"], s["off"], s["slow"], s["g"]).frame(int(lt * FPS)).astype(np.float32) * s.get("dim", 1.0)
            if punch > 1.001:
                im = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)); fr = np.array(E.kb_crop(im, punch, 0, 0, (W, H))).astype(np.float32)
            return fr
        if k == "img":
            z = (s["z"][0] + (s["z"][1] - s["z"][0]) * eio(p) * 0.6 + (s["z"][1] - s["z"][0]) * p * 0.4) * punch
            px = s["px"][0] + (s["px"][1] - s["px"][0]) * p; py = s["py"][0] + (s["py"][1] - s["py"][0]) * p
            if s["fit"]:
                bg = E.kb_crop(E.blurred_bg(s["key"], s["g"], 0.4), 1.0 + 0.04 * p, 0, 0, (W, H))
                src = E.graded(s["key"], s["g"]); fw = int(W * 1.0 * z); fh = int(src.height * fw / src.width)
                fg = src.resize((fw, fh), Image.BILINEAR)
                m = E.feather_mask(fw, fh, 40)
                bg.paste(fg, (int(W / 2 - fw / 2), int(780 - fh / 2)), m)
                return np.array(bg).astype(np.float32)
            return np.array(E.kb_crop(E.graded(s["key"], s["g"]), z, px, py, (W, H))).astype(np.float32)
        if k == "stack": return self.render_stack(s, t, lt)
        if k == "vsplit": return self.render_vsplit(s, t, lt)
        if k == "cta": return self.render_cta(s, t, lt)
    def render_stack(self, s, t, lt):
        base = Image.fromarray(np.clip(E.RADIAL[:1, :1] * 0 + 10, 0, 255).astype(np.uint8)).resize((W, H)).convert("RGBA")
        bg = E.kb_crop(E.blurred_bg("keynote07", "warm", 0.3), 1.02, 0, 0, (W, H)).convert("RGBA"); base = bg
        ph = 330; pw = 860
        for i, (key, lab, ts) in enumerate(s["items"]):
            k = eback((t - ts + 0.1) / 0.4) if t >= ts - 0.1 else 0
            if k <= 0: continue
            cy = (440, 820, 1520)[i]; cx = W / 2 + 120 * (1 - clamp(k)) * (1 if i % 2 else -1)
            im = E.kb_crop(E.graded(key, "neutral"), 1.05 + 0.05 * clamp((t - ts) / 3), 0, 0, (pw, ph)).convert("RGBA")
            fr = Image.new("RGBA", (pw + 8, ph + 8), (255, 255, 255, 240)); fr.paste(im, (4, 4))
            a = np.array(fr); a[..., 3] = (a[..., 3] * clamp(k)).astype(np.uint8)
            base.alpha_composite(Image.fromarray(a), (int(cx - pw / 2 - 4), int(cy - ph / 2 - 4)))
            put(base, stext(lab, "xb", 64, BLACK, shadow=False), cx - pw / 2 + 40, cy + ph / 2 - 30, clamp(k), "lb", pad=40) if False else None
            bx0, by0 = int(cx - pw / 2 + 24), int(cy + ph / 2 - 104)
            d = ImageDraw.Draw(base); lw = tw(lab, "xb", 58) + 48
            d.rounded_rectangle([bx0, by0, bx0 + lw, by0 + 80], radius=14, fill=GOLD + (int(255 * clamp(k)),))
            put(base, stext(lab, "xb", 58, BLACK, shadow=False), bx0 + lw / 2, by0 + 40, clamp(k), "mm", pad=40)
        return np.array(base.convert("RGB")).astype(np.float32)
    def render_vsplit(self, s, t, lt):
        base = Image.new("RGBA", (W, H), (8, 8, 10, 255))
        for i, (key, lab, ts) in enumerate(s["items"]):
            k = eo((t - ts + 0.15) / 0.4)
            if k <= 0: continue
            im = E.kb_crop(E.graded(key, "warm"), 1.05 + 0.04 * clamp((t - ts) / 3), 0, -0.3 if key == "mac1984" else 0, (W, H // 2 - 4)).convert("RGBA")
            a = np.array(im); a[..., 3] = int(255 * k)
            base.alpha_composite(Image.fromarray(a), (int(-80 * (1 - k)) if i == 0 else int(80 * (1 - k)), 0 if i == 0 else H // 2 + 4))
            ly = 300 if i == 0 else H - 260
            put(base, stext(lab, "pf9", 120, GOLD if i else WHITE, stroke=0), W / 2, ly, k, "mm")
        d = ImageDraw.Draw(base); d.rectangle([0, H // 2 - 4, W, H // 2 + 4], fill=GOLD + (255,))
        return np.array(base.convert("RGB")).astype(np.float32)
    def render_cta(self, s, t, lt):
        bg = np.array(E.kb_crop(E.blurred_bg(self.R["thumb_key"], "warm", 0.28), 1.0 + 0.02 * lt, 0, 0, (W, H))).astype(np.float32)
        pr = self.vid(("p", 1), "vid/14154.mp4", 2.0, 1.0, "warm").frame(int(lt * FPS)).astype(np.float32)
        fr = 255 - (255 - bg) * (255 - pr * 0.35) / 255
        base = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
        put(base, stext("WATCH THE FULL STORY", "xb", 66, WHITE, stroke=4), W / 2, 520, eo(lt / 0.35), "mm", scale=0.9 + 0.1 * eo(lt / 0.35))
        lk = eback((lt - 0.55) / 0.5) if lt > 0.55 else 0
        if lk > 0:
            put(base, stext("FOUNDER", "pf9", 150, WHITE), W / 2, 760, clamp(lk), "mm", scale=max(0.05, clamp(lk, 0, 1.15)))
            put(base, stext("FILES", "pf9", 150, GOLD), W / 2, 910, clamp(lk), "mm", scale=max(0.05, clamp(lk, 0, 1.15)))
        bk = eback((lt - 1.1) / 0.45) if lt > 1.1 else 0
        if bk > 0:
            d = ImageDraw.Draw(base); bw, bh = 560 * clamp(bk, 0, 1.1), 130 * clamp(bk, 0, 1.1); cy = 1130
            pulse = 1 + 0.03 * math.sin(lt * 7)
            bw *= pulse; bh *= pulse
            d.rounded_rectangle([W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2], radius=bh / 2, fill=GOLD + (255,))
            put(base, stext("WATCH NOW", "xb", 60, BLACK, shadow=False), W / 2, cy + 2, clamp(bk), "mm", scale=max(0.05, clamp(bk, 0, 1.1) * pulse))
        if t >= self.link_t - 0.1:
            k = eback((t - self.link_t + 0.1) / 0.4); bob = 12 * math.sin((t - self.link_t) * 8)
            d = ImageDraw.Draw(base); clicked = t >= self.link_t + 0.55; cy = 1360; bw, bh = 520 * clamp(k, 0, 1.1), 120 * clamp(k, 0, 1.1)
            d.rounded_rectangle([W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2], radius=bh / 2, fill=((70, 70, 74) if clicked else (229, 33, 23)) + (255,))
            put(base, stext("SUBSCRIBED" if clicked else "SUBSCRIBE", "xb", 56, WHITE, shadow=False), W / 2, cy + 2, clamp(k), "mm", scale=max(0.05, clamp(k, 0, 1.1)))
            put(base, stext("FOUNDER FILES", "b", 34, WHITE, track=6), W / 2, cy + 110, clamp(k), "mm")
        return np.array(base.convert("RGB")).astype(np.float32)
    # ---- overlays
    def overlays(self, layer, t):
        d = ImageDraw.Draw(layer)
        # progress bar
        d.rectangle([0, 0, W, 12], fill=(255, 255, 255, 60)); d.rectangle([0, 0, int(W * t / self.total), 12], fill=GOLD + (255,))
        # series pill
        pill = f"VIJAY MALLYA  ·  {self.R['part']}"
        pw = tw(pill, "b", 30, 4) + 56
        d.rounded_rectangle([W / 2 - pw / 2, 70, W / 2 + pw / 2, 126], radius=28, fill=(0, 0, 0, 150), outline=GOLD + (200,), width=2)
        put(layer, stext(pill, "b", 30, WHITE, track=4, shadow=False), W / 2, 98, 1, "mm")
        # hook header (first seconds)
        h1, h2 = self.R["hook"]; hv = win(t, 0.05, 3.4, 0.01, 0.3)
        if hv > 0:
            k1 = eback(t / 0.35); k2 = eback((t - 0.18) / 0.35)
            fs1 = 92
            while tw(h1, "xb", fs1) > W - 170: fs1 -= 4
            w1 = tw(h1, "xb", fs1) + 60
            d.rounded_rectangle([W / 2 - w1 / 2 * clamp(k1), 230, W / 2 + w1 / 2 * clamp(k1), 350], radius=18, fill=GOLD + (int(255 * hv),))
            put(layer, stext(h1, "xb", fs1, BLACK, shadow=False), W / 2, 292, hv * clamp(k1), "mm", scale=max(0.05, clamp(k1, 0, 1.1)))
            fs2 = 100
            while tw(h2, "xb", fs2) > W - 120: fs2 -= 4
            put(layer, stext(h2, "xb", fs2, WHITE, stroke=6), W / 2, 430, hv * clamp(k2), "mm", scale=max(0.05, clamp(k2, 0, 1.1)))
        # labels + credits for current shot
        cur = self.cur
        if cur.get("label"):
            lk = eo((t - cur["t0"] - 0.15) / 0.3) * clamp((cur["t1"] - t) / 0.15)
            lab = cur["label"]; lw = tw(lab, "b", 34, 5) + 50; y0 = 1560
            d.rounded_rectangle([60, y0, 60 + lw * lk, y0 + 64], radius=10, fill=(0, 0, 0, int(170 * lk)))
            d.rectangle([60, y0, 66, y0 + 64], fill=GOLD + (int(255 * lk),))
            put(layer, stext(lab, "b", 34, WHITE, track=5, shadow=False), 88, y0 + 32, lk, "lm")
        key = cur.get("key")
        cr = CREDIT_FOR(key) if key else None
        if cr: put(layer, stext(cr.replace("Photo: ", "").replace(" · Wikimedia Commons", ""), "r", 20, (235, 235, 235), shadow=True),
                   W - 40, 170, 0.8 * clamp((t - cur["t0"]) / 0.3), "rm", pad=40)
        # pops
        for p in self.POP:
            if not (p["t"] - 0.05 <= t <= p["t"] + p["dur"]): continue
            k = eback((t - p["t"]) / 0.35); v = clamp((p["t"] + p["dur"] - t) / 0.2)
            put(layer, stext(p["text"], p["font"], p["size"], p["color"], stroke=0 if p["font"].startswith("pf") else 6), W / 2, p["y"],
                v * clamp(k * 1.5), "mm", scale=max(0.05, 0.7 + 0.3 * clamp(k, 0, 1.2)))
            if p["sub"]:
                fss = 40
                while tw(p["sub"], "b", fss, 6) > W - 120: fss -= 2
                put(layer, stext(p["sub"], "b", fss, WHITE, track=6), W / 2, p["y"] + p["size"] * 0.75, v * eo((t - p["t"] - 0.25) / 0.3), "mm")
        self.draw_caps(layer, t)
    def frame(self, t, fi):
        idx = max(i for i, s in enumerate(self.S) if s["t0"] <= t + 1e-9); self.cur = self.S[idx]
        fr = self.render_shot(self.cur, t)
        fr = fr * VIG + GRAIN[fi % 3]
        if self.cur.get("flash") and t - self.cur["t0"] < 0.3:
            f = 1 - eo((t - self.cur["t0"]) / 0.3); fr = fr * (1 - f) + 255 * f
        fr *= clamp(t / 0.15) if t < 0.15 else 1
        base = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
        self.overlays(base, t)
        return base.convert("RGB")

@functools.lru_cache(None)
def logo_img():
    im = Image.open("img/ff_logo.png").convert("RGBA")
    return im.resize((int(im.width * 1.0), int(im.height * 1.0)))

if __name__ == "__main__":
    cmd, n = sys.argv[1], int(sys.argv[2])
    if cmd == "audio": build_audio(n)
    elif cmd == "still":
        r = Reel(n)
        for ts in sys.argv[3:]:
            t = float(ts); r.frame(t, 0).save(f"{OUT}/r{n}_{t:05.2f}.jpg", quality=88)
            for v in r.vids.values(): v.close()
            r.vids.clear()
    elif cmd == "render":
        r = Reel(n); N = int(r.total * FPS)
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-i", f"{OUT}/r{n}_mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
                                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                                f"{OUT}/reel{n}.mp4"], stdin=subprocess.PIPE)
        for fi in range(N):
            enc.stdin.write(r.frame(fi / FPS, fi).tobytes())
            if fi % 150 == 0: print(f"reel {n}: {fi/FPS:5.1f}/{r.total:.1f}", flush=True)
        enc.stdin.close(); enc.wait()
