"""Episode 2 - SAND CASTLE (beach, red tank top + shorts + sunglasses)."""
import math
import random

from engine import *

OUT = Outfit(top=(222, 72, 62), top_dark=(170, 52, 46), sleeve="none", pants=(36, 168, 170),
             shorts=True, glasses="up")
CX = 940.0  # castle centre
SAND = (232, 205, 150)
SAND_D = (210, 180, 126)


# ------------------------------------------------------------------ drawing
def bucket(P, hand, ang, f):
    x, y = hand
    P.arc(x, y + 22, 20, 22, 180, 360, 3, (60, 60, 60))
    P.poly([(x - 22, y + 22), (x + 22, y + 22), (x + 17, y + 62), (x - 17, y + 62)], (250, 200, 50))
    P.rect(x - 22, y + 22, x + 22, y + 28, (230, 170, 30))


def phone(P, hand, ang, f):
    x, y = hand
    P.rect(x - 9, y - 30, x + 9, y + 2, (30, 30, 40))
    P.rect(x - 7, y - 27, x + 7, y - 2, (120, 180, 240))


def castle(P, t, stage, washed):
    b = 795
    if washed:
        P.ellipse(CX, b, 95, 20, SAND_D)
        return
    s1, s2, s3 = clamp(stage), clamp(stage - 1), clamp(stage - 2)
    if s1 > 0:
        P.poly([(CX - 80, b), (CX + 80, b), (CX + 60, b - 36 * s1), (CX - 60, b - 36 * s1)], SAND)
    if s2 > 0:
        h = 60 * s2
        P.rect(CX - 48, b - 36 - h, CX + 48, b - 36, SAND_D)
        for k in range(4):
            x0 = CX - 48 + k * 26
            P.rect(x0, b - 36 - h - 12 * s2, x0 + 14, b - 36 - h, SAND_D)
        P.chord(CX, b - 36, 14, 22 * s2, 180, 360, (150, 120, 80))
    if s3 > 0:
        for dx in (-62, 62):
            h = 120 * s3
            P.rect(CX + dx - 18, b - 30 - h, CX + dx + 18, b - 30, SAND)
            P.poly([(CX + dx - 24, b - 30 - h), (CX + dx + 24, b - 30 - h), (CX + dx, b - 70 - h)], SAND_D)
    if t > 9.6:
        k = seg(t, 9.6, 9.75, back_out)
        P.line((CX + 62, 645), (CX + 62, 645 - 50 * k), 3, (90, 70, 50))
        P.poly([(CX + 62, 595 + 50 * (1 - k)), (CX + 96 * k + 62 * (1 - k), 605 + 46 * (1 - k)), (CX + 62, 615)],
               (230, 60, 60))


def chest(P, t):
    if t < 20.4 or t > 25.3:
        return
    rise = seg(t, 20.4, 21.2, ease_out)
    x, y = CX + 10, 800 - 60 * rise
    lid = seg(t, 21.2, 21.5, back_out)
    if lid > 0:
        for a in range(-80, 81, 20):
            ra = math.radians(a - 90)
            ln = 120 + 30 * math.sin(t * 6 + a)
            P.line((x + 40 * math.cos(ra), y - 30 + 40 * math.sin(ra)),
                   (x + ln * math.cos(ra) * lid, y - 30 + ln * math.sin(ra) * lid), 6, (255, 228, 110))
        P.ellipse(x, y - 34, 50 * lid, 14 * lid, (255, 210, 60))
    P.rect(x - 56, y - 30, x + 56, y + 30, (128, 82, 40))
    P.rect(x - 56, y - 30, x + 56, y - 22, (210, 170, 60))
    P.rect(x - 8, y - 22, x + 8, y - 4, (210, 170, 60))
    # lid (rotating back)
    ang = -1.9 * lid
    piv = (x - 56, y - 30)
    pts = [add(piv, rot(v, ang)) for v in ((0, 0), (112, 0), (106, -26), (6, -26))]
    P.poly(pts, (150, 98, 50))


def crab(P, x, y, sc=1.0, t=0.0):
    for side in (-1, 1):
        for k in range(3):
            P.line((x + side * 10 * sc, y + 2), (x + side * (22 + k * 5) * sc, y + (10 + k * 3) * sc), 3 * sc, (200, 50, 40))
        cl = (x + side * 26 * sc, y - 14 * sc + 3 * math.sin(t * 12 + side))
        P.line((x + side * 12 * sc, y - 4 * sc), cl, 4 * sc, (210, 60, 50))
        P.circle(cl[0], cl[1], 7 * sc, (225, 70, 55))
    P.ellipse(x, y, 18 * sc, 11 * sc, (230, 74, 58))
    for side in (-1, 1):
        P.line((x + side * 6 * sc, y - 8 * sc), (x + side * 7 * sc, y - 18 * sc), 2 * sc, (30, 30, 30))
        P.circle(x + side * 7 * sc, y - 19 * sc, 4 * sc, (255, 255, 255))
        P.circle(x + side * 7 * sc, y - 19 * sc, 2 * sc, (20, 20, 20))


def background(P, t, fl, cam):
    for i in range(14):
        y0 = -900 + i * 100
        P.rect(-800, y0, 2800, y0 + 101, lerp_col((92, 170, 230), (190, 228, 245), i / 13))
    P.circle(1320, 120, 70, (255, 238, 150))
    P.circle(1320, 120, 54, (255, 248, 200))
    for cx_, cy_, sp in ((300, 60, 9), (900, -60, 6), (1600, 30, 11)):
        x = cx_ + (t * sp) % 400
        for dx, r in ((-40, 30), (0, 42), (40, 32), (80, 24)):
            P.circle(x + dx, cy_, r, (250, 252, 255))
    # sea
    P.rect(-800, 470, 2800, 575, (40, 140, 200))
    P.rect(-800, 470, 2800, 490, (30, 110, 175))
    for k in range(-8, 30):
        x = k * 90 + (t * 20) % 90
        P.arc(x, 520 + (k % 3) * 14, 22, 6, 200, 340, 3, (150, 210, 240))
    # giant wave
    hw = seg(t, 12.4, 14.0, ease_in) * (1 - seg(t, 14.0, 14.4))
    if hw > 0:
        pts = [(-800, 575)]
        for x in range(-800, 2801, 60):
            bump = math.exp(-((x - 1000) / 900) ** 2)
            pts.append((x, 470 - 420 * hw * bump + 10 * math.sin(x * 0.02 + t * 6)))
        pts.append((2800, 575))
        P.poly(pts, (36, 120, 186))
        for x in range(-800, 2801, 40):
            bump = math.exp(-((x - 1000) / 900) ** 2)
            P.circle(x, 470 - 420 * hw * bump + 8, 16 * hw * bump + 2, (235, 248, 255))
    P.rect(-800, 560, 2800, 600, (205, 178, 130))
    P.rect(-800, 590, 2800, 1700, SAND)
    rnd = random.Random(2)
    for _ in range(90):
        x, y = rnd.uniform(-600, 2600), rnd.uniform(620, 1500)
        P.circle(x, y, rnd.uniform(2, 4), SAND_D)
    # umbrella + towel
    P.rect(180, 782, 470, 800, (240, 240, 240))
    for k in range(0, 290, 58):
        P.rect(180 + k, 782, 209 + k, 800, (60, 150, 220))
    P.line((340, 790), (360, 420), 7, (240, 240, 240))
    for k in range(6):
        a0, a1 = math.pi + k * math.pi / 6, math.pi + (k + 1) * math.pi / 6
        pts = [(360, 420), (360 + 210 * math.cos(a0), 470 + 60 * math.sin(a0) + 50),
               (360 + 210 * math.cos(a1), 470 + 60 * math.sin(a1) + 50)]
        P.poly(pts, (230, 70, 60) if k % 2 == 0 else (250, 245, 235))
    # palm tree
    for k in range(10):
        y = 790 - k * 52
        x = 1560 + 30 * math.sin(k * 0.25)
        P.ellipse(x, y, 26 - k, 26, (150, 110, 70) if k % 2 else (130, 95, 60))
    top = (1560 + 30 * math.sin(2.5), 790 - 9 * 52)
    for a in (-160, -120, -60, -20, 200):
        ra = math.radians(a)
        sway = 0.06 * math.sin(t * 1.5 + a)
        pts = [top]
        for j in range(1, 6):
            pts.append((top[0] + math.cos(ra + sway) * j * 45, top[1] + math.sin(ra + sway) * j * 30 + j * j * 6))
        P.polyline(pts, 24, (60, 150, 80))
    P.circle(top[0] - 10, top[1] + 20, 14, (110, 80, 50))
    P.circle(top[0] + 14, top[1] + 24, 14, (110, 80, 50))


def behind(P, t, fl, cam):
    castle(P, t, fl["stage"], fl["washed"])
    chest(P, t)
    if fl["bucket_ground"]:
        bucket(P, (1040, 735), 0, 1)
    if 18.6 < t < 20.4:
        star(P, CX + 20, 780, 12 + 6 * math.sin(t * 12), (255, 240, 140))


def front(P, t, fl, s, cam, ex):
    if fl["sand"] is not None:
        burst(P, (CX - 20, 770), fl["sand"] % 0.5, seed=int(fl["sand"] * 2), n=18, a0=200, a1=330,
              v0=200, v1=420, r0=4, r1=8, cols=(SAND_D,), life=0.5)
    if 11.55 < t < 11.7:
        P.circle(s["hf"][0], s["hf"][1] - 20, 40, (255, 255, 255))
    # foreground wave crash
    if 14.0 < t < 15.5:
        vw, vh = W / cam.s, H / cam.s
        left, right, top, bot = cam.cx - vw / 2 - 50, cam.cx + vw / 2 + 50, cam.cy - vh / 2 - 50, cam.cy + vh / 2 + 50
        k = seg(t, 14.05, 14.6, ease_out)
        edge = lerp(right + 200, left - 200, k)
        ytop = lerp(top, bot + 200, seg(t, 14.9, 15.45, ease_in))
        pts = [(right, ytop)]
        for i in range(21):
            y = lerp(ytop, bot, i / 20)
            pts.append((edge + 50 * math.sin(i * 1.3 + t * 9), y))
        pts.append((right, bot))
        P.poly(pts, (46, 140, 210))
        for i in range(21):
            y = lerp(ytop, bot, i / 20)
            P.circle(edge + 50 * math.sin(i * 1.3 + t * 9), y, 30, (235, 248, 255))
        P.rect(left, ytop - 20, right, ytop + 10, (235, 248, 255))
    if 14.6 < t < 16:
        pass
    if fl["wet"] and 15.3 < t < 26:
        pass


def on_head_factory(t):
    def f(P, s):
        hc = s["head"]
        # seaweed
        P.polyline([(hc[0] - 30, hc[1] - 44), (hc[0] - 40, hc[1] - 20), (hc[0] - 50, hc[1] + 5)], 6, (60, 140, 60))
        P.polyline([(hc[0] + 10, hc[1] - 50), (hc[0] + 18, hc[1] - 25), (hc[0] + 12, hc[1])], 6, (70, 160, 70))
        # crab rides on the head, then climbs to the nose
        k = seg(t, 24.6, 25.2)
        x = lerp(hc[0], hc[0] + s["head_ang"] * 0 + (60 if t < 25.8 else -60), k)
        y = lerp(hc[1] - 60, hc[1] + 6, k)
        crab(P, x, y, 1.0, t)
    return f


# ------------------------------------------------------------------ story
def story(t):
    ex = {"held": None}
    fl = {"stage": 0.0, "washed": False, "bucket_ground": False, "sand": None, "wet": False}
    if t < 3.3:
        p = walk(stand(0), t, 0.0, 3.0, 260, 820, period=0.6)
        p.eyes, p.mouth = "happy", "smile"
        p.hand_f = (p.hip[0] + 34, STAND_Y - 4)
        if t >= 3.0:
            p = blend_pose(p, crouch(820, depth=1.3, eyes="happy", mouth="smile"), seg(t, 3.0, 3.3))
        ex["held"] = bucket
        return p, ex, fl
    fl["bucket_ground"] = True
    if t < 8.5:
        p = crouch(820, depth=1.3, eyes="happy", mouth="grin" if t > 6 else "smile", look=(1, 0.8))
        ph = t * 14
        p.hand_f = (lerp(900, 970, (math.sin(t * 2.3) + 1) / 2), 730 - 16 * abs(math.sin(ph)) - 40 * clamp((t - 6) / 2))
        p.hand_b = (lerp(890, 940, (math.cos(t * 2.1) + 1) / 2), 740 - 16 * abs(math.cos(ph)) - 30 * clamp((t - 6) / 2))
        fl["stage"] = 3 * seg(t, 3.8, 8.0, lambda v: v)
        fl["sand"] = t - 3.5
        return p, ex, fl
    fl["stage"] = 3
    if t < 12.4:
        base = stand(820, eyes="happy", mouth="grin", look=(1, 0.3))
        if t < 9.2:
            p = blend_pose(crouch(820, depth=1.3, eyes="happy", mouth="grin"), base, seg(t, 8.5, 9.1))
        elif t < 9.9:
            p = P_(base, hand_f=lerp2((842, 632), (CX + 30, 600), seg(t, 9.2, 9.55)), torso=0.15)
        elif t < 10.6:
            p = blend_pose(base, P_(base, hand_f=(840, 610), hand_b=(808, 612), torso=-0.05,
                                    elbow_f="back", elbow_b="back", eyes="happy", mouth="grin"), seg(t, 9.9, 10.1))
        else:
            p = blend_pose(P_(base, hand_f=(840, 610), hand_b=(808, 612)), P_(base, hand_f=(905, 420), tilt=-0.1,
                                                                            look=(1, -0.6), mouth="grin", eyes="normal"),
                           seg(t, 10.6, 10.9))
            ex["held"] = phone
        return p, ex, fl
    if t < 14.1:
        p = stand(820, hand_f=(870, 500), eyes="happy", mouth="smile", look=(1, 1), tilt=0.25)
        ex["held"] = phone
        if t > 13.55:
            k = seg(t, 13.55, 13.75, ease_out)
            p = P_(p, tilt=lerp(0.25, -0.35, k), torso=lerp(0.05, -0.1, k), eyes="shock", mouth="bigO",
                   look=(-1, -1))
        return p, ex, fl
    fl["washed"] = True
    fl["wet"] = True
    ex["wet"] = True
    ex["on_head"] = on_head_factory(t)
    if t < 17.0:
        p = stand(820, eyes="normal", mouth="flat", look=(0, 0), torso=0.0, brow=0.5)
        ex["blink_off"] = 1.0
        if t > 16.3:
            p.eyes, p.mouth = "sad", "frown"
        return p, ex, fl
    if t < 21.4:
        p = crouch(820, depth=1.3, eyes="sad", mouth="frown", brow=1.3, look=(1, 1))
        p = blend_pose(stand(820, eyes="sad", mouth="frown"), p, seg(t, 17.0, 17.5))
        if t > 18.6:
            p.eyes, p.mouth, p.brow = "wide", "o", 0
            p.mouth_amt = 0.6
        if t > 19.4:
            ph = t * 22
            p.hand_f = (930 + 20 * math.sin(ph), 760 - 20 * abs(math.sin(ph)))
            p.hand_b = (900 - 20 * math.sin(ph), 760 - 20 * abs(math.cos(ph)))
            fl["sand"] = t - 19.4
            p.eyes = "happy"
            p.mouth = "grin"
        if t > 21.2:
            p.eyes, p.mouth = "wide", "bigO"
        return p, ex, fl
    if t < 24.6:
        base = stand(820, eyes="hyper" if t < 22.2 else "happy", mouth="grin", torso=-0.05, tilt=-0.1,
                     hand_f=(870, 390), hand_b=(790, 380), elbow_f="back", elbow_b="back")
        p = blend_pose(crouch(820, depth=1.3, eyes="wide", mouth="bigO"), base, seg(t, 21.4, 21.8))
        if t > 22.2:
            for j0 in (22.3, 23.3):
                jk = seg(t, j0, j0 + 0.7, lambda v: v)
                if 0 < jk < 1:
                    h = 120 * math.sin(jk * math.pi)
                    p.hip = (p.hip[0], p.hip[1] - h)
                    p.foot_b = (p.foot_b[0], p.foot_b[1] - h * 0.9)
                    p.foot_f = (p.foot_f[0], p.foot_f[1] - h * 0.9)
                    p.hand_f = (p.hand_f[0], p.hand_f[1] - h)
                    p.hand_b = (p.hand_b[0], p.hand_b[1] - h)
        return p, ex, fl
    if t < 25.8:
        p = stand(820, eyes="normal", mouth="smile", look=(1, 0.8))
        if t > 25.2:
            p = P_(p, eyes="shock", mouth="bigO", tilt=-0.2, hand_f=(880, 380), hand_b=(860, 400))
        return p, ex, fl
    p = walk(stand(0), t, 25.8, 30.0, 820, -40, period=0.3, stride=60, lift=36, bob=10, swing=10)
    p.eyes, p.mouth, p.torso, p.tilt = "shock", "bigO", 0.25, -0.1
    p.hand_f = (p.hip[0] - 40, 380 + 10 * math.sin(t * 30))
    p.hand_b = (p.hip[0] - 20, 380 + 10 * math.cos(t * 30))
    return p, ex, fl


def camera(t, pose):
    hx = pose.hip[0]
    sh = ((14.1, 1.0, 16), (12.6, 1.4, 3), (25.3, 0.4, 8), (13.6, 0.3, 6))
    if t < 3.0:
        return shaken(Cam(hx + 90, 520, 1.8), t, sh)
    if t < 25.8:
        keys = [(3.0, 910, 520, 1.8), (3.8, 920, 580, 2.05), (8.5, 920, 600, 2.15), (9.4, 900, 530, 1.9),
                (10.6, 880, 470, 2.05), (11.8, 880, 460, 2.2), (12.4, 900, 460, 2.0), (13.4, 900, 380, 1.5),
                (14.0, 900, 400, 1.6), (15.4, 880, 520, 1.95), (16.8, 870, 500, 2.2), (17.6, 900, 580, 2.1),
                (20.6, 920, 640, 2.4), (21.6, 920, 600, 2.5), (22.2, 880, 470, 1.8), (24.4, 880, 470, 1.8),
                (24.9, 860, 400, 2.7), (25.7, 860, 420, 2.5)]
        return cam_keys(t, keys, sh)
    k = seg(t, 25.8, 26.4)
    return shaken(Cam(lerp(860, hx - 60, k), lerp(420, 520, k), lerp(2.5, 1.85, k)), t, sh)


# ------------------------------------------------------------------ sound
def sound():
    sfx_ambient(0, 30, "waves", 0.10)
    chords_loop(0.0, 12.8, 100, [[60, 64, 67], [60, 65, 69], [59, 62, 67], [60, 64, 67]], [48, 53, 55, 48],
                inst="uke", drums="lofi", vel=0.16, mel=[None, 76, None, 79, None, 77, 76, None])
    cut_music(12.8)
    A.record_scratch(12.78)
    tt = tvec(1.3)
    place(M, 12.85, np.sin(2 * np.pi * np.cumsum(60 + 80 * tt) / A.SR) * tt * 0.6, 1.0)
    A.section_sad(17.3)
    chords_loop(22.1, 25.2, 128, [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]], [36, 31, 33, 29],
                inst="pluck", drums="dance", vel=0.2)
    cut_music(25.25)
    A.record_scratch(25.25)
    A.section_sneaky(26.0, 28.5)
    # sfx
    for k in range(10):
        A.thud(0.25 + k * 0.3, 0.2, 140)
    A.thud(3.35, 0.3, 90)
    for k in range(18):
        A.thud(3.9 + k * 0.25, 0.15, 160)
    for st in (4.5, 6.0, 7.5):
        sfx_pop(st)
    sfx_pop(9.62, 0.4)
    sfx_shutter(11.6)
    A.thud(14.1, 0.5, 50)
    sfx_splash(14.15, 1.6, 0.9)
    for tt_ in (15.6, 16.1, 16.7):
        A.plip(tt_, 1500, 0.25)
    for k in range(5):
        place(S, 18.7 + k * 0.08, A.bell(3000 + k * 400, 0.3, 0.06))
    for k in range(9):
        whoosh_t = 19.45 + k * 0.17
        A.whoosh(whoosh_t, 0.12, 0.18)
    A.thud(21.15, 0.35, 120)
    for k, f in enumerate((1047, 1319, 1568, 2093, 2637)):
        place(S, 21.25 + k * 0.06, A.bell(f, 1.0, 0.22))
    A.thud(23.0, 0.3, 120)
    A.thud(24.0, 0.3, 120)
    A.beep(25.3, 2500, 0.03, 0.2)
    for k in range(9):
        A.thud(25.85 + k * 0.15, 0.25, 130)
    # voices
    v_hum(0.6, [67, 69, 72, 69, 67, 64, 67, 72], 0.3, 0.28)
    v_hum(5.0, [72, 74, 76, 74], 0.32, 0.22)
    v_tada(9.85)
    v_hehe(11.0)
    v_uhoh(13.55)
    v_aaah(14.05, 0.5, 0.6)
    v_hmm(16.0, up=True, g=0.3)
    v_nooo(17.2, 1.1)
    v_sniff(18.3)
    v_hmm(18.75, up=True, g=0.45)
    v_ooh(21.35, 0.6)
    v_woohoo(22.3)
    v_yay(23.35)
    v_hmm(24.7, up=True, g=0.3)
    v_ow(25.3)
    v_aaah(25.9, 2.0, 0.6)


EP = Episode(title=("SAND", "CASTLE"), title_col=(255, 205, 90), outfit=OUT, story=story, camera=camera,
             background=background, behind=behind, front=front, sound=sound,
             flashes=[(14.5, 0.25, (255, 255, 255), 0.5), (11.6, 0.1, (255, 255, 255), 0.5),
                      (21.25, 0.3, (255, 240, 170), 0.35)],
             speed=lambda t: 0.7 if 25.9 < t < 28.4 else (0.5 if 22.3 < t < 23.0 else 0))

if __name__ == "__main__":
    run(EP)
