import sys; sys.path.insert(0, ".")
import reel as RL, engine as E
from PIL import Image, ImageDraw
import numpy as np
W, H = 1080, 1920
spec = {1: ("jobs1984b", "bw", (-0.3, -0.3), "FIRED FROM HIS", "OWN COMPANY?!"),
        2: ("iphone2007", "neutral", (0.05, -0.2), "THE DAY PHONES", "CHANGED FOREVER"),
        3: ("pixarbldg", "warm", (0.0, 0.0), "STEVE JOBS", "BUILT PIXAR?!")}
for n, (key, g, (px, py), h1, h2) in spec.items():
    im = E.kb_crop(E.graded(key, g), 1.1, px, py, (W, H))
    a = np.array(im).astype(np.float32) * RL.VIG
    base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA"); d = ImageDraw.Draw(base)
    w1 = RL.tw(h1, "xb", 104) + 70
    d.rounded_rectangle([W / 2 - w1 / 2, 560, W / 2 + w1 / 2, 700], radius=20, fill=RL.GOLD + (255,))
    RL.put(base, RL.stext(h1, "xb", 104, (0, 0, 0), shadow=False), W / 2, 632, 1, "mm")
    fs = 112
    while RL.tw(h2, "xb", fs) > W - 120: fs -= 4
    RL.put(base, RL.stext(h2, "xb", fs, (255, 255, 255), stroke=7), W / 2, 790, 1, "mm")
    lg = RL.logo_img(); s = 0.42; lg = lg.resize((int(lg.width * s), int(lg.height * s)))
    base.alpha_composite(lg, (int(W / 2 - lg.width / 2), 1180))
    RL.put(base, RL.stext(f"STEVE JOBS  ·  PART {n}", "b", 38, (255, 255, 255), track=6), W / 2, 1120, 1, "mm")
    base.convert("RGB").save(f"../reels/out/cover_reel{n}.jpg", quality=92)
