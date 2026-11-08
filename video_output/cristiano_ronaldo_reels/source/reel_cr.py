"""Founder File — vertical Cristiano Ronaldo reels (1080x1920).
python3 reel.py audio N          build reels/out/rN_mix.wav + rN_words.json
python3 reel.py still N t [t..]  stills
python3 reel.py render N         reels/out/reelN.mp4 (with audio)
"""
import sys, os, json, math, re, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import engine as E                     # reuse fonts, grading, Ken Burns, video reader, text helpers
E.FD = E.FD

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
 1: dict(audio="r1.mp3", music="676", moff=1.0, part="PART 1", hook=("LEFT HOME", "AT JUST 12?!"), thumb_key="hero16"),
 2: dict(audio="r2.mp3", music="51", moff=0.0, part="PART 2", hook=("18 YEARS OLD AT", "MAN UNITED?!"), thumb_key="mu2009"),
 3: dict(audio="r3.mp3", music="78", moff=1.0, part="PART 3", hook=("HOW CR7 BECAME", "A GLOBAL BRAND"), thumb_key="museucr7"),
}
CREDIT = {k: E.CRED(k) for k in E.MEDIA}
TH, GO = "v_thanks", "v_goals"

def shots_for(n, A):
    S, POP, HL = [], [], {}
    def img(t, key, z=(1.06, 1.18), px=(0, 0), py=(0, 0), g="neutral", fit=False, flash=False, w=True, label=None):
        S.append(dict(t0=t, kind="img", key=key, z=z, px=px, py=py, g=g, fit=fit, flash=flash, whoosh=w, label=label))
    def vid(t, key, off=0.0, slow=1.0, g="neutral", flash=False, w=True, dim=1.0, fit=False, label=None):
        S.append(dict(t0=t, kind="vidfit" if fit else "vid", key=key, src=f"vid/{key}.webm", off=off, slow=slow, g=g, flash=flash,
                      whoosh=w, dim=dim, label=label))
    def pop(t, text, color=GOLD, size=170, y=760, sfx=True, sub=None, dur=1.6, font="bb"):
        POP.append(dict(t=t, text=text, color=color, size=size, y=y, sfx=sfx, sub=sub, dur=dur, font=font))
    if n == 1:
        img(0.0, "trapiche", g="faded", z=(1.15, 1.3), px=(0.2, 0), w=False)
        vid(A("just to chase", -0.1), "v_takeoff", off=118.0, g="teal")
        img(A("that's exactly", -0.1), "euro16", z=(1.05, 1.2), py=(-0.4, -0.3), flash=True)
        pop(A("cristiano ronaldo"), "CRISTIANO RONALDO", WHITE, 150, 700, sub="FROM MADEIRA TO THE WORLD", dur=1.8)
        vid(A("he was born", -0.1), "v_statue", off=9.0, slow=1.1, g="warm", label="FUNCHAL · MADEIRA")
        img(A("in a family", -0.1), "laranjal", g="faded", z=(1.1, 1.25), px=(-0.4, 0.4))
        vid(A("but he had one", -0.1), TH, off=303.0, slow=1.2, dim=0.85)
        pop(A("one big dream"), "ONE BIG DREAM", GOLD, 150, 760)
        vid(A("becoming a professional", -0.1), "v_train", off=36.0, g="warm", fit=True)
        img(A("he moved", -0.1), "lisbon", g="warm", z=(1.05, 1.2), px=(-0.5, 0.5), label="LISBON", flash=True)
        pop(A("at just 12", 0.0), "AGE 12", GOLD, 240, 720)
        img(A("to join", -0.1), "alvalade", z=(1.0, 1.15), px=(0.3, -0.3), label="SPORTING CP")
        img(A("leaving his family", -0.1), "sp28", z=(1.0, 1.12))
        img(A("life wasn't easy", -0.1), "mu2008", g="bw", z=(1.05, 1.18), px=(0.4, 0.4))
        vid(A("but he refused", -0.1), TH, off=104.5, slow=1.15)
        pop(A("refused to give up", 0.1), "NEVER GIVE UP", WHITE, 150, 760, dur=1.4)
        vid(A("and that little boy", -0.1), TH, off=346.0, flash=True)
        img(A("one of the greatest", -0.1), "ballons", z=(1.0, 1.15), flash=True)
        pop(A("greatest footballers"), "5× BALLON D'OR", GOLD, 150, 760, sub="ONE OF THE GREATEST EVER", dur=1.8)
        HL.update({"12": GOLD, "football": GOLD, "ronaldo": GOLD, "cristiano": GOLD, "island": GOLD, "dream": GOLD, "lisbon": GOLD,
                   "sporting": GOLD, "cp": GOLD, "refused": RED, "money": RED, "easy": RED, "greatest": GOLD, "history": GOLD, "professional": GOLD})
    if n == 2:
        img(0.0, "mu2006", z=(1.1, 1.25), py=(-0.4, -0.3), w=False)
        img(A("and suddenly", -0.1), "oldtraf", z=(1.05, 1.2), px=(-0.3, 0.3), flash=True, label="OLD TRAFFORD")
        img(A("that's what happened", -0.1), "mushev", z=(1.05, 1.2), px=(-0.3, -0.3))
        img(A("he joined united", -0.1), "muchelsea", z=(1.05, 1.15), py=(-0.3, -0.3))
        pop(A("2003"), "2003", WHITE, 240, 720)
        img(A("wearing", -0.1), "mu2009", z=(1.2, 1.4), px=(0.35, 0.35), py=(0.0, -0.1), flash=True)
        pop(A("number"), "No. 7", GOLD, 280, 720, sub="THE LEGENDARY SHIRT", dur=2.0)
        img(A("initially", -0.1), "muscores", z=(1.05, 1.18), py=(-0.4, -0.3))
        img(A("but under", -0.1), "ferguson", z=(1.0, 1.12), py=(-0.3, -0.3), label="SIR ALEX FERGUSON")
        vid(A("he transformed", -0.1), GO, off=106.0, fit=True)
        pop(A("machine", -0.4), "GOAL MACHINE", GOLD, 160, 1500, dur=1.6)
        img(A("then came", -0.1), "bernabeu", z=(1.05, 1.2), flash=True, label="SANTIAGO BERNABÉU")
        pop(A("2009"), "2009", WHITE, 240, 720)
        vid(A("real madrid signed", -0.1), TH, off=8.5)
        pop(A("94 million"), "€94 MILLION", GOLD, 170, 760, sub="WORLD-RECORD TRANSFER", dur=1.8)
        vid(A("and what happened", -0.1), TH, off=326.5, fit=True, label="BICYCLE KICK · 2018")
        vid(A("451", -0.1), GO, off=170.0, flash=True, dim=0.6)
        pop(A("451"), "451 GOALS", GOLD, 190, 700, sub="IN 438 APPEARANCES", dur=2.2)
        vid(A("that's absolutely", -0.1), TH, off=230.0)
        pop(A("crazy"), "CRAZY!", RED, 200, 760, dur=1.0)
        HL.update({"18": GOLD, "manchester": GOLD, "united": GOLD, "ronaldo": GOLD, "cristiano": GOLD, "2003": GOLD, "number": GOLD,
                   "7": GOLD, "legendary": GOLD, "ferguson": GOLD, "machine": GOLD, "2009": GOLD, "real": GOLD, "madrid": GOLD,
                   "94": GOLD, "451": GOLD, "438": GOLD, "crazy": RED})
    if n == 3:
        vid(0.0, TH, off=221.5, w=False)
        img(A("even after", -0.1), "ballons", z=(1.0, 1.15), flash=True)
        vid(A("he still wanted", -0.1), "v_train", off=21.0, g="warm", fit=True)
        img(A("his success", -0.1), "por25b", z=(1.1, 1.25), py=(-0.3, -0.3))
        vid(A("it was about", -0.1), "v_train", off=3.0, g="warm", flash=True)
        pop(A("discipline"), "DISCIPLINE", GOLD, 190, 760, dur=1.4)
        vid(A("training and", -0.1), "v_train", off=45.0, g="warm", fit=True)
        img(A("from manchester", -0.1), "mu2008", z=(1.05, 1.18), label="MANCHESTER UNITED")
        img(A("to real madrid", -0.1), "rm2010", z=(1.05, 1.2), label="REAL MADRID")
        img(A("juventus", -0.1), "juve19", z=(1.0, 1.1), py=(-0.4, -0.4), label="JUVENTUS")
        img(A("and al", -0.1), "nassr40", z=(1.05, 1.2), label="AL NASSR")
        img(A("he kept proving", -0.1), "nassr44", z=(1.05, 1.15), px=(-0.45, -0.45))
        pop(A("different leagues"), "4 LEAGUES", GOLD, 180, 760, sub="ENGLAND · SPAIN · ITALY · SAUDI ARABIA", dur=1.8)
        img(A("and he didn't stop", -0.1), "museucr7", z=(1.1, 1.3), px=(0.3, 0.3), flash=True, label="MUSEU CR7")
        img(A("he turned his name", -0.1), "hotelf", z=(1.05, 1.2), px=(-0.3, 0.3))
        pop(A("global brand"), "CR7", GOLD, 300, 720, sub="A GLOBAL BRAND", dur=1.8)
        img(A("fragrances", -0.1), "hotelm", z=(1.0, 1.12), label="PESTANA CR7 HOTEL")
        vid(A("that's the power", -0.1), TH, off=278.0, flash=True, dim=0.7)
        pop(A("personal brand"), "PERSONAL BRAND", WHITE, 150, 760, dur=1.6)
        HL.update({"crazy": RED, "ronaldo": GOLD, "cristiano": GOLD, "better": GOLD, "talent": GOLD, "discipline": GOLD,
                   "training": GOLD, "manchester": GOLD, "united": GOLD, "real": GOLD, "madrid": GOLD, "juventus": GOLD, "nasser": GOLD,
                   "brand": GOLD, "cr7": GOLD, "power": GOLD, "personal": GOLD})
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
def words_for(n):
    T = json.load(open(RD + "/transcripts.json"))[str(n)]
    return [dict(w=w["w"].strip(), s=round(w["s"] + V0, 3), e=round(w["e"] + V0, 3)) for s in T for w in s["words"]]
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
        if norm(w["w"]) in ("want", "how") and i > len(words) * 0.6: return w["s"]
    raise KeyError("cta")

def build_audio(n):
    R = REELS[n]; words = words_for(n); A = anchor_fn(words)
    v = load(RD + "/" + R["audio"], af="loudnorm=I=-15:TP=-2:LRA=7")       # voice exactly as recorded (levelled only)
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
        if s.get("whoosh") and s["t0"] > 0.2: place(sfx("1491"), s["t0"] - 0.12, db(-17))
        if s.get("flash"): place(sfx("1143"), s["t0"], db(-14))
    for p in POP:
        if p["sfx"]: place(sfx("2782"), p["t"] - 0.02, db(-11))
    c0 = cta_start(words)
    place(sfx("788")[:int(2.25 * SR)] * np.linspace(0, 1, int(2.25 * SR))[:, None] ** 0.5, c0 - 2.1, db(-12))
    place(sfx("1143"), c0 - 0.02, db(-10))
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
        t = w.upper().replace("NASSER", "NASSR")
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
    def vid(self, key, src, off, slow, g, fit=False):
        if key not in self.vids:
            if fit:
                E.W, E.H = 1280, 720; v = E.Vid(src, off, slow, g); E.W, E.H = W, H
                self.vids[key] = v
            else: self.vids[key] = E.Vid(src, off, slow, g)
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
        if k == "vidfit":
            v = self.vid(("f", id(s)), s["src"], s["off"], s["slow"], s["g"], fit=True)
            fr = v.frame(int(lt * FPS)); im = Image.fromarray(fr)
            small = im.resize((96, 54), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
            bg = E.kb_crop(small.resize((960, 540), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)), 1.0, 0, 0, (W, H))
            bg = Image.fromarray((np.array(bg).astype(np.float32) * 0.5).astype(np.uint8))
            fw = int(W * 1.12 * punch); fh = int(fw * 9 / 16); fg = im.resize((fw, fh), Image.BILINEAR)
            bg.paste(fg, (int(W / 2 - fw / 2), int(860 - fh / 2)))
            ImageDraw.Draw(bg).rectangle([0, int(860 - fh / 2) - 4, W, int(860 - fh / 2) - 1], fill=GOLD)
            ImageDraw.Draw(bg).rectangle([0, int(860 + fh / 2), W, int(860 + fh / 2) + 3], fill=GOLD)
            return np.array(bg).astype(np.float32) * s.get("dim", 1.0)
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
        fr = bg
        base = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
        put(base, stext("FULL RONALDO STORY", "bb", 110, WHITE, stroke=4), W / 2, 520, eo(lt / 0.35), "mm", scale=0.9 + 0.1 * eo(lt / 0.35))
        lk = eback((lt - 0.55) / 0.5) if lt > 0.55 else 0
        if lk > 0:
            logo = logo_img(); sc = 0.62 * clamp(lk, 0, 1.15)
            lg = logo.resize((max(1, int(logo.width * sc)), max(1, int(logo.height * sc))), Image.BILINEAR)
            base.alpha_composite(lg, (int(W / 2 - lg.width / 2), int(820 - lg.height / 2)))
        bk = eback((lt - 1.1) / 0.45) if lt > 1.1 else 0
        if bk > 0:
            d = ImageDraw.Draw(base); bw, bh = 560 * clamp(bk, 0, 1.1), 130 * clamp(bk, 0, 1.1); cy = 1130
            pulse = 1 + 0.03 * math.sin(lt * 7)
            bw *= pulse; bh *= pulse
            d.rounded_rectangle([W / 2 - bw / 2, cy - bh / 2, W / 2 + bw / 2, cy + bh / 2], radius=bh / 2, fill=GOLD + (255,))
            put(base, stext("WATCH NOW", "xb", 60, BLACK, shadow=False), W / 2, cy + 2, clamp(bk), "mm", scale=max(0.05, clamp(bk, 0, 1.1) * pulse))
        if t >= self.link_t - 0.1:
            k = eback((t - self.link_t + 0.1) / 0.4); bob = 12 * math.sin((t - self.link_t) * 8)
            d = ImageDraw.Draw(base); sw, sh_ = 600 * clamp(k, 0, 1.1), 120 * clamp(k, 0, 1.1); cy2 = 1400 + bob * 0.3
            d.rounded_rectangle([W / 2 - sw / 2, cy2 - sh_ / 2, W / 2 + sw / 2, cy2 + sh_ / 2], radius=sh_ / 2, fill=(229, 33, 23, 255))
            put(base, stext("SUBSCRIBE", "xb", 60, WHITE, shadow=False), W / 2, cy2 + 2, clamp(k), "mm", scale=max(0.05, clamp(k, 0, 1.1)))
            put(base, stext("FOUNDER FILES", "xb", 40, WHITE, stroke=3, track=6), W / 2, 1530, clamp(k), "mm")
        return np.array(base.convert("RGB")).astype(np.float32)
    # ---- overlays
    def overlays(self, layer, t):
        d = ImageDraw.Draw(layer)
        # progress bar
        d.rectangle([0, 0, W, 12], fill=(255, 255, 255, 60)); d.rectangle([0, 0, int(W * t / self.total), 12], fill=GOLD + (255,))
        # series pill
        pill = f"CRISTIANO RONALDO  ·  {self.R['part']}"
        pw = tw(pill, "b", 30, 4) + 56
        d.rounded_rectangle([W / 2 - pw / 2, 70, W / 2 + pw / 2, 126], radius=28, fill=(0, 0, 0, 150), outline=GOLD + (200,), width=2)
        put(layer, stext(pill, "b", 30, WHITE, track=4, shadow=False), W / 2, 98, 1, "mm")
        # hook header (first seconds)
        h1, h2 = self.R["hook"]; hv = win(t, 0.05, 3.4, 0.01, 0.3)
        if hv > 0:
            k1 = eback(t / 0.35); k2 = eback((t - 0.18) / 0.35)
            w1 = tw(h1, "xb", 92) + 60
            d.rounded_rectangle([W / 2 - w1 / 2 * clamp(k1), 230, W / 2 + w1 / 2 * clamp(k1), 350], radius=18, fill=GOLD + (int(255 * hv),))
            put(layer, stext(h1, "xb", 92, BLACK, shadow=False), W / 2, 292, hv * clamp(k1), "mm", scale=max(0.05, clamp(k1, 0, 1.1)))
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
        cr = CREDIT.get(key) if key else None
        if cr: cr = cr.replace("Video: ", "")
        if cr: put(layer, stext(cr.replace("Photo: ", "").replace(" · Wikimedia Commons", ""), "r", 20, (235, 235, 235), shadow=True),
                   W - 40, 170, 0.8 * clamp((t - cur["t0"]) / 0.3), "rm", pad=40)
        # pops
        for p in self.POP:
            if not (p["t"] - 0.05 <= t <= p["t"] + p["dur"]): continue
            k = eback((t - p["t"]) / 0.35); v = clamp((p["t"] + p["dur"] - t) / 0.2)
            put(layer, stext(p["text"], p["font"], p["size"], p["color"], stroke=0 if p["font"].startswith("pf") else 6), W / 2, p["y"],
                v * clamp(k * 1.5), "mm", scale=max(0.05, 0.7 + 0.3 * clamp(k, 0, 1.2)))
            if p["sub"]:
                put(layer, stext(p["sub"], "b", 40, WHITE, track=6), W / 2, p["y"] + p["size"] * 0.75, v * eo((t - p["t"] - 0.25) / 0.3), "mm")
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
