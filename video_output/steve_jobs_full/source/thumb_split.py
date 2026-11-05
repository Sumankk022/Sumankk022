"""Main documentary thumbnail: 'then vs now' half split (1985 B&W | 2010 colour)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import reel as RL, engine as E
from thumbs import put, fit, badge, logo, GOLD, RED, WHITE, BLACK, OUT

W, H = 1920, 1080

def placed(key, g, face_xy, face_target, scale):
    """scale image by `scale`, put the image point face_xy (fractions) at canvas point face_target"""
    src = E.graded(key, g); s = scale * H / src.height
    im = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    x = int(face_target[0] - face_xy[0] * im.width); y = int(face_target[1] - face_xy[1] * im.height)
    canvas.paste(im, (x, y)); return np.array(canvas).astype(np.float32)

def make(diagonal=True, name="thumb_full_documentary_split"):
    left = placed("jobs1984b", "bw", (0.50, 0.30), (500, 400), 1.55)      # young Jobs face ~ left-centre
    right = placed("headshot2010", "warm", (0.52, 0.38), (1430, 420), 1.45)  # 2010 Jobs face ~ right-centre
    # warm the B&W slightly cold, push contrast
    left = np.clip((left - 128) * 1.12 + 120, 0, 255) * np.array([0.96, 0.98, 1.04])
    # split mask (diagonal or vertical) with a short soft transition zone
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top_x, bot_x = (1040, 880) if diagonal else (960, 960)
    line_x = top_x + (bot_x - top_x) * yy / H
    m = np.clip((xx - line_x) / 26 + 0.5, 0, 1)[..., None]
    img = left * (1 - m) + right * m
    # vignette + darker bottom band for the text
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.40 * np.clip(r - 0.55, 0, 1))[..., None]
    img *= (1 - 0.62 * np.clip((yy - 640) / 440, 0, 1) ** 1.2)[..., None]
    base = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    # glowing gold seam
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.line([(top_x, -10), (bot_x, H + 10)], fill=GOLD + (255,), width=26)
    glow = glow.filter(ImageFilter.GaussianBlur(22)); base.alpha_composite(glow)
    d = ImageDraw.Draw(base); d.line([(top_x, -10), (bot_x, H + 10)], fill=(255, 236, 180, 255), width=8)
    # year tags
    badge(base, 60, 60, "1985", fill=(20, 20, 20), col=WHITE, size=46)
    badge(base, W - 60 - (RL.tw("2010", "xb", 46, 3) + 50), 60, "2010", fill=GOLD, col=BLACK, size=46)
    # big words
    fs = fit("FIRED.", "xb", 210, 760)
    put(base, RL.stext("FIRED.", "xb", fs, RED, stroke=8), 70, 905, "lm")
    fs2 = fit("LEGEND.", "xb", 210, 820)
    put(base, RL.stext("LEGEND.", "xb", fs2, GOLD, stroke=8), W - 60, 905, "rm")
    # centre seam label + logo
    mid_x = (top_x + bot_x) / 2
    pill = "THE FULL STORY"; pw = RL.tw(pill, "xb", 40, 4) + 56
    d.rounded_rectangle([mid_x - pw / 2, 1000, mid_x + pw / 2, 1062], radius=31, fill=WHITE + (255,))
    put(base, RL.stext(pill, "xb", 40, BLACK, track=4, shadow=False), mid_x, 1031, "mm")
    logo(base, mid_x, 40, 400, "mt")
    out = base.convert("RGB").resize((1280, 720), Image.LANCZOS)
    out.save(f"{OUT}/{name}_1280x720.jpg", quality=93); return out

if __name__ == "__main__":
    a = make(True, "thumb_full_documentary_split")
    b = make(False, "thumb_full_documentary_split_straight")
    sh = Image.new("RGB", (1280, 1440)); sh.paste(a, (0, 0)); sh.paste(b, (0, 720)); sh.save(f"{OUT}/rev_split.jpg", quality=85)
