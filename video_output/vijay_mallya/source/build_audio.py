"""Vijay Mallya documentary — audio build.
8 narration clips -> pause re-timing (hook pauses added, over-long gaps tightened, speech untouched),
chapter cards with stings, per-chapter music beds with voice ducking, channel ident after voice 1,
riser + whoosh + double impact musical transition before the final CTA, end-card music.
Writes out/mix.wav, out/voice.wav, out/timeline.json
"""
import json, subprocess, os, re, functools
import numpy as np

SR = 48000
CARD = 3.6
END_CARD = 12.0
IDENT_LEN = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  "vid/intro.mp4"], capture_output=True, text=True).stdout)
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

# Silence wanted after a sentence (seconds, total gap). Hooks get a short dramatic beat;
# everything else keeps its natural gap but is capped so the read stays energetic.
NORMAL_CAP = 0.55
HOOKS = {
    1: {"glamorous airlines.": 0.85, "to have everything.": 1.05, "of good times.": 0.95, "flying experience.": 0.85,
        "falling apart.": 1.15, "airlines collapsed.": 1.0, "united kingdom.": 1.0, "business figures?": 0.9},
    2: {"karnataka.": 0.7, "28 years old.": 1.0, "wanted to expand.": 0.8, "beer brands.": 0.7, "still waiting.": 0.6},
    3: {"just another airline.": 0.9, "premium service.": 0.7, "instantly recognizable.": 0.7,
        "one major problem.": 1.1, "extremely expensive.": 0.75, "already tight.": 0.7},
    4: {"gopinath.": 0.7, "about the strategy.": 0.8, "a smart move.": 0.95, "impossible to ignore.": 0.95,
        "were frustrated.": 0.7},
    5: {"serious trouble.": 0.8, "operating permit.": 0.7, "think about that.": 0.9, "stopped flying.": 1.15,
        "were affected.": 0.7, "enormous crisis.": 0.9},
    6: {"kept increasing.": 0.8, "united kingdom.": 0.85, "released on bail.": 0.8, "economic offender.": 1.1,
        "battle continued.": 0.8, "carried out.": 0.75},
    7: {"part of the story.": 0.85, "two different things.": 1.0, "returning to india.": 0.8},
    8: {"risks of ambition.": 0.75, "still remember.": 0.6, "go wrong.": 0.8, "even more important.": 0.95,
        "financial sense.": 3.4,             # <- strong musical transition before the final CTA
        "disastrous decisions?": 0.6, "more to the story?": 0.45, "in the comments.": 0.7, "has a story.": 0.55},
}
CTA_AFTER = "sense."
ABBR = re.compile(r"^[A-Z]\.$")              # "G." "R." are initials, not sentence ends

def sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.?!]$", w["w"]) and not ABBR.match(w["w"]):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def env_db(a, sr, hop=0.01):
    h = int(hop * sr); n = len(a) // h
    x = a[:n * h].reshape(n, h)
    return 20 * np.log10(np.sqrt(np.mean(x ** 2, 1)) + 1e-9)

def silent_run(E, t0, t1, thr, hop=0.01):
    """longest run of frames below thr inside [t0, t1] -> (start, end) seconds"""
    i0, i1 = max(0, int(t0 / hop)), min(len(E), int(t1 / hop))
    best, cur = (None, 0), None
    for i in range(i0, i1):
        if E[i] < thr:
            if cur is None: cur = i
            if i - cur + 1 > best[1]: best = (cur, i - cur + 1)
        else: cur = None
    if best[0] is None: return None
    return best[0] * hop, (best[0] + best[1]) * hop

# ---------- process each clip ----------
clips = []
for k in range(1, 9):
    v = load(f"v{k}.mp3")
    E = env_db(v, SR)
    floor = np.percentile(E, 8); thr = max(floor + 10, -52)
    words = [dict(w=w["w"].strip(), s=w["s"], e=w["e"]) for s in T[str(k)] for w in s["words"]]
    sents = sentences(words)
    edits = []        # (silence_start, silence_end, new_length)
    log = []
    for si in range(len(sents) - 1):
        a_, b_ = sents[si][-1], sents[si + 1][0]
        text = " ".join(w["w"] for w in sents[si]).lower()
        run = silent_run(E, a_["e"] - 0.15, b_["s"] + 0.15, thr)
        if not run: continue
        s0, s1 = run; gap = s1 - s0
        want = min(gap, NORMAL_CAP)
        for key, p in HOOKS.get(k, {}).items():
            if text.endswith(key): want = max(p, gap if p < 2 else 0)
        if abs(want - gap) > 0.04:
            edits.append((s0, s1, want)); log.append(f"{text[-26:]:>26s} {gap:4.2f}->{want:4.2f}")
    # rebuild audio: keep 40 ms of the original silence on each side, put the new silence in the middle
    pieces, prev, shift = [], 0.0, []
    fade = int(0.006 * SR)
    for s0, s1, want in edits:
        keep = 0.04
        cut0, cut1 = s0 + keep, s1 - keep
        if cut1 <= cut0: continue
        seg = v[int(prev * SR):int(cut0 * SR)].copy()
        if len(seg) > fade: seg[-fade:] *= np.linspace(1, 0, fade)
        pieces.append(seg)
        newlen = max(0.0, want - 2 * keep)
        pieces.append(np.zeros(int(newlen * SR), np.float32))
        shift.append((cut0, cut1, newlen))
        prev = cut1
    tail = v[int(prev * SR):].copy()
    if len(tail) > fade and shift: tail[:fade] *= np.linspace(0, 1, fade)
    pieces.append(tail)
    vv = np.concatenate(pieces)
    def nt(t, kind="s"):
        d = 0.0
        for c0, c1, nl in shift:
            if t >= c1: d += nl - (c1 - c0)
            elif t > c0: return c0 + d + (nl if kind == "s" else 0.0)    # inside an edited silence: snap to its edge
        return t + d
    # trim leading/trailing silence
    Ev = env_db(vv, SR)
    nz = np.where(Ev > thr)[0]
    lead = max(0, int(nz[0] * 0.01 * SR) - int(0.12 * SR)); tl = min(len(vv), int((nz[-1] + 1) * 0.01 * SR) + int(0.3 * SR))
    vv = vv[lead:tl]; off = lead / SR
    W = [dict(w=w["w"], s=round(nt(w["s"], "s") - off, 3), e=round(max(nt(w["e"], "e"), nt(w["s"], "s") + 0.05) - off, 3)) for w in words]
    extra = {}
    if k == 8:
        i_cta = next(i for i, w in enumerate(words) if w["w"].lower() == CTA_AFTER)
        extra["cta_gap"] = (W[i_cta]["e"], W[i_cta + 1]["s"])
    if k == 1:
        i_b = next(i for i, w in enumerate(words) if w["w"].lower() == "apart.")
        extra["intro_lift"] = (W[i_b - 4]["s"], W[i_b]["e"])            # "But then, everything started falling apart."
        i_k = next(i for i, w in enumerate(words) if w["w"].lower() == "collapsed.")
        extra["collapse"] = (W[i_k]["s"], W[i_k]["e"])
    dur = len(vv) / SR
    span = W[-1]["e"] - W[0]["s"]
    print(f"v{k}: {len(edits)} gap edits  {len(W)} words in {span:5.1f}s -> {len(W)/span*60:5.1f} wpm   (orig {len(v)/SR:5.1f}s -> {dur:5.1f}s)")
    for l in log: print("     ", l)
    clips.append(dict(k=k, audio=vv, words=W, dur=dur, extra=extra))

# ---------- global timeline ----------
CHAPTERS = [None,
    dict(n=1, title="Born Into Business", years="1955 — 2004", music="79", moff=0.0),
    dict(n=2, title="The Airline Dream", years="2005 — 2007", music="598", moff=15.0),
    dict(n=3, title="The Big Gamble", years="2007 — 2011", music="597", moff=5.0),
    dict(n=4, title="Grounded", years="2012", music="614", moff=40.0),
    dict(n=5, title="The Legal Battle", years="2016 — 2020", music="678", moff=0.0),
    dict(n=6, title="Unfinished Business", years="2020 — 2026", music="552", moff=15.0),
    dict(n=7, title="The Lesson", years="Legacy", music="546", moff=14.0),
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
        IDENT = (seg["v1"] + 0.45, seg["v1"] + 0.45 + IDENT_LEN)
        t = IDENT[1] + 0.05
    segs.append(seg)
END0 = segs[-1]["v1"] + 0.5
TOTAL = END0 + END_CARD
n = int(TOTAL * SR)

voice = np.zeros(n, np.float32)
for c, s in zip(clips, segs):
    i = int(s["v0"] * SR); voice[i:i + len(c["audio"])] += c["audio"]
save("out/_voice.wav", voice)
voice = load("out/_voice.wav", af="highpass=f=70,loudnorm=I=-16:TP=-2:LRA=7")[:n]
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
@functools.lru_cache(None)
def track(name):
    return load(f"music/{name}.mp3", ch=2, af="loudnorm=I=-15:TP=-1.5")
def sfx(name): return load(f"sfx/{name}.mp3", ch=2)

env = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
env = np.clip(env / (np.percentile(env[env > 1e-4], 95) + 1e-9) * 1.2, 0, 1)
CARDS = [s['card'] for s in segs[1:]]
def bed(name, t0, t1, off=0.0, gap_db=-15, under_db=-22, fi=1.2, fo=1.2):
    tr = track(name); L_ = int((t1 - t0) * SR)
    seg = tr[int(off * SR):]
    while len(seg) < L_: seg = np.concatenate([seg, tr[int(4 * SR):]])
    seg = fade(seg[:L_], fi, fo)
    e = env[int(t0 * SR):int(t0 * SR) + L_]
    g = db(gap_db) + (db(under_db) - db(gap_db)) * e
    tt = t0 + np.arange(L_) / SR
    for c0_, c1_ in CARDS:                                   # swell during chapter cards
        g = g * (1 + (db(4) - 1) * np.clip(np.minimum(tt - c0_, c1_ - tt) / 0.5 + 1, 0, 1) * ((tt > c0_ - 0.5) & (tt < c1_ + 0.5)))
    place(music, seg * g[:, None], t0)

# intro: glamour bed -> hit on "But then..." -> dark drums bed -> channel ident
s1 = segs[0]
lift0, lift1 = s1["extra"]["intro_lift"]
bed("371", 0.0, lift0 + 0.25, 30.0, -14, -21, fi=0.4, fo=0.35)
place(music, sfx("1714"), lift0 - 1.0, db(-12))           # whoosh into the turn
place(music, sfx("2782"), lift0 - 0.05, db(-8))            # impact
k0, k1 = s1["extra"]["collapse"]
place(music, sfx("1143"), k0 - 0.05, db(-12))
bed("680", lift0 - 0.05, IDENT[0] + 0.45, 0.0, -12, -20, fi=0.05, fo=0.8)
place(music, load("vid/intro.mp4", ch=2, af="loudnorm=I=-17:TP=-2"), IDENT[0], 1.0)
for s in segs[1:]:
    c0, c1 = s["card"]
    nxt = segs[segs.index(s) + 1]["card"][0] if s is not segs[-1] else None
    place(music, sfx("1489"), c0 - 0.35, db(-15))
    place(music, sfx("1143"), c0 + 0.05, db(-13))
    if s["k"] == 8:
        cta0, cta1 = s["extra"]["cta_gap"]
        bed(s["music"], c0, cta0 + 0.3, s["moff"], -13, -22, fi=0.8, fo=0.45)
        impact = cta1 - 0.35
        place(music, fade(sfx("788")[:int(2.6 * SR)], 0.3, 0.12), impact - 2.5, db(-3))   # riser
        place(music, sfx("1714"), impact - 1.0, db(-10))                                   # whoosh
        place(music, sfx("2782"), impact, db(-2))                                          # impact
        place(music, sfx("1143"), impact, db(-8))
        place(music, sfx("2782"), impact + 0.42, db(-9))                                   # second hit
        bed("846", impact, TOTAL, 30.0, -10, -18, fi=0.03, fo=3.0)
        s["impact"] = impact
    else:
        quiet = s["k"] in (5, 7)
        bed(s["music"], c0, (nxt if nxt else s["v1"]) + 1.0, s["moff"], -15 if quiet else -14,
            -23 if quiet else -22, fi=0.4, fo=1.2)
place(music, sfx("498"), END0 + 1.6, db(-15))

mix = music + voice[:, None]
save("out/_mix.wav", mix)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "out/_mix.wav", "-af", "loudnorm=I=-14:TP=-1.2:LRA=11",
                "-ar", "48000", "-c:a", "pcm_s24le", "out/mix.wav"], check=True)
save("out/voice.wav", voice)
for s in segs: s.pop("music", None)
json.dump(dict(ident=IDENT, segs=segs, total=TOTAL, end0=END0, card=CARD,
               chapters=[c for c in CHAPTERS if c]), open("out/timeline.json", "w"), indent=1)
allw = sum(len(s["words"]) for s in segs)
print(f"TOTAL {int(TOTAL//60)}:{TOTAL%60:04.1f}  words {allw}")
print("chapters:", [(c['title'], f"{int(s['card'][0]//60)}:{int(s['card'][0]%60):02d}") for c, s in zip(CHAPTERS[1:], segs[1:])])
