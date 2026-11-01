"""Episode 3 - PANCAKE PANIC (kitchen, chef coat + chef hat)."""
import math

from engine import *

OUT = Outfit(top=(238, 238, 242), top_dark=(196, 198, 208), sleeve="long", pants=(58, 60, 72),
             hat="chef", hat_col=(248, 248, 250), neckerchief=(214, 54, 54))
CEIL = -150.0
STOVE_PAN = (935.0, 578.0)
PLATE = (1040.0, 588.0)
PANC = (226, 168, 88)
PANC_D = (196, 136, 64)
X = 760.0


# ------------------------------------------------------------------ props
def pan_center(hand, ang, f):
    return add(hand, rot((f * 78, -4), ang))


def draw_pan(P, hand, ang, f):
    c = pan_center(hand, ang, f)
    P.line(hand, add(hand, rot((f * 34, -4), ang)), 9, (40, 40, 46))
    pts = [add(c, rot(v, ang)) for v in ((-48, -8), (48, -8), (40, 8), (-40, 8))]
    P.poly(pts, (44, 46, 54))


def bowl(P, hand, ang, f):
    c = add(hand, rot((f * 26, -6), ang))
    pts = [add(c, rot((40 * math.cos(a), 30 * math.sin(a)), ang)) for a in [i * math.pi / 12 for i in range(13)]]
    P.poly(pts, (120, 180, 220))
    P.poly([add(c, rot(v, ang)) for v in ((-38, -3), (38, -3), (38, 3), (-38, 3))], (245, 225, 170))


def whisk(P, hand, ang, f):
    P.line(hand, (hand[0] + 6, hand[1] + 40), 4, (190, 190, 200))
    P.ellipse(hand[0] + 7, hand[1] + 52, 8, 14, (200, 200, 210))


def fork(P, hand, ang, f):
    tip = (hand[0] + f * 30, hand[1] - 30)
    P.line(hand, tip, 4, (200, 200, 210))
    for k in (-5, 0, 5):
        P.line(tip, (tip[0] + f * 8 + k, tip[1] - 12), 2, (200, 200, 210))


def pancake(P, x, y, sc=1.0, flat=1.0):
    P.ellipse(x, y, 40 * sc, 9 * flat * sc + 1, PANC_D)
    P.ellipse(x, y - 2, 37 * sc, 7 * flat * sc + 1, PANC)


def background(P, t, fl, cam):
    P.rect(-800, -900, 2800, CEIL, (210, 206, 196))
    P.rect(-800, CEIL - 14, 2800, CEIL, (180, 176, 166))
    P.rect(-800, CEIL, 2800, 800, (176, 214, 204))
    for y in range(int(CEIL), 800, 46):
        P.line((-800, y), (2800, y), 2, (156, 194, 184), cap=False)
    for x in range(-800, 2800, 46):
        P.line((x, CEIL), (x, 800), 2, (156, 194, 184), cap=False)
    # hanging lamp
    P.line((900, CEIL), (900, -40), 3, (60, 60, 60))
    P.chord(900, -10, 50, 34, 180, 360, (230, 120, 70))
    P.circle(900, -8, 12, (255, 240, 180))
    # floor
    P.rect(-800, 800, 2800, 1700, (120, 110, 104))
    for i in range(-10, 40):
        for j in range(0, 8):
            if (i + j) % 2 == 0:
                P.rect(i * 80, 800 + j * 80, i * 80 + 80, 880 + j * 80, (150, 140, 132))
    # upper cabinets
    for x0 in range(480, 1440, 160):
        P.rect(x0, 90, x0 + 150, 270, (172, 122, 82))
        P.rect(x0 + 10, 100, x0 + 140, 260, (186, 136, 94))
        P.rect(x0 + 120, 170, x0 + 128, 200, (230, 220, 200))
    P.rect(820, 270, 1040, 300, (150, 152, 160))  # hood
    P.poly([(840, 300), (1020, 300), (1060, 340), (800, 340)], (170, 172, 180))
    # fridge
    P.rect(160, 160, 420, 800, (232, 236, 240))
    P.rect(160, 440, 420, 448, (190, 196, 204))
    P.rect(390, 260, 400, 380, (170, 176, 186))
    P.rect(390, 480, 400, 600, (170, 176, 186))
    P.rect(220, 220, 270, 280, (250, 220, 90))
    P.rect(290, 240, 330, 300, (120, 200, 240))
    # window
    P.rect(1560, 110, 1880, 430, (240, 240, 240))
    P.rect(1576, 126, 1864, 414, (160, 210, 245))
    P.circle(1780, 200, 30, (255, 240, 170))
    P.rect(1712, 110, 1726, 430, (240, 240, 240))
    P.rect(1576, 360, 1864, 414, (110, 170, 110))
    # counter
    P.rect(480, 600, 1500, 800, (170, 120, 80))
    for x0 in range(490, 1490, 200):
        P.rect(x0, 620, x0 + 190, 790, (184, 132, 90))
        P.rect(x0 + 85, 640, x0 + 105, 648, (230, 220, 200))
    P.rect(470, 584, 1510, 604, (84, 88, 100))
    # stove top
    P.rect(860, 578, 1010, 586, (40, 40, 46))
    if fl.get("burner", True):
        for k in range(5):
            P.ellipse(900 + k * 18, 580, 6, 3, (90, 160, 255))
    # utensils jar
    P.rect(1300, 530, 1340, 586, (200, 90, 70))
    P.line((1310, 530), (1300, 470), 4, (160, 120, 80))
    P.line((1328, 530), (1340, 460), 4, (200, 200, 210))


def behind(P, t, fl, cam):
    # plate
    P.ellipse(PLATE[0], PLATE[1] - 4, 48, 8, (245, 245, 248))
    if fl["bowl_counter"]:
        bowl(P, (1130, 582), 0, 1)
    if not fl["pan_held"]:
        draw_pan(P, (857, 582), 0, 1)
    # pancakes not on the head
    for st in fl["cakes"]:
        kind = st[0]
        if kind == "pan":
            pancake(P, st[1][0], st[1][1] - 9, st[2])
        elif kind == "air":
            x, y, spin = st[1]
            pancake(P, x, y, 1.0, abs(math.cos(spin)) * 1.4 + 0.2)
        elif kind == "ceil":
            x, wob = st[1], st[2]
            P.ellipse(x, CEIL + 8 + 6 * wob, 52, 12 + 4 * wob, PANC_D)
            P.ellipse(x, CEIL + 6 + 6 * wob, 48, 9 + 4 * wob, PANC)
            if wob > 0:
                P.ellipse(x + 30, CEIL + 22 + 14 * wob, 5, 8 * wob + 1, PANC)
        elif kind == "plate":
            pancake(P, PLATE[0], PLATE[1] - 12, 1.0)


def front(P, t, fl, s, cam, ex):
    if fl.get("batter"):
        a, b = fl["batter"]
        P.line(a, b, 6, (245, 225, 170))
    if fl.get("splat") is not None:
        burst(P, fl["splat_pos"], fl["splat"], seed=4, n=24, a0=0, a1=360, v0=120, v1=380, r0=4, r1=9,
              cols=(PANC, (245, 225, 170)), life=0.5, g=900)
    if 3.6 < t < 16.3 or (t > 4 and fl["pan_held"]):
        pc = fl["pan_c"]
        for k in range(3):
            ph = (t * 0.9 + k / 3) % 1
            P.circle(pc[0] - 20 + k * 20 + 6 * math.sin(ph * 9), pc[1] - 20 - 70 * ph, 6 * (1 - ph) + 1, (235, 235, 240))


def face_cake(t):
    def f(P, s):
        hc = s["head"]
        ang = s["head_ang"]
        fc = s.get("_face", 1)
        k = 1 - seg(t, 22.6, 24.4, lambda v: v)
        if k <= 0:
            return
        P.ellipse(hc[0], hc[1] + 4, 62 * k, 58 * k, PANC_D)
        P.ellipse(hc[0], hc[1], 58 * k, 54 * k, PANC)
        for dx, dy in ((-24, -20), (20, 26), (-14, 30), (30, -8)):
            P.circle(hc[0] + dx * k, hc[1] + dy * k, 6 * k, PANC_D)
        if t > 21.2:
            blink = (t % 1.3) < 0.1
            for dx, sc in ((14, 1.0), (36, 0.78)):
                v = rot((dx, -8), ang)
                e = (hc[0] + v[0], hc[1] + v[1])
                P.circle(e[0], e[1], 13 * sc, (14, 14, 18))
                if not blink:
                    P.ellipse(e[0], e[1], 8 * sc, 10, (238, 232, 214))
                    P.circle(e[0] + 1, e[1], 4 * sc, (40, 40, 46))
        if t > 22.5:
            v = rot((28, 24), ang)
            m = (hc[0] + v[0], hc[1] + v[1])
            P.ellipse(m[0], m[1], 10, 6 + 6 * abs(math.sin(t * 14)), (120, 36, 46))
    return f


# ------------------------------------------------------------------ story
def cakes(t, pan_c):
    out = []
    # pancake 1
    if 3.6 <= t < 6.9:
        out.append(("pan", pan_c, seg(t, 3.6, 4.4)))
    elif 6.9 <= t < 7.6:
        k = (t - 6.9) / 0.7
        x = lerp(pan_c[0], 900, k)
        y = lerp(pan_c[1] - 10, CEIL + 10, 1 - (1 - k) ** 2)
        out.append(("air", (x, y, k * 9)))
    elif 7.6 <= t < 20.0:
        out.append(("ceil", 900, seg(t, 18.4, 19.9) * (0.6 + 0.4 * math.sin(t * 20))))
    elif 20.0 <= t < 20.25:
        k = (t - 20.0) / 0.25
        out.append(("air", (900 - 100 * k, lerp(CEIL + 10, 340, k * k), k * 3)))
    # pancake 2
    if 13.1 <= t < 14.2 or 14.8 <= t < 16.3:
        out.append(("pan", pan_c, seg(t, 13.1, 13.8)))
    elif 14.2 <= t < 14.8:
        k = (t - 14.2) / 0.6
        out.append(("air", (pan_c[0], pan_c[1] - 10 - 110 * math.sin(k * math.pi), k * math.pi * 2)))
    elif 16.3 <= t < 16.6:
        k = (t - 16.3) / 0.3
        out.append(("air", (lerp(pan_c[0], PLATE[0], k), lerp(pan_c[1] - 10, PLATE[1] - 12, k), 0)))
    elif 16.6 <= t < 27.0:
        out.append(("plate",))
    elif 27.0 <= t < 27.6:
        k = (t - 27.0) / 0.6
        out.append(("air", (lerp(PLATE[0], 1060, k), lerp(PLATE[1] - 12, CEIL + 10, 1 - (1 - k) ** 2), k * 10)))
    elif t >= 27.6:
        out.append(("ceil", 1060, 0.0))
    return out


def story(t):
    ex = {"held": None}
    fl = {"pan_held": False, "bowl_counter": True, "batter": None, "splat": None, "splat_pos": (900, CEIL)}
    base = stand(X, eyes="happy", mouth="smile", torso=0.08)
    hand_pan = (868, 572)
    p = base
    if t < 3.0:
        a = t * 9
        p = P_(base, hand_b=(808, 528), hand_f=(828 + 18 * math.cos(a), 512 + 8 * math.sin(a)), look=(1, 1), tilt=0.15)
        ex["held_b"] = bowl
        ex["held"] = whisk
        fl["bowl_counter"] = False
    elif t < 4.9:
        fl["bowl_counter"] = False
        k = seg(t, 3.0, 3.5)
        p = P_(base, hand_b=(808, 560), hand_f=lerp2((828, 512), (888, 480), k), look=(1, 1), tilt=0.15)
        ex["held"] = bowl
        ex["item_ang"] = 1.0 * seg(t, 3.4, 3.7) * (1 - seg(t, 4.4, 4.7))
        if 3.6 < t < 4.4:
            lip = add(p.hand_f, rot((26 + 40, -6), ex["item_ang"]))
            fl["batter"] = (lip, (STOVE_PAN[0], STOVE_PAN[1] - 8))
    elif t < 5.0:
        p = P_(base, hand_f=hand_pan)
    elif t < 13.0:
        fl["pan_held"] = True
        ex["held"] = draw_pan
        if t < 6.8:
            jig = 5 * math.sin(t * 25) * seg(t, 5.2, 5.4)
            p = P_(base, hand_f=(hand_pan[0] + jig, hand_pan[1] - 6), eyes="happy" if (t % 1.2) < 0.6 else "normal",
                   mouth="grin", look=(1, 0.5))
        elif t < 8.0:
            k = seg(t, 6.8, 6.95, ease_out) * (1 - seg(t, 7.05, 7.3))
            p = P_(base, hand_f=(hand_pan[0], hand_pan[1] - 70 * k), eyes="normal", mouth="o", mouth_amt=0.7,
                   look=(0, -1.2), tilt=-0.3 * seg(t, 7.0, 7.3))
            ex["item_ang"] = -0.6 * k
            if t > 7.6:
                p.eyes = "wide"
        elif t < 9.5:
            p = P_(base, hand_f=hand_pan, eyes="shock" if t < 8.6 else "squint", mouth="bigO" if t < 8.6 else "wavy",
                   look=(0, -1.3), tilt=-0.35, torso=-0.05)
        elif t < 11.5:
            p = P_(base, hand_f=(820, 300), hand_b=(790, 520), eyes="squint", mouth="wavy", look=(0, -1),
                   tilt=-0.35, torso=-0.05, elbow_f="back")
            for j0 in (9.6, 10.6):
                jk = seg(t, j0, j0 + 0.6, lambda v: v)
                if 0 < jk < 1:
                    h = 110 * math.sin(jk * math.pi)
                    p.hip = (p.hip[0], p.hip[1] - h)
                    p.foot_b = (p.foot_b[0], p.foot_b[1] - h)
                    p.foot_f = (p.foot_f[0], p.foot_f[1] - h)
                    p.hand_f = (p.hand_f[0], p.hand_f[1] - h)
                    p.hand_b = (p.hand_b[0], p.hand_b[1] - h)
            ex["item_ang"] = -1.2
        else:
            k = seg(t, 11.5, 11.8)
            p = P_(base, hand_f=(820, 560), hand_b=(700, 560), eyes="normal", mouth="wavy", torso=0.0,
                   tilt=0.15 * math.sin(t * 6), brow=0.6, look=(1, 0))
            p.hip = (X, STAND_Y - 8 * math.sin(seg(t, 11.7, 12.1) * math.pi))
            ex["item_ang"] = 0.0
            fl["pan_held"] = True
            if t > 12.5:
                fl["pan_held"] = False
                ex["held"] = None
    elif t < 16.7:
        if t < 13.9:
            k = seg(t, 13.0, 13.2)
            p = P_(base, hand_f=(888, 480), hand_b=(808, 560), look=(1, 1), tilt=0.15)
            ex["held"] = bowl
            fl["bowl_counter"] = False
            ex["item_ang"] = 1.0 * seg(t, 13.0, 13.2) * (1 - seg(t, 13.6, 13.85))
            if 13.1 < t < 13.6:
                lip = add(p.hand_f, rot((66, -6), ex["item_ang"]))
                fl["batter"] = (lip, (STOVE_PAN[0], STOVE_PAN[1] - 8))
        else:
            fl["pan_held"] = True
            ex["held"] = draw_pan
            k = seg(t, 14.15, 14.25) * (1 - seg(t, 14.3, 14.5))
            p = P_(base, hand_f=(hand_pan[0], hand_pan[1] - 25 * k), eyes="normal", mouth="wavy", look=(1, -0.6),
                   tilt=0.05, brow=-0.5)
            ex["item_ang"] = -0.25 * k
            if t > 14.8:
                p = P_(base, hand_f=hand_pan, hand_b=(740, 380), eyes="happy", mouth="grin", elbow_b="back")
                if t > 16.0:
                    kk = seg(t, 16.0, 16.3)
                    p.hand_f = lerp2(hand_pan, (900, 560), kk)
                    ex["item_ang"] = 0.5 * seg(t, 16.25, 16.5)
                    p.hand_b = lerp2((740, 380), (740, 620), kk)
    elif t < 20.25:
        k = seg(t, 17.0, 17.4)
        p = P_(base, hand_f=lerp2((860, 560), (850, 470), seg(t, 17.6, 18.0)), eyes="happy", mouth="smile", look=(1, 0.3))
        ex["held"] = fork
        if t > 18.0:
            p.mouth, p.mouth_amt, p.eyes = "o", 1.0, "closed"
        if t > 19.4:
            p = P_(p, eyes="wide", mouth="o", look=(0, -1.3), tilt=-0.3, mouth_amt=0.6)
    else:
        ex["on_head"] = face_cake(t)
        p = P_(base, hand_f=(850, 470), eyes="closed", mouth="flat", tilt=-0.1)
        ex["held"] = fork
        if t > 24.4:
            p = P_(base, eyes="happy", mouth="grin", hand_f=(850, 480), hand_b=(720, 400), elbow_b="back",
                   tilt=-0.1 + 0.1 * math.sin(t * 8))
            ex["held"] = fork
        if t > 26.6:
            k = seg(t, 26.7, 27.0, ease_out) * (1 - seg(t, 27.1, 27.3))
            p = P_(base, eyes="happy", mouth="grin", hand_f=(lerp(980, 1010, k), 590 - 70 * k), look=(1, 0))
            ex["held"] = None
        if t > 27.6:
            p = P_(base, eyes="normal", mouth="smile", hand_f=(820, 560), hand_b=(700, 560), look=(1, -1.2),
                   tilt=-0.25, brow=0.4)
    if fl["pan_held"]:
        fl["pan_c"] = pan_center(p.hand_f if ex.get("held") is draw_pan else p.hand_f, ex.get("item_ang", 0), 1)
    else:
        fl["pan_c"] = STOVE_PAN
    if fl["pan_held"] and ex.get("held") is not draw_pan:
        fl["pan_held"] = False
        fl["pan_c"] = STOVE_PAN
    fl["cakes"] = cakes(t, fl["pan_c"])
    if 7.6 <= t < 8.0:
        fl["splat"], fl["splat_pos"] = t - 7.6, (900, CEIL + 8)
    if 20.25 <= t < 20.8:
        fl["splat"], fl["splat_pos"] = t - 20.25, (X + 20, 360)
    if 27.6 <= t < 28.0:
        fl["splat"], fl["splat_pos"] = t - 27.6, (1060, CEIL + 8)
    return p, ex, fl


def camera(t, pose):
    keys = [(0, 840, 520, 1.85), (3.0, 880, 520, 2.1), (5.0, 870, 500, 2.0), (6.8, 880, 470, 1.9),
            (7.25, 900, 200, 1.6), (7.8, 900, 150, 1.7), (8.4, 870, 450, 1.85), (11.5, 860, 470, 1.95),
            (12.6, 880, 520, 2.1), (16.0, 900, 520, 2.0), (17.8, 880, 470, 2.4), (18.3, 880, 470, 2.4),
            (18.7, 900, 60, 2.0), (19.4, 880, 380, 2.0), (20.0, 880, 320, 1.7), (20.3, 860, 380, 2.4),
            (22.4, 860, 370, 2.8), (24.4, 860, 430, 2.2), (26.6, 920, 470, 1.9), (27.3, 960, 160, 1.6),
            (28.2, 920, 330, 1.6), (30.0, 900, 360, 1.75)]
    return cam_keys(t, keys, ((7.6, 0.4, 7), (20.25, 0.6, 14), (27.6, 0.3, 6)))


# ------------------------------------------------------------------ sound
SWING = ([[57, 60, 64, 67], [50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59]], [45, 38, 43, 36])


def sound():
    chords_loop(0.0, 7.6, 116, *SWING, inst="epiano", drums="swing", vel=0.17,
                mel=[None, 76, 79, None, 81, None, 79, 76])
    cut_music(7.6)
    A.record_scratch(7.6)
    A.section_sneaky(8.6, 12.4)
    chords_loop(15.0, 20.2, 128, [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]], [36, 31, 33, 29],
                inst="pluck", drums="dance", vel=0.2)
    cut_music(20.22)
    A.record_scratch(20.22)
    chords_loop(25.0, 30.0, 116, *SWING, inst="epiano", drums="swing", vel=0.17, mel=[None, 76, 79, None, 81, None, 79, 84])
    # sfx
    for k in range(20):
        A.whoosh(0.2 + k * 0.14, 0.05, 0.08)
    for k in range(4):
        A.plip(3.6 + k * 0.15, 600, 0.12)
    sfx_sizzle(3.7, 12.5, 0.12)
    A.whoosh(6.85, 0.35, 0.45)
    A.thud(7.6, 0.45, 160)
    sfx_splash(7.6, 0.3, 0.3)
    A.thud(9.75, 0.3, 120)
    A.thud(10.75, 0.3, 120)
    for k in range(3):
        A.plip(13.15 + k * 0.15, 600, 0.12)
    A.whoosh(14.2, 0.25, 0.25)
    A.thud(14.8, 0.25, 200)
    place(S, 14.85, A.bell(1568, 0.8, 0.22))
    A.whoosh(16.3, 0.2, 0.2)
    A.beep(16.62, 3000, 0.02, 0.15)
    for k in range(4):
        place(S, 18.6 + k * 0.2, A.highpass(noise(0.05), 2) * 0.2)
    A.whoosh(19.95, 0.3, 0.4)
    A.thud(20.25, 0.6, 100)
    sfx_splash(20.25, 0.4, 0.5)
    A.whoosh(26.9, 0.3, 0.4)
    A.thud(27.6, 0.4, 160)
    sfx_splash(27.6, 0.3, 0.3)
    # voices
    v_hum(0.5, [72, 74, 76, 79, 76, 74, 72, 67], 0.3, 0.26)
    v_hum(5.4, [76, 79, 84], 0.25, 0.3)
    v_hehe(6.0, 2)
    v_huh(8.05)
    v_hmm(8.9, up=True)
    v_hup(9.7)
    v_hup(10.7)
    v_hmm(11.8, up=False, g=0.4)
    v_yay(14.9)
    v_mmm(17.9)
    v_hmm(19.45, up=True, g=0.45)
    v_hmm(21.4, up=True, g=0.3)
    v_nom(22.6, 3)
    v_nom(23.5, 3)
    v_mmm(24.6)
    v_hehe(26.5, 2)
    v_hmm(27.75, up=True, g=0.35)
    v_hehe(28.6, 3)


EP = Episode(title=("PANCAKE", "PANIC"), title_col=(255, 196, 92), outfit=OUT, story=story, camera=camera,
             background=background, behind=behind, front=front, sound=sound,
             flashes=[(20.25, 0.2, (255, 240, 200), 0.5)])

if __name__ == "__main__":
    run(EP)
