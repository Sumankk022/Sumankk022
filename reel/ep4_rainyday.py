"""Episode 4 - RAINY DAY (city street, yellow raincoat + hood + red boots)."""
import math
import random

from engine import *

OUT = Outfit(top=(248, 196, 40), top_dark=(206, 156, 24), sleeve="long", pants=(48, 58, 88),
             boots=(206, 56, 50), hat="hood_up", hat_col=(240, 186, 34))
PUD1 = 1060.0     # sidewalk puddle
PUD2 = 1150.0     # road-edge puddle
RED = (214, 52, 62)


def clear_k(t):
    return seg(t, 23.6, 25.6)


# ------------------------------------------------------------------ props
def umbrella_at(P, hand, ang, mode):
    if mode == "closed":
        tip = add(hand, rot((0, 150), ang))
        P.line(hand, tip, 4, (60, 60, 60))
        P.poly([add(hand, rot((-8, 30), ang)), add(hand, rot((8, 30), ang)), add(hand, rot((2, 140), ang)),
                add(hand, rot((-2, 140), ang))], RED)
        P.arc(hand[0] - 8, hand[1], 9, 9, 180, 360, 4, (60, 60, 60))
        return
    top = add(hand, rot((0, -185), ang))
    P.line(add(hand, rot((0, 10), ang)), top, 4, (60, 60, 60))
    if mode == "open":
        pts = [add(top, rot((115 * math.cos(a), 30 - 78 * math.sin(a)), ang)) for a in [i * math.pi / 16 for i in range(17)]]
        P.poly(pts, RED)
        for k in range(5):
            x0 = -115 + k * 46
            P.chord(*add(top, rot((x0 + 23, 30), ang)), 23, 9, 0, 180, (180, 40, 50))
    else:  # inside-out
        pts = [add(top, rot((120 * math.cos(a), -20 - 70 * math.sin(a)), ang)) for a in [i * math.pi / 16 for i in range(17)]]
        rim = [add(top, rot((x, 6), ang)) for x in (130, 0, -130)]
        P.poly(pts + [rim[2]], RED)
        for a in (0.3, 1.0, 1.6, 2.2, 2.85):
            P.line(top, add(top, rot((125 * math.cos(a), -20 - 70 * math.sin(a)), ang)), 2, (60, 60, 60))
    P.arc(hand[0] - 8, hand[1] + 12, 9, 9, 0, 180, 4, (60, 60, 60))


def mk_umb(mode):
    def f(P, hand, ang, face):
        umbrella_at(P, hand, ang, mode)
    return f


def car(P, x):
    y = 1010
    P.rect(x - 160, y - 90, x + 160, y - 20, (60, 120, 200))
    P.poly([(x - 90, y - 90), (x + 70, y - 90), (x + 40, y - 150), (x - 70, y - 150)], (60, 120, 200))
    P.poly([(x - 76, y - 94), (x - 10, y - 94), (x - 10, y - 142), (x - 62, y - 142)], (170, 210, 240))
    P.poly([(x + 2, y - 94), (x + 60, y - 94), (x + 34, y - 142), (x + 2, y - 142)], (170, 210, 240))
    for dx in (-95, 95):
        P.circle(x + dx, y - 18, 34, (24, 24, 28))
        P.circle(x + dx, y - 18, 14, (150, 150, 160))
    P.rect(x + 150, y - 72, x + 162, y - 56, (255, 240, 150))


def background(P, t, fl, cam):
    ck = clear_k(t)
    for i in range(14):
        y0 = -900 + i * 110
        night = lerp_col((60, 70, 92), (98, 110, 132), i / 13)
        day = lerp_col((120, 180, 235), (220, 236, 245), i / 13)
        P.rect(-800, y0, 2800, y0 + 111 + (400 if i == 13 else 0), lerp_col(night, day, ck))
    if fl.get("flash"):
        P.rect(-800, -900, 2800, 500, (230, 235, 255))
    if ck > 0:
        P.circle(1500, -150, 80, lerp_col((150, 170, 200), (255, 238, 150), ck))
        cols = [(230, 70, 70), (240, 150, 60), (245, 220, 80), (100, 200, 110), (80, 150, 230), (140, 100, 210)]
        span = 180 * seg(t, 24.2, 25.8)
        for k, c in enumerate(cols):
            if span > 1:
                P.arc(1080, 600, 560 - k * 22, 470 - k * 22, 180, 180 + span, 22, c)
    # clouds
    for cx_, cy_ in ((300, -320), (900, -420), (1500, -300), (2000, -380)):
        x = cx_ + 20 * math.sin(t * 0.3)
        c = lerp_col((84, 92, 110), (245, 248, 252), ck)
        for dx, r in ((-80, 60), (0, 80), (80, 64), (150, 44)):
            P.circle(x + dx, cy_ + 120 * ck, r, c)
    # far buildings
    bc = lerp_col((70, 80, 102), (140, 156, 180), ck)
    rnd = random.Random(4)
    x = -800
    while x < 2800:
        w = rnd.randint(110, 220)
        h = rnd.randint(250, 650)
        P.rect(x, 600 - h, x + w - 10, 760, bc)
        for wy in range(600 - h + 20, 740, 40):
            for wx in range(x + 14, x + w - 30, 30):
                if rnd.random() < 0.35:
                    P.rect(wx, wy, wx + 14, wy + 20, lerp_col((235, 205, 120), (190, 210, 230), ck))
        x += w
    # shop front
    P.rect(200, 380, 760, 760, (150, 86, 70))
    P.rect(240, 520, 520, 740, (60, 70, 90))
    P.rect(250, 530, 510, 730, (250, 210, 130) if ck < 0.5 else (170, 200, 220))
    P.rect(570, 540, 690, 760, (90, 60, 50))
    for k in range(7):
        P.poly([(200 + k * 80, 440), (280 + k * 80, 440), (280 + k * 80, 500), (200 + k * 80, 500)],
               (230, 230, 225) if k % 2 else (50, 140, 110))
    P.text(480, 410, "CAFE", 34, (255, 230, 170))
    # bus stop + lamp
    P.rect(1400, 380, 1410, 790, (70, 74, 84))
    P.circle(1405, 380, 34, (50, 120, 200))
    P.text(1405, 381, "BUS", 18, (255, 255, 255))
    P.rect(895, 260, 905, 790, (50, 54, 64))
    P.line((900, 262), (950, 250), 6, (50, 54, 64))
    P.ellipse(960, 260, 26, 12, (255, 236, 160) if ck < 0.5 else (200, 200, 190))
    # sidewalk / road
    P.rect(-800, 760, 2800, 805, (128, 132, 142))
    for x0 in range(-800, 2800, 120):
        P.line((x0, 760), (x0, 805), 2, (110, 114, 124), cap=False)
    P.rect(-800, 805, 2800, 822, (160, 164, 172))
    P.rect(-800, 822, 2800, 1700, (52, 54, 62))
    for x0 in range(-800, 2800, 220):
        P.rect(x0, 1080, x0 + 120, 1094, (220, 210, 140))
    # puddles
    P.ellipse(PUD1, 796, 78, 9, (90, 110, 150))
    P.ellipse(PUD1 - 10, 794, 40, 4, (150, 175, 210))
    P.ellipse(PUD2, 838, 110, 12, (70, 90, 130))


def front(P, t, fl, s, cam, ex):
    if fl.get("umb_free"):
        pos, ang, mode = fl["umb_free"]
        umbrella_at(P, pos, ang, mode)
    if fl.get("splash1") is not None:
        burst(P, (PUD1, 790), fl["splash1"], seed=8, n=50, a0=200, a1=340, v0=300, v1=700, r0=5, r1=12,
              cols=((150, 190, 240), (210, 230, 255)), life=0.8)
    if fl.get("car_x") is not None:
        car(P, fl["car_x"])
    if fl.get("splash2") is not None:
        tau = fl["splash2"]
        burst(P, (PUD2, 840), tau, seed=9, n=220, a0=220, a1=295, v0=500, v1=1400, r0=8, r1=24,
              cols=((120, 170, 240), (190, 220, 255), (150, 195, 250)), life=1.0, g=1500)
        burst(P, (PUD2 - 60, 840), tau, seed=10, n=90, a0=235, a1=280, v0=900, v1=1500, r0=12, r1=26,
              cols=((110, 160, 235),), life=0.8, g=1500)
    if 6.0 < t < 9.6:
        rnd = random.Random(int(t * 15))
        for _ in range(9):
            y = rnd.uniform(cam.cy - 400, cam.cy + 300)
            x = cam.cx - 300 + ((t * 1600 + rnd.uniform(0, 900)) % 900)
            P.line((x, y), (x + 120, y - 10), 3, (220, 230, 245))
    amt = (1.0 + 0.5 * seg(t, 9.0, 10.0)) * (1 - clear_k(t))
    rain(P, cam, t, amt, col=(170, 190, 225))
    if fl.get("notes"):
        music_notes(P, s, t)
    if fl.get("stars"):
        stars_ring(P, s, t)


# ------------------------------------------------------------------ story
def story(t):
    ex = {"held": None}
    fl = {}
    if t < 5.6:
        if t < 4.25:
            p = walk(stand(0), t, 0.0, 4.25, 300, 960, period=0.62)
        else:
            k = seg(t, 4.25, 4.95, lambda v: v)
            x = lerp(960, 1170, min(1, k)) + (t - 4.95) * 0 if t < 4.95 else lerp(1170, 1220, seg(t, 4.95, 5.6))
            h = 100 * math.sin(clamp(k) * math.pi)
            p = stand(x, torso=0.1, eyes="happy", mouth="grin")
            p.hip = (x, STAND_Y - h + (16 if 4.95 < t < 5.15 else 0))
            p.foot_b = (x - 30, 790 - h * 0.8)
            p.foot_f = (x + 34, 790 - h * 0.8)
        p.eyes = "happy" if t < 4 else p.eyes
        p.mouth = "smile" if t < 4 else "grin"
        p.hand_f = (p.hip[0] + 34, 480 + (p.hip[1] - STAND_Y))
        p.elbow_f = "down"
        ex["held"] = mk_umb("open")
        return p, ex, fl
    X = 1220.0
    if t < 8.8:
        k = seg(t, 6.0, 6.4)
        p = stand(X, eyes="happy", mouth="smile", hand_f=(X + 34, 480))
        if t > 6.0:
            p = blend_pose(p, stand(X, torso=-0.3, tilt=-0.2, eyes="shock", mouth="bigO",
                                    hand_f=(X + 120, 400 + 20 * math.sin(t * 13)), hand_b=(X + 90, 420),
                                    foot_b=(X - 50, 790), foot_f=(X + 10, 790)), k)
            slide = 30 * seg(t, 6.4, 8.8)
            p.hip = (p.hip[0] - slide, p.hip[1])
            p.foot_b = (p.foot_b[0] - slide, 790)
            p.foot_f = (p.foot_f[0] - slide, 790)
        ex["held"] = mk_umb("open" if t < 6.4 else "inv")
        ex["item_ang"] = 0.5 * k + 0.12 * math.sin(t * 11) * k
        return p, ex, fl
    X = 1190.0
    ex["wet"] = t > 9.2
    if t < 12.4:
        k = seg(t, 8.8, 9.2, ease_out)
        p = stand(X, torso=lerp(-0.3, 0.2, k), eyes="shock" if t < 9.6 else "sad", mouth="bigO" if t < 9.6 else "frown",
                  brow=1.2 if t > 9.6 else 0, look=(1, -1) if t < 10 else (0, 1))
        if t > 9.8:
            p.torso, p.tilt = 0.25, 0.3
        if t < 10.4:
            fk = seg(t, 8.8, 10.4, lambda v: v)
            fl["umb_free"] = ((X + 120 + 900 * fk, 400 - 900 * fk), fk * 12, "inv")
        if t > 11.4:
            k2 = seg(t, 11.4, 11.7)
            p = blend_pose(p, stand(X, face=-1, eyes="happy", mouth="grin", look=(1, 1), tilt=0.2), k2)
        return p, ex, fl
    if t < 13.5:
        k = seg(t, 12.5, 13.3, lambda v: v)
        x = lerp(X, PUD1, k)
        h = 140 * math.sin(k * math.pi)
        p = stand(x, face=-1, eyes="happy", mouth="grin", torso=0.1, hand_f=(x - 60, 360 - h), hand_b=(x + 40, 370 - h),
                  elbow_f="back", elbow_b="back")
        p.hip = (x, STAND_Y - h + (20 if t > 13.3 else 0))
        p.foot_b, p.foot_f = (x + 20, 790 - h * 0.85), (x - 20, 790 - h * 0.85)
        fl["splash1"] = t - 13.3 if t > 13.3 else None
        return p, ex, fl
    if t < 18.4:
        fl["splash1"] = t - 13.3 if t < 14.2 else None
        face = 1 if int((t - 13.5) * 2.5) % 2 == 0 else -1
        x = PUD1 + 30 * math.sin(t * 2)
        b = 14 * abs(math.sin(t * 7.8))
        p = stand(x, face=face, eyes="happy", mouth="grin", tilt=-0.15, torso=-0.05,
                  hand_f=(x + face * 60, 330 + 30 * math.sin(t * 7.8)), hand_b=(x - face * 50, 340 + 30 * math.cos(t * 7.8)),
                  elbow_f="back", elbow_b="back")
        p.hip = (x, STAND_Y - b)
        p.foot_b = (x - face * 22, 790 - b * 0.6 * (1 + math.sin(t * 7.8)))
        p.foot_f = (x + face * 22, 790 - b * 0.6 * (1 - math.sin(t * 7.8)))
        fl["notes"] = True
        if t > 18.0:
            fl["car_x"] = lerp(cam_left_guess(t) - 400, PUD2, seg(t, 18.0, 18.4, lambda v: v))
        return p, ex, fl
    X = PUD1
    if t < 22.4:
        if t < 19.0:
            fl["car_x"] = lerp(PUD2, PUD2 + 1500, seg(t, 18.4, 19.0, lambda v: v))
        fl["splash2"] = t - 18.4 if t < 19.6 else None
        p = stand(X, face=1, eyes="shock" if t < 18.9 else "normal", mouth="bigO" if t < 18.9 else "flat",
                  hand_f=(X + 60, 330), hand_b=(X - 50, 340), elbow_f="back", elbow_b="back", tilt=-0.1)
        ex["blink_off"] = 0.7
        if t > 19.8:
            p = blend_pose(p, stand(X, eyes="normal", mouth="flat", brow=0.4), seg(t, 19.8, 20.2))
        if 20.3 < t < 21.2:
            p = P_(p, eyes="shock", mouth="wavy", torso=-0.15, hand_f=(X + 30, 470), hand_b=(X + 10, 480))
            fl["flash"] = 20.3 < t < 20.45
        if t > 21.8:
            fk = seg(t, 21.8, 22.4, ease_in)
            fl["umb_free"] = ((X + 30, lerp(-700, 160, fk)), 3.14, "closed")
        return p, ex, fl
    if t < 23.0:
        p = stand(X, eyes="closed", mouth="wavy", torso=0.1, tilt=0.2)
        fl["stars"] = True
        k = seg(t, 22.5, 22.8, back_out)
        p.hand_f = lerp2((X + 30, 640), (X + 34, 480), k)
        ex["held"] = mk_umb("closed" if t < 22.65 else "open")
        if t < 22.65:
            ex["item_ang"] = math.pi
        return p, ex, fl
    if t < 25.8:
        p = stand(X, eyes="normal" if t < 24.3 else "wide", mouth="flat" if t < 24.3 else "smile",
                  hand_f=(X + 34, 480), look=(1, -1) if t > 24.2 else (0, 0), tilt=-0.2 if t > 24.2 else 0)
        fl["stars"] = t < 23.4
        ex["held"] = mk_umb("open")
        return p, ex, fl
    if t < 27.5:
        k = seg(t, 25.8, 26.2)
        p = stand(X, eyes="happy", mouth="grin", hand_f=lerp2((X + 34, 480), (X + 28, 600), k), look=(1, -1), tilt=-0.15)
        ex["held"] = mk_umb("open" if k < 0.5 else "closed")
        return p, ex, fl
    if t < 27.95:
        k = seg(t, 27.5, 27.9)
        p = stand(X, eyes="closed", mouth="o", mouth_amt=0.8, torso=lerp(0, -0.3, k), tilt=lerp(0, -0.3, k),
                  hand_f=(X + 28, 600), hand_b=(X + 40, 420))
        ex["held"] = mk_umb("closed")
        return p, ex, fl
    k = seg(t, 27.95, 28.1, ease_out)
    p = stand(X, eyes="closed" if t < 28.6 else "happy", mouth="bigO" if t < 28.5 else "grin",
              torso=lerp(-0.3, 0.45, k) if t < 28.5 else 0.1, tilt=lerp(-0.3, 0.3, k) if t < 28.5 else 0.0,
              hand_f=(X + 50, 470), hand_b=(X + 20, 560))
    ex["held"] = mk_umb("open")
    return p, ex, fl


def cam_left_guess(t):
    return 900.0


def camera(t, pose):
    hx = pose.hip[0]
    sh = ((18.4, 0.7, 12), (20.3, 0.8, 8), (22.4, 0.3, 8), (27.95, 0.3, 9))
    if t < 5.6:
        return shaken(Cam(hx + 70, 500, 1.85), t, sh)
    keys = [(5.6, 1290, 500, 1.85), (6.4, 1240, 470, 1.9), (8.8, 1240, 440, 1.75), (9.6, 1230, 480, 2.1),
            (11.4, 1210, 470, 2.3), (12.4, 1150, 520, 1.85), (13.4, 1080, 540, 1.8), (17.8, 1090, 560, 1.7),
            (18.6, 1100, 560, 1.7), (19.8, 1080, 450, 2.3), (21.6, 1080, 430, 2.4), (22.2, 1080, 420, 2.0),
            (23.2, 1080, 400, 2.3), (24.0, 1080, 380, 1.6), (25.8, 1080, 380, 1.55), (27.4, 1080, 440, 2.3),
            (28.2, 1080, 440, 2.0), (30, 1080, 440, 1.8)]
    return cam_keys(t, keys, sh)


# ------------------------------------------------------------------ sound
def sound():
    sfx_ambient(0, 24.8, "rain", 0.13)
    chords_loop(0.0, 6.1, 78, [[57, 60, 64, 67], [50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59]],
                [45, 38, 43, 36], inst="epiano", drums="lofi", vel=0.17, mel=[None, 76, None, 74, 72, None, 69, None])
    cut_music(6.1)
    A.section_sad(10.2)
    chords_loop(13.3, 18.4, 128, [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]], [36, 31, 33, 29],
                inst="uke", drums="dance", vel=0.18)
    cut_music(18.42)
    A.record_scratch(18.42)
    chords_loop(24.3, 27.5, 90, [[60, 64, 67, 72], [65, 69, 72, 77], [67, 71, 74, 79], [60, 64, 67, 72]],
                [48, 53, 55, 48], inst="musicbox", drums="none", vel=0.15)
    cut_music(27.5)
    A.section_lullaby(28.4, 30.0)
    # sfx
    for k in range(14):
        tt = 0.2 + k * 0.31
        A.thud(tt, 0.2, 140)
        A.plip(tt, 900, 0.06)
    A.whoosh(4.3, 0.3, 0.3)
    A.thud(4.95, 0.3, 120)
    sfx_wind(6.0, 3.2, 0.7)
    sfx_pop(6.4, 0.4)
    sfx_boing(6.42, 0.3)
    A.whoosh(8.8, 0.5, 0.5)
    sfx_splash(13.3, 0.9, 0.7)
    for k in range(10):
        A.plip(13.6 + k * 0.45, 1000 + 200 * (k % 3), 0.08)
    for k in range(2):
        tt = tvec(0.2)
        hn = np.sign(np.sin(2 * np.pi * (380 + 90 * k) * tt)) + np.sign(np.sin(2 * np.pi * 480 * tt))
        place(S, 17.95 + k * 0.25, A.lowpass(hn, 6) * A.env_adsr(len(tt), 0.01, 0.03), 0.18)
    A.whoosh(18.1, 0.8, 0.6)
    sfx_splash(18.4, 1.4, 0.9)
    for tt_ in (19.2, 19.6, 20.0):
        A.plip(tt_, 1500, 0.25)
    sfx_thunder(20.3, 0.9)
    A.whoosh(21.9, 0.5, 0.35)
    sfx_bonk(22.4, 0.6)
    sfx_pop(22.68, 0.4)
    for t0 in (24.9, 25.2, 25.9, 26.4):
        tt = tvec(0.12)
        f = 3200 + 1200 * np.sin(np.pi * tt / 0.12)
        place(S, t0, np.sin(2 * np.pi * np.cumsum(f) / A.SR) * np.sin(np.pi * tt / 0.12) * 0.15, 1.0)
    sfx_pop(28.0, 0.4)
    # voices
    v_hum(0.6, [69, 72, 74, 76, 74, 72, 69], 0.32, 0.26)
    v_hehe(5.05)
    v_whoa(6.25)
    v_aaah(8.85, 0.5, 0.55)
    v_nooo(10.2, 0.9)
    v_hehe(11.75)
    v_woohoo(12.55)
    v_yay(15.4)
    v_hum(16.3, [72, 76, 79, 76], 0.3, 0.25)
    v_eek(18.25)
    v_hmm(19.9, up=False, g=0.3)
    v_eek(20.4)
    v_ow(22.42)
    v_ooh(24.6)
    v_achoo(27.5)
    v_hehe(28.7)


EP = Episode(title=("RAINY", "DAY"), title_col=(255, 214, 70), outfit=OUT, story=story, camera=camera,
             background=background, front=front, sound=sound,
             flashes=[(20.3, 0.35, (235, 240, 255), 0.7), (18.4, 0.15, (200, 225, 255), 0.4)],
             speed=lambda t: 0.6 if 18.0 < t < 18.6 else 0)

if __name__ == "__main__":
    run(EP)
