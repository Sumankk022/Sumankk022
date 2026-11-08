"""Ronaldo documentary audio: 8 narration clips at original (energetic) speed.
- extra pause after each hook line, run-on sentences given breathing room
- intro ident (vid/intro.mp4) right after voice 1
- chapter cards with stings, per-chapter music beds with ducking
- riser -> whoosh -> double impact musical transition before the final CTA
Writes out/mix.wav, out/timeline.json
"""
import json, subprocess, os, re, functools
import numpy as np
SR = 48000; CARD = 3.4; END_CARD = 12.0
IDENT_LEN = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "vid/intro.mp4"], capture_output=True, text=True).stdout)
os.makedirs("out", exist_ok=True)
db = lambda x: 10 ** (x / 20)
def load(path, ch=1, af=None, sr=SR):
    cmd = ["ffmpeg", "-v", "error", "-i", path] + (["-af", af] if af else []) + ["-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    return a.reshape(-1, ch).copy() if ch > 1 else a.copy()
def save(path, a):
    ch = 1 if a.ndim == 1 else a.shape[1]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", str(ch), "-i", "-", "-c:a", "pcm_s24le", path],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)

T = json.load(open("transcripts.json"))
FIX = {"Madera.": "Madeira.", "Nasser": "Nassr"}
# total silence wanted after hook lines (seconds). Matched on the sentence's ending, lowercase.
HOOKS = {
 1: {"in the world.": 1.25, "right?": 1.1, "ronaldo did.": 1.2, "worth millions.": 0.95, "very differently.": 1.1},
 2: {"madeira.": 1.0, "always easy.": 0.95, "football.": 1.1, "big challenge.": 1.15, "12 years old.": 1.35, "chase a dream.": 0.95},
 3: {"wasn't easy.": 1.0, "something special.": 0.9, "hated losing.": 1.25, "impressed them.": 1.0, "sign him.": 1.0,
     "more surprise.": 1.15, "seven shirt.": 1.05},
 4: {"player yet.": 1.0, "unbelievable.": 1.15, "ballon d'or.": 1.2, "came knocking.": 1.0, "wanted him.": 1.15},
 5: {"another level.": 1.0, "breaking records.": 1.1, "awards.": 0.95, "lionel messi.": 1.15, "was better.": 0.85},
 6: {"as expected.": 1.15, "surprising decision.": 1.15, "saudi arabia.": 0.95},
 7: {"for portugal.": 1.1, "disaster struck.": 1.25, "the final.": 1.15, "european champions.": 1.25, "his career.": 0.95, "and 2025.": 0.95},
 8: {"global brand.": 1.0, "than football.": 0.95, "so interesting.": 0.95, "to deny.": 1.15, "global phenomenon.": 1.05,
     "keep going.": 3.4, "team messi?": 0.95},   # 'keep going.' -> strong musical transition before the CTA
}
MIN_GAP = 0.42

def words_of(k):
    ws = []
    for s in T[str(k)]:
        for w in s["words"]:
            t = w["w"].strip()
            if ws and (t.startswith("'") or t.startswith("-")): ws[-1]["w"] += t; ws[-1]["e"] = w["e"]; continue
            ws.append(dict(w=FIX.get(t, t), s=w["s"], e=w["e"]))
    for w in ws:
        w["w"] = w["w"].replace("Ballon d'Or", "Ballon d'Or")
    # merge "Ballon" "d'Or" display later; keep tokens
    return ws

def quiet_cut(a, sr, t0, t1):
    best, bt = 1e9, (t0 + t1) / 2
    for t in np.arange(t0, max(t0 + 0.01, t1), 0.005):
        x = a[int(t * sr):int((t + 0.02) * sr)]
        if len(x) == 0: continue
        e = float(np.mean(x ** 2))
        if e < best: best, bt = e, t
    return bt

clips = []
for k in range(1, 9):
    raw = load(f"v{k}.mp3", sr=16000)
    words = words_of(k)
    cuts = []
    for i in range(len(words) - 1):
        a_, b_ = words[i], words[i + 1]
        if not re.search(r"[.?!]$", a_["w"]): continue
        # sentence text
        j = i
        while j > 0 and not re.search(r"[.?!]$", words[j - 1]["w"]): j -= 1
        text = " ".join(w["w"] for w in words[j:i + 1]).lower()
        gap = max(0.0, b_["s"] - a_["e"])
        want = MIN_GAP
        for key, p in HOOKS.get(k, {}).items():
            if text.endswith(key): want = p
        add = max(0.0, want - gap)
        if add < 0.04: continue
        lo, hi = a_["e"] - 0.03, max(b_["s"] + 0.03, a_["e"] + 0.1)
        if gap < 0.08: lo, hi = a_["e"] - 0.1, a_["e"] + 0.3
        c = quiet_cut(raw, 16000, lo, hi)
        cuts.append((c, add, text[-22:]))
    v = load(f"v{k}.mp3")
    # tiny fades at each cut to avoid clicks
    pieces, prev = [], 0.0
    for c, p, _ in cuts:
        seg = v[int(prev * SR):int(c * SR)].copy(); f = min(len(seg), 96)
        seg[-f:] *= np.linspace(1, 0, f)
        if prev > 0: seg[:f] *= np.linspace(0, 1, f)
        pieces += [seg, np.zeros(int(p * SR), np.float32)]; prev = c
    last = v[int(prev * SR):].copy(); f = 96
    if prev > 0: last[:f] *= np.linspace(0, 1, f)
    pieces.append(last)
    vv = np.concatenate(pieces)
    nt = lambda t: t + sum(p for c, p, _ in cuts if c <= t + 1e-6)
    lvl = np.convolve(vv ** 2, np.ones(480) / 480, mode="same")
    nz = np.where(lvl > db(-50) ** 2)[0]
    lead = max(0, nz[0] - int(0.12 * SR)); tail = min(len(vv), nz[-1] + int(0.3 * SR))
    vv = vv[lead:tail]; off = lead / SR
    W = [dict(w=w["w"], s=round(nt(w["s"]) - off, 3), e=round(nt(w["e"]) - off, 3)) for w in words]
    extra = {}
    if k == 8:
        i_cta = next(i for i, w in enumerate(words) if w["w"].lower() == "going.")
        extra["cta_gap"] = (W[i_cta]["e"], W[i_cta + 1]["s"])
    added = sum(p for _, p, _ in cuts)
    print(f"v{k}: +{added:4.1f}s pauses at {len(cuts)} points -> {len(vv)/SR:5.1f}s  " +
          "; ".join(f"{t}+{p:.2f}" for c, p, t in cuts if p > 0.3))
    clips.append(dict(k=k, audio=vv, words=W, dur=len(vv) / SR, extra=extra))

CHAPTERS = [None,
 dict(n=1, title="The Island Boy", years="1985 — 1997", music="79", moff=10.0),
 dict(n=2, title="The Lisbon Test", years="1997 — 2003", music="53", moff=0.0),
 dict(n=3, title="Becoming CR7", years="2003 — 2009", music="51", moff=0.0),
 dict(n=4, title="The Record Breaker", years="2009 — 2018", music="78", moff=1.0),
 dict(n=5, title="New Frontiers", years="2018 — 2023", music="846", moff=4.0),
 dict(n=6, title="For Portugal", years="2016 — 2026", music="598", moff=26.0),
 dict(n=7, title="More Than Football", years="The Legacy", music="52", moff=4.0),
]
t = 0.5; segs = []
for i, c in enumerate(clips):
    seg = dict(k=c["k"])
    if i > 0: seg["card"] = (t, t + CARD); seg.update(CHAPTERS[i]); t += CARD
    seg["v0"] = t
    seg["words"] = [dict(w=w["w"], s=round(w["s"] + t, 3), e=round(w["e"] + t, 3)) for w in c["words"]]
    seg["extra"] = {k_: (a + t, b + t) for k_, (a, b) in c["extra"].items()}
    t += c["dur"]; seg["v1"] = t; t += 0.5
    if i == 0:
        IDENT = (seg["v1"] + 0.55, seg["v1"] + 0.55 + IDENT_LEN); t = IDENT[1] + 0.05
    segs.append(seg)
END0 = segs[-1]["v1"] + 0.6; TOTAL = END0 + END_CARD; n = int(TOTAL * SR)

voice = np.zeros(n, np.float32)
for c, s in zip(clips, segs):
    i = int(s["v0"] * SR); voice[i:i + len(c["audio"])] += c["audio"]
save("out/_voice.wav", voice)
voice = load("out/_voice.wav", af="highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=10:release=150:makeup=1.5,loudnorm=I=-16:TP=-2:LRA=7")[:n]
voice = np.pad(voice, (0, max(0, n - len(voice))))

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
def track(name): return load(f"music/{name}.mp3", ch=2, af="loudnorm=I=-15:TP=-1.5")
@functools.lru_cache(None)
def sfx(name): return load(f"sfx/{name}.mp3", ch=2)
env = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
env = np.clip(env / (np.percentile(env[env > 1e-4], 95) + 1e-9) * 1.2, 0, 1)
CARDS = [s["card"] for s in segs[1:]]
def bed(name, t0, t1, off=0.0, gap_db=-13, under_db=-21, fi=1.0, fo=1.2):
    tr = track(name); L_ = int((t1 - t0) * SR)
    seg = tr[int(off * SR):]
    while len(seg) < L_: seg = np.concatenate([seg, tr[int(8 * SR):int(len(tr) - 6 * SR)]])
    seg = fade(seg[:L_], fi, fo)
    e = env[int(t0 * SR):int(t0 * SR) + L_]
    g = db(gap_db) + (db(under_db) - db(gap_db)) * e
    tt = t0 + np.arange(L_) / SR
    for c0_, c1_ in CARDS:
        m = (tt > c0_ - 0.5) & (tt < c1_ + 0.5)
        g = g * (1 + (db(4) - 1) * np.clip(np.minimum(tt - c0_, c1_ - tt) / 0.5 + 1, 0, 1) * m)
    place(music, seg * g[:, None], t0)

s1 = segs[0]
place(music, sfx("2782"), 0.0, db(-9))                      # cold-open hit
bed("676", 0.0, IDENT[0] + 0.5, 1.0, -12, -20, fi=0.05, fo=0.6)
place(music, sfx("1714"), IDENT[0] - 1.0, db(-12))
place(music, load("vid/intro.mp4", ch=2, af="loudnorm=I=-17:TP=-2"), IDENT[0], 1.0)
for idx, s in enumerate(segs[1:], 1):
    c0, c1 = s["card"]
    nxt = segs[idx + 1]["card"][0] if idx + 1 < len(segs) else None
    place(music, sfx("1489"), c0 - 0.35, db(-14))
    place(music, sfx("1143"), c0 + 0.05, db(-12))
    if s["k"] == 8:
        cta0, cta1 = s["extra"]["cta_gap"]
        bed(s["music"], c0, cta0 + 0.3, s["moff"], -12, -21, fi=0.6, fo=0.5)
        impact = cta1 - 0.35
        place(music, fade(sfx("788")[:int(2.6 * SR)], 0.3, 0.1), impact - 2.5, db(-3))
        place(music, sfx("1714"), impact - 1.0, db(-10))
        place(music, sfx("2782"), impact, db(-1))
        place(music, sfx("1143"), impact, db(-7))
        place(music, fade(sfx("462")[:int(4 * SR)], 0.05, 2.0), impact, db(-16))
        bed("677", impact, TOTAL, 1.0, -9, -18, fi=0.03, fo=3.0)
        s["impact"] = impact
    else:
        bed(s["music"], c0, (nxt if nxt else s["v1"]) + 0.8, s["moff"], -13, -21, fi=0.4, fo=1.0)
# moments: crowd swells
def at(ch, phrase):
    toks = phrase.lower().split(); ws = segs[ch]["words"]
    for i in range(len(ws) - len(toks) + 1):
        if all(re.sub(r"[^a-z0-9']", "", ws[i + j]["w"].lower()) == toks[j] for j in range(len(toks))): return ws[i]["s"]
    raise KeyError(phrase)
place(music, fade(sfx("462")[:int(5 * SR)], 0.4, 2.5), at(6, "and portugal eventually won") - 0.2, db(-19))
place(music, fade(sfx("3022")[:int(5 * SR)], 0.8, 2.5), at(3, "manchester united won the") - 0.4, db(-22))
place(music, sfx("498"), END0 + 1.6, db(-15))

mix = music + voice[:, None]
save("out/_mix.wav", mix)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "out/_mix.wav", "-af", "loudnorm=I=-14:TP=-1.2:LRA=11",
                "-ar", "48000", "-c:a", "pcm_s24le", "out/mix.wav"], check=True)
for s in segs: s.pop("music", None)
json.dump(dict(ident=IDENT, segs=segs, total=TOTAL, end0=END0, card=CARD, chapters=[c for c in CHAPTERS if c]),
          open("out/timeline.json", "w"), indent=1)
print(f"TOTAL {int(TOTAL//60)}:{TOTAL%60:04.1f}")
