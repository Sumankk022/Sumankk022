"""Full-length audio: 8 narration clips -> re-timed (~134 wpm, pitch preserved),
hook pauses, chapter cards with stings, per-chapter music beds with ducking,
riser+impact musical transition before the final CTA, end-card music.
Writes out/mix.wav, out/voice.wav, out/timeline.json
"""
import json, subprocess, os, re
import numpy as np

SR = 48000
TARGET_WPM = 134
CARD = 3.6            # chapter card length (music only)
END_CARD = 12.0
IDENT_LEN = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "vid/intro.mp4"], capture_output=True, text=True).stdout)       # room for YouTube end-screen elements
os.makedirs("out", exist_ok=True)
db = lambda x: 10 ** (x / 20)

def load(path, ch=1, af=None, sr=SR):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    return a.reshape(-1, ch) if ch > 1 else a.copy()

def save(path, a):
    ch = 1 if a.ndim == 1 else a.shape[1]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", str(ch), "-i", "-",
                    "-c:a", "pcm_s24le", path], input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)

T = json.load(open("transcripts.json"))
VOICE_FX = ("highpass=f=75,equalizer=f=220:t=q:w=1.2:g=-1.5,equalizer=f=3200:t=q:w=1.0:g=2.5,"
            "equalizer=f=9000:t=h:w=0.7:g=1.5,acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2")

# extra pauses after specific hook lines (matched on sentence text, lowercase substring)
HOOKS = {
    2: {"perfect.": 0.6, "unusual choice.": 0.55, "want to use.": 0.3},
    3: {"more accessible.": 0.6, "apple two.": 0.45, "serious company.": 0.6, "brought pressure.": 0.6, "created conflict.": 0.4},
    4: {"growing.": 0.5, "left apple.": 0.75, "for a moment.": 1.0, "30 years old.": 0.8, "without him.": 0.4},
    5: {"didn't disappear.": 0.6, "creative force.": 0.5, "beyond apple.": 0.6, "entertainment.": 0.4},
    6: {"struggling.": 0.5, "interim ceo.": 0.6, "in 2007.": 0.6, "it was the iphone.": 1.0, "in the world.": 0.4},
    7: {"personal challenge.": 0.5, "age of 56.": 1.4, "without criticism.": 0.6, "with a cost.": 0.4},
    8: {"business history.": 0.5, "is over.": 0.5, "even greater.": 3.0,   # <- musical transition before final CTA
        "creation?": 0.5, "the iphone?": 0.6, "comments.": 0.5, "founder files.": 0.4},
}
CTA_AFTER = "even greater."

def sentences(words):
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if re.search(r"[.?!]$", w["w"].strip()):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def quiet_cut(a, sr, t0, t1):
    best, bt = 1e9, (t0 + t1) / 2
    for t in np.arange(t0, t1, 0.005):
        x = a[int(t * sr):int((t + 0.02) * sr)]
        if len(x) == 0: continue
        e = float(np.mean(x ** 2))
        if e < best: best, bt = e, t
    return bt

# ---------- process each clip ----------
clips = []
for k in range(1, 9):
    raw = load(f"v{k}.mp3", sr=16000)
    words = [dict(w=w["w"].strip(), s=w["s"], e=w["e"]) for s in T[str(k)] for w in s["words"]]
    sents = sentences(words)
    cuts = []   # (orig_time, pause)
    if k == 1:   # intro: the hand-tuned plan from the short version (transition shortened: CTA moved to the end)
        cuts = [(9.00, .85), (11.95, .80), (22.70, .65), (25.60, .60), (28.05, .70), (30.85, .35), (36.10, 1.30), (38.65, .55)]
        for w in words:
            if w["w"] == "And": w["s"] = 28.24
    else:
        for si, sent in enumerate(sents[:-1]):
            a_, b_ = words[sent[-1]], words[sents[si + 1][0]]
            text = " ".join(words[i]["w"] for i in sent).lower()
            n = len(sent)
            pause = 0.22
            if n <= 6: pause = 0.5
            if text.endswith("?"): pause = 0.6
            for key, p in HOOKS.get(k, {}).items():
                if text.endswith(key): pause = p
            lo, hi = a_["e"] - 0.05, max(b_["s"] + 0.05, a_["e"] + 0.12)
            if b_["s"] - a_["e"] < 0.1: lo, hi = a_["e"] - 0.1, a_["e"] + 0.45
            c = quiet_cut(raw, 16000, lo, hi)
            if b_["s"] < c: b_["s"] = c + 0.01
            cuts.append((c, pause, text[-24:]))
        cuts = [(c, p) for c, p, *_ in cuts]
    speech = words[-1]["e"] - words[0]["s"]
    tot_p = sum(p for _, p in cuts)
    if k == 8:
        tot_p_for_rate = tot_p - 3.0 + 0.5
    else:
        tot_p_for_rate = tot_p
    target = len(words) / TARGET_WPM * 60
    tempo = 1.0                                  # original speed — narration used exactly as recorded
    v = load(f"v{k}.mp3")                        # no time-stretch, no EQ/compression
    def nt(t, cuts=cuts, tempo=tempo):
        return t / tempo + sum(p for c, p in cuts if c <= t + 1e-6)
    pieces, prev = [], 0.0
    for c, p in cuts:
        pieces += [v[int(prev / tempo * SR):int(c / tempo * SR)], np.zeros(int(p * SR), np.float32)]; prev = c
    pieces.append(v[int(prev / tempo * SR):])
    vv = np.concatenate(pieces)
    # trim leading/trailing silence to 0.15 s
    lvl = np.convolve(vv ** 2, np.ones(480) / 480, mode="same")
    nz = np.where(lvl > db(-50) ** 2)[0]
    lead = max(0, nz[0] - int(0.15 * SR)); tail = min(len(vv), nz[-1] + int(0.25 * SR))
    vv = vv[lead:tail]; off = lead / SR
    W = [dict(w=w["w"], s=round(nt(w["s"]) - off, 3), e=round(nt(w["e"]) - off, 3)) for w in words]
    # snap starts sitting in silence onto the real onset
    def L(t, d=0.02):
        x = vv[max(0, int(t * SR)):int((t + d) * SR)]
        return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -120
    for w in W:
        if L(w["s"], 0.04) < -50:
            t = w["s"]
            while t < w["s"] + 1.5 and L(t) < -42: t += 0.01
            if t < w["s"] + 1.5: w["e"] = max(w["e"], t + 0.08); w["s"] = round(t, 3)
    extra = {}
    if k == 8:
        i_cta = next(i for i, w in enumerate(words) if w["w"].lower() == "greater.")
        extra["cta_gap"] = (W[i_cta]["e"], W[i_cta + 1]["s"])
    if k == 1:
        extra["intro_lift"] = (nt(35.64) - off, nt(36.42) - off)
    dur = len(vv) / SR
    span = W[-1]["e"] - W[0]["s"]
    print(f"v{k}: tempo {tempo:.3f}  pauses {tot_p:4.1f}s  {len(W)} words in {span:5.1f}s -> {len(W)/span*60:5.1f} wpm"
          + ("  (excl. CTA transition: %.1f wpm)" % (len(W) / (span - 2.5) * 60) if k == 8 else ""))
    clips.append(dict(k=k, audio=vv, words=W, dur=dur, tempo=tempo, extra=extra))

# ---------- global timeline ----------
CHAPTERS = [None,
    dict(n=1, title="The Curious Kid", years="1955 — 1974", music="79", moff=0.0),
    dict(n=2, title="From Garage to Giant", years="1976 — 1980", music="598", moff=17.0),
    dict(n=3, title="The Fall", years="1984 — 1985", music="614", moff=19.0),
    dict(n=4, title="The Wilderness Years", years="1985 — 1995", music="543", moff=22.0),
    dict(n=5, title="The Comeback", years="1996 — 2007", music="846", moff=0.0),
    dict(n=6, title="The Cost", years="2003 — 2011", music="546", moff=15.0),
    dict(n=7, title="The Lesson", years="Legacy", music="606", moff=20.0),
]
t = 0.4
segs = []
for i, c in enumerate(clips):
    seg = dict(k=c["k"], words=None)
    if i > 0:
        seg["card"] = (t, t + CARD); seg.update(CHAPTERS[i]); t += CARD
    seg["v0"] = t
    seg["words"] = [dict(w=w["w"], s=round(w["s"] + t, 3), e=round(w["e"] + t, 3)) for w in c["words"]]
    seg["extra"] = {k_: (a + t, b + t) for k_, (a, b) in c["extra"].items()}
    t += c["dur"]; seg["v1"] = t
    t += 0.6
    if i == 0:                      # channel ident (user's intro.mp4) plays right after voice 1
        IDENT = (seg["v1"] + 0.35, seg["v1"] + 0.35 + IDENT_LEN)
        t = IDENT[1] + 0.05
    segs.append(seg)
END0 = segs[-1]["v1"] + 0.5
TOTAL = END0 + END_CARD
n = int(TOTAL * SR)

voice = np.zeros(n, np.float32)
for c, s in zip(clips, segs):
    i = int(s["v0"] * SR); voice[i:i + len(c["audio"])] += c["audio"]
save("out/_voice.wav", voice)
voice = load("out/_voice.wav", af="loudnorm=I=-16:TP=-2:LRA=7")[:n]
voice = np.pad(voice, (0, max(0, n - len(voice))))

# ---------- music ----------
music = np.zeros((n, 2), np.float32)
def place(buf, clip, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(clip) <= 0: return
    if i < 0: clip = clip[-i:]; i = 0
    clip = clip[:len(buf) - i]; buf[i:i + len(clip)] += clip * gain
def fade(a, fi=0.0, fo=0.0):
    a = a.copy()
    if fi: k = min(len(a), int(fi * SR)); a[:k] *= np.linspace(0, 1, k)[:, None]
    if fo: k = min(len(a), int(fo * SR)); a[-k:] *= np.linspace(1, 0, k)[:, None]
    return a
@__import__("functools").lru_cache(None)
def track(name):
    return load(f"music/{name}.mp3", ch=2, af="loudnorm=I=-15:TP=-1.5")
def sfx(name): return load(f"sfx/{name}.mp3", ch=2)

env = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
env = np.clip(env / (np.percentile(env[env > 1e-4], 95) + 1e-9) * 1.2, 0, 1)
def bed(name, t0, t1, off=0.0, gap_db=-15, under_db=-22, fi=1.2, fo=1.2):
    tr = track(name); L_ = int((t1 - t0) * SR)
    seg = tr[int(off * SR):]
    while len(seg) < L_: seg = np.concatenate([seg, tr[int(4 * SR):]])   # loop if needed
    seg = fade(seg[:L_], fi, fo)
    e = env[int(t0 * SR):int(t0 * SR) + L_]
    g = db(gap_db) + (db(under_db) - db(gap_db)) * e
    tt = t0 + np.arange(L_) / SR                       # swell during chapter cards
    for c0_, c1_ in CARDS:
        g = g * (1 + (db(4) - 1) * np.clip(np.minimum(tt - c0_, c1_ - tt) / 0.5 + 1, 0, 1) * ((tt > c0_ - 0.5) & (tt < c1_ + 0.5)))
    place(music, seg * g[:, None], t0)

CARDS = [s['card'] for s in segs[1:]]
# intro
s1 = segs[0]
lift0, lift1 = s1["extra"]["intro_lift"]
bed("32", 0.0, lift0 + 0.35, 0.0, -16, -23, fi=0.6, fo=0.5)
place(music, sfx("1714"), lift1 - 1.2, db(-13))
place(music, sfx("2782"), lift1 - 0.25, db(-7))
bed("31", lift1 - 0.25, IDENT[0] + 0.45, 72.0, -11, -19, fi=0.05, fo=0.8)
# the ident's own sound, levelled so it sits with the narration sections
place(music, load("vid/intro.mp4", ch=2, af="loudnorm=I=-17:TP=-2"), IDENT[0], 1.0)
STINGS = []
for s in segs[1:]:
    c0, c1 = s["card"]
    nxt = segs[segs.index(s) + 1]["card"][0] if s is not segs[-1] else None
    STINGS.append(c0)
    place(music, sfx("1489"), c0 - 0.35, db(-15))
    place(music, sfx("1143"), c0 + 0.05, db(-13))
    if s["k"] == 8:
        cta0, cta1 = s["extra"]["cta_gap"]
        bed(s["music"], c0, cta0 + 0.3, s["moff"], -12, -21, fi=0.8, fo=0.45)
        # STRONG musical transition into the final CTA: riser -> whoosh -> double impact -> big finale track
        impact = cta1 - 0.30
        place(music, fade(sfx("788")[:int(2.25 * SR)], 0.3, 0.12), impact - 2.1, db(-3))
        place(music, sfx("1714"), impact - 1.0, db(-11))
        place(music, sfx("2782"), impact, db(-2))
        place(music, sfx("1143"), impact, db(-8))
        bed("33", impact, TOTAL, 18.0, -10, -18, fi=0.03, fo=3.0)
        s["impact"] = impact
    else:
        bed(s["music"], c0, (nxt if nxt else s["v1"]) + 1.0, s["moff"], -14 if s["k"] != 7 else -16,
            -22 if s["k"] != 7 else -24, fi=0.4, fo=1.2)
# end-card click + hit
place(music, sfx("498"), END0 + 1.6, db(-15))
rng = np.random.default_rng(3); ck = int(0.025 * SR)
click = (rng.standard_normal(ck) * np.exp(-np.linspace(0, 9, ck))).astype(np.float32); click = np.stack([click, click], 1)

mix = music + voice[:, None]
save("out/_mix.wav", mix)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "out/_mix.wav", "-af", "loudnorm=I=-14:TP=-1.2:LRA=11",
                "-ar", "48000", "-c:a", "pcm_s24le", "out/mix.wav"], check=True)
save("out/voice.wav", voice)
for s in segs: s.pop("music", None)
json.dump(dict(ident=IDENT, segs=segs, total=TOTAL, end0=END0, card=CARD,
               chapters=[c for c in CHAPTERS if c]), open("out/timeline.json", "w"), indent=1)
allw = sum(len(s["words"]) for s in segs)
print(f"TOTAL {TOTAL/60:.0f}:{TOTAL%60:04.1f}  words {allw}")
