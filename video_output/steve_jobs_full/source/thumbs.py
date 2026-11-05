"""Thumbnails / covers for all Steve Jobs videos (Founder File)."""
import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
import reel as RL, engine as E

GOLD, RED, WHITE, BLACK = (242, 193, 91), (230, 45, 38), (255, 255, 255), (0, 0, 0)
OUT = "../reels/out/thumbs"; import os; os.makedirs(OUT, exist_ok=True)

def put(base, arr, x, y, anchor="lt", a=1.0, pad=None):
    im = Image.fromarray(arr); pd = pad if pad is not None else 40
    bw, bh = im.width - 2 * pd, im.height - 2 * pd
    if anchor[0] == "m": x -= bw / 2
    elif anchor[0] == "r": x -= bw
    if anchor[1] == "m": y -= bh / 2
    elif anchor[1] == "b": y -= bh
    if a < 1: arr = arr.copy(); arr[..., 3] = (arr[..., 3] * a).astype(np.uint8); im = Image.fromarray(arr)
    base.alpha_composite(im, (int(x - pd), int(y - pd)))
def fit(txt, font, size, maxw):
    while RL.tw(txt, font, size) > maxw: size -= 4
    return size
def photo(key, g, size, z, px, py):
    return E.kb_crop(E.graded(key, g), z, px, py, size).convert("RGBA")
def hfade(im, x0, x1, left_dark=True):
    """darken towards the left (for text) with a smooth ramp between x0..x1"""
    a = np.array(im).astype(np.float32); w = a.shape[1]
    xs = np.arange(w)[None, :, None]; m = np.clip((xs - x0) / (x1 - x0), 0, 1) ** 1.3
    if not left_dark: m = 1 - m
    a[..., :3] *= 0.08 + 0.92 * m
    return Image.fromarray(a.astype(np.uint8))
def vignette(im, s=0.45):
    a = np.array(im).astype(np.float32); h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]; r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a[..., :3] *= (1 - s * np.clip(r - 0.6, 0, 1))[..., None]; return Image.fromarray(a.astype(np.uint8))
def polaroid(key, g, size, z, px, py, angle, label, lab_col=RED):
    w, h = size; im = photo(key, g, (w, h), z, px, py)
    fr = Image.new("RGBA", (w + 28, h + 96), (250, 248, 242, 255)); fr.paste(im, (14, 14))
    d = ImageDraw.Draw(fr); fs = fit(label, "xb", 46, w - 10)
    put(fr, RL.stext(label, "xb", fs, lab_col, shadow=False), (w + 28) / 2, h + 14 + 41, "mm")
    sh = Image.new("RGBA", (fr.width + 80, fr.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 48, fr.width + 40, fr.height + 48], fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(16)); sh.alpha_composite(fr, (40, 40))
    return sh.rotate(angle, resample=Image.BICUBIC, expand=True)
def logo(base, x, y, width, anchor="lt"):
    lg = RL.logo_img(); s = width / lg.width; lg = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS)
    if anchor == "mt": x -= lg.width / 2
    if anchor == "rt": x -= lg.width
    base.alpha_composite(lg, (int(x), int(y)))
def badge(base, x, y, text, fill=RED, col=WHITE, size=40, anchor="l"):
    d = ImageDraw.Draw(base); w = RL.tw(text, "xb", size, 3) + 50; h = size + 30
    if anchor == "m": x -= w / 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill=fill + (255,))
    put(base, RL.stext(text, "xb", size, col, track=3, shadow=False), x + w / 2, y + h / 2 + 1, "mm")
def arrow(base, p0, p1, col=GOLD, width=14):
    d = ImageDraw.Draw(base); d.line([p0, p1], fill=col + (255,), width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]); L = 46
    pts = [p1, (p1[0] - L * math.cos(ang - 0.5), p1[1] - L * math.sin(ang - 0.5)), (p1[0] - L * math.cos(ang + 0.5), p1[1] - L * math.sin(ang + 0.5))]
    d.polygon(pts, fill=col + (255,))

# ------------------------------------------------ 16:9 — full documentary
def full_doc():
    W, H = 1920, 1080
    bg = photo("headshot2010", "warm", (W, H), 1.0, 0, 0)
    base = Image.new("RGBA", (W, H), (8, 8, 14, 255))
    src = E.graded("headshot2010", "warm"); s = 1.32 * H / src.height
    fg = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS).convert("RGBA")
    base.alpha_composite(fg, (W - fg.width + 560, -int(0.05 * fg.height)))
    base = vignette(hfade(base, 760, 1180), 0.35).convert("RGBA")
    p = polaroid("jobs1984b", "bw", (290, 320), 1.25, 0, -0.35, -7, "1985: FIRED")
    base.alpha_composite(p, (590, 590))
    arrow(base, (960, 700), (1120, 560))
    put(base, RL.stext("HE GOT", "xb", 150, WHITE, stroke=0), 90, 210, "lm")
    put(base, RL.stext("FIRED.", "xb", 190, RED, stroke=0), 86, 375, "lm")
    d = ImageDraw.Draw(base); d.rectangle([96, 480, 690, 488], fill=GOLD + (255,))
    put(base, RL.stext("Then he changed", "pfi", 82, GOLD), 92, 560, "lm")
    put(base, RL.stext("the world.", "pfi", 82, GOLD), 92, 650, "lm")
    badge(base, 96, 760, "THE FULL STORY", fill=GOLD, col=BLACK, size=44)
    logo(base, 70, 900, 470)
    base.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{OUT}/thumb_full_documentary_1280x720.jpg", quality=93)

# ------------------------------------------------ 16:9 — 1-minute video
def short_video():
    W, H = 1920, 1080
    base = E.kb_crop(E.blurred_bg("mac1984", "warm", 0.75), 1.0, 0.6, 0, (W, H)).convert("RGBA")
    src = E.graded("mac1984", "warm"); s = 1.15 * H / src.height * 1.0
    fg = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS).convert("RGBA")
    fg.putalpha(E.feather_mask(fg.width, fg.height, 90)); base.alpha_composite(fg, (W - fg.width - 120, -int(0.02 * fg.height)))
    base = vignette(hfade(base, 760, 1180), 0.3).convert("RGBA")
    put(base, RL.stext("THE MAN", "xb", 160, WHITE), 90, 220, "lm")
    put(base, RL.stext("WHO LOST", "xb", 160, WHITE), 90, 390, "lm")
    put(base, RL.stext("APPLE", "xb", 210, GOLD), 84, 580, "lm")
    badge(base, 96, 720, "60-SECOND STORY", fill=RED, size=44)
    logo(base, 70, 880, 460)
    base.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{OUT}/thumb_1min_video_1280x720.jpg", quality=93)

# ------------------------------------------------ 9:16 — reel covers
def cover(n, key, g, z, px, py, h1, h2, inset, inset_label, inset_angle, part_col=GOLD):
    W, H = 1080, 1920
    base = photo(key, g, (W, H), z, px, py)
    a = np.array(base).astype(np.float32); yy = np.arange(H)[:, None, None]
    a[..., :3] *= (1 - 0.55 * np.clip((yy - 900) / 700, 0, 1)) * (1 - 0.35 * np.clip((400 - yy) / 400, 0, 1))
    base = vignette(Image.fromarray(a.astype(np.uint8)), 0.3).convert("RGBA")
    d = ImageDraw.Draw(base)
    fs1 = fit(h1, "xb", 110, W - 160); w1 = RL.tw(h1, "xb", fs1) + 70
    d.rounded_rectangle([W / 2 - w1 / 2, 1060, W / 2 + w1 / 2, 1060 + fs1 + 44], radius=20, fill=GOLD + (255,))
    put(base, RL.stext(h1, "xb", fs1, BLACK, shadow=False), W / 2, 1060 + (fs1 + 44) / 2 + 2, "mm")
    fs2 = fit(h2, "xb", 124, W - 110)
    put(base, RL.stext(h2, "xb", fs2, WHITE, stroke=8), W / 2, 1060 + fs1 + 44 + 95, "mm")
    if inset:
        k, gg, zz, ipx, ipy = inset
        p = polaroid(k, gg, (380, 300), zz, ipx, ipy, inset_angle, inset_label, RED if n == 1 else BLACK)
        base.alpha_composite(p, (W - p.width - 20, 1440) if n != 2 else (20, 1440))
    badge(base, 70 if n != 1 else 70, 1500 if n == 2 else 1520, f"PART {n}", fill=RED, size=54) if n != 2 else badge(base, W - 300, 1520, f"PART {n}", fill=RED, size=54)
    logo(base, W / 2, 80, 620, "mt")
    base.convert("RGB").save(f"{OUT}/cover_reel{n}_1080x1920.jpg", quality=93)

if __name__ == "__main__":
    full_doc(); short_video()
    cover(1, "jobs1984b", "bw", 1.08, -0.3, -0.6, "FIRED FROM HIS", "OWN COMPANY?!",
          ("apple1", "warm", 1.1, 0, 0), "HIS COMPANY", -6)
    cover(2, "jobs07a", "neutral", 1.25, -0.45, -0.55, "THE DAY PHONES", "CHANGED FOREVER",
          ("iphonedock", "neutral", 1.15, 0, -0.2), "THE 1ST iPHONE", 6)
    cover(3, "redshawl", "warm", 1.0, 0, -0.45, "HE ALSO", "BUILT PIXAR?!",
          ("pixarhq", "warm", 1.1, 0, 0), "PIXAR", -6)
