"""Thumbnails for the Vijay Mallya documentary (16:9) and the 3 reels (9:16 covers)."""
import os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import reel as RL, engine as E

GOLD, RED, WHITE, BLACK = (242, 193, 91), (230, 45, 38), (255, 255, 255), (0, 0, 0)
OUT = "../thumbs"; os.makedirs(OUT, exist_ok=True)

def put(base, arr, x, y, anchor="lt", a=1.0, pad=40):
    im = Image.fromarray(arr); bw, bh = im.width - 2 * pad, im.height - 2 * pad
    if anchor[0] == "m": x -= bw / 2
    elif anchor[0] == "r": x -= bw
    if anchor[1] == "m": y -= bh / 2
    elif anchor[1] == "b": y -= bh
    base.alpha_composite(im, (int(x - pad), int(y - pad)))
def fit(txt, font, size, maxw, track=0):
    while RL.tw(txt, font, size, track) > maxw: size -= 4
    return size
def photo(key, g, size, z=1.0, px=0, py=0):
    return E.kb_crop(E.graded(key, g), z, px, py, size).convert("RGBA")
def shade(im, kind, a0, a1, strength=0.92):
    a = np.array(im).astype(np.float32); h, w = a.shape[:2]
    if kind == "left": m = np.clip((np.arange(w)[None, :] - a0) / (a1 - a0), 0, 1)
    else: m = np.clip((a1 - np.arange(h)[:, None]) / (a1 - a0), 0, 1)      # "bottom": dark below a0
    m = m ** 1.3; a[..., :3] *= ((1 - strength) + strength * m)[..., None]
    return Image.fromarray(a.astype(np.uint8))
def vignette(im, s=0.45):
    a = np.array(im).astype(np.float32); h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]; r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a[..., :3] *= (1 - s * np.clip(r - 0.6, 0, 1))[..., None]; return Image.fromarray(a.astype(np.uint8))
def polaroid(key, g, size, z, px, py, angle, label, lab_col=RED):
    w, h = size; im = photo(key, g, (w, h), z, px, py)
    fr = Image.new("RGBA", (w + 28, h + 96), (250, 248, 242, 255)); fr.paste(im, (14, 14))
    fs = fit(label, "xb", 46, w - 10)
    put(fr, RL.stext(label, "xb", fs, lab_col, shadow=False), (w + 28) / 2, h + 14 + 41, "mm")
    sh = Image.new("RGBA", (fr.width + 80, fr.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 48, fr.width + 40, fr.height + 48], fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(16)); sh.alpha_composite(fr, (40, 40))
    return sh.rotate(angle, resample=Image.BICUBIC, expand=True)
def badge(base, x, y, text, fill=RED, col=WHITE, size=40, anchor="l"):
    d = ImageDraw.Draw(base); w = RL.tw(text, "xb", size, 3) + 50; h = size + 30
    if anchor == "m": x -= w / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=fill + (255,))
    put(base, RL.stext(text, "xb", size, col, track=3, shadow=False), x + w / 2, y + h / 2 + 1, "mm")
def arrow(base, p0, p1, col=GOLD, width=14):
    d = ImageDraw.Draw(base); d.line([p0, p1], fill=col + (255,), width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]); L = 46
    d.polygon([p1, (p1[0] - L * math.cos(ang - 0.5), p1[1] - L * math.sin(ang - 0.5)),
               (p1[0] - L * math.cos(ang + 0.5), p1[1] - L * math.sin(ang + 0.5))], fill=col + (255,))

_LOGO = None
def logo_img():
    global _LOGO
    if _LOGO is None:
        fr = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-ss", "4.5", "-i", "vid/intro.mp4", "-frames:v", "1", "-f", "rawvideo",
                                           "-pix_fmt", "rgb24", "-"], capture_output=True).stdout, np.uint8).reshape(1080, 1920, 3)
        c = fr[325:625, 315:1725].astype(np.float32)
        a = np.clip((c.max(2) - 28) * 3.2, 0, 255)
        rgb = np.clip(c * 255 / np.maximum(a[..., None], 1), 0, 255)
        _LOGO = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA")
    return _LOGO
def logo(base, x, y, width, anchor="lt"):
    lg = logo_img(); s = width / lg.width; lg = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS)
    if anchor == "mt": x -= lg.width / 2
    base.alpha_composite(lg, (int(x), int(y)))
def vframe(num, t, size):
    w, h = size
    fr = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", f"vid/{num}.mp4", "-frames:v", "1", "-vf",
                         f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        capture_output=True).stdout
    return Image.fromarray(E.grade(np.frombuffer(fr, np.uint8).reshape(h, w, 3), "cool")).convert("RGBA")

# ------------------------------------------------ 16:9 main documentary
def main_thumb():
    W, H = 1920, 1080
    base = Image.new("RGBA", (W, H), (8, 8, 14, 255))
    src = E.graded("mallya_wef", "warm"); s = 1.18 * H / src.height
    fg = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS).convert("RGBA")
    base.alpha_composite(fg, (W - fg.width + 330, -int(0.06 * fg.height)))
    base = vignette(shade(base, "left", 700, 1150), 0.35).convert("RGBA")
    p = polaroid("kfcounter", "faded", (300, 320), 1.2, 0.2, -0.1, 7, "GROUNDED")
    base.alpha_composite(p, (560, 560))

    put(base, RL.stext("KING OF", "xb", 140, WHITE), 90, 190, "lm")
    put(base, RL.stext("GOOD TIMES", "xb", 150, GOLD), 86, 340, "lm")
    d = ImageDraw.Draw(base); d.rectangle([96, 445, 760, 453], fill=RED + (255,))
    put(base, RL.stext("...then it all", "pfi", 80, WHITE), 92, 530, "lm")
    put(base, RL.stext("crashed.", "pf9", 120, RED), 92, 640, "lm")
    badge(base, 96, 770, "THE FULL STORY", fill=GOLD, col=BLACK, size=44)
    logo(base, 80, 905, 520)
    base.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{OUT}/Thumbnail_Main_1280x720.jpg", quality=93)

# ------------------------------------------------ 9:16 reel covers
def cover(n, bg, l1, l2, l2col, pol=None, part=None):
    W, H = 1080, 1920
    base = shade(bg, "bottom", 900, 1500, 0.9).convert("RGBA")
    d = ImageDraw.Draw(base)
    pill = f"VIJAY MALLYA  ·  PART {n}"; pw = RL.tw(pill, "b", 40, 4) + 70
    d.rounded_rectangle([W / 2 - pw / 2, 90, W / 2 + pw / 2, 166], radius=38, fill=(0, 0, 0, 170), outline=GOLD + (230,), width=3)
    put(base, RL.stext(pill, "b", 40, WHITE, track=4, shadow=False), W / 2, 128, "mm")
    for p_ in ([pol] if isinstance(pol, tuple) else (pol or [])): base.alpha_composite(p_[0], p_[1])
    f1 = fit(l1, "xb", 120, W - 160); w1 = RL.tw(l1, "xb", f1) + 70
    d = ImageDraw.Draw(base); d.rounded_rectangle([W / 2 - w1 / 2, 1300, W / 2 + w1 / 2, 1300 + f1 + 50], radius=20, fill=GOLD + (255,))
    put(base, RL.stext(l1, "xb", f1, BLACK, shadow=False), W / 2, 1300 + (f1 + 50) / 2, "mm")
    f2 = fit(l2, "xb", 130, W - 120)
    put(base, RL.stext(l2, "xb", f2, l2col, stroke=7), W / 2, 1300 + f1 + 140, "mm")
    logo(base, W / 2, 1700, 560, "mt")
    base.convert("RGB").save(f"{OUT}/Reel_Part{n}_Cover_1080x1920.jpg", quality=93)

def reels():
    W, H = 1080, 1920
    bg1 = photo("mallya_wef", "warm", (W, H), 1.0, 0.4, 0)
    cover(1, bg1, "KING OF GOOD TIMES", "WHAT WENT WRONG?", RED)
    bg2 = photo("a330c", "neutral", (W, H), 1.0, 0.25, 0)
    cover(2, bg2, "WHAT GROUNDED", "KINGFISHER AIRLINES?", WHITE,
          pol=[(polaroid("kfcounter", "faded", (300, 280), 1.1, 0.2, 0, 8, "2012: GROUNDED"), (660, 300)),
               (polaroid("mallya_wef", "warm", (500, 600), 1.2, 0.42, -0.35, -5, "VIJAY MALLYA", lab_col=BLACK), (50, 420))])
    bg3 = vframe(26852, 4.0, (W, H))
    cover(3, bg3, "HOW DID HE END UP", "IN THE UK?", WHITE,
          pol=(polaroid("mallya_wef", "bw", (360, 400), 1.15, 0.4, -0.3, -6, "VIJAY MALLYA"), (60, 620)))

if __name__ == "__main__":
    main_thumb(); reels(); print(sorted(os.listdir(OUT)))
