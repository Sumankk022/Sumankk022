"""
Shared engine for the cartoon reel series.

Builds on render.py (rig, face, painter, camera helpers) and audio.py
(instruments, formant voice, SFX) and adds:
  * Outfit-driven character drawing (hats, sleeves, scarves, glasses...)
  * Keyframe pose tracks + walk cycles
  * Generic particles / rain / snow / stars effects
  * An Episode runner:  python3 epX.py video <dir> | audio <wav> | preview <dir> t1,t2..
"""
import math
import os
import random
import subprocess
import sys
from multiprocessing import Process

import numpy as np
from PIL import Image, ImageChops, ImageDraw

import audio as A
import render as R
from render import (FPS, H, SS, W, Cam, Painter, Pose, add, back_out, blend_pose, clamp, ease,
                    ease_in, ease_out, keyed, lerp, lerp2, lerp_col, rot, seg, up_vec, _font,
                    FONT_BOLD, C_BLACK, C_RIM)

STAND_Y = 590.0
FLOOR = 800.0
DUR = 30.0
NFRAMES = int(DUR * FPS)


# ======================================================================= outfit
class Outfit:
    def __init__(self, **kw):
        self.top = (38, 108, 222)
        self.top_dark = (28, 80, 175)
        self.sleeve = "long"      # long | short | none
        self.hood = False         # hood hanging behind the neck
        self.pocket = False
        self.pants = C_BLACK
        self.shorts = False
        self.shoes = (8, 8, 12)
        self.boots = None         # colour of tall boots
        self.hat = None           # chef | beanie | headband | hood_up | cap
        self.hat_col = (240, 240, 240)
        self.hat_col2 = (220, 60, 60)
        self.glasses = None       # up | on
        self.scarf = None
        self.apron = None
        self.neckerchief = None
        self.wrist = None
        self.__dict__.update(kw)


def draw_char(P, p, t, o, ex=None):
    ex = ex or {}
    s = R.skeleton(p)
    f = p.face
    off = (f * 4.5, -2.5)
    dark = (8, 8, 12)

    def col(rim, c):
        return C_RIM if rim else c

    def L(rim, a, b, w, c):
        o_ = off if rim else (0, 0)
        P.line(add(a, o_), add(b, o_), w, col(rim, c))

    def C(rim, c_, r, c):
        o_ = off if rim else (0, 0)
        P.circle(c_[0] + o_[0], c_[1] + o_[1], r, col(rim, c))

    def leg(rim, hip, knee, foot, base):
        thigh = o.pants if not o.shorts else o.pants
        shin = o.pants if not o.shorts else base
        L(rim, hip, knee, 31, thigh if thigh != C_BLACK else base)
        L(rim, knee, foot, 29, shin if shin != C_BLACK else base)
        if o.boots:
            mid = lerp2(knee, foot, 0.45)
            L(rim, mid, foot, 33, o.boots)
        fc = o.boots or o.shoes
        o_ = off if rim else (0, 0)
        P.ellipse(foot[0] + f * 12 + o_[0], foot[1] + 2 + o_[1], 26, 12, col(rim, fc))

    def arm(rim, sh, el, hand, c_up, front):
        w1, w2 = (30, 28) if front else (28, 26)
        up_c = c_up if o.sleeve in ("long", "short") else (C_BLACK if front else dark)
        lo_c = c_up if o.sleeve == "long" else (C_BLACK if front else dark)
        L(rim, sh, el, w1, up_c)
        L(rim, el, hand, w2, lo_c)
        if o.wrist and not rim:
            P.line(lerp2(el, hand, 0.72), lerp2(el, hand, 0.86), w2 + 3, o.wrist)
        C(rim, hand, 15 if front else 14, C_BLACK if front else dark)

    def head_at(dx, dy):
        v = rot((dx * f, dy), s["head_ang"])
        return (s["head"][0] + v[0], s["head"][1] + v[1])

    def hat_back(rim):
        if o.hat == "hood_up":
            c = head_at(-6, -4)
            C(rim, c, 64, o.hat_col)

    def hat_front(rim):
        o_ = off if rim else (0, 0)
        hc = s["head"]
        if o.hat == "chef":
            band = [head_at(-42, -36), head_at(42, -36), head_at(40, -58), head_at(-40, -58)]
            P.poly([add(q, o_) for q in band], col(rim, o.hat_col))
            for dx, dy, r in ((-26, -82, 28), (0, -96, 32), (26, -82, 28), (0, -70, 30)):
                c = head_at(dx, dy)
                P.circle(c[0] + o_[0], c[1] + o_[1], r, col(rim, o.hat_col))
        elif o.hat == "beanie":
            pts = [head_at(54 * math.cos(a), -34 + 44 * math.sin(a))
                   for a in np.linspace(math.pi, 2 * math.pi, 14)]
            P.poly([add(q, o_) for q in pts], col(rim, o.hat_col))
            L(rim, head_at(-54, -36), head_at(54, -36), 14, o.hat_col2)
            C(rim, head_at(-4, -84), 15, o.hat_col2)
        elif o.hat == "headband":
            L(rim, head_at(-52, -26), head_at(52, -30), 13, o.hat_col)
            if not rim:
                tail = head_at(-52, -26)
                fl_ = math.sin(t * 9) * 6
                P.line(tail, (tail[0] - f * 26, tail[1] + 18 + fl_), 7, o.hat_col)
                P.line(tail, (tail[0] - f * 30, tail[1] + 4 + fl_), 7, o.hat_col)
        elif o.hat == "hood_up" and not rim:
            # hood rim over the forehead
            pts = [head_at(60 * math.cos(a), -2 + 62 * math.sin(a)) for a in np.linspace(math.pi * 1.05, math.pi * 1.95, 12)]
            inner = [head_at(48 * math.cos(a), 4 + 50 * math.sin(a)) for a in np.linspace(math.pi * 1.95, math.pi * 1.05, 12)]
            P.poly(pts + inner, o.hat_col)
        elif o.hat == "cap":
            pts = [head_at(54 * math.cos(a), -6 + 54 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 14)]
            P.poly([add(q, o_) for q in pts], col(rim, o.hat_col))
            L(rim, head_at(30, -8), head_at(86, -4), 10, o.hat_col)

    def shapes(rim):
        leg(rim, s["hip_b"], s["kb"], s["fb"], dark)
        arm(rim, s["sh_b"], s["eb"], s["hb"], darker(o.top_dark), False)
        if o.hood:
            hu = up_vec(p.torso + p.tilt * 0.4, f)
            hc = (s["neck"][0] - f * 22 + hu[0] * 10, s["neck"][1] + hu[1] * 10 + 8)
            o_ = off if rim else (0, 0)
            P.ellipse(hc[0] + o_[0], hc[1] + o_[1], 30, 44, col(rim, o.top_dark))
        if o.scarf:
            u = up_vec(p.torso, f)
            n = s["neck"]
            fl_ = math.sin(t * 7) * 8
            tail = [n, (n[0] - f * 30, n[1] + 14 + fl_ * 0.3), (n[0] - f * 56, n[1] + 30 + fl_)]
            for a, b in zip(tail, tail[1:]):
                L(rim, a, b, 18, darker(o.scarf))
        hat_back(rim)
        L(rim, s["hip"], s["shoulder"], 62, o.top)
        if not rim:
            u = up_vec(p.torso, f)
            if o.pocket:
                pc = (s["hip"][0] + u[0] * 30 + f * 6, s["hip"][1] + u[1] * 30)
                P.line(pc, (pc[0] + u[0] * 26, pc[1] + u[1] * 26), 30, o.top_dark)
            if o.apron:
                a0 = (s["hip"][0] + f * 14 - u[0] * 30, s["hip"][1] - u[1] * 30)
                a1 = (s["hip"][0] + f * 14 + u[0] * 118, s["hip"][1] + u[1] * 118)
                P.line(a0, a1, 40, o.apron)
            if o.sleeve == "none":
                # tank-top: show the shoulders as skin
                P.circle(s["shoulder"][0], s["shoulder"][1] - 4, 20, C_BLACK)
        leg(rim, s["hip"], s["kf"], s["ff"], C_BLACK)
        C(rim, s["head"], R.HEAD_R, C_BLACK)
        hat_front(rim)

    def front_arm(rim):
        arm(rim, s["shoulder"], s["ef"], s["hf"], o.top, True)

    shapes(True)
    front_arm(True)
    shapes(False)
    R.draw_face(P, p, s, t, ex)
    # neck pieces
    n = s["neck"]
    if o.scarf:
        P.line((n[0] - f * 26, n[1] + 6), (n[0] + f * 22, n[1] + 2), 22, o.scarf)
    if o.neckerchief:
        P.line((n[0] - f * 22, n[1] + 8), (n[0] + f * 20, n[1] + 4), 14, o.neckerchief)
        P.poly([(n[0] + f * 10, n[1] + 6), (n[0] + f * 26, n[1] + 6), (n[0] + f * 16, n[1] + 30)], o.neckerchief)
    if o.glasses:
        dy = -34 if o.glasses == "up" else -8
        e1, e2 = head_at(14, dy), head_at(37, dy + 2)
        P.line(e1, e2, 4, (30, 30, 30))
        for e, sc in ((e1, 1.0), (e2, 0.8)):
            P.ellipse(e[0], e[1], 12 * sc, 9, (30, 32, 40))
            P.ellipse(e[0] - 3 * f, e[1] - 3, 4 * sc, 2.5, (120, 140, 170))
    if ex.get("wet"):
        for k in range(5):
            ph = (t * 1.7 + k * 0.21) % 1
            c = head_at(-40 + k * 20, 40 + 50 * ph)
            P.ellipse(c[0], c[1], 4, 6, (150, 200, 255))
    if ex.get("on_head"):
        ex["on_head"](P, s)
    front_arm(False)
    if ex.get("held"):
        ex["held"](P, s["hf"], ex.get("item_ang", 0.0), f)
    if ex.get("held_b"):
        ex["held_b"](P, s["hb"], ex.get("item_ang_b", 0.0), f)
    return s


def darker(c, k=0.8):
    return tuple(int(v * k) for v in c)


# ======================================================================= poses
def stand(x, face=1, **kw):
    return R.stand_pose(x, face=face, **kw)


def crouch(x, face=1, depth=1.0, **kw):
    p = R.stand_pose(x, face=face, torso=0.55 * depth, tilt=0.1)
    p.hip = (x, STAND_Y + 85 * depth)
    p.foot_b = (x - face * 32, 790)
    p.foot_f = (x + face * 40, 790)
    p.hand_b = (x + face * 70, 720)
    p.hand_f = (x + face * 90, 720)
    p.__dict__.update(kw)
    return p


def floor_sit(x, face=1, **kw):
    p = R.stand_pose(x, face=face, torso=-0.1, tilt=0.0)
    p.hip = (x, 762)
    p.foot_b = (x + face * 170, 792)
    p.foot_f = (x + face * 190, 792)
    p.hand_b = (x - face * 50, 780)
    p.hand_f = (x - face * 40, 785)
    p.__dict__.update(kw)
    return p


def walk(p, t, t0, t1, x0, x1, period=0.55, stride=46, lift=26, bob=6, arms=True, swing=30):
    k = clamp((t - t0) / (t1 - t0))
    x = lerp(x0, x1, k)
    face = 1 if x1 >= x0 else -1
    ph = (t - t0) * 2 * math.pi / period
    fb, ff = R.walk_feet(x, face, ph, stride, lift)
    p.face = face
    p.hip = (x, STAND_Y - bob * abs(math.sin(ph)))
    p.foot_b, p.foot_f = fb, ff
    if arms:
        p.hand_b = (x - face * swing * math.sin(ph), STAND_Y + 36)
        p.hand_f = (x + face * swing * math.sin(ph), STAND_Y + 38)
    return p


class Track:
    """keys: list of (t_start, pose_or_fn(t), blend_duration)."""

    def __init__(self, keys):
        self.keys = keys

    @staticmethod
    def _ev(k, t):
        return k[1](t) if callable(k[1]) else k[1]

    def at(self, t):
        ks = self.keys
        i = 0
        for j, k in enumerate(ks):
            if k[0] <= t:
                i = j
        cur = self._ev(ks[i], t)
        if i == 0:
            return cur
        prev = self._ev(ks[i - 1], t)
        k = seg(t, ks[i][0], ks[i][0] + ks[i][2]) if ks[i][2] > 0 else 1.0
        if k >= 1:
            return cur
        return blend_pose(prev, cur, k)


def P_(base, **kw):
    """copy pose with overrides"""
    p = Pose()
    p.__dict__.update(base.__dict__)
    p.__dict__.update(kw)
    return p


# ======================================================================= camera
def cam_keys(t, keys, shakes=()):
    cx, cy, s = keyed(t, keys)
    return shaken(Cam(cx, cy, s), t, shakes)


def shaken(cam, t, shakes):
    sh = 0.0
    for t0, dur, amp in shakes:
        if t0 <= t < t0 + dur:
            sh = max(sh, amp * (1 - (t - t0) / dur))
    if sh:
        cam.cx += sh * math.sin(t * 91) / cam.s
        cam.cy += sh * math.cos(t * 77) / cam.s
    return cam


# ======================================================================= effects
def burst(P, origin, tau, seed=1, n=80, a0=180, a1=360, v0=200, v1=700, g=1300,
          r0=5, r1=14, cols=((245, 245, 240),), life=1.1):
    if tau is None or tau < 0 or tau > life + 0.3:
        return
    rnd = random.Random(seed)
    for _ in range(n):
        a = math.radians(rnd.uniform(a0, a1))
        v = rnd.uniform(v0, v1)
        r = rnd.uniform(r0, r1)
        d = rnd.random() * 0.15
        c = cols[rnd.randrange(len(cols))]
        tt = tau - d
        if tt < 0:
            continue
        x = origin[0] + math.cos(a) * v * tt
        y = origin[1] + math.sin(a) * v * tt + 0.5 * g * tt * tt
        rr = r * (1 - clamp(tt / life))
        if rr > 0.5:
            P.circle(x, y, rr, c)


def rain(P, cam, t, amount=1.0, col=(170, 190, 230), seed=3, slant=0.25):
    if amount <= 0:
        return
    rnd = random.Random(seed)
    vw, vh = W / cam.s, H / cam.s
    x0, y0 = cam.cx - vw / 2, cam.cy - vh / 2
    for _ in range(int(160 * amount)):
        bx, by, sp = rnd.random(), rnd.random(), rnd.uniform(900, 1300)
        y = y0 + ((by * vh + t * sp) % vh)
        x = x0 + ((bx * vw - (t * sp) * slant) % vw)
        P.line((x, y), (x + slant * 30, y + 30), 2.2, col, cap=False)


def snow(P, cam, t, amount=1.0, seed=5):
    rnd = random.Random(seed)
    vw, vh = W / cam.s, H / cam.s
    x0, y0 = cam.cx - vw / 2, cam.cy - vh / 2
    for _ in range(int(110 * amount)):
        bx, by, sp, r = rnd.random(), rnd.random(), rnd.uniform(40, 110), rnd.uniform(2.5, 6)
        y = y0 + ((by * vh + t * sp) % vh)
        x = x0 + ((bx * vw + 25 * math.sin(t * 1.3 + by * 9)) % vw)
        P.circle(x, y, r, (250, 252, 255))


def stars_ring(P, s, t, k=1.0):
    if k <= 0:
        return
    hc = s["head"]
    for i in range(3):
        a = t * 5 + i * 2 * math.pi / 3
        x, y = hc[0] + 62 * math.cos(a), hc[1] - 66 + 16 * math.sin(a)
        star(P, x, y, 14 * k, (255, 225, 80))


def star(P, x, y, r, col):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    P.poly(pts, col)


def shock_lines(P, s, col=(255, 255, 255)):
    hc = s["head"]
    for a in (-60, -30, 0, 30, 60):
        ra = math.radians(a - 90)
        P.line((hc[0] + math.cos(ra) * 75, hc[1] + math.sin(ra) * 75),
               (hc[0] + math.cos(ra) * 100, hc[1] + math.sin(ra) * 100), 6, col)


def sweat(P, s, t):
    hc = s["head"]
    for i in range(2):
        ph = (t * 2.2 + i * 0.5) % 1.0
        P.ellipse(hc[0] - 40 - i * 14, hc[1] - 30 + 60 * ph, 6, 9, (150, 210, 255))


def bulb(P, s, k):
    R.draw_bulb(P, s, k)


def music_notes(P, s, t, k=1.0):
    if k <= 0:
        return
    hc = s["head"]
    for i in range(2):
        ph = (t * 0.7 + i * 0.5) % 1
        x, y = hc[0] + 50 + 30 * ph, hc[1] - 50 - 90 * ph
        r = 9 * k * (1 - ph * 0.5)
        P.ellipse(x, y, r * 1.2, r, (255, 255, 255))
        P.line((x + r, y), (x + r, y - 30 * k), 3, (255, 255, 255))


# ======================================================================= episode runner
class Episode:
    def __init__(self, **kw):
        self.title = ("TITLE", "TWO")
        self.title_col = (255, 196, 92)
        self.end = ("THE END", "follow for more")
        self.outfit = Outfit()
        self.flashes = []     # (t0, dur, colour, alpha)
        self.tint = None      # fn(t) -> (colour, alpha) | None
        self.speed = None     # fn(t) -> amount
        self.__dict__.update(kw)


_VIG = None


def _overlay(img, ep, t):
    items = []
    if t < 3.4:
        a = seg(t, 0.25, 0.7) * (1 - seg(t, 2.8, 3.3))
        items.append((ep.title[0], 92, 250, a, (255, 255, 255)))
        items.append((ep.title[1], 150, 370, a, ep.title_col))
    if t > 28.6:
        a = seg(t, 28.6, 29.0)
        items.append((ep.end[0], 120, 300, a, (255, 255, 255)))
        items.append((ep.end[1], 46, 420, a, (255, 210, 140)))
    if not items:
        return img
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for s_, size, y, a, col in items:
        f = _font(FONT_BOLD, size)
        al = int(255 * a)
        d.text((W / 2 + 6, y + 8), s_, font=f, fill=(0, 0, 0, int(al * 0.55)), anchor="mm")
        d.text((W / 2, y), s_, font=f, fill=col + (al,), anchor="mm")
    base = img.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")


def frame(ep, t):
    global _VIG
    if _VIG is None:
        _VIG = R.make_vignette()
    pose, ex, fl = ep.story(t)
    cam = ep.camera(t, pose)
    img = Image.new("RGB", (W * SS, H * SS), (0, 0, 0))
    P = Painter(img, cam)
    ep.background(P, t, fl, cam)
    if hasattr(ep, "behind"):
        ep.behind(P, t, fl, cam)
    s = draw_char(P, pose, t, ep.outfit, ex)
    if hasattr(ep, "front"):
        ep.front(P, t, fl, s, cam, ex)
    if ep.speed:
        R.draw_speedlines(img, ep.speed(t), t)
    out = img.reduce(SS)
    out = ImageChops.multiply(out, _VIG)
    for t0, dur, col, al in ep.flashes:
        if t0 <= t < t0 + dur:
            out = Image.blend(out, Image.new("RGB", (W, H), col), al * (1 - (t - t0) / dur))
    if ep.tint:
        tt = ep.tint(t)
        if tt and tt[1] > 0:
            out = Image.blend(out, Image.new("RGB", (W, H), tt[0]), tt[1])
    out = _overlay(out, ep, t)
    fade = min(seg(t, 0.0, 0.5), 1 - seg(t, 29.55, 30.0))
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, fade)
    return out


def _chunk(ep, i0, i1, path):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(i0, i1):
        pr.stdin.write(frame(ep, i / FPS).tobytes())
    pr.stdin.close()
    pr.wait()


def mixdown(path, music_gain=0.58):
    m = A.music / (np.max(np.abs(A.music)) + 1e-9)
    mix = music_gain * m + 0.75 * A.sfx + 0.9 * A.voice
    fi, fo = int(0.4 * A.SR), int(0.6 * A.SR)
    mix[:fi] *= np.linspace(0, 1, fi)
    mix[-fo:] *= np.linspace(1, 0, fo)
    mix = np.tanh(mix * 1.1)
    mix = mix / np.max(np.abs(mix)) * 0.89
    right = np.concatenate([np.zeros(12), mix[:-12]])
    pcm = (np.stack([mix, right], axis=1) * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(A.SR)
        w.writeframes(pcm.tobytes())


def cut_music(t):
    i = int(t * A.SR)
    A.music[i:] *= 0
    A.music[max(0, i - 400):i] *= np.linspace(1, 0, min(i, 400))


def run(ep):
    mode = sys.argv[1]
    if mode == "audio":
        ep.sound()
        mixdown(sys.argv[2], getattr(ep, "music_gain", 0.58))
        return
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if mode == "preview":
        for ts in sys.argv[3].split(","):
            frame(ep, float(ts)).save(os.path.join(out, f"prev_{float(ts):05.2f}.png"))
        return
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    step = math.ceil(NFRAMES / workers)
    procs, parts = [], []
    for w in range(workers):
        a, b = w * step, min(NFRAMES, (w + 1) * step)
        path = os.path.join(out, f"part{w}.mp4")
        parts.append(path)
        pr = Process(target=_chunk, args=(ep, a, b, path))
        pr.start()
        procs.append(pr)
    for pr in procs:
        pr.join()
    with open(os.path.join(out, "parts.txt"), "w") as fh:
        for pth in parts:
            fh.write(f"file '{os.path.abspath(pth)}'\n")


# ======================================================================= voice / sfx helpers
V = A.voice
S = A.sfx
M = A.music
vocal, breathy, place, tvec, noise = A.vocal, A.breathy, A.place, A.tvec, A.noise


def say(t0, pitch, vowels, amp, dur, g=0.6, **kw):
    place(V, t0, vocal(pitch, vowels, amp, dur, **kw), g)


def v_huh(t):
    place(V, t - 0.05, breathy(0.07, 1300), 0.3)
    say(t, [(0, 210), (0.6, 380), (1, 470)], [(0, "uh"), (1, "uh")], [(0, 0), (0.1, 1), (0.75, 1), (1, 0)], 0.42, 0.75, shift=1.15)


def v_nooo(t, d=1.2):
    say(t, [(0, 340), (0.15, 360), (1, 170)], [(0, "n"), (0.1, "o"), (0.8, "o"), (1, "u")],
        [(0, 0), (0.1, 1), (0.85, 0.7), (1, 0)], d, 0.7, vib=0.035)


def v_yay(t):
    say(t, [(0, 420), (0.5, 500), (1, 440)], [(0, "i"), (0.3, "a"), (1, "i")], [(0, 0), (0.12, 1), (1, 0)], 0.4, 0.7)


def v_woohoo(t):
    say(t, [(0, 300), (1, 520)], [(0, "u"), (1, "u")], [(0, 0), (0.15, 1), (1, 0.2)], 0.34, 0.8)
    place(V, t + 0.33, breathy(0.06, 1200), 0.25)
    say(t + 0.36, [(0, 540), (0.5, 680), (1, 600)], [(0, "u"), (1, "o")], [(0, 0), (0.1, 1), (0.8, 0.8), (1, 0)], 0.55, 0.8)


def v_hehe(t, n=3):
    for k in range(n):
        say(t + k * 0.14, [(0, 400 + k * 15), (1, 360 + k * 15)], [(0, "e"), (1, "i")],
            [(0, 0), (0.15, 1), (1, 0)], 0.12, 0.55, breath=0.25)


def v_aha(t):
    say(t, [(0, 300), (0.4, 290), (0.55, 380), (1, 450)], [(0, "a"), (1, "a")],
        [(0, 0), (0.08, 1), (0.35, 0.9), (0.45, 0.05), (0.55, 1), (0.9, 1), (1, 0)], 0.5, 0.65, breath=0.1)


def v_tada(t):
    say(t, [(0, 330), (1, 330)], [(0, "a"), (1, "a")], [(0, 0), (0.2, 1), (1, 0)], 0.16, 0.6)
    say(t + 0.2, [(0, 440), (0.7, 470), (1, 440)], [(0, "a"), (1, "a")], [(0, 0), (0.1, 1), (0.8, 0.8), (1, 0)], 0.55, 0.65, vib=0.02)


def v_hmm(t, up=True, g=0.4):
    say(t, [(0, 200), (1, 280 if up else 160)], [(0, "m"), (1, "m")], [(0, 0), (0.3, 1), (1, 0)], 0.4, g)


def v_hum(t, notes, step=0.28, g=0.3):
    for k, m in enumerate(notes):
        f = A.mtof(m)
        say(t + k * step, [(0, f), (1, f)], [(0, "m"), (1, "u")], [(0, 0), (0.2, 1), (1, 0)], step * 0.95, g)


def v_whoa(t):
    say(t, [(0, 280), (0.5, 420), (1, 300)], [(0, "u"), (0.3, "o"), (1, "a")], [(0, 0), (0.15, 1), (1, 0)], 0.6, 0.7)


def v_aaah(t, d=1.0, g=0.7):
    say(t, [(0, 480), (0.3, 560), (1, 520)], [(0, "a"), (1, "ae")], [(0, 0), (0.05, 1), (0.9, 0.9), (1, 0)], d, g, vib=0.05)


def v_ow(t):
    say(t, [(0, 520), (1, 300)], [(0, "a"), (0.6, "o"), (1, "u")], [(0, 0), (0.08, 1), (1, 0)], 0.42, 0.8)


def v_ooh(t, g=0.5):
    say(t, [(0, 280), (0.5, 400), (1, 380)], [(0, "u"), (1, "o")], [(0, 0), (0.25, 1), (1, 0)], 0.6, g)


def v_strain(t, d=1.5, g=0.5):
    say(t, [(0, 170), (1, 240)], [(0, "n"), (0.2, "uh"), (1, "uh")], [(0, 0), (0.1, 1), (0.95, 1), (1, 0)], d, g, vib=0.06, breath=0.15)


def v_hup(t, g=0.45):
    say(t, [(0, 260), (1, 210)], [(0, "uh"), (1, "u")], [(0, 0), (0.2, 1), (1, 0)], 0.2, g)


def v_hey(t):
    place(V, t - 0.04, breathy(0.06, 1500), 0.3)
    say(t, [(0, 360), (1, 330)], [(0, "e"), (1, "i")], [(0, 0), (0.1, 1), (1, 0)], 0.35, 0.75)


def v_eek(t):
    say(t, [(0, 600), (1, 720)], [(0, "i"), (1, "i")], [(0, 0), (0.1, 1), (1, 0)], 0.3, 0.6)


def v_achoo(t):
    say(t, [(0, 300), (1, 420)], [(0, "a"), (1, "a")], [(0, 0), (0.3, 0.6), (1, 0.8)], 0.35, 0.4)
    place(V, t + 0.38, breathy(0.3, 2200, ((0, 1), (0.2, 0.8), (1, 0))), 0.7)
    say(t + 0.38, [(0, 380), (1, 250)], [(0, "u"), (1, "u")], [(0, 0), (0.1, 1), (1, 0)], 0.3, 0.6)


def v_nom(t, n=3):
    for k in range(n):
        say(t + k * 0.22, [(0, 260), (1, 240)], [(0, "m"), (0.5, "o"), (1, "m")], [(0, 0), (0.3, 1), (1, 0)], 0.18, 0.45)


def v_mmm(t):
    say(t, [(0, 230), (0.5, 330), (1, 260)], [(0, "m"), (1, "m")], [(0, 0), (0.2, 1), (1, 0)], 0.8, 0.5)


def v_uhoh(t):
    say(t, [(0, 340), (1, 330)], [(0, "uh"), (1, "uh")], [(0, 0), (0.2, 1), (1, 0)], 0.18, 0.6)
    say(t + 0.22, [(0, 270), (1, 250)], [(0, "o"), (1, "u")], [(0, 0), (0.2, 1), (1, 0)], 0.3, 0.6)


def v_sniff(t):
    for k in range(2):
        place(V, t + k * 0.18, breathy(0.12, 2500), 0.25)


def sfx_splash(t, d=1.0, g=0.6):
    tt = tvec(d)
    x = A.lowpass(noise(d), 3) * np.exp(-tt * 3.5) * A.env_adsr(len(tt), 0.01, 0.2)
    place(S, t, x, g)
    A.thud(t, 0.4, 70)


def sfx_pop(t, g=0.35):
    A.plip(t, 1800, g)


def sfx_wind(t, d=1.2, g=0.4):
    n = int(d * A.SR)
    tt = np.linspace(0, 1, n)
    x = A.lowpass(noise(d)[:n], 12) * np.sin(np.pi * tt) ** 1.5
    place(S, t, x * 3, g)


def sfx_bonk(t, g=0.5):
    tt = tvec(0.25)
    place(S, t, np.sin(2 * np.pi * np.cumsum(500 * np.exp(-tt * 8) + 200) / A.SR) * np.exp(-tt * 12), g)


def sfx_boing(t, g=0.4):
    tt = tvec(0.5)
    f = 220 + 120 * np.sin(2 * np.pi * 9 * tt) * np.exp(-tt * 4)
    place(S, t, np.sin(2 * np.pi * np.cumsum(f) / A.SR) * np.exp(-tt * 5), g)


def sfx_thunder(t, g=0.8):
    d = 2.2
    tt = tvec(d)
    x = A.lowpass(noise(d), 40) * (np.exp(-tt * 1.6) + 0.6 * np.exp(-np.abs(tt - 0.3) * 6))
    place(S, t, x * 6, g)


def sfx_crack(t, g=0.5):
    tt = tvec(0.25)
    place(S, t, A.highpass(noise(0.25), 2) * np.exp(-tt * 25), g)
    for k in range(4):
        tt2 = tvec(0.04)
        place(S, t + 0.03 * k, A.highpass(noise(0.04), 2) * np.exp(-tt2 * 80), g * 0.8)


def sfx_shutter(t, g=0.4):
    for k in range(2):
        tt = tvec(0.03)
        place(S, t + k * 0.06, A.highpass(noise(0.03), 2) * np.exp(-tt * 150), g)


def sfx_sizzle(t, d, g=0.18):
    n = int(d * A.SR)
    x = A.highpass(noise(d)[:n], 2) * (0.5 + 0.5 * np.abs(np.sin(np.arange(n) / A.SR * 37)))
    cr = np.zeros(n)
    idx = A.rng.integers(0, n, int(d * 60))
    cr[idx] = A.rng.uniform(-1, 1, len(idx))
    place(S, t, x * 0.5 + cr * 0.8, g)


def sfx_ambient(buf_t0, d, kind="rain", g=0.12):
    n = int(d * A.SR)
    x = noise(d)[:n]
    if kind == "rain":
        y = A.highpass(x, 2) * 0.6 + A.lowpass(x, 6) * 0.4
    elif kind == "waves":
        tt = np.arange(n) / A.SR
        y = A.lowpass(x, 14) * 3 * (0.4 + 0.6 * np.sin(2 * np.pi * tt / 4.5) ** 2)
    else:  # wind
        tt = np.arange(n) / A.SR
        y = A.lowpass(x, 30) * 4 * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 3.1))
    y[: int(0.3 * A.SR)] *= np.linspace(0, 1, int(0.3 * A.SR))
    y[-int(0.3 * A.SR):] *= np.linspace(1, 0, int(0.3 * A.SR))
    place(S, buf_t0, y, g)


def jingle(t, g=0.12):
    for k in range(4):
        tt = tvec(0.15)
        f = A.rng.uniform(5000, 7000)
        place(M, t + k * 0.012, np.sin(2 * np.pi * f * tt) * np.exp(-tt * 30) * A.highpass(noise(0.15), 2), g)


def chords_loop(t0, t1, bpm, chords, roots, inst="epiano", drums="lofi", mel=None, vel=0.16):
    beat = 60 / bpm
    b = 0
    while t0 + b * beat < t1 - 0.01:
        t = t0 + b * beat
        ci = (b // 2) % len(chords)
        if inst == "epiano" and b % 2 == 0:
            for k, m in enumerate(chords[ci]):
                place(M, t + 0.012 * k, A.epiano(m, beat * 1.9, vel))
        elif inst == "uke":
            pat = [0, 1, 2, 1] if b % 2 == 0 else [2, 1, 0, 1]
            for k in range(2):
                for j, m in enumerate(chords[ci]):
                    place(M, t + k * beat / 2 + j * 0.015, A.pluck(m + 12, 0.25, vel * 1.4))
        elif inst == "pluck":
            for m in chords[ci]:
                place(M, t + beat * 0.5, A.pluck(m + 12, 0.2, vel))
        elif inst == "musicbox":
            m = chords[ci][b % len(chords[ci])] + 24
            place(M, t, A.musicbox(m, 1.0, vel * 1.6))
            place(M, t + beat / 2, A.musicbox(chords[ci][(b + 2) % len(chords[ci])] + 24, 0.8, vel * 1.1))
        elif inst == "square":
            for k in range(4):
                place(M, t + k * beat / 4, A.square(chords[ci][k % len(chords[ci])] + 12, beat / 4 * 0.9, vel * 0.6))
        if b % 2 == 0 or drums in ("rock", "dance"):
            place(M, t, A.bass(roots[ci], beat * (1.8 if drums == "lofi" else 0.45), 0.5))
        if drums == "lofi":
            if b % 4 in (0, 2):
                place(M, t, A.kick(0.7))
            if b % 4 in (1, 3):
                place(M, t, A.snare(0.22))
            place(M, t, A.hat(0.1))
            place(M, t + beat * 0.6, A.hat(0.07))
        elif drums in ("dance", "rock"):
            place(M, t, A.kick(0.85))
            if b % 2 == 1:
                place(M, t, A.snare(0.32) if drums == "rock" else A.clap(0.35))
            place(M, t + beat * 0.5, A.hat(0.12))
            if drums == "rock":
                place(M, t + beat * 0.5, A.bass(roots[ci] + 12, beat * 0.4, 0.35))
        elif drums == "waltz":
            if b % 3 == 0:
                place(M, t, A.bass(roots[ci], beat * 0.9, 0.45))
            else:
                jingle(t)
        elif drums == "swing":
            place(M, t, A.bass(roots[ci] + (0, 4, 7, 5)[b % 4], beat * 0.8, 0.45))
            place(M, t, A.hat(0.08, 0.1))
            place(M, t + beat * 0.66, A.hat(0.06, 0.05))
            if b % 2 == 1:
                place(M, t, A.snare(0.12))
        if mel:
            m = mel[b % len(mel)]
            if m:
                place(M, t + beat * 0.5, A.epiano(m, beat * 0.8, vel * 0.8))
        b += 1
