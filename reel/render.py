"""
"The Last Coffee" - 30 second vertical cartoon reel renderer.

Flat-vector stick-figure style (dark room, blue hoodie, white rim light).
Renders 1080x1920 @ 30fps with 2x supersampling, in parallel chunks,
then writes video-only MP4 segments that build.sh muxes with audio.

Usage: python3 render.py <out_dir> [workers]
"""
import math
import os
import random
import subprocess
import sys
from multiprocessing import Process

from PIL import Image, ImageChops, ImageDraw, ImageFont

W, H = 1080, 1920
SS = 2  # supersampling factor
FPS = 30
DUR = 30.0
NFRAMES = int(DUR * FPS)

FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBoldItalic.ttf"
if not os.path.exists(FONT_MONO):
    FONT_MONO = FONT_BOLD

# ---------------------------------------------------------------- palette
C_BLACK = (14, 14, 18)
C_RIM = (232, 236, 246)
C_HOOD = (38, 108, 222)
C_HOOD_D = (28, 80, 175)
C_HOOD_DD = (22, 62, 140)
C_WALL = (98, 108, 128)
C_WALL_TOP = (78, 86, 104)
C_BASE = (66, 72, 88)
C_FLOOR = (100, 84, 72)
C_FLOOR_L = (82, 68, 58)
C_DESK = (138, 108, 78)
C_DESK_TOP = (158, 126, 92)
C_DESK_D = (112, 88, 66)
C_METAL = (46, 50, 60)
C_CHAIR = (62, 66, 78)
C_SCREEN = (18, 20, 28)


# ---------------------------------------------------------------- math utils
def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in(t):
    t = clamp(t)
    return t * t * t


def back_out(t):
    t = clamp(t)
    c = 1.9
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def seg(t, a, b, fn=ease):
    if b <= a:
        return 1.0 if t >= b else 0.0
    return fn((t - a) / (b - a))


def lerp_col(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def lerp2(p, q, t):
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


def rot(v, a):
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def up_vec(angle, face):
    return (face * math.sin(angle), -math.cos(angle))


# ---------------------------------------------------------------- camera / canvas
class Cam:
    def __init__(self, cx, cy, s):
        self.cx, self.cy, self.s = cx, cy, s

    def p(self, x, y):
        k = self.s * SS
        return ((x - self.cx) * k + W * SS / 2, (y - self.cy) * k + H * SS / 2)

    def l(self, v):
        return v * self.s * SS


class Painter:
    def __init__(self, img, cam):
        self.d = ImageDraw.Draw(img)
        self.cam = cam

    def poly(self, pts, col):
        self.d.polygon([self.cam.p(*q) for q in pts], fill=col)

    def rect(self, x0, y0, x1, y1, col):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col)

    def circle(self, x, y, r, col):
        X, Y = self.cam.p(x, y)
        R = self.cam.l(r)
        self.d.ellipse([X - R, Y - R, X + R, Y + R], fill=col)

    def ellipse(self, x, y, rx, ry, col):
        X, Y = self.cam.p(x, y)
        RX, RY = self.cam.l(rx), self.cam.l(ry)
        self.d.ellipse([X - RX, Y - RY, X + RX, Y + RY], fill=col)

    def ring(self, x, y, r, w, col):
        X, Y = self.cam.p(x, y)
        R = self.cam.l(r)
        self.d.ellipse([X - R, Y - R, X + R, Y + R], outline=col, width=max(1, int(self.cam.l(w))))

    def line(self, a, b, w, col, cap=True):
        A, B = self.cam.p(*a), self.cam.p(*b)
        ww = max(1, int(self.cam.l(w)))
        self.d.line([A, B], fill=col, width=ww)
        if cap:
            r = ww / 2
            for X, Y in (A, B):
                self.d.ellipse([X - r, Y - r, X + r, Y + r], fill=col)

    def polyline(self, pts, w, col):
        for i in range(len(pts) - 1):
            self.line(pts[i], pts[i + 1], w, col)

    def arc(self, x, y, rx, ry, a0, a1, w, col):
        X, Y = self.cam.p(x, y)
        RX, RY = self.cam.l(rx), self.cam.l(ry)
        self.d.arc([X - RX, Y - RY, X + RX, Y + RY], a0, a1, fill=col,
                   width=max(1, int(self.cam.l(w))))

    def chord(self, x, y, rx, ry, a0, a1, col):
        X, Y = self.cam.p(x, y)
        RX, RY = self.cam.l(rx), self.cam.l(ry)
        self.d.chord([X - RX, Y - RY, X + RX, Y + RY], a0, a1, fill=col)

    def text(self, x, y, s, size, col, font=FONT_BOLD, anchor="mm"):
        sz = max(4, int(self.cam.l(size)))
        f = _font(font, sz)
        self.d.text(self.cam.p(x, y), s, font=f, fill=col, anchor=anchor)


_FONTS = {}


def _font(path, size):
    key = (path, size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(path, size)
    return _FONTS[key]


# ---------------------------------------------------------------- story constants
FLOOR = 800
DESK_Y = 590
SIT_HIP = (565.0, 668.0)
MUG_DESK = (817.0, DESK_Y)  # bottom-centre of mug on desk
MACHINE_MUG = (1676.0, DESK_Y)
STAND_Y = 590.0
MACH_X = 1555.0
DRAWER_X = 1070.0


def sky_mix(t):
    return seg(t, 27.6, 29.6)


# ---------------------------------------------------------------- background
def draw_background(P, t, shake_mach):
    dawn = sky_mix(t)
    wall = lerp_col(C_WALL, (122, 112, 118), dawn * 0.6)
    walltop = lerp_col(C_WALL_TOP, (100, 92, 100), dawn * 0.6)
    P.rect(-800, -800, 2800, FLOOR, wall)
    P.rect(-800, -800, 2800, -20, walltop)
    P.rect(-800, FLOOR - 22, 2800, FLOOR, C_BASE)
    # floor + planks
    P.rect(-800, FLOOR, 2800, 1700, C_FLOOR)
    for i in range(-12, 40):
        x0 = i * 95
        P.line((x0, FLOOR), (x0 + (x0 - 1000) * 0.55, 1700), 3, C_FLOOR_L, cap=False)
    for yy in (900, 1040):
        P.line((-800, yy), (2800, yy), 2, C_FLOOR_L, cap=False)

    # posters
    for (x0, y0, x1, y1) in ((660, 40, 890, 190), (960, 40, 1190, 170)):
        P.rect(x0, y0, x1, y1, (52, 84, 150))
        P.rect(x0 + 8, y0 + 8, x1 - 8, y1 - 8, (88, 104, 138))
    P.polyline([(680, 160), (730, 120), (780, 140), (840, 80), (870, 95)], 5, (150, 170, 210))
    P.ring(1075, 105, 38, 5, (150, 170, 210))
    P.line((1075, 105), (1100, 80), 5, (150, 170, 210))

    # wall clock
    P.circle(1320, 200, 46, (50, 56, 70))
    P.circle(1320, 200, 39, (205, 210, 220))
    hours = 3 + 3 * dawn
    ah = hours / 12 * 2 * math.pi
    am = (t * 0.8) % (2 * math.pi)
    P.line((1320, 200), (1320 + 20 * math.sin(ah), 200 - 20 * math.cos(ah)), 5, C_BLACK)
    P.line((1320, 200), (1320 + 30 * math.sin(am), 200 - 30 * math.cos(am)), 3, C_BLACK)
    P.circle(1320, 200, 4, (200, 60, 60))

    # shelf + wheel
    P.rect(322, -60, 334, FLOOR, (84, 70, 60))
    for yy in (230, 520, 735):
        P.rect(-500, yy, 340, yy + 10, (84, 70, 60))
    P.rect(40, 165, 130, 230, (150, 66, 60))
    P.rect(140, 175, 225, 230, (98, 92, 160))
    P.rect(-60, 180, 30, 230, (170, 172, 178))
    P.circle(150, 385, 132, (38, 40, 48))
    P.circle(150, 385, 120, wall)
    for k in range(16):
        a = k / 16 * math.pi
        P.line((150 + 118 * math.cos(a), 385 + 118 * math.sin(a)),
               (150 - 118 * math.cos(a), 385 - 118 * math.sin(a)), 2, (38, 40, 48), cap=False)
    P.circle(150, 385, 9, (38, 40, 48))
    P.rect(30, 650, 140, 735, (138, 72, 66))
    P.rect(160, 665, 300, 735, (104, 140, 98))

    # window
    sky_top = lerp_col((44, 58, 92), (245, 150, 100), dawn)
    sky_bot = lerp_col((70, 86, 120), (252, 205, 140), dawn)
    P.rect(1410, 20, 1910, 410, (168, 178, 194))
    for i in range(10):
        y0 = 34 + i * 36
        P.rect(1424, y0, 1896, y0 + 37, lerp_col(sky_top, sky_bot, i / 9))
    # sun / moon
    if dawn > 0.01:
        P.circle(1800, lerp(400, 220, dawn), 30, lerp_col(sky_bot, (255, 232, 150), dawn))
    if dawn < 1:
        P.circle(1520, 90, 22, lerp_col((225, 228, 210), sky_top, dawn))
        P.circle(1530, 84, 20, lerp_col(sky_top, sky_top, 0))
    bcol = lerp_col((112, 128, 156), (150, 110, 120), dawn)
    for (x0, top, w) in ((1440, 230, 70), (1530, 150, 90), (1640, 260, 60), (1720, 120, 80), (1820, 200, 70)):
        P.rect(x0, top, x0 + w, 396, bcol)
        if dawn < 0.7:
            rnd = random.Random(int(x0))
            for wy in range(int(top) + 18, 380, 34):
                for wx in range(int(x0) + 10, int(x0 + w) - 12, 22):
                    if rnd.random() < 0.3:
                        P.rect(wx, wy, wx + 10, wy + 14, (230, 205, 120))
    P.rect(1410, 20, 1910, 34, (168, 178, 194))
    P.rect(1410, 396, 1910, 410, (168, 178, 194))
    P.rect(1653, 20, 1667, 410, (168, 178, 194))
    P.rect(1395, 405, 1925, 422, (186, 194, 206))

    # coffee machine cabinet + machine
    P.rect(1560, DESK_Y, 1830, FLOOR - 4, (82, 88, 104))
    P.rect(1560, DESK_Y, 1830, DESK_Y + 10, (100, 106, 122))
    P.line((1695, DESK_Y + 20), (1695, FLOOR - 16), 3, (60, 64, 78), cap=False)
    P.rect(1670, 680, 1680, 720, (150, 156, 170))
    P.rect(1710, 680, 1720, 720, (150, 156, 170))
    jx = shake_mach
    P.rect(1606 + jx, 430, 1754 + jx, 470, (40, 43, 52))
    P.rect(1612 + jx, 470, 1630 + jx, DESK_Y, (40, 43, 52))
    P.rect(1730 + jx, 470, 1750 + jx, DESK_Y, (40, 43, 52))
    P.rect(1606 + jx, DESK_Y - 8, 1754 + jx, DESK_Y, (34, 36, 44))
    P.rect(1662 + jx, 470, 1690 + jx, 486, (28, 30, 36))
    # display
    disp = (60, 200, 120)
    if 13.8 <= t < 15.6:
        disp = (230, 60, 60) if int(t * 6) % 2 == 0 else (90, 30, 34)
    P.rect(1640 + jx, 442, 1700 + jx, 460, (20, 22, 26))
    P.rect(1644 + jx, 446, 1696 + jx, 456, disp)
    if 13.8 <= t < 15.6:
        P.text(1670 + jx, 451, "EMPTY", 9, (255, 235, 235))
    P.circle(1728 + jx, 451, 8, (200, 70, 60) if not (12.6 < t < 12.9) else (255, 140, 120))

    # lamp
    P.ellipse(1240, DESK_Y - 4, 26, 6, (60, 64, 76))
    P.line((1240, DESK_Y - 6), (1215, 430), 7, (64, 68, 80))
    P.line((1215, 430), (1160, 350), 7, (64, 68, 80))
    P.poly([(1140, 330), (1192, 338), (1180, 372), (1150, 362)], (78, 82, 96))

    # desk
    for lx in (660, 1300):
        P.rect(lx - 9, DESK_Y + 10, lx + 9, FLOOR - 4, C_METAL)
    P.rect(700, DESK_Y + 10, 712, FLOOR - 40, (40, 43, 52))
    P.rect(1255, DESK_Y + 10, 1267, FLOOR - 40, (40, 43, 52))
    P.rect(640, DESK_Y, 1330, DESK_Y + 26, C_DESK)
    P.rect(640, DESK_Y, 1330, DESK_Y + 6, C_DESK_TOP)
    # drawer
    dopen = seg(t, 17.6, 18.0) * (1 - seg(t, 19.0, 19.4))
    if dopen > 0:
        P.rect(1040, DESK_Y + 26, 1290, DESK_Y + 26 + 30 * dopen, (60, 46, 36))
    dy = 22 * dopen
    P.rect(1040, DESK_Y + 26 + dy, 1290, DESK_Y + 100 + dy * 1.4, C_DESK_D)
    P.rect(1145, DESK_Y + 58 + dy * 1.2, 1185, DESK_Y + 66 + dy * 1.2, (205, 205, 200))

    # keyboard
    P.rect(700, DESK_Y - 7, 800, DESK_Y, (34, 36, 44))
    P.rect(704, DESK_Y - 7, 796, DESK_Y - 4, (64, 68, 80))

    # monitor
    P.rect(992, DESK_Y - 6, 1068, DESK_Y, C_METAL)
    P.rect(1022, 500, 1038, DESK_Y - 4, C_METAL)
    P.rect(895, 320, 1165, 512, C_SCREEN)
    draw_screen(P, t)


def draw_screen(P, t):
    x0, y0, x1, y1 = 905, 330, 1155, 502
    P.rect(x0, y0, x1, y1, (26, 30, 42))
    if t >= 27.3:
        k = back_out(seg(t, 27.3, 27.6, lambda v: v))
        P.rect(x0, y0, x1, y1, (24, 70, 48))
        r = 42 * k
        if r > 1:
            P.circle(1030, 400, r, (60, 200, 110))
            P.polyline([(1030 - 20 * k, 402), (1030 - 5 * k, 418 * 1 if k else 400), (1030 + 22 * k, 386)], 8 * k + 1, (255, 255, 255))
        P.text(1030, 472, "DONE!", 22 * max(k, 0.05), (220, 255, 230))
        return
    fast = 23.9 <= t < 27.3
    speed = 140 if fast else 8
    # left panel (code) + right panel
    P.rect(x0 + 8, y0 + 8, x0 + 140, y1 - 8, (36, 42, 58))
    P.rect(x0 + 148, y0 + 8, x1 - 8, y0 + 90, (36, 42, 58))
    P.rect(x0 + 148, y0 + 98, x1 - 8, y1 - 8, (36, 42, 58))
    cols = [(110, 170, 255), (240, 170, 90), (150, 220, 140), (200, 140, 230), (170, 180, 200)]
    off = (t * speed) % 14
    rnd = random.Random(7)
    for i in range(14):
        ln = int((t * speed) // 14) + i
        rr = random.Random(ln * 31 + 5)
        yy = y0 + 16 + i * 11 - off
        if yy < y0 + 12 or yy > y1 - 14:
            continue
        xi = x0 + 14 + rr.randint(0, 3) * 8
        wlen = rr.randint(20, 90)
        P.rect(xi, yy, min(xi + wlen, x0 + 134), yy + 5, cols[rr.randint(0, 4)])
    _ = rnd
    if fast:
        prog = seg(t, 24.0, 27.2, lambda v: v)
        P.rect(x0 + 156, y0 + 40, x1 - 16, y0 + 58, (20, 22, 30))
        P.rect(x0 + 158, y0 + 42, x0 + 158 + (x1 - 16 - 2 - (x0 + 158)) * prog, y0 + 56, (80, 220, 120))
        P.text((x0 + x1 + 140) / 2, y0 + 24, f"{int(prog * 100)}%", 13, (220, 255, 230))
    else:
        P.rect(x0 + 160, y0 + 22, x0 + 220, y0 + 30, (110, 170, 255))
        P.rect(x0 + 160, y0 + 40, x1 - 24, y0 + 46, (70, 80, 100))
        P.rect(x0 + 160, y0 + 56, x1 - 50, y0 + 62, (70, 80, 100))


def draw_chair(P):
    hx, hy = SIT_HIP
    P.poly([(hx - 70, hy + 12), (hx - 46, hy + 12), (hx - 22, hy - 200), (hx - 60, hy - 205)], C_CHAIR)
    P.ellipse(hx - 40, hy - 150, 26, 66, C_CHAIR)
    P.rect(hx - 6, hy + 20, hx + 6, 760, (46, 50, 60))
    P.rect(hx - 70, hy + 10, hx + 70, hy + 30, (70, 74, 86))
    P.rect(hx - 80, 758, hx + 80, 768, (46, 50, 60))
    for dx in (-76, 0, 76):
        P.circle(hx + dx, 780, 12, (30, 32, 40))


# ---------------------------------------------------------------- character
L_UP, L_LO = 90.0, 85.0
L_TH, L_SH = 102.0, 118.0
HEAD_R = 52.0


def ik(a, target, l1, l2, face, prefer_down=True):
    dx, dy = target[0] - a[0], target[1] - a[1]
    d = math.hypot(dx, dy)
    d = clamp(d, 1e-3, l1 + l2 - 0.5)
    base = math.atan2(dy, dx)
    cosv = clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1)
    off = math.acos(cosv)
    c1 = (a[0] + l1 * math.cos(base + off), a[1] + l1 * math.sin(base + off))
    c2 = (a[0] + l1 * math.cos(base - off), a[1] + l1 * math.sin(base - off))
    if prefer_down == "fwd":
        j = c1 if (c1[0] - c2[0]) * face > 0 else c2
    elif prefer_down == "back":
        j = c1 if (c1[0] - c2[0]) * face < 0 else c2
    else:
        j = c1 if c1[1] > c2[1] else c2
    end = (j[0] + l2 * math.cos(math.atan2(target[1] - j[1], target[0] - j[0])),
           j[1] + l2 * math.sin(math.atan2(target[1] - j[1], target[0] - j[0])))
    return j, end


class Pose:
    def __init__(self, **kw):
        self.hip = (0.0, 0.0)
        self.face = 1
        self.torso = 0.0
        self.tilt = 0.0
        self.hand_b = (0.0, 0.0)
        self.hand_f = (0.0, 0.0)
        self.foot_b = (0.0, 0.0)
        self.foot_f = (0.0, 0.0)
        self.eyes = "normal"
        self.mouth = "flat"
        self.mouth_amt = 1.0
        self.look = (0.0, 0.0)
        self.brow = 0.0  # +sad / -angry
        self.elbow_b = "down"
        self.elbow_f = "down"
        self.__dict__.update(kw)


def sit_pose(**kw):
    p = Pose(hip=SIT_HIP, torso=0.18, tilt=0.08, hand_b=(730, 580), hand_f=(762, 580),
             foot_b=(662, 788), foot_f=(680, 790))
    p.__dict__.update(kw)
    return p


def stand_pose(x, face=1, **kw):
    p = Pose(hip=(x, STAND_Y), face=face, torso=0.05, tilt=0.0,
             hand_b=(x - face * 18, STAND_Y + 40), hand_f=(x + face * 22, STAND_Y + 42),
             foot_b=(x - face * 16, 788), foot_f=(x + face * 18, 790))
    p.__dict__.update(kw)
    return p


def blend_pose(a, b, k):
    p = Pose()
    p.__dict__.update(b.__dict__ if k >= 0.5 else a.__dict__)
    for name in ("hip", "hand_b", "hand_f", "foot_b", "foot_f", "look"):
        setattr(p, name, lerp2(getattr(a, name), getattr(b, name), k))
    for name in ("torso", "tilt", "brow", "mouth_amt"):
        setattr(p, name, lerp(getattr(a, name), getattr(b, name), k))
    return p


def skeleton(p):
    f = p.face
    hip = p.hip
    u = up_vec(p.torso, f)
    shoulder = (hip[0] + u[0] * 150, hip[1] + u[1] * 150)
    neck = (hip[0] + u[0] * 182, hip[1] + u[1] * 182)
    hu = up_vec(p.torso + p.tilt, f)
    head = (neck[0] + hu[0] * 48, neck[1] + hu[1] * 48)
    sh_b = (shoulder[0] - f * 6, shoulder[1] - 2)
    eb, hb = ik(sh_b, p.hand_b, L_UP, L_LO, f, p.elbow_b if p.elbow_b != "down" else True)
    ef, hf = ik(shoulder, p.hand_f, L_UP, L_LO, f, p.elbow_f if p.elbow_f != "down" else True)
    hip_b = (hip[0] - f * 6, hip[1])
    kb, fb = ik(hip_b, p.foot_b, L_TH, L_SH, f, "fwd")
    kf, ff = ik(hip, p.foot_f, L_TH, L_SH, f, "fwd")
    return dict(hip=hip, shoulder=shoulder, sh_b=sh_b, neck=neck, head=head,
                eb=eb, hb=hb, ef=ef, hf=hf, kb=kb, fb=fb, kf=kf, ff=ff, hip_b=hip_b,
                head_ang=f * (p.torso + p.tilt))


def draw_character(P, p, t, extras=None):
    """Two passes: white rim silhouette offset toward the light, then fill."""
    extras = extras or {}
    s = skeleton(p)
    f = p.face
    off = (f * 4.5, -2.5)

    def shapes(rim):
        o = off if rim else (0, 0)

        def L(a, b, w, col):
            P.line(add(a, o), add(b, o), w + (0 if not rim else 0), C_RIM if rim else col)

        def Cc(c, r, col):
            P.circle(c[0] + o[0], c[1] + o[1], r, C_RIM if rim else col)

        # back leg
        L(s["hip_b"], s["kb"], 30, (8, 8, 12))
        L(s["kb"], s["fb"], 28, (8, 8, 12))
        foot(P, s["fb"], f, o, rim, (8, 8, 12))
        # back arm
        L(s["sh_b"], s["eb"], 28, C_HOOD_DD)
        L(s["eb"], s["hb"], 26, C_HOOD_DD)
        Cc(s["hb"], 14, (8, 8, 12))
        # hood behind head
        hu = up_vec(p.torso + p.tilt * 0.4, f)
        hood_c = (s["neck"][0] - f * 22 + hu[0] * 10, s["neck"][1] + hu[1] * 10 + 8)
        if not rim:
            P.ellipse(hood_c[0], hood_c[1], 30, 44, C_HOOD_D)
        else:
            P.ellipse(hood_c[0] + o[0], hood_c[1] + o[1], 30, 44, C_RIM)
        # torso (hoodie)
        L(s["hip"], s["shoulder"], 62, C_HOOD)
        # pocket
        if not rim:
            u = up_vec(p.torso, f)
            pc = (s["hip"][0] + u[0] * 30 + f * 6, s["hip"][1] + u[1] * 30)
            P.line(pc, (pc[0] + u[0] * 26, pc[1] + u[1] * 26), 30, C_HOOD_D)
        # front leg
        L(s["hip"], s["kf"], 32, C_BLACK)
        L(s["kf"], s["ff"], 30, C_BLACK)
        foot(P, s["ff"], f, o, rim, C_BLACK)
        # head
        Cc(s["head"], HEAD_R, C_BLACK)

    def front_arm(rim):
        o = off if rim else (0, 0)
        P.line(add(s["shoulder"], o), add(s["ef"], o), 30, C_RIM if rim else C_HOOD)
        P.line(add(s["ef"], o), add(s["hf"], o), 28, C_RIM if rim else C_HOOD)
        P.circle(s["hf"][0] + o[0], s["hf"][1] + o[1], 15, C_RIM if rim else C_BLACK)

    held = extras.get("held")
    shapes(True)
    front_arm(True)
    shapes(False)
    draw_face(P, p, s, t, extras)
    if held == "mug_behind":
        pass
    front_arm(False)
    if held == "mug":
        draw_mug(P, s["hf"], extras.get("item_ang", 0.0), f, held=True)
    elif held == "can":
        draw_can(P, s["hf"], extras.get("item_ang", 0.0), f)
    return s


def foot(P, pos, f, o, rim, col):
    c = (pos[0] + f * 12 + o[0], pos[1] + 2 + o[1])
    P.ellipse(c[0], c[1], 26, 12, C_RIM if rim else col)


def draw_face(P, p, s, t, extras):
    f = p.face
    hc = s["head"]
    ang = s["head_ang"]

    def at(dx, dy):
        v = rot((dx * f, dy), ang)
        return (hc[0] + v[0], hc[1] + v[1])

    eye_col = (238, 232, 214)
    pup = (40, 40, 46)
    lx, ly = p.look
    e1, e2 = at(14, -8), at(36, -6)
    eyes = p.eyes
    # automatic blink
    if eyes in ("normal", "tired", "sad", "wide"):
        ph = (t + extras.get("blink_off", 0)) % 3.1
        if ph < 0.09:
            eyes = "closed"

    if eyes in ("normal", "sad", "wide", "shock", "hyper"):
        big = {"normal": 1.0, "sad": 1.0, "wide": 1.18, "shock": 1.42, "hyper": 1.5}[eyes]
        for e, sc in ((e1, 1.0), (e2, 0.78)):
            P.ellipse(e[0], e[1], 9 * big * sc, 12 * big, eye_col)
            pr = 5.0 if eyes not in ("shock", "hyper") else 2.6
            P.circle(e[0] + f * lx * 3 + f * 1.5, e[1] + ly * 3, pr * (sc * 0.9 + 0.1), pup)
        if eyes == "hyper":
            for e in (e1, e2):
                P.ring(e[0], e[1], 15, 2, (255, 230, 90))
    elif eyes == "tired":
        for e, sc in ((e1, 1.0), (e2, 0.78)):
            P.chord(e[0], e[1], 9 * sc, 11, 0, 180, eye_col)
            P.circle(e[0] + f * 1.5 + f * lx * 2, e[1] + 4, 4 * sc, pup)
            P.line((e[0] - 10 * sc, e[1]), (e[0] + 10 * sc, e[1]), 3, (200, 196, 182))
    elif eyes == "happy":
        for e, sc in ((e1, 1.0), (e2, 0.78)):
            P.arc(e[0], e[1] + 4, 9 * sc, 9, 200, 340, 4, eye_col)
    elif eyes == "closed":
        for e, sc in ((e1, 1.0), (e2, 0.78)):
            P.arc(e[0], e[1] - 2, 9 * sc, 7, 20, 160, 4, eye_col)
    elif eyes == "squint":
        for e, sc in ((e1, 1.0), (e2, 0.78)):
            P.line((e[0] - 9 * sc, e[1] - 3), (e[0] + 9 * sc, e[1] + 1), 4, eye_col)

    # brows
    if eyes not in ("closed",):
        b = p.brow
        lift = -21 - (6 if eyes in ("shock", "wide", "hyper") else 0)
        for e, sc in ((e1, 1.0), (e2, 0.78)):
            inner = -1 if e is e1 else 1
            a = (e[0] - 9 * sc * f, e[1] + lift + b * 4 * inner)
            c = (e[0] + 9 * sc * f, e[1] + lift - b * 4 * inner)
            P.line(a, c, 4, eye_col)

    m = at(28, 24)
    mo = p.mouth
    amt = p.mouth_amt
    mc = (238, 232, 214)
    if mo == "flat":
        P.line(at(20, 24), at(36, 23), 3.5, mc)
    elif mo == "wavy":
        P.polyline([at(18, 25), at(23, 22), at(28, 26), at(33, 22), at(38, 25)], 3, mc)
    elif mo == "smile":
        P.arc(m[0], m[1] - 6, 11, 9, 20, 160, 4, mc)
    elif mo == "grin":
        P.chord(m[0], m[1] - 4, 13, 12, 0, 180, (240, 240, 235))
        P.line((m[0] - 13, m[1] - 4), (m[0] + 13, m[1] - 4), 2, (90, 30, 40))
    elif mo == "frown":
        P.arc(m[0], m[1] + 6, 10, 8, 200, 340, 4, mc)
    elif mo == "o":
        P.ellipse(m[0], m[1], 5 * amt + 1, 6 * amt + 1, (120, 36, 46))
    elif mo == "yawn":
        P.ellipse(m[0], m[1] + 2, 6 + 6 * amt, 3 + 14 * amt, (120, 36, 46))
        if amt > 0.4:
            P.ellipse(m[0], m[1] + 8 * amt, 5 * amt, 4 * amt, (210, 90, 100))
    elif mo == "bigO":
        P.ellipse(m[0], m[1] + 2, 10, 14 * amt, (120, 36, 46))
    elif mo == "sleep":
        P.ellipse(m[0], m[1], 4, 3 + 2 * math.sin(t * 3), (120, 36, 46))


def draw_mug(P, pos, ang, face, held=False):
    """pos: if held -> hand position (handle), else bottom-centre on table."""
    if held:
        c = add(pos, rot((face * 24, -2), ang))
    else:
        c = (pos[0], pos[1] - 21)
    pts = [add(c, rot(v, ang)) for v in ((-17, -21), (17, -21), (17, 21), (-17, 21))]
    hv = [add(c, rot((-face * 22, dy), ang)) for dy in (-10, 0, 10)]
    P.polyline([add(c, rot((-face * 15, -10), ang))] + hv + [add(c, rot((-face * 15, 10), ang))], 5, (30, 30, 36))
    P.poly(pts, (28, 28, 34))
    rim = [add(c, rot(v, ang)) for v in ((-17, -21), (17, -21), (17, -17), (-17, -17))]
    P.poly(rim, (60, 60, 70))
    lab = [add(c, rot(v, ang)) for v in ((-10, -4), (10, -4), (10, 4), (-10, 4))]
    P.poly(lab, (235, 150, 50))
    return c


def draw_can(P, pos, ang, face):
    c = add(pos, rot((face * 6, -6), ang))
    body = [add(c, rot(v, ang)) for v in ((-13, -25), (13, -25), (13, 25), (-13, 25))]
    P.poly(body, (60, 190, 96))
    top = [add(c, rot(v, ang)) for v in ((-13, -25), (13, -25), (11, -30), (-11, -30))]
    P.poly(top, (200, 205, 214))
    bolt = [(2, -16), (-7, 2), (0, 2), (-3, 16), (8, -4), (1, -4), (4, -16)]
    P.poly([add(c, rot(v, ang)) for v in bolt], (255, 225, 60))
    return add(c, rot((0, -30), ang))


# ---------------------------------------------------------------- story: pose per time
def walk_feet(x, face, phase, stride=46, lift=26):
    fb = (x + face * stride * math.sin(phase + math.pi) - face * 4, 790 - lift * max(0, math.cos(phase + math.pi)))
    ff = (x + face * stride * math.sin(phase) + face * 4, 790 - lift * max(0, math.cos(phase)))
    return fb, ff


def typing_hands(t, amp=7, freq=17):
    b = (730, 580 - amp * abs(math.sin(t * freq)))
    f = (764, 580 - amp * abs(math.sin(t * freq + 1.7)))
    return b, f


def story(t):
    """Returns (pose, extras, scene_flags)."""
    ex = {"held": None, "item_ang": 0.0}
    fl = {"mug_on_desk": True, "mug_at_machine": False, "bulb": 0.0, "foam": 0.0,
          "spray": None, "zzz": 0.0, "mach_shake": 0.0, "drop": None, "speed": 0.0,
          "sweat": 0.0, "mach_drip": None, "can_in_drawer": True}

    if t < 4.4:
        hb, hf = typing_hands(t)
        droop = seg(t, 0.3, 2.4)
        p = sit_pose(hand_b=hb, hand_f=hf, tilt=lerp(0.04, 0.26, droop), eyes="tired",
                     mouth="flat", torso=lerp(0.16, 0.24, droop))
        k = seg(t, 2.4, 2.8) * (1 - seg(t, 3.7, 4.1))
        if k > 0:
            yawn = sit_pose(hand_b=(600, 360), hand_f=(650, 350), tilt=-0.28, torso=0.05,
                            eyes="closed", mouth="yawn", elbow_b="back", elbow_f="back")
            p = blend_pose(p, yawn, k)
            p.mouth_amt = math.sin(clamp((t - 2.4) / 1.5) * math.pi)
            if k > 0.5:
                p.eyes, p.mouth = "closed", "yawn"
        return p, ex, fl

    if t < 9.2:
        base = sit_pose(hand_b=(730, 580), eyes="tired", tilt=0.18, torso=0.2)
        if t < 5.2:
            k = seg(t, 4.4, 5.1)
            p = blend_pose(base, sit_pose(hand_b=(730, 580), hand_f=(800, 570), torso=0.5,
                                          tilt=0.2, eyes="normal", look=(1, 0.5)), k)
            p.hand_f = lerp2((764, 580), (801, 572), k)
            return p, ex, fl
        fl["mug_on_desk"] = False
        ex["held"] = "mug"
        mouth_pos = (676, 452)
        if t < 6.6:
            k = seg(t, 5.2, 6.0)
            p = sit_pose(hand_b=(730, 580), torso=lerp(0.5, 0.12, k), tilt=lerp(0.2, -0.22, k),
                         hand_f=lerp2((801, 572), mouth_pos, k), eyes="closed" if t > 5.7 else "normal",
                         mouth="o", mouth_amt=0.7, look=(1, -1))
            ex["item_ang"] = -lerp(0, 1.9, seg(t, 5.4, 6.1))
            if t > 6.1:
                p.eyes = "normal"
                p.look = (1, -1.2)
            return p, ex, fl
        if t < 7.0:
            p = sit_pose(hand_b=(730, 580), torso=0.12, tilt=-0.22, hand_f=mouth_pos,
                         eyes="normal", look=(1, -1.3), mouth="o", mouth_amt=0.9)
            ex["item_ang"] = -1.9 - 0.15 * seg(t, 6.6, 6.9)
            dk = seg(t, 6.62, 6.95, lambda v: v)
            fl["drop"] = dk if dk < 1 else None
            return p, ex, fl
        if t < 8.2:
            k = seg(t, 7.0, 7.25, ease_out)
            p = sit_pose(hand_b=(730, 580), torso=lerp(0.12, 0.0, k), tilt=lerp(-0.22, -0.32, k),
                         hand_f=lerp2(mouth_pos, (700, 500), k), eyes="shock", mouth="bigO", mouth_amt=1.0)
            ex["item_ang"] = lerp(-2.05, -0.3, k)
            return p, ex, fl
        # shake upside down above face
        k = seg(t, 8.2, 8.45)
        sh = math.sin((t - 8.2) * 40) * 14 * seg(t, 8.35, 8.5) * (1 - seg(t, 9.0, 9.2))
        p = sit_pose(hand_b=(730, 580), torso=0.05, tilt=lerp(-0.32, -0.45, k),
                     hand_f=(lerp(700, 650, k) + sh, lerp(500, 350, k)), eyes="squint",
                     mouth="frown", look=(0, -1), elbow_f="back")
        ex["item_ang"] = lerp(-0.3, -math.pi, k)
        return p, ex, fl

    if t < 12.6:
        fl["mug_on_desk"] = False
        ex["held"] = "mug"
        if t < 10.0:
            k = seg(t, 9.2, 9.95)
            a = sit_pose(hand_b=(730, 580), torso=0.05, tilt=-0.45, hand_f=(650, 350),
                         eyes="squint", mouth="frown", elbow_f="back")
            b = stand_pose(640, hand_f=(690, 548), eyes="normal", mouth="flat", look=(1, 0))
            p = blend_pose(a, b, k)
            p.hip = (lerp(565, 640, k), lerp(668, STAND_Y, ease_out(clamp(k * 1.2))))
            ex["item_ang"] = lerp(-math.pi, 0, k)
            p.elbow_f = "down" if k > 0.5 else "back"
            return p, ex, fl
        if t < 12.2:
            k = (t - 10.0) / 2.2
            x = lerp(640, MACH_X, ease(k) * 0.15 + k * 0.85)
            ph = (t - 10.0) * (2 * math.pi / 0.55)
            fb, ff = walk_feet(x, 1, ph)
            bob = 6 * abs(math.sin(ph))
            p = stand_pose(x, hand_f=(x + 52, STAND_Y - 40 - bob), eyes="normal", mouth="flat",
                           look=(1, 0), torso=0.12)
            p.hip = (x, STAND_Y - bob)
            p.hand_b = (x - 30 * math.sin(ph), STAND_Y + 38)
            p.foot_b, p.foot_f = fb, ff
            return p, ex, fl
        k = seg(t, 12.2, 12.55)
        p = stand_pose(MACH_X, torso=lerp(0.12, 0.3, k), hand_f=lerp2((MACH_X + 52, STAND_Y - 40), (1660, 566), k),
                       eyes="normal", mouth="flat", look=(1, 0.6))
        return p, ex, fl

    # --- at the coffee machine
    if t < 15.6:
        fl["mug_on_desk"] = False
        fl["mug_at_machine"] = True
        if t < 12.95:
            k = seg(t, 12.55, 12.75) * (1 - seg(t, 12.8, 12.95))
            p = stand_pose(MACH_X, torso=0.22, hand_f=lerp2((1650, 520), (1724, 452), k),
                           eyes="normal", mouth="flat", look=(1, -0.2))
            p.hand_f = lerp2((1660, 566), (1724, 452), seg(t, 12.55, 12.72)) if t < 12.8 else lerp2((1724, 452), (MACH_X + 30, STAND_Y + 30), seg(t, 12.8, 12.95))
            return p, ex, fl
        if t < 13.8:
            fl["mach_shake"] = math.sin(t * 70) * 3.5
            p = stand_pose(MACH_X, torso=0.12, eyes="wide", mouth="smile", look=(1, 0.7),
                           hand_b=(MACH_X - 10, STAND_Y + 20), hand_f=(MACH_X + 50, STAND_Y - 10))
            p.hip = (MACH_X, STAND_Y - 4 * abs(math.sin(t * 9)))
            return p, ex, fl
        if t < 14.3:
            fl["mach_drip"] = seg(t, 13.95, 14.25, lambda v: v)
            p = stand_pose(MACH_X, torso=0.15, eyes="shock", mouth="o", mouth_amt=0.8, look=(1, 0.8))
            return p, ex, fl
        k = seg(t, 14.3, 14.9)
        p = stand_pose(MACH_X, torso=lerp(0.15, 0.42, k), tilt=lerp(0.0, 0.42, k), eyes="sad", brow=1.3,
                       mouth="frown", look=(0.4, 1))
        p.hip = (MACH_X, lerp(STAND_Y, STAND_Y + 14, k))
        p.hand_b = (MACH_X + 10, STAND_Y + 64)
        p.hand_f = (MACH_X + 34, STAND_Y + 66)
        return p, ex, fl

    # --- idea + run back
    if t < 17.6:
        fl["mug_on_desk"] = False
        fl["mug_at_machine"] = True
        if t < 16.2:
            k = seg(t, 15.6, 15.85, back_out)
            a = stand_pose(MACH_X, torso=0.42, tilt=0.42, eyes="sad", brow=1.3, mouth="frown")
            a.hip = (MACH_X, STAND_Y + 14)
            a.hand_b = (MACH_X + 10, STAND_Y + 64)
            a.hand_f = (MACH_X + 34, STAND_Y + 66)
            b = stand_pose(MACH_X, torso=-0.05, tilt=-0.15, eyes="wide", mouth="grin", look=(0, -1),
                           hand_f=(MACH_X + 60, STAND_Y - 130), elbow_f="down")
            p = blend_pose(a, b, k)
            fl["bulb"] = seg(t, 15.6, 15.8, back_out)
            return p, ex, fl
        fl["bulb"] = 1 - seg(t, 16.2, 16.4)
        k = (t - 16.2) / 1.4
        x = lerp(MACH_X, DRAWER_X, clamp(ease(k) * 0.3 + k * 0.7))
        ph = (t - 16.2) * (2 * math.pi / 0.34)
        fb, ff = walk_feet(x, -1, ph, stride=58, lift=36)
        bob = 9 * abs(math.sin(ph))
        p = stand_pose(x, face=-1, torso=0.32, eyes="happy", mouth="grin")
        p.hip = (x, STAND_Y - bob)
        p.hand_b = (x + 46 * math.sin(ph), STAND_Y + 10 - 20 * abs(math.cos(ph)))
        p.hand_f = (x - 46 * math.sin(ph), STAND_Y + 10 - 20 * abs(math.sin(ph)))
        p.foot_b, p.foot_f = fb, ff
        fl["speed"] = 0.6
        return p, ex, fl

    # --- drawer, can
    fl["mug_on_desk"] = False
    fl["mug_at_machine"] = True
    stand_x = DRAWER_X
    if t < 18.25:
        k = seg(t, 17.55, 17.75)
        p = stand_pose(stand_x, torso=lerp(0.2, 0.62, k), tilt=0.1, eyes="happy", mouth="grin")
        p.hip = (stand_x, STAND_Y + 22 * k)
        p.foot_b, p.foot_f = (stand_x - 30, 790), (stand_x + 26, 790)
        p.hand_f = lerp2((stand_x + 30, STAND_Y), (1165, 668), seg(t, 17.55, 17.7))
        if t > 17.9:
            p.hand_f = lerp2((1165, 668), (1160, 630), seg(t, 17.9, 18.2))
            ex["held"] = "can"
            fl["can_in_drawer"] = False
        return p, ex, fl
    fl["can_in_drawer"] = False
    ex["held"] = "can"
    if t < 20.3:
        k = seg(t, 18.25, 18.6, back_out)
        p = stand_pose(stand_x, torso=lerp(0.62, -0.05, k), tilt=-0.1, eyes="happy", mouth="grin")
        p.hip = (stand_x, STAND_Y + 22 * (1 - k))
        p.foot_b, p.foot_f = (stand_x - 30, 790), (stand_x + 26, 790)
        p.hand_f = lerp2((1160, 630), (1150, 300), k)
        p.elbow_f = "down"
        if t > 18.8:
            shake = math.sin((t - 18.8) * 44) * 26 * (1 - seg(t, 19.7, 19.9))
            p.hand_f = (1140, 380 + shake)
            p.hand_b = (stand_x + 10, STAND_Y + 40)
            p.eyes = "happy"
        if t > 19.85:
            kk = seg(t, 19.85, 20.15)
            p.hand_f = lerp2((1140, 380), (1138, 396), kk)
            p.hand_b = lerp2((stand_x + 10, STAND_Y + 40), (1128, 352), kk)
            ex["item_ang"] = -0.55 * kk
            p.eyes = "normal"
            p.mouth = "smile"
            p.look = (1, 0.4)
        return p, ex, fl

    # --- SPRAY!
    if t < 23.0:
        k = seg(t, 20.3, 20.45, ease_out)
        p = stand_pose(stand_x, torso=lerp(-0.05, -0.2, k), tilt=lerp(0.0, -0.3, k), eyes="shock", mouth="bigO")
        p.hand_f = (1138, 396)
        p.hand_b = lerp2((1128, 352), (stand_x - 20, STAND_Y + 30), k)
        ex["item_ang"] = -0.55
        fl["spray"] = t - 20.3
        fl["foam"] = seg(t, 20.35, 20.6)
        if t > 21.2:
            p.torso, p.tilt = -0.12, -0.1
            p.eyes = "normal" if t < 22.4 else "closed"
            p.mouth = "flat"
            p.look = (0, 0)
            ex["blink_off"] = 1.4
        if t > 22.3:
            kk = seg(t, 22.3, 22.6)
            p.hand_f = lerp2((1138, 396), (1112, 368), kk)
            ex["item_ang"] = lerp(-0.55, -1.7, kk)
            p.mouth = "o"
            p.mouth_amt = 0.6
        return p, ex, fl

    # --- HYPER
    if t < 23.9:
        fl["foam"] = 1 - seg(t, 23.0, 23.35)
        if t < 23.4:
            p = stand_pose(stand_x, torso=-0.12, tilt=-0.25, eyes="hyper", mouth="grin",
                           hand_f=(1150, 300), hand_b=(stand_x - 40, 330))
            p.hip = (stand_x, STAND_Y - 18 * math.sin(seg(t, 23.0, 23.4, lambda v: v) * math.pi))
            ex["item_ang"] = 0.3
            return p, ex, fl
        k = seg(t, 23.4, 23.8, ease)
        a = stand_pose(stand_x, torso=-0.12, tilt=-0.25, eyes="hyper", mouth="grin",
                       hand_f=(1150, 300), hand_b=(stand_x - 40, 330))
        b = sit_pose(eyes="hyper", mouth="grin", torso=0.3, tilt=0.15)
        p = blend_pose(a, b, k)
        p.eyes, p.mouth = "hyper", "grin"
        fl["speed"] = 1.0
        ex["held"] = None if k > 0.5 else "can"
        fl["can_on_desk"] = k > 0.5
        return p, ex, fl

    ex["held"] = None
    fl["can_on_desk"] = True
    if t < 27.3:
        hb, hf = typing_hands(t, amp=14, freq=46)
        p = sit_pose(hand_b=hb, hand_f=hf, eyes="hyper", mouth="grin", torso=0.32,
                     tilt=0.1 + 0.03 * math.sin(t * 30), look=(1, 0.3))
        fl["sweat"] = 1.0
        fl["speed"] = 0.5
        return p, ex, fl

    if t < 27.85:
        k = seg(t, 27.3, 27.45, back_out)
        p = sit_pose(hand_b=lerp2((730, 575), (590, 340), k), hand_f=lerp2((764, 575), (660, 330), k),
                     torso=lerp(0.32, 0.0, k), tilt=-0.2, eyes="happy", mouth="grin",
                     elbow_b="back", elbow_f="back")
        return p, ex, fl

    k = seg(t, 27.85, 28.05, ease_in)
    p = sit_pose(hand_b=lerp2((590, 340), (712, 586), k), hand_f=lerp2((660, 330), (808, 586), k),
                 torso=lerp(0.0, 0.9, k), tilt=lerp(-0.2, 0.32, k), eyes="closed", mouth="sleep",
                 elbow_b="down", elbow_f="down")
    fl["zzz"] = seg(t, 28.3, 28.6)
    return p, ex, fl


# ---------------------------------------------------------------- camera track
CAM_KEYS = [
    (0.0, 760, 560, 1.72),
    (2.4, 740, 540, 1.85),
    (4.4, 730, 530, 1.95),
    (5.2, 720, 520, 2.05),
    (6.0, 650, 462, 3.0),
    (7.0, 650, 462, 3.0),
    (7.6, 650, 455, 3.2),
    (8.2, 650, 440, 2.9),
    (9.0, 680, 470, 2.3),
]


def keyed(t, keys):
    if t <= keys[0][0]:
        return keys[0][1:]
    for i in range(len(keys) - 1):
        a, b = keys[i], keys[i + 1]
        if a[0] <= t <= b[0]:
            k = ease((t - a[0]) / (b[0] - a[0]))
            return tuple(lerp(a[j], b[j], k) for j in range(1, len(a)))
    return keys[-1][1:]


def camera(t, pose):
    hx = pose.hip[0]
    if t < 9.0:
        cx, cy, s = keyed(t, CAM_KEYS)
    elif t < 10.0:
        cx, cy, s = keyed(t, [(9.0, 680, 470, 2.3), (10.0, 720, 520, 1.85)])
    elif t < 12.2:
        cx, cy, s = hx + 80, 520, 1.85
        k = seg(t, 10.0, 10.5)
        cx = lerp(720, cx, k)
    elif t < 15.6:
        cx, cy, s = keyed(t, [(12.2, MACH_X + 80, 520, 1.85), (12.8, 1640, 500, 2.05),
                              (14.3, 1630, 480, 2.15), (15.5, 1600, 440, 2.6)])
    elif t < 16.2:
        cx, cy, s = keyed(t, [(15.5, 1600, 440, 2.6), (15.75, 1590, 420, 2.9), (16.2, 1560, 470, 2.4)])
    elif t < 17.6:
        k = seg(t, 16.2, 16.6)
        cx = lerp(1560, hx - 80, k)
        cy, s = lerp(470, 520, k), lerp(2.4, 1.85, k)
    elif t < 20.3:
        cx, cy, s = keyed(t, [(17.6, DRAWER_X - 80, 520, 1.85), (18.0, 1100, 540, 1.95),
                              (18.6, 1110, 420, 2.5), (20.0, 1110, 400, 2.75)])
    elif t < 23.4:
        cx, cy, s = keyed(t, [(20.3, 1110, 400, 2.75), (20.5, 1100, 390, 2.4), (21.3, 1100, 380, 2.9),
                              (23.0, 1100, 370, 3.1), (23.2, 1100, 380, 2.7)])
    elif t < 24.0:
        cx, cy, s = keyed(t, [(23.4, 1100, 380, 2.7), (24.0, 790, 520, 1.95)])
    elif t < 27.3:
        cx, cy, s = keyed(t, [(24.0, 790, 520, 1.95), (27.3, 780, 500, 2.25)])
    else:
        cx, cy, s = keyed(t, [(27.3, 780, 500, 2.25), (27.5, 780, 480, 2.1), (28.2, 790, 520, 2.0),
                              (30.0, 800, 500, 2.45)])
    # shake
    sh = 0.0
    for t0, dur, amp in ((7.0, 0.5, 9), (20.3, 0.9, 14), (23.0, 0.4, 8), (27.95, 0.3, 7), (13.0, 0.8, 1.5)):
        if t0 <= t < t0 + dur:
            sh = max(sh, amp * (1 - (t - t0) / dur))
    if 24.0 <= t < 27.3:
        sh = max(sh, 2.0)
    if sh:
        cx += sh * math.sin(t * 91) / s
        cy += sh * math.cos(t * 77) / s
    return Cam(cx, cy, s)


# ---------------------------------------------------------------- effects
FOAM = []
_r = random.Random(42)
for _i in range(170):
    ang = math.radians(_r.uniform(150, 260))  # leftward/up toward face (facing right => face is to the left)
    spd = _r.uniform(250, 900)
    FOAM.append((math.cos(ang) * spd, math.sin(ang) * spd, _r.uniform(5, 15), _r.random()))
FOAM_BLOBS = [(_r.uniform(-40, 46), _r.uniform(-46, 40), _r.uniform(9, 20)) for _ in range(16)]


def draw_spray(P, origin, tau):
    if tau is None or tau < 0 or tau > 1.4:
        return
    for vx, vy, r, d in FOAM:
        tt = tau - d * 0.25
        if tt < 0:
            continue
        x = origin[0] + vx * tt
        y = origin[1] + vy * tt + 0.5 * 1400 * tt * tt
        rr = r * (1 - clamp(tt / 1.1))
        if rr > 0.5:
            col = (245, 245, 238) if d > 0.35 else (232, 226, 196)
            P.circle(x, y, rr, col)
    if tau < 0.2:
        P.circle(origin[0], origin[1], 60 * (1 - tau / 0.2) + 10, (250, 250, 245))


def draw_foam_on_head(P, s, amt, t):
    if amt <= 0:
        return
    hc = s["head"]
    for i, (dx, dy, r) in enumerate(FOAM_BLOBS):
        rr = r * amt
        P.circle(hc[0] + dx, hc[1] + dy, rr, (244, 244, 236))
        if i % 3 == 0 and t > 20.8:
            drip = clamp((t - 20.8 - i * 0.05) * 22, 0, 46) * amt
            P.line((hc[0] + dx, hc[1] + dy), (hc[0] + dx, hc[1] + dy + drip), rr * 0.7, (240, 240, 230))


def draw_bulb(P, s, k):
    if k <= 0.01:
        return
    c = (s["head"][0] + 6, s["head"][1] - 118)
    r = 26 * k
    for a in range(0, 360, 45):
        ra = math.radians(a)
        P.line((c[0] + math.cos(ra) * (r + 10), c[1] + math.sin(ra) * (r + 10)),
               (c[0] + math.cos(ra) * (r + 26 * k), c[1] + math.sin(ra) * (r + 26 * k)), 5 * k, (255, 230, 90))
    P.circle(c[0], c[1], r, (255, 226, 80))
    P.rect(c[0] - 10 * k, c[1] + r - 4, c[0] + 10 * k, c[1] + r + 12 * k, (170, 174, 186))


def draw_zzz(P, s, k, t):
    if k <= 0:
        return
    base = (s["head"][0] - 10, s["head"][1] - 70)
    for i in range(3):
        ph = ((t - 28.3) * 0.55 + i / 3) % 1.0
        x = base[0] + 50 * ph + 18 * math.sin(ph * 6 + i)
        y = base[1] - 170 * ph
        size = (22 + 26 * ph) * k
        col = lerp_col((250, 250, 255), (160, 170, 200), ph)
        P.text(x, y, "Z", size, col)


def draw_speedlines(img, amount, t):
    if amount <= 0:
        return
    d = ImageDraw.Draw(img)
    rnd = random.Random(int(t * 30))
    cx, cy = W * SS / 2, H * SS / 2
    for _ in range(int(26 * amount)):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(0.62, 0.8) * H * SS
        r1 = r0 + rnd.uniform(160, 520)
        d.line([(cx + math.cos(a) * r0 * 0.6, cy + math.sin(a) * r0),
                (cx + math.cos(a) * r1 * 0.6, cy + math.sin(a) * r1)], fill=(235, 240, 250), width=6)


def draw_sweat(P, s, t):
    hc = s["head"]
    for i in range(2):
        ph = (t * 2.2 + i * 0.5) % 1.0
        x = hc[0] - 40 - i * 14
        y = hc[1] - 30 + 60 * ph
        P.ellipse(x, y, 6, 9, (150, 210, 255))
    # keyboard sparks
    rnd = random.Random(int(t * 30))
    for _ in range(4):
        x = rnd.uniform(700, 800)
        P.line((x, DESK_Y - 10), (x + rnd.uniform(-20, 20), DESK_Y - rnd.uniform(25, 55)), 3, (255, 230, 120))


# ---------------------------------------------------------------- overlays (final res)
def make_vignette():
    v = Image.new("L", (W, H), 0)
    px = v.load()
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            dx = (x - W / 2) / (W * 0.62)
            dy = (y - H / 2) / (H * 0.62)
            d = math.sqrt(dx * dx + dy * dy)
            val = int(255 * clamp(1.08 - 0.55 * d * d))
            for yy in range(y, min(y + 4, H)):
                for xx in range(x, min(x + 4, W)):
                    px[xx, yy] = val
    return Image.merge("RGB", (v, v, v))


def overlay_text(img, t):
    # Title card + ending card
    items = []
    if t < 3.4:
        a = seg(t, 0.25, 0.7) * (1 - seg(t, 2.8, 3.3))
        items.append(("THE LAST", 92, 250, a, (255, 255, 255)))
        items.append(("COFFEE", 150, 370, a, (255, 196, 92)))
    if t > 28.6:
        a = seg(t, 28.6, 29.0)
        items.append(("THE END", 120, 300, a, (255, 255, 255)))
        items.append(("follow for more", 46, 420, a, (255, 210, 140)))
    if not items:
        return img
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for s_, size, y, a, col in items:
        f = _font(FONT_BOLD, size)
        al = int(255 * a)
        d.text((W / 2 + 6, y + 8), s_, font=f, fill=(0, 0, 0, int(al * 0.55)), anchor="mm")
        d.text((W / 2, y), s_, font=f, fill=col + (al,), anchor="mm", stroke_width=0)
    base = img.convert("RGBA")
    base.alpha_composite(layer)
    return base.convert("RGB")


VIGNETTE = None


def render_frame(t):
    global VIGNETTE
    if VIGNETTE is None:
        VIGNETTE = make_vignette()
    pose, ex, fl = story(t)
    cam = camera(t, pose)
    img = Image.new("RGB", (W * SS, H * SS), C_WALL)
    P = Painter(img, cam)
    draw_background(P, t, fl["mach_shake"])

    if fl["mug_on_desk"]:
        draw_mug(P, MUG_DESK, 0.0, 1)
    if fl["mug_at_machine"]:
        draw_mug(P, MACHINE_MUG, 0.0, 1)
        if 12.85 < t < 13.8:
            for i in range(3):
                ph = ((t - 12.85) * 1.3 + i * 0.33) % 1
                P.circle(1676 + 10 * math.sin(ph * 8 + i), 540 - 60 * ph, 8 * (1 - ph) + 2, (210, 214, 222))
        if fl["mach_drip"] is not None:
            P.ellipse(1676, lerp(488, 552, fl["mach_drip"]), 3, 5, (120, 80, 50))
    if fl["can_in_drawer"] and 17.75 < t < 18.0:
        P.rect(1150, DESK_Y + 30, 1176, DESK_Y + 44, (60, 190, 96))
    if fl.get("can_on_desk"):
        draw_can(P, (846, DESK_Y - 19), 0.0, 1)
    draw_chair(P)

    s = draw_character(P, pose, t, ex)

    if fl["drop"] is not None:
        mc = add(s["hf"], rot((24, -2), ex["item_ang"]))
        top = add(mc, rot((0, -22), ex["item_ang"]))
        y = lerp(top[1] + 4, top[1] + 30, fl["drop"])
        P.ellipse(top[0] - 4, y, 4, 6, (130, 84, 50))
    if fl["spray"] is not None:
        can_top = add(add(s["hf"], rot((6, -6), ex["item_ang"])), rot((0, -30), ex["item_ang"]))
        draw_spray(P, can_top, fl["spray"])
    draw_foam_on_head(P, s, fl["foam"], t)
    draw_bulb(P, s, fl["bulb"])
    draw_zzz(P, s, fl["zzz"], t)
    if fl["sweat"]:
        draw_sweat(P, s, t)
    # shock lines
    if 7.0 <= t < 7.7 or 13.8 <= t < 14.2:
        hc = s["head"]
        for a in (-60, -30, 0, 30, 60):
            ra = math.radians(a - 90)
            P.line((hc[0] + math.cos(ra) * 75, hc[1] + math.sin(ra) * 75),
                   (hc[0] + math.cos(ra) * 100, hc[1] + math.sin(ra) * 100), 6, (255, 255, 255))
    if 15.6 <= t < 16.2:
        pass
    draw_speedlines(img, fl["speed"], t)
    # white flash on spray
    out = img.reduce(SS)
    out = ImageChops.multiply(out, VIGNETTE)
    if 20.3 <= t < 20.5:
        out = Image.blend(out, Image.new("RGB", (W, H), (255, 255, 255)), 0.75 * (1 - (t - 20.3) / 0.2))
    dawn = sky_mix(t)
    if dawn > 0:
        out = Image.blend(out, Image.new("RGB", (W, H), (255, 160, 90)), 0.12 * dawn)
    out = overlay_text(out, t)
    # fades
    fade = min(seg(t, 0.0, 0.5), 1 - seg(t, 29.55, 30.0))
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, fade)
    return out


# ---------------------------------------------------------------- driver
def render_chunk(i0, i1, path):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(i0, i1):
        pr.stdin.write(render_frame(i / FPS).tobytes())
    pr.stdin.close()
    pr.wait()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "out"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else os.cpu_count() or 4
    os.makedirs(out, exist_ok=True)
    if os.environ.get("PREVIEW"):
        for ts in os.environ["PREVIEW"].split(","):
            render_frame(float(ts)).save(os.path.join(out, f"prev_{float(ts):05.2f}.png"))
        return
    step = math.ceil(NFRAMES / workers)
    procs, parts = [], []
    for w in range(workers):
        a, b = w * step, min(NFRAMES, (w + 1) * step)
        if a >= b:
            break
        path = os.path.join(out, f"part{w}.mp4")
        parts.append(path)
        pr = Process(target=render_chunk, args=(a, b, path))
        pr.start()
        procs.append(pr)
    for pr in procs:
        pr.join()
    with open(os.path.join(out, "parts.txt"), "w") as fh:
        for pth in parts:
            fh.write(f"file '{os.path.abspath(pth)}'\n")


if __name__ == "__main__":
    main()
