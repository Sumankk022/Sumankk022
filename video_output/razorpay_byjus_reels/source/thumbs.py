"""Thumbnails for the Razorpay IPO / BYJU'S reels.  python3 thumbs.py  ->  OUT/thumb_*.jpg
Reuses fonts, text sprites and the FounderFile logo (lifted from the vertical intro) from reel.py."""
import math, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import reel as R
from reel import stext, rrect, glow, tw, GOLD, RED, WHITE, BLACK, GREEN, OUT, AS

def canvas_put(img, arr, x, y, a=1.0, anchor="lt", scale=1.0, rot=0.0):
    R.put(img, arr, x, y, a, anchor, scale, rot=rot)

def cover(path, size, focus=(0.5, 0.4), zoom=1.0):
    im = Image.open(path).convert("RGB"); w, h = size
    c = max(w / im.width, h / im.height) * zoom; nw, nh = int(im.width * c), int(im.height * c)
    im = im.resize((nw, nh), Image.LANCZOS)
    x = int(clampi((nw - w) * focus[0], 0, nw - w)); y = int(clampi((nh - h) * focus[1], 0, nh - h))
    return im.crop((x, y, x + w, y + h))
def clampi(v, a, b): return max(a, min(b, v))

def grade(im, bright=1.0, contrast=1.15, sat=1.1, tint=None):
    im = ImageEnhance.Contrast(ImageEnhance.Color(ImageEnhance.Brightness(im).enhance(bright)).enhance(sat)).enhance(contrast)
    if tint:
        a = np.array(im).astype(np.float32) * np.array(tint, np.float32); im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return im

def shade(im, top=0.0, bottom=0.0, top_h=0.35, bot_h=0.5, side=0.0, color=(0, 0, 0)):
    """darken top / bottom bands with smooth gradients"""
    w, h = im.size; a = np.array(im).astype(np.float32)
    y = np.linspace(0, 1, h)[:, None]
    m = np.maximum(top * np.clip(1 - y / top_h, 0, 1) ** 1.3, bottom * np.clip((y - (1 - bot_h)) / bot_h, 0, 1) ** 1.2)
    if side:
        x = np.linspace(-1, 1, w)[None, :]; m = np.maximum(m, side * np.abs(x) ** 3)
    a = a * (1 - m[..., None]) + np.array(color, np.float32) * m[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def logo(scale):
    lg = R.ident_logo(); return lg.resize((int(lg.width * scale), int(lg.height * scale)), Image.LANCZOS)

def box_text(img, txt, size, x, y, fill, color=BLACK, padx=34, h=None, anchor="mm", rot=0.0, r=18, glow_=True):
    w = tw(txt, "bk", size) + 2 * padx; hh = h or int(size * 1.28)
    if glow_: canvas_put(img, glow(int(w), hh, r, fill, 26, 120), x, y, 1, anchor, rot=rot)
    canvas_put(img, rrect(int(w), hh, r, fill + (255,)), x, y, 1, anchor, rot=rot)
    canvas_put(img, stext(txt, "bk", size, color, shadow=False), x, y - size * 0.03, 1, anchor, rot=rot)

def arrow(img, pts, color, width, head=70):
    """thick arrow with glow along a polyline"""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.line(pts, fill=color + (255,), width=width, joint="curve")
    (x1, y1), (x2, y2) = pts[-2], pts[-1]; ang = math.atan2(y2 - y1, x2 - x1)
    tip = (x2 + head * 0.55 * math.cos(ang), y2 + head * 0.55 * math.sin(ang))
    l = (x2 + head * math.cos(ang + 2.5), y2 + head * math.sin(ang + 2.5)); r_ = (x2 + head * math.cos(ang - 2.5), y2 + head * math.sin(ang - 2.5))
    d.polygon([tip, l, r_], fill=color + (255,))
    gl = lay.filter(ImageFilter.GaussianBlur(18)); ga = np.array(gl); ga[..., 3] = (ga[..., 3] * 0.9).astype(np.uint8)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sd = np.array(lay); sd[..., :3] = 0; sd[..., 3] = (sd[..., 3] * 0.6).astype(np.uint8)
    img.alpha_composite(Image.fromarray(sd).filter(ImageFilter.GaussianBlur(10)), (8, 12))
    img.alpha_composite(Image.fromarray(ga)); img.alpha_composite(lay)

def credit(img, txt, x, y, anchor="rb"):
    canvas_put(img, stext(txt, "m", 20, (235, 235, 235)), x, y, 0.8, anchor)

def logo_card(img, key, cx, cy, width, rot):
    lg = R.logo_sprite(key); s = width / lg.width; lg = lg.resize((int(lg.width * s), int(lg.height * s)), Image.LANCZOS)
    pw, ph = lg.width + 80, lg.height + 64
    card = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    card.alpha_composite(Image.fromarray(rrect(pw, ph, 26, (255, 255, 255, 255))))
    card.alpha_composite(lg, (40 + 40, 40 + 32))
    card = card.rotate(rot, Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0)); a = np.array(card); a[..., :3] = 0; a[..., 3] = (a[..., 3] * 0.65).astype(np.uint8)
    img.alpha_composite(Image.fromarray(a).filter(ImageFilter.GaussianBlur(22)), (int(cx - card.width / 2 + 10), int(cy - card.height / 2 + 22)))
    img.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2)))

# ============================================================ RAZORPAY
def razorpay_v():
    W, H = 1080, 1920
    bg = grade(cover(f"{AS}/img/bse.jpg", (W, H), (0.42, 0.25), 1.0), 0.8, 1.15, 1.05, (1.02, 1.0, 0.95))
    bg = shade(bg, top=0.85, bottom=0.97, top_h=0.33, bot_h=0.62, side=0.35)
    img = bg.convert("RGBA")
    lg = logo(0.62); img.alpha_composite(lg, (int(W / 2 - lg.width / 2), 70))
    logo_card(img, "rzplogo", W / 2 - 40, 690, 520, 4)
    box_text(img, "IPO", 150, W / 2 + 300, 520, GOLD, rot=-8)
    # headline block
    canvas_put(img, stext("RAZORPAY IS", "bk", 112, WHITE), W / 2, 1055, 1, "mm")
    box_text(img, "GOING PUBLIC", 112, W / 2, 1185, GOLD)
    # valuation drop
    y = 1395
    canvas_put(img, stext("$7.5B", "bk", 140, WHITE), 230, y, 1, "mm")
    arrow(img, [(450, y - 25), (570, y - 25), (640, y + 10)], RED, 28, 60)
    canvas_put(img, stext("$5B", "bk", 170, RED), 855, y, 1, "mm")
    canvas_put(img, stext("2021", "b", 40, (220, 220, 220), track=6), 230, y + 105, 1, "mm")
    canvas_put(img, stext("IPO TARGET", "b", 40, (220, 220, 220), track=6), 855, y + 105, 1, "mm")
    box_text(img, "WILL INVESTORS BUY IN?", 60, W / 2, 1650, RED, WHITE, r=40, h=104)
    credit(img, "Photo: Niyantha Shekhar · CC BY 2.0 · Wikimedia Commons", W - 30, H - 24)
    return img.convert("RGB")

def razorpay_h():
    W, H = 1280, 720
    bg = grade(cover(f"{AS}/img/bse.jpg", (W, H), (0.5, 0.2), 1.0), 0.75, 1.15, 1.05)
    bg = shade(bg, top=0.5, bottom=0.6, top_h=0.3, bot_h=0.45)
    a = np.array(bg).astype(np.float32); x = np.linspace(0, 1, W)[None, :, None]
    a = a * (1 - 0.88 * np.clip(1 - x / 0.62, 0, 1) ** 1.2); img = Image.fromarray(a.astype(np.uint8)).convert("RGBA")
    lg = logo(0.4); img.alpha_composite(lg, (50, 40))
    canvas_put(img, stext("RAZORPAY IS", "bk", 92, WHITE), 60, 250, 1, "lm")
    box_text(img, "GOING PUBLIC", 92, 60, 365, GOLD, anchor="lm")
    canvas_put(img, stext("$7.5B", "bk", 100, WHITE), 60, 515, 1, "lm")
    arrow(img, [(375, 500), (455, 500), (500, 528)], RED, 22, 48)
    canvas_put(img, stext("$5B?", "bk", 112, RED), 545, 515, 1, "lm")
    logo_card(img, "rzplogo", 1035, 600, 330, -5)
    box_text(img, "IPO", 100, 1110, 120, GOLD, rot=8)
    credit(img, "Photo: Niyantha Shekhar · CC BY 2.0", W - 16, H - 12)
    return img.convert("RGB")

# ============================================================ BYJU'S
def crack(img, x0, y0, x1, y1, seed=3):
    rng = np.random.default_rng(seed); d = ImageDraw.Draw(img)
    pts = [(x0, y0)]; n = 9
    for i in range(1, n):
        t = i / n; pts.append((x0 + (x1 - x0) * t + rng.uniform(-26, 26), y0 + (y1 - y0) * t + rng.uniform(-14, 14)))
    pts.append((x1, y1))
    d.line(pts, fill=(0, 0, 0, 255), width=12, joint="curve"); d.line(pts, fill=(255, 255, 255, 230), width=3)

def byjus_v():
    W, H = 1080, 1920
    bg = grade(cover(f"{AS}/img/byjuann3.jpg", (W, H), (0.38, 0.3), 1.0), 0.9, 1.2, 0.9, (1.08, 0.92, 0.9))
    bg = shade(bg, top=0.8, bottom=0.97, top_h=0.3, bot_h=0.55, side=0.3)
    img = bg.convert("RGBA")
    lg = logo(0.62); img.alpha_composite(lg, (int(W / 2 - lg.width / 2), 70))
    logo_card(img, "byjulogo", 250, 400, 300, -6)
    # $22B cracked
    y = 1180
    canvas_put(img, stext("$22 BILLION", "bk", 128, GOLD), W / 2, y, 1, "mm")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); crack(lay, 170, y - 20, 910, y + 45); img.alpha_composite(lay)
    arrow(img, [(W / 2 - 150, y + 140), (W / 2 - 75, y + 140)], RED, 20, 44); arrow(img, [(W / 2 + 150, y + 140), (W / 2 + 75, y + 140)], RED, 20, 44)
    canvas_put(img, stext("STARTUP", "b", 44, WHITE, track=10), W / 2, y - 120, 1, "mm")
    canvas_put(img, stext("TO", "bk", 70, WHITE), W / 2, y + 140, 1, "mm")
    box_text(img, "INSOLVENCY", 132, W / 2, y + 290, RED, WHITE, rot=-3)
    box_text(img, "WHAT WENT WRONG?", 58, W / 2, 1720, GOLD, BLACK, r=40, h=100)
    credit(img, "Photo: RPSkokie · CC BY-SA 4.0 · Wikimedia Commons", W - 30, H - 24)
    return img.convert("RGB")

def byjus_h():
    W, H = 1280, 720
    bg = grade(cover(f"{AS}/img/byjuann3.jpg", (W, H), (0.5, 0.3), 1.0), 0.95, 1.2, 0.9, (1.08, 0.92, 0.9))
    a = np.array(bg).astype(np.float32); x = np.linspace(0, 1, W)[None, :, None]
    a = a * (1 - 0.9 * np.clip((x - 0.45) / 0.35, 0, 1) ** 1.1)       # dark right side for text (Byju stays left)
    img = shade(Image.fromarray(a.astype(np.uint8)), top=0.3, bottom=0.5, bot_h=0.4).convert("RGBA")
    lg = logo(0.4); img.alpha_composite(lg, (W - lg.width - 40, 36))
    cx = 930
    canvas_put(img, stext("$22 BILLION", "bk", 90, GOLD), cx, 250, 1, "mm")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); crack(lay, cx - 270, 235, cx + 270, 275); img.alpha_composite(lay)
    canvas_put(img, stext("TO", "bk", 56, WHITE), cx, 360, 1, "mm")
    box_text(img, "INSOLVENCY", 96, cx, 465, RED, WHITE, rot=-3)
    box_text(img, "WHAT WENT WRONG?", 44, cx, 610, GOLD, BLACK, r=32, h=78)
    logo_card(img, "byjulogo", 190, 110, 220, -6)
    credit(img, "Photo: RPSkokie · CC BY-SA 4.0", W - 16, H - 12)
    return img.convert("RGB")

if __name__ == "__main__":
    for nm, fn in (("Razorpay_1080x1920", razorpay_v), ("Razorpay_1280x720", razorpay_h),
                   ("Byjus_1080x1920", byjus_v), ("Byjus_1280x720", byjus_h)):
        fn().save(f"{OUT}/Thumbnail_{nm}.jpg", quality=93); print(nm)
