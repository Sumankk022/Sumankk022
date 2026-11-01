"""Episode 6 - SNOW DAY (snowy park, purple puffer jacket + beanie + scarf)."""
import math
import random

from engine import *

OUT = Outfit(top=(140, 82, 204), top_dark=(104, 60, 160), sleeve="long", pants=(42, 46, 64),
             boots=(110, 72, 42), hat="beanie", hat_col=(222, 60, 64), hat_col2=(245, 245, 248),
             scarf=(40, 182, 186))
SNX = 1000.0
SNOW = (244, 247, 252)
SNOW_D = (206, 216, 234)
HIDE = (-9000.0, STAND_Y)


# ------------------------------------------------------------------ props
def snowball(P, x, y, r):
    P.circle(x, y, r, SNOW_D)
    P.circle(x - r * 0.08, y - r * 0.08, r * 0.92, SNOW)


def snowman(P, t, fl):
    if fl.get("sm_gone"):
        return
    br = fl.get("sm_r", 0)
    if br <= 0:
        return
    bx = fl.get("sm_x", SNX)
    snowball(P, bx, 800 - br, br)
    lvl = fl.get("sm_decor", 0)
    if lvl >= 3:
        for side in (-1, 1):
            P.line((bx + side * 50, 690), (bx + side * 115, 640), 5, (110, 70, 40))
            P.line((bx + side * 100, 652), (bx + side * 112, 628), 4, (110, 70, 40))
    for k in range(3):
        if br > 60:
            P.circle(bx, 690 + k * 34, 6, (40, 40, 46))
    h = fl.get("sm_head")
    if h:
        hx, hy, hr, ha = h
        snowball(P, hx, hy, hr)
        look = fl.get("sm_look", 0)
        if lvl >= 2:
            for dx in (-14, 14):
                v = rot((dx + look * 6, -10), ha)
                P.circle(hx + v[0], hy + v[1], 5.5, (30, 30, 34))
            for k in range(5):
                v = rot((-16 + k * 8, 18 - 4 * math.sin(k / 4 * math.pi)), ha)
                P.circle(hx + v[0], hy + v[1], 3, (30, 30, 34))
        if lvl >= 1:
            v0, v1, v2 = rot((0, -4), ha), rot((40, 0), ha), rot((0, 6), ha)
            P.poly([(hx + v0[0], hy + v0[1]), (hx + v1[0], hy + v1[1]), (hx + v2[0], hy + v2[1])], (240, 130, 40))


def held_ball(r):
    def f(P, hand, ang, face):
        snowball(P, hand[0] + face * 8, hand[1] - r * 0.4, r)
    return f


def tree(P, x, s=1.0, shake=0.0):
    P.rect(x - 10 * s, 800 - 60 * s, x + 10 * s, 800, (100, 70, 50))
    for k in range(3):
        y0 = 800 - 60 * s - k * 80 * s
        w = (110 - k * 25) * s
        dx = shake * math.sin(k * 2 + 1)
        P.poly([(x - w + dx, y0), (x + w + dx, y0), (x + dx, y0 - 130 * s)], (40, 100, 80))
        P.poly([(x - w * 0.5 + dx, y0 - 65 * s), (x + w * 0.5 + dx, y0 - 65 * s), (x + dx, y0 - 130 * s)], SNOW)


def background(P, t, fl, cam):
    for i in range(14):
        y0 = -900 + i * 110
        P.rect(-800, y0, 2800, y0 + 111 + (500 if i == 13 else 0), lerp_col((150, 170, 200), (220, 228, 238), i / 13))
    P.circle(400, -200, 60, (245, 245, 235))
    for cx_, r in ((-200, 500), (600, 420), (1500, 560), (2400, 480)):
        P.circle(cx_, 640 + r * 0.6, r, (226, 232, 244))
    for x in (-300, 150, 1250, 1900, 2300):
        tree(P, x, 1.25)
    P.rect(-800, 640, 2800, 1700, SNOW)
    for x0 in range(-800, 2800, 300):
        P.ellipse(x0 + 120, 900, 180, 16, SNOW_D)
    # lamp + bench
    P.rect(395, 300, 405, 800, (50, 54, 64))
    P.ellipse(400, 296, 24, 14, (255, 240, 190))
    P.rect(380, 280, 420, 290, SNOW)
    P.rect(1260, 680, 1440, 696, (130, 90, 60))
    P.rect(1260, 640, 1440, 654, (130, 90, 60))
    P.rect(1270, 696, 1280, 790, (50, 54, 64))
    P.rect(1420, 696, 1430, 790, (50, 54, 64))
    P.rect(1256, 632, 1444, 642, SNOW)
    tree(P, 1700, 1.0, fl.get("tree_shake", 0.0))


def behind(P, t, fl, cam):
    if fl.get("roll"):
        x, r = fl["roll"]
        snowball(P, x, 800 - r, r)
    snowman(P, t, fl)
    if fl.get("loose_head"):
        x, y, r = fl["loose_head"]
        snowball(P, x, y, r)
        P.poly([(x, y - 4), (x + 30, y + 2), (x, y + 6)], (240, 130, 40))


def front(P, t, fl, s, cam, ex):
    # breath puffs
    if t < 23 and (t % 1.4) < 0.6:
        ph = (t % 1.4) / 0.6
        hc = s["head"]
        f = 1 if s["hf"][0] >= s["hip"][0] - 200 else 1
        P.circle(hc[0] + s["head_ang"] * 0 + 70 * (1 if fl.get("face", 1) > 0 else -1) + 20 * ph * fl.get("face", 1),
                 hc[1] + 20 - 10 * ph, 8 + 10 * ph, (250, 252, 255))
    for fly in fl.get("flying", []):
        x, y = fly
        snowball(P, x, y, 16)
    for sp in fl.get("splats", []):
        pos, tau = sp
        burst(P, pos, tau, seed=int(pos[0] + pos[1]), n=30, a0=0, a1=360, v0=100, v1=380, r0=4, r1=10,
              cols=(SNOW, SNOW_D), life=0.6, g=900)
    if fl.get("face_snow"):
        hc = s["head"]
        for dx, dy, r in ((20, -6, 22), (34, 14, 18), (8, 16, 16), (38, -14, 14)):
            P.circle(hc[0] + dx * fl.get("face", 1), hc[1] + dy, r * fl["face_snow"], SNOW)
    if fl.get("giant"):
        gx, gr, rot_a = fl["giant"]
        gy = 800 - gr
        if fl.get("legs"):
            for k, sgn in ((0, 1), (1, -1)):
                a = rot_a + k * 0.5
                base = (gx + math.cos(a) * gr * 0.9, gy + math.sin(a) * gr * 0.9)
                tip = (gx + math.cos(a) * (gr + 110), gy + math.sin(a) * (gr + 110))
                kick = 18 * math.sin(t * 25 + k * 2)
                P.line(base, (tip[0] + kick, tip[1]), 30, OUT.pants)
                P.ellipse(tip[0] + kick, tip[1], 24, 14, OUT.boots)
        snowball(P, gx, gy, gr)
        # carrot + stick sticking out
        a = rot_a + 2.2
        c0 = (gx + math.cos(a) * gr * 0.95, gy + math.sin(a) * gr * 0.95)
        c1 = (gx + math.cos(a) * (gr + 40), gy + math.sin(a) * (gr + 40))
        P.line(c0, c1, 10, (240, 130, 40))
        a = rot_a + 3.3
        P.line((gx + math.cos(a) * gr * 0.9, gy + math.sin(a) * gr * 0.9),
               (gx + math.cos(a) * (gr + 70), gy + math.sin(a) * (gr + 70)), 6, (110, 70, 40))
    if fl.get("stars"):
        stars_ring(P, s, t)
    if fl.get("flake") is not None:
        hc = s["head"]
        k = fl["flake"]
        x, y = hc[0] + 60 + 30 * math.sin(k * 8), lerp(hc[1] - 260, hc[1] + 2, k)
        star(P, x, y, 9, (255, 255, 255))
    snow(P, cam, t, 1.0 if t < 21.5 else 1.6)


def throw_path(t, t0, t1, a, b, arc=80):
    k = (t - t0) / (t1 - t0)
    return (lerp(a[0], b[0], k), lerp(a[1], b[1], k) - arc * math.sin(k * math.pi))


# ------------------------------------------------------------------ story
def story(t):
    ex = {"held": None}
    fl = {"face": 1}
    L = -200.0   # off-screen thrower position
    flying, splats = [], []
    # snowman state
    if t >= 7.4:
        fl["sm_r"] = 75
        fl["sm_x"] = SNX
    if t >= 9.3:
        fl["sm_head"] = (SNX, 610, 46, 0.0)
    fl["sm_decor"] = (1 if t > 9.8 else 0) + (1 if t > 10.2 else 0) + (1 if t > 10.6 else 0)

    if t < 3.0:
        p = walk(stand(0), t, 0.0, 3.0, 300, 690, period=0.62)
        p.eyes, p.mouth = ("happy", "smile") if t < 2.2 else ("wide", "o")
        p.look = (0, -1) if t > 2.2 else (0, 0)
        p.mouth_amt = 0.7
    elif t < 7.4:
        k = seg(t, 3.0, 7.4, lambda v: v)
        r = lerp(22, 75, k)
        bx = lerp(800, SNX, k)
        fl["roll"] = (bx, r)
        x = bx - r - 70
        p = walk(stand(0), t, 3.0, 7.4, 800 - 22 - 70, SNX - 75 - 70, period=0.7, stride=34, bob=4, arms=False)
        p.torso, p.tilt = 0.45, 0.1
        p.hand_f = (bx - r * 0.8, 800 - r * 1.1)
        p.hand_b = (bx - r * 0.9, 800 - r * 0.8)
        p.eyes, p.mouth = "squint", "grin"
    elif t < 9.4:
        x = 880.0
        if t < 8.4:
            p = crouch(x, depth=1.0, eyes="happy", mouth="smile", hand_f=(x + 90, 700), hand_b=(x + 70, 706))
            if t > 7.7:
                ex["held"] = held_ball(lerp(10, 44, seg(t, 7.7, 8.3)))
        else:
            k = seg(t, 8.4, 9.2)
            p = stand(x, torso=0.25, eyes="happy", mouth="grin", look=(1, -0.5),
                      hand_f=lerp2((x + 60, 560), (SNX - 20, 640), k), hand_b=lerp2((x + 50, 560), (SNX - 34, 640), k))
            ex["held"] = held_ball(44)
            if t > 9.25:
                ex["held"] = None
    elif t < 11.5:
        x = 900.0
        targets = [(SNX + 20, 612), (SNX, 600), (SNX - 40, 670)]
        i = min(2, int((t - 9.4) / 0.4))
        p = stand(x, torso=0.3, eyes="happy", mouth="smile", look=(1, 0), hand_f=targets[i])
        if t > 10.8:
            p = blend_pose(p, stand(820, eyes="happy", mouth="grin", hand_f=(850, 612), hand_b=(790, 612),
                                    elbow_f="back", elbow_b="back"), seg(t, 10.8, 11.4))
    elif t < 12.4:
        p = stand(820, eyes="happy", mouth="grin", hand_f=(850, 612), hand_b=(790, 612), elbow_f="back", elbow_b="back",
                  tilt=-0.1)
        if t > 12.1:
            flying.append(throw_path(t, 12.1, 12.4, (L, 400), (790, 330)))
    elif t < 14.3:
        k = seg(t, 12.4, 12.6, ease_out)
        p = stand(820, eyes="closed", mouth="bigO", torso=0.35 * k, tilt=0.3 * k)
        splats.append(((790, 330), t - 12.4))
        if t > 12.7:
            p = stand(820, face=-1, eyes="squint", mouth="frown", brow=-1.4, look=(1, 0))
            fl["face"] = -1
        if 13.5 < t < 14.0:
            p = stand(820, face=1, eyes="squint", mouth="frown", brow=-1.4, look=(1, 0))
            fl["face"] = 1
            fl["sm_look"] = 1.4 * seg(t, 13.65, 13.75)
        if t > 14.0:
            p = stand(820, face=-1, eyes="normal", mouth="flat", look=(1, 0))
            fl["face"] = -1
            flying.append(throw_path(t, 14.0, 14.3, (L, 380), (765, 365), 30))
    elif t < 16.6:
        fl["face"] = -1
        splats.append(((765, 365), t - 14.3))
        fl["face_snow"] = 1 - seg(t, 15.0, 15.3)
        p = stand(820, face=-1, eyes="closed", mouth="flat", torso=-0.2, tilt=-0.2)
        if t > 15.0:
            p = crouch(820, face=-1, depth=0.9, eyes="squint", mouth="frown", brow=-1.4, hand_f=(735, 760), hand_b=(745, 766))
        if t > 15.6:
            ex["held"] = held_ball(16)
            k = seg(t, 15.6, 16.1)
            p = blend_pose(p, stand(820, face=-1, eyes="squint", mouth="grin", brow=-1.4, hand_f=(880, 380),
                                    elbow_f="back", torso=-0.15), k)
        if t > 16.15:
            k = seg(t, 16.15, 16.3, ease_out)
            p = stand(820, face=-1, eyes="squint", mouth="bigO", brow=-1.4, torso=lerp(-0.15, 0.3, k),
                      hand_f=lerp2((880, 380), (700, 440), k))
            ex["held"] = None if k > 0.6 else held_ball(16)
            if k > 0.6:
                flying.append(throw_path(t, 16.25, 16.6, (700, 440), (L, 300), 60))
    elif t < 19.5:
        x = 1120.0
        k = seg(t, 16.6, 17.0)
        p = blend_pose(stand(820, face=-1, eyes="squint", mouth="grin"),
                       crouch(x, face=-1, depth=1.0, eyes="shock", mouth="o", mouth_amt=0.7, hand_f=(1060, 690),
                              hand_b=(1070, 700), look=(1, -0.3)), k)
        if k < 1:
            p.hip = (lerp(820, x, k), p.hip[1])
        fl["face"] = -1
        for t0 in (17.0, 17.6, 18.2, 18.8):
            if t0 < t < t0 + 0.35:
                tgt = (SNX - 40, 700) if t0 < 18.8 else (SNX - 30, 610)
                flying.append(throw_path(t, t0, t0 + 0.35, (L, 420), tgt, 60))
            if t0 + 0.35 <= t < t0 + 0.95:
                splats.append(((SNX - 40, 700) if t0 < 18.8 else (SNX - 30, 610), t - t0 - 0.35))
        if t > 19.15:
            fl["sm_head"] = None
            hk = seg(t, 19.15, 19.5, lambda v: v)
            fl["loose_head"] = (lerp(SNX, 1210, hk), lerp(610, 754, hk) - 90 * math.sin(hk * math.pi), 46)
            p.eyes, p.mouth = "shock", "bigO"
    elif t < 21.5:
        fl["face"] = -1
        if t < 20.4:
            fl["sm_head"] = None
            fl["loose_head"] = (1210, 754, 46)
            p = stand(1120, face=-1, eyes="sad", mouth="frown", brow=1.3, look=(-1, 1))
            if t > 19.9:
                p = crouch(1150, face=1, depth=1.0, eyes="sad", mouth="frown", brow=1.3, hand_f=(1200, 740), hand_b=(1190, 746))
                fl["face"] = 1
        else:
            k = seg(t, 20.4, 21.1)
            hx, hy = lerp(1215, SNX, k), lerp(720, 606, k)
            fl["sm_head"] = (hx, hy, 46, 0.35 * k) if k >= 1 else None
            if k < 1:
                fl["loose_head"] = (hx, hy, 46)
            p = stand(1110, face=1, eyes="sad", mouth="frown", brow=1.0, torso=0.3, hand_f=(hx - 30, hy + 30),
                      hand_b=(hx - 40, hy + 40))
            if k >= 1:
                p = stand(1110, face=-1, eyes="normal", mouth="wavy", hand_f=(1080, 630), hand_b=(1150, 630))
                fl["face"] = -1
        fl["sm_head"] = fl.get("sm_head") or None
        if t > 21.1:
            fl["sm_head"] = (SNX, 606, 46, 0.35)
    elif t < 23.2:
        fl["sm_head"] = (SNX, 606, 46, 0.35)
        fl["face"] = -1
        p = stand(1110, face=-1, eyes="shock" if t > 22.0 else "normal", mouth="bigO" if t > 22.0 else "wavy",
                  look=(1, -0.6), hand_f=(1070, 480), hand_b=(1090, 490))
        if t > 22.0:
            gk = seg(t, 22.0, 23.2, lambda v: v)
            gx = lerp(250, 1060, gk)
            fl["giant"] = (gx, 210, gx / 210)
    elif t < 26.6:
        fl["sm_gone"] = True
        gk = seg(t, 23.2, 26.0, ease_out)
        gx = lerp(1060, 1460, gk)
        fl["giant"] = (gx, 210 + 10 * gk, gx / 210)
        fl["legs"] = True
        fl["tree_shake"] = 14 * math.sin(t * 40) * seg(t, 25.8, 26.0) * (1 - seg(t, 26.0, 26.6))
        p = stand(HIDE[0])
    else:
        fl["sm_gone"] = True
        gx = 1460.0
        fl["giant"] = (gx, 220, gx / 210)
        pop = seg(t, 26.6, 26.9, back_out)
        p = stand(gx, eyes="closed" if t < 27.6 else "normal", mouth="wavy" if t < 27.6 else "flat",
                  hand_f=(gx + 150, 290 - 30 * math.sin(t * 8)), hand_b=(gx - 140, 300 + 30 * math.sin(t * 8)),
                  elbow_f="down", elbow_b="down")
        p.hip = (gx, lerp(820, 470, pop))
        p.foot_b, p.foot_f = (gx - 20, 900), (gx + 20, 900)
        fl["stars"] = 26.9 < t < 27.6
        if t > 27.4:
            fl["flake"] = seg(t, 27.4, 28.1, lambda v: v)
            p.look = (0.6, lerp(-1.2, 0.4, fl["flake"]))
        if t > 28.1:
            p = P_(p, eyes="closed", mouth="o", tilt=-0.25)
            fl["flake"] = None
        if t > 28.45:
            k = seg(t, 28.45, 28.6, ease_out)
            p = P_(p, eyes="closed", mouth="bigO", tilt=lerp(-0.25, 0.3, k))
        if t > 29.0:
            p = P_(p, eyes="happy", mouth="grin", tilt=0.0)
    fl["flying"] = flying
    fl["splats"] = splats
    return p, ex, fl


def camera(t, pose):
    hx = pose.hip[0]
    sh = ((12.4, 0.3, 7), (14.3, 0.3, 7), (19.15, 0.3, 6), (21.6, 1.6, 4), (23.2, 0.5, 12), (26.0, 0.4, 10))
    if t < 3.0:
        return shaken(Cam(hx + 80, 520, 1.85), t, sh)
    keys = [(3.0, 840, 540, 1.85), (7.4, 960, 560, 1.8), (9.4, 950, 520, 2.0), (10.8, 960, 520, 2.1),
            (11.5, 920, 520, 1.95), (12.6, 880, 480, 2.2), (14.3, 860, 470, 2.4), (15.6, 860, 520, 2.0),
            (16.6, 900, 540, 1.75), (19.4, 1060, 560, 1.85), (20.4, 1100, 560, 2.1), (21.4, 1080, 520, 1.8),
            (23.0, 980, 520, 1.6), (24.5, 1250, 520, 1.6), (26.2, 1460, 500, 1.7), (27.2, 1460, 380, 2.2),
            (28.0, 1460, 330, 2.5), (30.0, 1460, 350, 2.2)]
    return cam_keys(t, keys, sh)


# ------------------------------------------------------------------ sound
WALTZ = ([[60, 64, 67], [65, 69, 72], [67, 71, 74], [60, 64, 67]], [48, 53, 55, 48])


def sound():
    sfx_ambient(0, 30, "wind", 0.07)
    chords_loop(0.0, 12.4, 150, *WALTZ, inst="musicbox", drums="waltz", vel=0.16)
    cut_music(12.42)
    A.record_scratch(12.42)
    A.section_sneaky(14.6, 16.6)
    chords_loop(16.6, 19.2, 160, [[60, 63, 67], [58, 62, 65]], [36, 34], inst="square", drums="dance", vel=0.17)
    cut_music(19.2)
    A.section_sad(19.6)
    tt = tvec(1.6)
    place(M, 21.6, np.sin(2 * np.pi * np.cumsum(45 + 40 * tt) / A.SR) * 0.6 * (tt / 1.6), 1.0)
    chords_loop(26.7, 30.0, 150, *WALTZ, inst="musicbox", drums="waltz", vel=0.14)
    # sfx
    for k in range(10):
        A.thud(0.25 + k * 0.31, 0.15, 160)
        place(S, 0.25 + k * 0.31, A.highpass(noise(0.08), 3) * np.exp(-tvec(0.08) * 30) * 0.15)
    for k in range(14):
        place(S, 3.1 + k * 0.32, A.lowpass(noise(0.3), 8) * np.sin(np.pi * tvec(0.3) / 0.3) * 0.25)
    sfx_pop(7.45, 0.3)
    sfx_pop(9.3, 0.3)
    for tt_ in (9.8, 10.2, 10.6):
        sfx_pop(tt_, 0.35)
    for t0 in (12.1, 14.0, 16.25, 17.0, 17.6, 18.2, 18.8):
        A.whoosh(t0, 0.3, 0.3)
    for t0 in (12.4, 14.3, 17.35, 17.95, 18.55, 19.15):
        A.thud(t0, 0.35, 140)
        place(S, t0, A.lowpass(noise(0.25), 3) * np.exp(-tvec(0.25) * 14) * 0.5)
    A.thud(19.5, 0.3, 110)
    sfx_pop(21.1, 0.3)
    d = 4.4
    tt = tvec(d)
    rumble = A.lowpass(noise(d), 40) * 5 * np.minimum(1, tt / 1.6) * np.exp(-np.maximum(tt - 3.6, 0) * 4)
    place(S, 21.6, rumble, 0.6)
    A.thud(23.2, 0.7, 60)
    A.thud(26.0, 0.7, 60)
    place(S, 26.05, A.lowpass(noise(0.6), 4) * np.exp(-tvec(0.6) * 6), 0.4)
    sfx_pop(26.7, 0.45)
    for k in range(3):
        place(S, 27.4 + k * 0.08, A.bell(3500 + k * 500, 0.3, 0.06))
    # voices
    v_hum(0.5, [72, 76, 79, 76, 72], 0.3, 0.26)
    v_ooh(2.3, 0.55)
    v_strain(3.4, 0.6, 0.3)
    v_hum(4.6, [67, 72, 76, 72], 0.4, 0.22)
    v_hehe(8.0)
    v_tada(11.45)
    v_ow(12.42)
    v_hey(12.9)
    v_hmm(13.6, up=True, g=0.45)
    place(V, 14.32, breathy(0.25, 1700, ((0, 1), (1, 0))), 0.5)
    v_hey(15.7)
    v_hup(16.2)
    v_whoa(17.05)
    v_eek(18.25)
    v_nooo(19.5, 1.2)
    v_sniff(20.8)
    v_uhoh(22.0)
    v_aaah(23.1, 2.8, 0.5)
    v_ooh(26.95, 0.35)
    v_hmm(27.6, up=True, g=0.35)
    v_achoo(28.0)
    v_hehe(29.05)


EP = Episode(title=("SNOW", "DAY"), title_col=(130, 210, 255), outfit=OUT, story=story, camera=camera,
             background=background, behind=behind, front=front, sound=sound,
             flashes=[(23.2, 0.2, (255, 255, 255), 0.5)],
             speed=lambda t: 0.6 if 23.2 < t < 25.6 else 0)

if __name__ == "__main__":
    run(EP)
