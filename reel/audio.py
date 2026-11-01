"""
Soundtrack for "The Last Coffee": synthesized BGM, cartoon SFX and
wordless reaction voices (formant-synthesised gibberish: yawn, "huh?!",
"nooo", giggles, "woohoo", snores). No dialogue / narration.

Usage: python3 audio.py out.wav
"""
import math
import sys
import wave

import numpy as np

SR = 44100
DUR = 30.0
N = int(SR * DUR)
rng = np.random.default_rng(3)

music = np.zeros(N)
sfx = np.zeros(N)
voice = np.zeros(N)


def place(buf, t0, sig, gain=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def tvec(d):
    return np.arange(int(d * SR)) / SR


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.005, r=0.05):
    e = np.ones(n)
    na, nr = min(n, max(1, int(a * SR))), min(n, max(1, int(r * SR)))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, k=8):
    if k <= 1:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def highpass(x, k=8):
    return x - lowpass(x, k)


def noise(d):
    return rng.uniform(-1, 1, int(d * SR))


# ------------------------------------------------------------- instruments
def epiano(m, d, vel=0.5):
    t = tvec(d + 0.6)
    f = mtof(m)
    s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t + 0.3)
         + 0.08 * np.sin(2 * np.pi * f * 7.02 * t) * np.exp(-t * 18))
    s *= np.exp(-t * 2.2) * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t))
    e = np.ones_like(t)
    rel = int(d * SR)
    e[rel:] = np.exp(-(t[rel:] - d) * 9)
    return s * e * env_adsr(len(t), 0.004, 0.02) * vel


def bass(m, d, vel=0.6):
    t = tvec(d)
    f = mtof(m)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return s * np.exp(-t * 1.5) * env_adsr(len(t), 0.006, 0.04) * vel


def kick(vel=1.0):
    t = tvec(0.35)
    f = 45 + 90 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) * vel


def snare(vel=0.5):
    t = tvec(0.22)
    return (highpass(noise(0.22), 3) * 0.8 + 0.4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 22) * vel


def clap(vel=0.5):
    t = tvec(0.2)
    n = highpass(noise(0.2), 4)
    e = np.exp(-t * 30) + 0.6 * np.exp(-np.maximum(t - 0.012, 0) * 30) * (t > 0.012)
    return n * e * vel


def hat(vel=0.25, d=0.06):
    t = tvec(d)
    return highpass(noise(d), 2) * np.exp(-t * 70) * vel


def pluck(m, d=0.25, vel=0.5):
    t = tvec(d)
    f = mtof(m)
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.2 * np.sin(6 * np.pi * f * t)
    return s * np.exp(-t * 14) * env_adsr(len(t), 0.002, 0.02) * vel


def square(m, d, vel=0.3, duty_soft=4):
    t = tvec(d)
    f = mtof(m)
    s = np.sign(np.sin(2 * np.pi * f * t))
    s = lowpass(s, duty_soft)
    return s * env_adsr(len(t), 0.002, 0.03) * np.exp(-t * 4) * vel


def musicbox(m, d=1.2, vel=0.35):
    t = tvec(d)
    f = mtof(m)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6)
    return s * np.exp(-t * 3.5) * env_adsr(len(t), 0.002, 0.05) * vel


def bell(f, d=1.2, vel=0.5):
    t = tvec(d)
    s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 4)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 8))
    return s * np.exp(-t * 3) * env_adsr(len(t), 0.001, 0.05) * vel


# ------------------------------------------------------------- music sections
def section_lofi(t0, t1):
    bpm = 80
    beat = 60 / bpm
    chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]
    roots = [41, 40, 38, 36]
    mel = [72, None, 69, 67, None, 64, 67, None, 69, None, 72, 74, None, 72, 69, None]
    b = 0
    while t0 + b * beat < t1:
        t = t0 + b * beat
        ci = (b // 2) % 4
        if b % 2 == 0:
            for k, m in enumerate(chords[ci]):
                place(music, t + 0.012 * k, epiano(m, beat * 1.9, 0.16))
            place(music, t, bass(roots[ci], beat * 1.8, 0.5))
        if b % 4 in (0, 2):
            place(music, t, kick(0.75))
        if b % 4 in (1, 3):
            place(music, t, snare(0.25))
        place(music, t, hat(0.12))
        place(music, t + beat * 0.6, hat(0.08))
        m = mel[b % len(mel)]
        if m:
            place(music, t + beat * 0.5, epiano(m, beat * 0.8, 0.12))
        b += 1
    # vinyl crackle
    cr = np.zeros(int((t1 - t0) * SR))
    idx = rng.integers(0, len(cr), int((t1 - t0) * 40))
    cr[idx] = rng.uniform(-0.25, 0.25, len(idx))
    place(music, t0, cr + highpass(noise(t1 - t0), 2) * 0.01)


def section_sneaky(t0, t1):
    beat = 60 / 112 / 2
    seq = [50, None, 53, None, 57, None, 56, None, 55, None, 53, 52, 50, None, 45, None]
    i = 0
    while t0 + i * beat < t1:
        t = t0 + i * beat
        m = seq[i % len(seq)]
        if m:
            place(music, t, pluck(m, 0.22, 0.45))
        if i % 4 == 0:
            place(music, t, pluck(38, 0.3, 0.4))
        if i % 2 == 1:
            place(music, t, hat(0.05, 0.03))
        i += 1


def section_sad(t0):
    for k, m in enumerate([67, 66, 65, 64]):
        d = 0.32 if k < 3 else 0.9
        place(music, t0 + k * 0.32, epiano(m, d, 0.22))
        place(music, t0 + k * 0.32, epiano(m - 12, d, 0.12))


def section_upbeat(t0, t1):
    bpm = 128
    beat = 60 / bpm
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    roots = [36, 31, 33, 29]
    b = 0
    while t0 + b * beat < t1 - 0.01:
        t = t0 + b * beat
        ci = (b // 2) % 4
        place(music, t, kick(0.8))
        if b % 2 == 1:
            place(music, t, clap(0.35))
        place(music, t + beat * 0.5, hat(0.12))
        place(music, t, bass(roots[ci], beat * 0.45, 0.5))
        place(music, t + beat * 0.5, bass(roots[ci] + 12, beat * 0.4, 0.4))
        for m in chords[ci]:
            place(music, t + beat * 0.5, pluck(m + 12, 0.18, 0.18))
        b += 1


def section_hyper(t0, t1):
    bpm = 160
    beat = 60 / bpm
    arps = [[72, 76, 79, 84], [71, 74, 79, 83], [69, 72, 76, 81], [65, 69, 72, 77]]
    roots = [36, 31, 33, 29]
    b = 0
    while t0 + b * beat < t1 - 0.01:
        t = t0 + b * beat
        ci = (b // 4) % 4
        place(music, t, kick(0.85))
        if b % 2 == 1:
            place(music, t, snare(0.3))
        for k in range(4):
            place(music, t + k * beat / 4, square(arps[ci][k], beat / 4 * 0.9, 0.1))
            place(music, t + k * beat / 4, hat(0.06, 0.03))
        place(music, t, square(roots[ci], beat * 0.9, 0.16, 12))
        b += 1


def section_lullaby(t0, t1):
    notes = [(0.0, 84), (0.4, 79), (0.8, 76), (1.2, 79), (1.6, 81), (2.0, 79), (2.4, 76)]
    for dt, m in notes:
        if t0 + dt < t1:
            place(music, t0 + dt, musicbox(m, 1.4, 0.28))
    for dt, m in ((0.0, 48), (0.8, 55), (1.6, 53)):
        place(music, t0 + dt, epiano(m, 0.8, 0.12))


def record_scratch(t0):
    d = 0.32
    t = tvec(d)
    rate = 1 + 3 * np.sin(np.pi * t / d * 1.5)
    src = lowpass(noise(d * 4), 6)
    idx = np.clip(np.cumsum(np.abs(rate)) * 1.6, 0, len(src) - 1).astype(int)
    sig = src[idx] * np.exp(-t * 4) * 1.3
    sig += 0.4 * np.sin(2 * np.pi * np.cumsum(300 + 900 * np.sin(np.pi * t / d)) / SR) * np.exp(-t * 6)
    place(sfx, t0, sig, 0.55)


# ------------------------------------------------------------- formant voice
VOW = {
    "a": (800, 1250, 2600), "o": (520, 880, 2600), "u": (340, 900, 2400),
    "e": (560, 1900, 2600), "i": (320, 2400, 3100), "uh": (640, 1250, 2600),
    "m": (260, 1100, 2400), "n": (280, 1700, 2600), "ae": (720, 1700, 2600),
}


def resonate(x, freqs, bw):
    """Time-varying 2-pole resonator (per-sample python loop, short signals only)."""
    y = np.zeros_like(x)
    y1 = y2 = 0.0
    r = math.exp(-math.pi * bw / SR)
    for n in range(len(x)):
        c = 2 * r * math.cos(2 * math.pi * freqs[n] / SR)
        v = x[n] + c * y1 - r * r * y2
        y[n] = v
        y2, y1 = y1, v
    return y * (1 - r)


def vocal(pitch_pts, vowel_pts, amp_pts, dur, breath=0.08, shift=1.12, vib=0.0):
    """pitch/vowel/amp: lists of (time_frac, value). Returns signal."""
    n = int(dur * SR)
    tt = np.linspace(0, 1, n)
    f0 = np.interp(tt, [p[0] for p in pitch_pts], [p[1] for p in pitch_pts])
    if vib:
        f0 = f0 * (1 + vib * np.sin(2 * np.pi * 6 * tt * dur))
    ph = 2 * np.pi * np.cumsum(f0) / SR
    src = np.zeros(n)
    for k in range(1, 24):
        src += np.sin(k * ph) / k * (k * f0 < 6000)
    src += noise(dur)[:n] * breath * 6
    amp = np.interp(tt, [p[0] for p in amp_pts], [p[1] for p in amp_pts])
    # formant tracks
    keys = [v[0] for v in vowel_pts]
    out = np.zeros(n)
    for fi, (bw, g) in enumerate(((90, 1.0), (110, 0.7), (160, 0.35))):
        track = np.interp(tt, keys, [VOW[v[1]][fi] * shift for v in vowel_pts])
        out += resonate(src, track, bw) * g
    out *= amp
    return out / (np.max(np.abs(out)) + 1e-9)


def breathy(d, f=1200, amp_pts=((0, 0), (0.2, 1), (1, 0))):
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    x = noise(d)[:n]
    y = resonate(x, np.full(n, f), 600) + 0.5 * resonate(x, np.full(n, f * 2.1), 900)
    a = np.interp(tt, [p[0] for p in amp_pts], [p[1] for p in amp_pts])
    y = y * a
    return y / (np.max(np.abs(y)) + 1e-9)


def build_voices():
    # 2.45 yawn: "haaa-aawm"
    y = vocal([(0, 230), (0.25, 330), (0.7, 250), (1, 150)],
              [(0, "a"), (0.6, "a"), (0.85, "o"), (1, "m")],
              [(0, 0), (0.12, 0.7), (0.3, 1), (0.8, 0.8), (1, 0)], 1.35, breath=0.12)
    place(voice, 2.45, y, 0.55)
    place(voice, 2.4, breathy(0.25, 1400), 0.2)
    # 5.75 slurp attempt "mm?"
    place(voice, 6.15, vocal([(0, 200), (1, 270)], [(0, "m"), (1, "m")], [(0, 0), (0.3, 1), (1, 0)], 0.35), 0.35)
    # 7.03 "HUH?!"
    place(voice, 7.0, breathy(0.07, 1300), 0.3)
    place(voice, 7.05, vocal([(0, 210), (0.6, 380), (1, 470)], [(0, "uh"), (1, "uh")],
                             [(0, 0), (0.1, 1), (0.75, 1), (1, 0)], 0.42, shift=1.15), 0.75)
    # 8.4 confused "hmm-hmm?"
    place(voice, 8.45, vocal([(0, 260), (0.5, 230), (1, 300)], [(0, "m"), (1, "m")], [(0, 0), (0.2, 1), (0.45, 0.2), (0.6, 1), (1, 0)], 0.6), 0.35)
    # 9.4 grunt standing up "hup"
    place(voice, 9.35, vocal([(0, 240), (1, 200)], [(0, "uh"), (1, "u")], [(0, 0), (0.2, 1), (1, 0)], 0.2), 0.35)
    # 13.0 hopeful "ooh~"
    place(voice, 12.95, vocal([(0, 300), (0.5, 380), (1, 360)], [(0, "u"), (1, "o")], [(0, 0), (0.25, 1), (1, 0)], 0.5), 0.35)
    # 14.38 "NOOOO"
    place(voice, 14.38, vocal([(0, 340), (0.15, 360), (1, 170)], [(0, "n"), (0.1, "o"), (0.8, "o"), (1, "u")],
                              [(0, 0), (0.1, 1), (0.85, 0.7), (1, 0)], 1.25, vib=0.035, shift=1.12), 0.7)
    # 15.62 "AHA!"
    place(voice, 15.62, vocal([(0, 300), (0.4, 290), (0.55, 380), (1, 450)], [(0, "a"), (0.4, "a"), (0.5, "a"), (1, "a")],
                              [(0, 0), (0.08, 1), (0.35, 0.9), (0.45, 0.05), (0.55, 1), (0.9, 1), (1, 0)], 0.5, breath=0.1), 0.65)
    # 18.35 "hehehe"
    for k in range(3):
        place(voice, 18.35 + k * 0.14, vocal([(0, 400 + k * 15), (1, 360 + k * 15)], [(0, "e"), (1, "i")],
                                             [(0, 0), (0.15, 1), (1, 0)], 0.12, breath=0.25), 0.55)
    # 20.45 "AAH!" (sprayed)
    place(voice, 20.42, vocal([(0, 380), (0.3, 480), (1, 330)], [(0, "a"), (1, "ae")], [(0, 0), (0.05, 1), (1, 0)], 0.45), 0.7)
    # 21.9 dazed "...mm?"
    place(voice, 21.9, vocal([(0, 180), (1, 250)], [(0, "m"), (1, "m")], [(0, 0), (0.4, 1), (1, 0)], 0.45), 0.35)
    # 22.6 sip
    place(voice, 22.6, breathy(0.35, 2600, ((0, 0), (0.5, 1), (1, 0))), 0.18)
    # 23.0 "WOO-HOOO!"
    place(voice, 23.0, vocal([(0, 300), (1, 520)], [(0, "u"), (1, "u")], [(0, 0), (0.15, 1), (1, 0.2)], 0.34), 0.8)
    place(voice, 23.33, breathy(0.06, 1200), 0.25)
    place(voice, 23.36, vocal([(0, 540), (0.5, 680), (1, 600)], [(0, "u"), (1, "o")], [(0, 0), (0.1, 1), (0.8, 0.8), (1, 0)], 0.55), 0.8)
    # 27.32 "YAY!"
    place(voice, 27.32, vocal([(0, 420), (0.5, 500), (1, 440)], [(0, "i"), (0.3, "a"), (1, "i")], [(0, 0), (0.12, 1), (1, 0)], 0.4), 0.7)
    # snores
    for t0 in (28.35, 29.25):
        n = int(0.7 * SR)
        tt = np.arange(n) / SR
        pulses = (np.sin(2 * np.pi * 34 * tt) > 0.6).astype(float)
        sn = lowpass(pulses * noise(0.7)[:n] + 0.3 * pulses, 12)
        sn *= np.sin(np.pi * tt / 0.7) ** 1.5
        place(voice, t0, sn / (np.max(np.abs(sn)) + 1e-9), 0.45)
        w = tvec(0.45)
        wh = np.sin(2 * np.pi * np.cumsum(900 + 300 * w / 0.45) / SR) * np.sin(np.pi * w / 0.45) * 0.4
        place(voice, t0 + 0.72, wh + breathy(0.45, 1800) * 0.3, 0.3)


# ------------------------------------------------------------- SFX
def click():
    t = tvec(0.03)
    return highpass(noise(0.03), 2) * np.exp(-t * 300) * rng.uniform(0.5, 1)


def typing(t0, t1, rate):
    t = t0
    while t < t1:
        place(sfx, t, click(), 0.35)
        t += rng.uniform(0.6, 1.4) / rate


def whoosh(t0, d=0.35, g=0.35, up=True):
    n = int(d * SR)
    tt = np.linspace(0, 1, n)
    x = noise(d)[:n]
    k = 3
    y = lowpass(x, k) * np.sin(np.pi * tt) ** 2
    place(sfx, t0, y, g)


def plip(t0, f0=1400, g=0.4):
    t = tvec(0.12)
    f = f0 * np.exp(-t * 12) + 300
    place(sfx, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 30), g)


def thud(t0, g=0.5, f=70):
    t = tvec(0.2)
    sig = np.sin(2 * np.pi * np.cumsum(f + 60 * np.exp(-t * 40)) / SR) * np.exp(-t * 22)
    sig += lowpass(noise(0.2), 10) * np.exp(-t * 40) * 0.5
    place(sfx, t0, sig, g)


def beep(t0, f=1800, d=0.09, g=0.25):
    t = tvec(d)
    place(sfx, t0, np.sin(2 * np.pi * f * t) * env_adsr(len(t), 0.003, 0.02), g)


def build_sfx():
    typing(0.25, 2.4, 11)
    typing(3.85, 4.4, 11)
    whoosh(5.15, 0.4, 0.2)
    plip(6.9, 1300, 0.5)
    record_scratch(6.98)
    whoosh(7.0, 0.25, 0.3)
    for k in range(5):
        whoosh(8.4 + k * 0.15, 0.12, 0.18)
    # chair squeak
    t = tvec(0.25)
    place(sfx, 9.35, np.sin(2 * np.pi * np.cumsum(700 + 400 * np.sin(t * 30)) / SR) * np.exp(-t * 8) * 0.25, 1.0)
    # footsteps walk 10.0-12.2
    tt = 10.0
    while tt < 12.2:
        thud(tt + 0.1, 0.35, 90)
        tt += 0.275
    beep(12.45, 900, 0.03, 0.2)  # clink
    plip(12.5, 2500, 0.15)
    beep(12.72, 1800, 0.09, 0.25)
    # machine rumble 12.85-13.8
    d = 0.95
    t = tvec(d)
    rum = (np.sign(np.sin(2 * np.pi * 55 * t)) * 0.5 + lowpass(noise(d), 20)) * (1 + 0.5 * np.sin(2 * np.pi * 12 * t))
    rum *= env_adsr(len(t), 0.05, 0.2)
    place(sfx, 12.85, lowpass(rum, 6), 0.3)
    # buzzer
    for k in range(2):
        t = tvec(0.22)
        bz = lowpass(np.sign(np.sin(2 * np.pi * 110 * t)), 3) * env_adsr(len(t), 0.005, 0.03)
        place(sfx, 13.82 + k * 0.28, bz, 0.25)
    plip(14.2, 900, 0.3)
    # pop + ding (idea)
    plip(15.6, 2400, 0.3)
    place(sfx, 15.62, bell(1760, 1.2, 0.35))
    place(sfx, 15.62, bell(2637, 1.0, 0.15))
    # fast footsteps
    tt = 16.2
    while tt < 17.5:
        thud(tt, 0.3, 110)
        tt += 0.17
    # drawer slide
    d = 0.4
    t = tvec(d)
    place(sfx, 17.62, lowpass(noise(d), 4) * np.sin(np.pi * t / d) * (1 + 0.5 * np.sin(2 * np.pi * 40 * t)), 0.3)
    # sparkle
    for k, f in enumerate((2093, 2637, 3136, 4186)):
        place(sfx, 18.3 + k * 0.06, bell(f, 0.5, 0.12))
    # can shaking
    tt = 18.8
    while tt < 19.85:
        d = 0.09
        t = tvec(d)
        place(sfx, tt, highpass(noise(d), 3) * np.sin(np.pi * t / d) * 0.6 + lowpass(noise(d), 30) * 0.4, 0.35)
        tt += 0.142
    # tab click + PSSSHH
    beep(20.25, 3200, 0.015, 0.4)
    d = 1.3
    t = tvec(d)
    ps = highpass(noise(d), 2) * (np.exp(-t * 2.2) * 0.9 + 0.1) * env_adsr(len(t), 0.004, 0.3)
    place(sfx, 20.3, ps, 0.8)
    place(sfx, 20.3, lowpass(noise(0.3), 12) * np.exp(-tvec(0.3) * 10), 0.6)
    thud(20.42, 0.4, 120)
    # drips
    for tt in (21.4, 21.85, 22.25):
        plip(tt, 1600, 0.3)
    # zip whoosh
    whoosh(23.38, 0.4, 0.5)
    # crazy typing
    typing(23.95, 27.3, 34)
    # success chime
    for k, f in enumerate((1047, 1319, 1568, 2093)):
        place(sfx, 27.3 + k * 0.07, bell(f, 1.0, 0.25))
    # head thud
    thud(27.98, 0.6, 80)
    # birds at sunrise
    for t0 in (28.9, 29.1, 29.5):
        t = tvec(0.12)
        f = 3200 + 1200 * np.sin(np.pi * t / 0.12)
        place(sfx, t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.12) * 0.15, 1.0)


def build_music():
    section_lofi(0.0, 7.0)
    # hard cut at the scratch
    i = int(6.99 * SR)
    music[i:] *= 0
    music[i - 400:i] *= np.linspace(1, 0, 400)
    section_sneaky(8.1, 13.8)
    section_sad(14.5)
    section_upbeat(15.65, 20.25)
    i = int(20.27 * SR)
    music[i:] *= 0
    record_scratch(20.27)
    section_hyper(23.15, 27.3)
    i = int(27.32 * SR)
    music[i:] *= 0
    section_lullaby(28.1, 30.0)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "audio.wav"
    build_music()
    build_sfx()
    build_voices()
    mix = 0.58 * music / (np.max(np.abs(music)) + 1e-9) + 0.75 * sfx + 0.9 * voice
    # fades
    fi = int(0.4 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    fo = int(0.6 * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = np.tanh(mix * 1.1)
    mix = mix / np.max(np.abs(mix)) * 0.89
    # slight stereo width via tiny delay on music
    left = mix
    right = np.concatenate([np.zeros(12), mix[:-12]])
    st = np.stack([left, right], axis=1)
    pcm = (st * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main()
