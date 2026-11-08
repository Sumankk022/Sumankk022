import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from rembg import remove, new_session
W, H = 1080, 1920
hs = new_session("u2net_human_seg"); gs = new_session("isnet-general-use")
BB = "fonts/@fontsource_bebas-neue/package/files/bebas-neue-latin-400-normal.woff"
OS = "fonts/@fontsource_oswald/package/files/oswald-latin-700-normal.woff"
GOLD = (246, 190, 62); RED = (235, 30, 40)
yy, xx = np.mgrid[0:H, 0:W]
def cut(im, s=hs, matte=False):
    c = remove(im, session=s, alpha_matting=matte, alpha_matting_foreground_threshold=235, alpha_matting_background_threshold=15, alpha_matting_erode_size=8)
    a = c.split()[3].point(lambda v: 0 if v < 70 else v).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2)); c.putalpha(a)
    return c.crop(c.getbbox())
def photo_bg(path, color=1.0, bright=0.6, tint=(1, 1, 1), centering=(0.5, 0.5)):
    im = ImageOps.fit(Image.open(path).convert("RGB"), (W, H), centering=centering)
    im = ImageEnhance.Brightness(ImageEnhance.Color(im).enhance(color)).enhance(bright)
    return Image.fromarray((np.array(im).astype(np.float32) * np.array(tint)).clip(0, 255).astype(np.uint8)).convert("RGBA")
def glow_bg(cx, cy, col, rays=True):
    r = np.hypot(xx - cx, yy - cy); R = (np.clip(1 - r / 1300, 0, 1) ** 1.7)[..., None] * np.array(col, np.float32)
    if rays:
        ang = np.arctan2(yy - cy, xx - cx); R += (((0.5 + 0.5 * np.cos(ang * 16)) ** 6) * np.clip(1 - r / 1500, 0, 1))[..., None] * np.array(col) * 0.45
    R += 12
    return Image.fromarray(R.clip(0, 255).astype(np.uint8)).convert("RGBA")
def place(bg, img, h_, cx, top, glow=None, color=1.0):
    s = h_ / img.height; im = img.resize((int(img.width * s), h_), Image.LANCZOS)
    if color != 1.0:
        a = im.split()[3]; im = ImageEnhance.Color(im.convert("RGB")).enhance(color).convert("RGBA"); im.putalpha(a)
    if glow:
        a = im.split()[3].filter(ImageFilter.GaussianBlur(18)); g = Image.new("RGBA", im.size, glow); g.putalpha(a.point(lambda v: min(255, v * 2)))
        bg.alpha_composite(g, (cx - im.width // 2, top))
    bg.alpha_composite(im, (cx - im.width // 2, top))
def shade(bg, y0, y1, a0, a1):
    t = np.clip((yy - y0) / (y1 - y0), 0, 1); al = (a0 + (a1 - a0) * t) * ((yy >= y0) | (a0 > 0))
    lay = np.zeros((H, W, 4), np.uint8); lay[..., 3] = np.clip(al, 0, 255).astype(np.uint8)
    bg.alpha_composite(Image.fromarray(lay))
def text(bg, s, size, xy, fill=(255, 255, 255), font=BB, stroke=12, rot=0, maxw=None):
    while maxw and ImageFont.truetype(font, size).getlength(s) > maxw: size -= 4
    f = ImageFont.truetype(font, size); lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text((xy[0] + 8, xy[1] + 10), s, font=f, fill=(0, 0, 0, 210), anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0, 210))
    lay = lay.filter(ImageFilter.GaussianBlur(8)); ImageDraw.Draw(lay).text(xy, s, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))
    if rot: lay = lay.rotate(rot, center=xy, resample=Image.BICUBIC)
    bg.alpha_composite(lay)
def box_text(bg, s, size, xy, fill, tc=(0, 0, 0), font=BB, rot=0):
    f = ImageFont.truetype(font, size); tw = f.getlength(s); lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = xy[0] - tw / 2 - 34, xy[1] - size * 0.62, xy[0] + tw / 2 + 34, xy[1] + size * 0.55
    d.rounded_rectangle([x0 + 8, y0 + 12, x1 + 8, y1 + 12], radius=18, fill=(0, 0, 0, 150)); lay = lay.filter(ImageFilter.GaussianBlur(8)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=fill, outline=(0, 0, 0), width=7)
    d.text((xy[0], xy[1] + 4), s, font=f, fill=tc, anchor="mm")
    if rot: lay = lay.rotate(rot, center=xy, resample=Image.BICUBIC)
    bg.alpha_composite(lay)
def pill(bg, s, y):
    f = ImageFont.truetype(OS, 40); tw = f.getlength(s); d = ImageDraw.Draw(bg)
    d.rounded_rectangle([W / 2 - tw / 2 - 36, y - 38, W / 2 + tw / 2 + 36, y + 38], radius=38, fill=(0, 0, 0, 190), outline=GOLD, width=4)
    d.text((W / 2, y), s, font=f, fill=(255, 255, 255), anchor="mm")
def sparkles(bg, x0, x1, y0, y1, n=80, seed=3):
    d = ImageDraw.Draw(bg); rng = np.random.default_rng(seed)
    for _ in range(n):
        x, y, s = rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(1.5, 5); d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 235, 170, 230))

# ---------- PART 1: LEFT HOME AT 12?!
bg = photo_bg("img/trapiche.jpg", color=0.35, bright=0.5, tint=(0.9, 0.97, 1.12), centering=(0.5, 0.6))
plane = Image.open("out/logo_frame.png")  # placeholder unused
src = Image.open("img/muchelsea.jpg").convert("RGB"); w, h = src.size
young = cut(src.crop((int(w * .28), int(h * .12), int(w * .72), h)))
shade(bg, 1100, 1920, 0, 235)
place(bg, young, 1350, 560, 560, glow=(150, 180, 255, 255))
pill(bg, "CRISTIANO RONALDO  ·  PART 1", 150)
box_text(bg, "LEFT HOME", 170, (W / 2, 370), GOLD, rot=3)
text(bg, "AT JUST 12?!", 260, (W / 2, 590), rot=-2, maxw=1000)
box_text(bg, "FROM A POOR ISLAND", 92, (W / 2, 1600), (20, 20, 24), tc=(255, 255, 255))
text(bg, "TO THE TOP OF THE WORLD", 92, (W / 2, 1740), GOLD, stroke=8, maxw=1000)
bg.convert("RGB").save("out/cover1.jpg", quality=93)

# ---------- PART 2: 18 YEARS OLD AT MAN UNITED?!
bg = glow_bg(540, 900, (200, 20, 30))
wm = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(wm).text((W / 2 + 40, 1000), "7", font=ImageFont.truetype(BB, 1500), fill=(255, 255, 255, 40), anchor="mm"); bg.alpha_composite(wm)
src = Image.open("img/mu2006.jpg").convert("RGB"); w, h = src.size
p2 = cut(src.crop((int(w * .25), 0, int(w * .85), h)))
place(bg, p2, 1300, 560, 640, glow=(255, 90, 90, 255))
shade(bg, 1350, 1920, 0, 220)
sparkles(bg, 0, W, 300, 1400, 50, 7)
pill(bg, "CRISTIANO RONALDO  ·  PART 2", 150)
text(bg, "18 YEARS OLD", 210, (W / 2, 360), maxw=1000, rot=-2)
box_text(bg, "AT MAN UNITED?!", 150, (W / 2, 560), GOLD, rot=2)
box_text(bg, "451 GOALS", 130, (W / 2, 1590), (20, 20, 24), tc=GOLD)
text(bg, "IN 438 GAMES", 100, (W / 2, 1740), (255, 255, 255), stroke=8)
bg.convert("RGB").save("out/cover2.jpg", quality=93)

# ---------- PART 3: HOW CR7 BECAME A GLOBAL BRAND
bg = glow_bg(540, 820, (255, 170, 40))
wm = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(wm).text((W / 2, 1000), "CR7", font=ImageFont.truetype(BB, 620), fill=(255, 240, 200, 45), anchor="mm"); bg.alpha_composite(wm)
rich = cut(ImageEnhance.Sharpness(Image.open("out/rich_346.5.png").convert("RGB").crop((600, 0, 1450, 810))).enhance(1.6), hs, matte=True)
place(bg, rich, 1180, 560, 620, glow=(255, 215, 100, 255))
shade(bg, 1350, 1920, 0, 225)
sparkles(bg, 0, W, 250, 1500, 90, 4)
pill(bg, "CRISTIANO RONALDO  ·  PART 3", 150)
text(bg, "HOW CR7 BECAME", 170, (W / 2, 350), maxw=1000, rot=-2)
box_text(bg, "A GLOBAL BRAND", 160, (W / 2, 555), GOLD, rot=2)
text(bg, "FOOTBALL  ·  FASHION  ·  HOTELS", 70, (W / 2, 1600), (255, 255, 255), font=OS, stroke=6, maxw=1000)
box_text(bg, "$1.4 BILLION EMPIRE", 110, (W / 2, 1740), (40, 160, 70), tc=(255, 255, 255))
bg.convert("RGB").save("out/cover3.jpg", quality=93)
