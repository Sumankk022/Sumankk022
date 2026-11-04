"""Re-time the narration (pitch-preserving slow-down + hook pauses), then mix
music bed, transition riser/impact, finale music and SFX. Writes:
  out/voice_timed.wav, out/mix.wav, out/timeline.json (word times on new timeline)
"""
import json, subprocess, numpy as np, os

SR = 48000
TEMPO = 0.92                      # 8% slower (pitch preserved) -> ~136 wpm incl. pauses
os.makedirs("out", exist_ok=True)

def load(path, sr=SR, ch=1, af=None):
    cmd = ["ffmpeg", "-v", "error", "-i", path]
    if af: cmd += ["-af", af]
    cmd += ["-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
    return a.reshape(-1, ch) if ch > 1 else a

def save(path, a):
    a = np.clip(a, -1, 1).astype(np.float32)
    ch = 1 if a.ndim == 1 else a.shape[1]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", str(ch),
                    "-i", "-", "-c:a", "pcm_s24le", path], input=a.tobytes(), check=True)

# ---------- 1. voice: stretch + light broadcast polish ----------
voice = load("voice.mp3", af=(f"rubberband=tempo={TEMPO}:formant=preserved:pitchq=quality,"
                               "highpass=f=75,equalizer=f=220:t=q:w=1.2:g=-1.5,"
                               "equalizer=f=3200:t=q:w=1.0:g=2.5,equalizer=f=9000:t=h:w=0.7:g=1.5,"
                               "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2"))

# cut points (original seconds, chosen in true digital silence) and pause inserted there
HOOK_PAUSES = [
    (9.00, 0.85, "hook 1: '...pushed out of it.'"),
    (11.95, 0.80, "hook 2: '...happened to Steve Jobs.'"),
    (22.70, 0.65, "'...no longer wanted him in charge.'"),
    (25.60, 0.60, "'...treated that as the end.'"),
    (28.05, 0.70, "'...a new beginning.' (originally no gap at all)"),
    (30.85, 0.35, "'...didn't just save Apple.'"),
    (36.10, 2.40, "MUSICAL TRANSITION before the final CTA"),
    (38.65, 0.55, "'This is the story of Steve Jobs.'"),
]
TRANS_CUT = 36.10

def new_time(t):
    """map original-audio seconds -> final timeline seconds"""
    return t / TEMPO + sum(p for c, p, _ in HOOK_PAUSES if c <= t + 1e-6)

pieces, prev = [], 0.0
for cut, pause, _ in HOOK_PAUSES:
    pieces.append(voice[int(prev / TEMPO * SR):int(cut / TEMPO * SR)])
    pieces.append(np.zeros(int(pause * SR), np.float32))
    prev = cut
pieces.append(voice[int(prev / TEMPO * SR):])
v = np.concatenate(pieces)
# voice loudness: normalise to -16 LUFS on its own
save("out/_v.wav", v)
v = load("out/_v.wav", af="loudnorm=I=-16:TP=-2:LRA=7")
VOICE_END = len(v) / SR

# ---------- 2. timeline of words ----------
T = json.load(open("transcript.json"))
words = [{"w": w["w"].strip(), "s": round(new_time(w["s"]), 3), "e": round(new_time(w["e"]), 3)}
         for s in T for w in s["words"]]
# snap word starts that whisper placed inside silence onto the real onset
def lvl(t, d=0.02):
    x = v[int(t * SR):int((t + d) * SR)]
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -120
for w in words:
    if lvl(w["s"], 0.04) < -50:
        t = w["s"]
        while t < w["s"] + 1.5 and lvl(t) < -42: t += 0.01
        if t < w["s"] + 1.5:
            print("snap", w["w"], w["s"], "->", round(t, 2)); w["e"] = max(w["e"], t + 0.08); w["s"] = round(t, 3)
trans_start = new_time(35.64)           # end of "...uses technology."
voice_back = new_time(36.42)            # "This is the story..."
impact_t = voice_back - 0.30
last_word = words[-1]["e"]
END_CARD = 5.8
TOTAL = last_word + 0.45 + END_CARD
n = int(TOTAL * SR)

# ---------- 3. music ----------
def place(buf, clip, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf): return
    clip = clip[:len(buf) - i]
    buf[i:i + len(clip)] += clip * gain

def fade(a, fin=0.0, fout=0.0):
    a = a.copy()
    if fin: k = int(fin * SR); a[:k] *= np.linspace(0, 1, k)[:, None]
    if fout: k = int(fout * SR); a[-k:] *= np.linspace(1, 0, k)[:, None]
    return a

db = lambda x: 10 ** (x / 20)
music = np.zeros((n, 2), np.float32)

# bed: "Driving Ambition" from the top, cut for the drop just before the transition
bed = load("music/32.mp3", ch=2)
bed_len = trans_start + 0.25
bed = fade(bed[:int(bed_len * SR)], fin=0.6, fout=0.55)
# side-chain style ducking under the voice (smooth envelope of the voice)
env = np.abs(v[:len(bed)]) if len(v) >= len(bed) else np.pad(np.abs(v), (0, len(bed) - len(v)))
k = int(0.25 * SR); env = np.convolve(env, np.ones(k) / k, mode="same")
env = env / (env.max() + 1e-9)
duck = db(-16) + (db(-23) - db(-16)) * np.clip(env * 6, 0, 1)   # -21 dB in gaps, -28 dB under words
place(music, bed * duck[:, None], 0.0)

# riser into the impact (peak of riser 788 is ~2.1 s into the file)
riser = load("sfx/788.mp3", ch=2)[:int(2.25 * SR)]
place(music, fade(riser, fin=0.3, fout=0.12), impact_t - 2.1, db(-4))
# whoosh sweep + big impact on the downbeat
place(music, load("sfx/1714.mp3", ch=2), impact_t - 1.0, db(-12))
place(music, load("sfx/2782.mp3", ch=2), impact_t, db(-3))
place(music, load("sfx/1143.mp3", ch=2), impact_t, db(-9))

# finale: "Dreaming Big" climax section carries the last lines + end card
fin = load("music/31.mp3", ch=2)
off = 72.0
fin = fin[int(off * SR):int((off + TOTAL - impact_t + 0.5) * SR)]
fin = fade(fin, fin=0.04, fout=2.6)
fin = fin[:n - int(impact_t * SR)]
fenv = np.abs(np.pad(v, (0, max(0, n - len(v)))))[int(impact_t * SR):int(impact_t * SR) + len(fin)]
fenv = np.convolve(fenv, np.ones(k) / k, mode="same"); fenv = fenv / (fenv.max() + 1e-9)
fduck = db(-10) + (db(-18) - db(-10)) * np.clip(fenv * 6, 0, 1)
place(music, fin * fduck[:len(fin), None], impact_t)

# subtle transition whooshes (visual cuts with big text moves) — kept sparse
WHOOSH_AT = []
def whoosh(t, gain=-20, f="sfx/1489.mp3"):
    WHOOSH_AT.append(t); place(music, load(f, ch=2), t - 0.55, db(gain))
whoosh(new_time(9.24), -17)          # into "That is exactly what happened..."
whoosh(new_time(11.0), -19, "sfx/1492.mp3")  # STEVE JOBS title reveal
whoosh(new_time(23.02), -21)        # "Most people..."
whoosh(new_time(28.25), -19, "sfx/1492.mp3")  # the return
whoosh(last_word + 0.45, -16)      # end card
END_T0 = last_word + 0.45
place(music, load("sfx/498.mp3", ch=2), END_T0 + 1.1, db(-16))   # soft hit when SUBSCRIBE lands
# synthetic mouse click when the cursor presses SUBSCRIBE
rng = np.random.default_rng(3); ck = int(0.025 * SR)
click = (rng.standard_normal(ck) * np.exp(-np.linspace(0, 9, ck))).astype(np.float32)
click = np.stack([click, click], 1)
place(music, click, END_T0 + 2.4, db(-14)); place(music, click * 0.6, END_T0 + 2.47, db(-14))

mix = music.copy()
mix[:len(v)] += np.repeat(v[:n, None], 2, axis=1)
save("out/_mix.wav", mix)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "out/_mix.wav", "-af",
                "loudnorm=I=-14:TP=-1.2:LRA=9,aresample=48000", "-c:a", "pcm_s24le", "out/mix.wav"], check=True)
save("out/voice_timed.wav", v)

wc = len(words)
speech_span = last_word - words[0]["s"]
json.dump({"words": words, "total": TOTAL, "trans_start": trans_start, "impact": impact_t,
           "voice_back": voice_back, "last_word": last_word, "new_time_cuts": HOOK_PAUSES,
           "tempo": TEMPO}, open("out/timeline.json", "w"), indent=1)
print(f"words={wc} original=44.36s ({wc/44.36*60:.0f} wpm)  new narration={speech_span:.2f}s "
      f"({wc/speech_span*60:.0f} wpm incl. pauses+transition)  total video={TOTAL:.2f}s")
print(f"transition {trans_start:.2f}->{voice_back:.2f}  impact@{impact_t:.2f}")
