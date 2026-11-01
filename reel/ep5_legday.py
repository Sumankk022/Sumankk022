"""Episode 5 - LEG DAY (gym, orange tank top + headband + wristbands)."""
import math

from engine import *

OUT = Outfit(top=(246, 140, 40), top_dark=(200, 104, 26), sleeve="none", pants=(88, 94, 110), shorts=True,
             shoes=(236, 236, 242), hat="headband", hat_col=(220, 44, 52), wrist=(220, 44, 52))
X = 900.0
PLATE_FLOOR = (985.0, 725.0)
PLATE_DROP = (1010.0, 725.0)


def plate(P, c, wob=0.0):
    x, y = c
    P.circle(x, y, 76, (30, 30, 34))
    P.circle(x, y, 66, (200, 40, 46))
    P.circle(x, y, 40, (30, 30, 34))
    P.circle(x, y, 12, (180, 180, 190))
    P.text(x, y - 52, "200", 14, (255, 255, 255))


def tiny_db(P, hand, ang, f):
    x, y = hand
    P.line((x - 14, y), (x + 14, y), 4, (200, 200, 210))
    P.circle(x - 14, y, 8, (250, 130, 190))
    P.circle(x + 14, y, 8, (250, 130, 190))


def background(P, t, fl, cam):
    P.rect(-800, -900, 2800, 800, (66, 72, 88))
    P.rect(-800, 560, 2800, 600, (240, 130, 40))
    P.rect(-800, 600, 2800, 800, (56, 60, 74))
    # posters
    P.rect(1180, 110, 1500, 330, (30, 30, 36))
    P.text(1340, 180, "NO PAIN", 44, (246, 140, 40))
    P.text(1340, 250, "NO GAIN", 44, (255, 255, 255))
    P.rect(420, 120, 640, 320, (40, 120, 200))
    P.circle(530, 200, 40, (255, 255, 255))
    P.rect(500, 240, 560, 300, (255, 255, 255))
    # windows strip
    for x0 in range(-600, 2600, 260):
        P.rect(x0, -260, x0 + 200, -20, (110, 140, 180))
    # dumbbell rack
    P.rect(240, 600, 680, 616, (40, 42, 50))
    P.rect(240, 690, 680, 706, (40, 42, 50))
    P.rect(250, 600, 264, 790, (40, 42, 50))
    P.rect(656, 600, 670, 790, (40, 42, 50))
    for k in range(5):
        x = 290 + k * 82
        for y in (584, 674):
            P.line((x - 22, y), (x + 22, y), 8, (150, 150, 160))
            P.circle(x - 22, y, 15, (34, 34, 40))
            P.circle(x + 22, y, 15, (34, 34, 40))
    if not fl.get("tiny_taken"):
        tiny_db(P, (700, 785), 0, 1)
    # bench
    P.rect(1500, 690, 1760, 716, (200, 50, 50))
    P.rect(1520, 716, 1534, 790, (40, 42, 50))
    P.rect(1726, 716, 1740, 790, (40, 42, 50))
    # floor
    P.rect(-800, 800, 2800, 1700, (42, 44, 52))
    for x0 in range(-800, 2800, 240):
        P.line((x0, 800), (x0 + (x0 - 1000) * 0.5, 1700), 3, (34, 36, 42), cap=False)
    if fl.get("crack"):
        cx, k = PLATE_DROP[0], fl["crack"]
        for a, ln in ((-170, 160), (-130, 120), (-30, 140), (10, 180), (-80, 90)):
            ra = math.radians(a)
            P.line((cx, 802), (cx + math.cos(ra) * ln * k, 802 - math.sin(ra) * ln * 0.4 * k), 4, (20, 20, 24))


def behind(P, t, fl, cam):
    if fl.get("plate") and fl.get("plate_behind"):
        plate(P, fl["plate"])


def front(P, t, fl, s, cam, ex):
    if fl.get("plate") and not fl.get("plate_behind"):
        plate(P, fl["plate"])
    if fl.get("chalk") is not None:
        burst(P, fl["chalk_pos"], fl["chalk"], seed=3, n=50, a0=0, a1=360, v0=60, v1=260, r0=8, r1=20,
              cols=((240, 240, 245), (220, 220, 228)), life=0.9, g=-60)
    if fl.get("strain"):
        sweat(P, s, t)
        hc = s["head"]
        for dx, dy in ((-20, -34), (-30, -24)):
            P.line((hc[0] + dx - 8, hc[1] + dy), (hc[0] + dx + 8, hc[1] + dy), 4, (255, 90, 90))
            P.line((hc[0] + dx, hc[1] + dy - 8), (hc[0] + dx, hc[1] + dy + 8), 4, (255, 90, 90))
    if fl.get("stars"):
        stars_ring(P, s, t)
    if fl.get("bulge"):
        k = fl["bulge"]
        m = lerp2(s["shoulder"], s["ef"], 0.5)
        P.circle(m[0], m[1] - 10, 22 * k, C_BLACK)
        if k > 0.9:
            star(P, m[0] + 20, m[1] - 40, 10, (255, 240, 150))
    if fl.get("toss") is not None:
        tiny_db(P, fl["toss"], 0, 1)
    if fl.get("shine"):
        hc = s["head"]
        star(P, hc[0] + 60, hc[1] - 40, 12 + 5 * math.sin(t * 20), (255, 240, 150))


# ------------------------------------------------------------------ story
def story(t):
    ex = {"held": None}
    fl = {"plate": PLATE_FLOOR, "plate_behind": False}
    if t < 3.0:
        p = walk(stand(0), t, 0.0, 3.0, 350, X, period=0.66, bob=9, swing=36)
        p.eyes, p.mouth, p.torso, p.tilt = "happy", "grin", -0.08, -0.1
        return p, ex, fl
    if t < 5.6:
        k = seg(t, 3.0, 3.3)
        p = stand(X, eyes="happy", mouth="grin", torso=-0.05, tilt=-0.1)
        if t < 4.5:
            pump = 12 * math.sin(t * 10)
            p = blend_pose(p, P_(p, hand_f=(X + 40, 330 + pump), hand_b=(X - 50, 340 - pump), elbow_f="back", elbow_b="back"), k)
            fl["shine"] = True
        else:
            c = (X + 70, 470)
            clap_k = abs(math.sin((t - 4.5) * 9))
            p = P_(p, hand_f=(c[0] + 10 * clap_k, c[1]), hand_b=(c[0] - 14 * clap_k, c[1] + 4), eyes="normal", mouth="flat",
                   look=(1, 0.4))
            if t > 4.95:
                fl["chalk"], fl["chalk_pos"] = t - 4.95, c
        return p, ex, fl
    if t < 8.5:
        p = crouch(X, depth=1.3, eyes="squint", mouth="grin", hand_f=PLATE_FLOOR, hand_b=(PLATE_FLOOR[0] - 10, PLATE_FLOOR[1] + 4))
        p = blend_pose(stand(X), p, seg(t, 5.6, 6.1))
        if t > 6.2:
            j = 3 * math.sin(t * 60)
            p.hip = (p.hip[0] + j, p.hip[1])
            p.tilt = -0.1
            fl["strain"] = True
            fl["plate"] = (PLATE_FLOOR[0] + 0.6 * j, PLATE_FLOOR[1] - (2 if int(t * 20) % 2 else 0))
        return p, ex, fl
    if t < 12.5:
        if t < 9.3:
            k = seg(t, 8.5, 9.1, ease_out)
            p = blend_pose(crouch(X, depth=1.3, eyes="squint", mouth="grin", hand_f=PLATE_FLOOR),
                           stand(X, eyes="squint", mouth="grin", hand_f=(965, 480), hand_b=(955, 486)), k)
            fl["strain"] = True
        elif t < 10.0:
            k = seg(t, 9.3, 9.6, back_out)
            p = blend_pose(stand(X, eyes="squint", mouth="grin", hand_f=(965, 480), hand_b=(955, 486)),
                           stand(X, eyes="happy", mouth="bigO", hand_f=(925, 285), hand_b=(915, 290), tilt=-0.2), k)
        else:
            sway = 50 * math.sin((t - 10.0) * 3.2) * seg(t, 10.0, 10.8)
            p = stand(X + sway, eyes="shock" if t > 10.8 else "happy", mouth="bigO" if t > 10.8 else "grin",
                      hand_f=(925 + sway * 1.6, 285), hand_b=(915 + sway * 1.6, 290), tilt=-0.2, torso=-0.05 + sway / 400,
                      look=(1 if int(t * 5) % 2 else -1, -1))
            p.foot_b = (X - 18 + sway * 0.3, 790)
            p.foot_f = (X + 20 + sway * 0.3, 790)
            fl["strain"] = t > 10.8
        fl["plate"] = p.hand_f
        fl["plate_behind"] = t > 9.35
        return p, ex, fl
    if t < 16.0:
        k = seg(t, 12.5, 13.3, ease_in)
        a = stand(X, eyes="shock", mouth="bigO", hand_f=(925, 285), hand_b=(915, 290), tilt=-0.2)
        b = floor_sit(860, eyes="closed", mouth="wavy", tilt=0.1)
        p = blend_pose(a, b, k)
        if t < 13.15:
            pk = seg(t, 12.5, 13.15, ease_in)
            fl["plate"] = lerp2((925, 285), PLATE_DROP, pk)
            fl["plate_behind"] = pk < 0.4
        else:
            fl["plate"] = (PLATE_DROP[0], PLATE_DROP[1] - 30 * max(0, math.sin((t - 13.15) * 12)) * math.exp(-(t - 13.15) * 6))
            fl["crack"] = seg(t, 13.15, 13.3)
        if t > 13.3:
            fl["stars"] = True
            p.tilt = 0.15 * math.sin(t * 4)
        return p, ex, fl
    fl["plate"] = PLATE_DROP
    fl["crack"] = 1.0
    if t < 17.0:
        p = blend_pose(floor_sit(860, eyes="closed", mouth="wavy"), stand(860, eyes="normal", mouth="frown", brow=0.8), seg(t, 16.0, 16.8))
        return p, ex, fl
    if t < 19.4:
        if t < 18.3:
            p = walk(stand(0), t, 17.0, 18.3, 860, 640, period=0.6)
            p.eyes, p.mouth = "normal", "flat"
            p.look = (1, 0.5)
        else:
            p = crouch(640, face=-1, depth=0.9, eyes="happy", mouth="smile", look=(1, 1))
            p.hand_f = lerp2((600, 700), (700, 780), seg(t, 18.4, 18.7))
            p.hand_f = (580 - 0, 760) if t < 18.4 else p.hand_f
            p.hand_f = (640 - 60, 760)
            if t > 18.9:
                fl["tiny_taken"] = True
                ex["held"] = tiny_db
                p = blend_pose(p, stand(640, face=-1, eyes="happy", mouth="grin", hand_f=(600, 520)), seg(t, 18.9, 19.3))
            else:
                fl["tiny_taken"] = False
        return p, ex, fl
    fl["tiny_taken"] = True
    if t < 22.4:
        k = seg(t, 19.4, 19.7)
        curl = (math.sin((t - 19.7) * 7) + 1) / 2
        p = stand(640, face=1, eyes="happy", mouth="grin", tilt=-0.1,
                  hand_f=lerp2((690, 610), (668, 420), curl), elbow_f="down", look=(1, 0))
        ex["held"] = tiny_db
        if t > 20.6:
            fl["bulge"] = seg(t, 20.6, 21.0, back_out)
            p.hand_f = (650, 330)
            p.elbow_f = "back"
            p.hand_b = (620, 340)
            p.elbow_b = "back"
        return p, ex, fl
    if t < 23.35:
        k = seg(t, 22.4, 22.6, ease_out)
        p = stand(640, eyes="happy", mouth="grin", hand_f=lerp2((650, 330), (700, 400), k), look=(1, -1.2), tilt=-0.25)
        if t > 22.6:
            tk = seg(t, 22.6, 23.35, lambda v: v)
            fl["toss"] = (lerp(700, 662, tk), 400 - 260 * math.sin(tk * math.pi * 0.85) + 400 * tk ** 3)
            p.look = (0, lerp(-1.3, 1.2, tk))
            p.tilt = lerp(-0.3, 0.3, tk)
            p.eyes = "wide" if tk > 0.6 else "happy"
        else:
            ex["held"] = tiny_db
        return p, ex, fl
    if t < 26.8:
        hop = abs(math.sin((t - 23.4) * 9))
        x = 640 - 60 * seg(t, 23.4, 26.8, lambda v: v) * 0
        p = stand(x, eyes="closed", mouth="bigO", torso=0.35, tilt=0.2,
                  hand_f=(x + 70, 640), hand_b=(x + 50, 650))
        p.hip = (x + 8 * math.sin(t * 3), STAND_Y - 40 * hop)
        p.foot_b = (x - 10, 790 - 40 * hop)
        p.foot_f = (x + 62, 690 - 40 * hop)
        fl["toss"] = (662, 778)
        if t > 25.2:
            p.eyes = "sad"
            p.mouth = "frown"
        return p, ex, fl
    fl["toss"] = (662, 778)
    k = seg(t, 26.8, 27.6, ease_in)
    p = blend_pose(stand(640, eyes="sad", mouth="frown"), floor_sit(600, eyes="closed", mouth="wavy", torso=-1.25,
                                                                      tilt=0.0, hand_b=(470, 790), hand_f=(500, 792)), k)
    if t > 27.6:
        p.hip = (600, 770)
        p.torso = -1.3 + 0.04 * math.sin(t * 6)
        p.mouth = "o"
        p.mouth_amt = 0.5 + 0.4 * abs(math.sin(t * 6))
    return p, ex, fl


def camera(t, pose):
    hx = pose.hip[0]
    sh = ((13.15, 0.6, 16), (23.35, 0.3, 8), (6.2, 2.3, 2.5))
    if t < 3.0:
        return shaken(Cam(hx + 70, 520, 1.85), t, sh)
    keys = [(3.0, 970, 520, 1.85), (4.5, 960, 470, 2.3), (5.6, 960, 500, 2.1), (6.4, 960, 600, 2.4),
            (8.4, 960, 600, 2.6), (9.4, 930, 450, 1.75), (10.0, 930, 420, 1.6), (12.4, 920, 440, 1.75),
            (13.4, 900, 600, 1.8), (15.8, 880, 600, 2.4), (17.0, 800, 540, 1.9), (18.6, 700, 560, 2.0),
            (20.4, 700, 470, 2.4), (22.2, 700, 420, 2.2), (23.3, 700, 470, 1.9), (26.6, 680, 540, 2.0),
            (28.0, 620, 640, 2.0), (30, 620, 620, 2.2)]
    return cam_keys(t, keys, sh)


# ------------------------------------------------------------------ sound
ROCK = ([[52, 59, 64], [55, 62, 67], [57, 64, 69], [50, 57, 62]], [40, 43, 45, 38])


def sound():
    chords_loop(0.0, 6.2, 140, *ROCK, inst="square", drums="rock", vel=0.24)
    cut_music(6.2)
    for k in range(9):
        place(M, 6.3 + k * 0.25, A.kick(0.6 + 0.04 * k))
    tt = tvec(2.3)
    place(M, 6.2, np.sin(2 * np.pi * np.cumsum(55 + 30 * tt) / A.SR) * 0.5 * (tt / 2.3), 1.0)
    for m in (64, 68, 71, 76):
        place(M, 9.35, A.epiano(m, 1.6, 0.25))
    place(S, 9.4, A.bell(1319, 1.2, 0.3))
    chords_loop(9.4, 12.4, 140, *ROCK, inst="square", drums="rock", vel=0.24)
    cut_music(12.42)
    A.record_scratch(12.42)
    A.section_sneaky(16.8, 22.4)
    chords_loop(23.4, 26.8, 160, [[60, 63, 67], [58, 62, 65]], [36, 34], inst="pluck", drums="dance", vel=0.15)
    cut_music(26.8)
    A.section_sad(26.9)
    A.section_lullaby(28.4, 30.0)
    # sfx
    for k in range(5):
        A.thud(0.3 + k * 0.66, 0.35, 110)
        A.thud(0.63 + k * 0.66, 0.3, 120)
    for k in range(6):
        place(S, 4.55 + k * 0.11, A.clap(0.25))
    A.whoosh(4.95, 0.5, 0.35)
    for k in range(18):
        place(S, 6.25 + k * 0.12, A.highpass(noise(0.03), 2) * 0.12)
    A.whoosh(8.5, 0.4, 0.3)
    A.whoosh(9.3, 0.3, 0.3)
    A.whoosh(12.5, 0.6, 0.4)
    A.thud(13.15, 0.9, 50)
    sfx_crack(13.17, 0.6)
    A.thud(13.3, 0.5, 80)
    for t0 in (13.7, 14.0, 14.5, 14.8, 15.3):
        tt = tvec(0.12)
        f = 3000 + 1400 * np.sin(np.pi * tt / 0.12)
        place(S, t0, np.sin(2 * np.pi * np.cumsum(f) / A.SR) * np.sin(np.pi * tt / 0.12) * 0.18, 1.0)
    for k in range(4):
        A.thud(17.1 + k * 0.3, 0.2, 140)
    place(S, 18.9, A.bell(2400, 0.3, 0.15))
    for k in range(4):
        A.whoosh(19.7 + k * 0.9, 0.2, 0.12)
    sfx_boing(20.65, 0.45)
    A.whoosh(22.6, 0.3, 0.3)
    sfx_bonk(23.35, 0.6)
    for k in range(10):
        A.thud(23.5 + k * 0.35, 0.25, 130)
    A.thud(27.55, 0.5, 70)
    # voices
    v_hehe(3.3, 3)
    v_hup(5.0)
    v_strain(6.3, 2.1, 0.5)
    v_aaah(9.35, 0.8, 0.75)
    v_uhoh(10.9)
    v_whoa(12.5)
    v_hmm(14.2, up=False, g=0.3)
    v_hmm(16.9, up=True, g=0.35)
    v_ooh(18.85, 0.4)
    v_hehe(20.2, 3)
    v_hum(21.2, [72, 76, 79], 0.25, 0.25)
    v_eek(23.05)
    v_ow(23.38)
    v_ow(24.3)
    v_ow(25.4)
    v_nooo(26.9, 0.8)
    for k in range(3):
        place(V, 27.8 + k * 0.5, breathy(0.3, 900), 0.25)


EP = Episode(title=("LEG", "DAY"), title_col=(255, 150, 50), outfit=OUT, story=story, camera=camera,
             background=background, behind=behind, front=front, sound=sound,
             flashes=[(9.4, 0.25, (255, 240, 200), 0.4), (13.15, 0.15, (255, 255, 255), 0.4)],
             speed=lambda t: 0.5 if 9.3 < t < 9.8 else 0)

if __name__ == "__main__":
    run(EP)
