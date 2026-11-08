import numpy as np, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from rembg import remove, new_session
W, H = 1280, 720
ses = new_session("isnet-general-use"); hs = new_session("u2net_human_seg")
def cut(im, s=None, matte=True):
    c = remove(im, session=s or ses, alpha_matting=matte, alpha_matting_foreground_threshold=235, alpha_matting_background_threshold=15, alpha_matting_erode_size=8)
    a = c.split()[3].point(lambda v: 0 if v < 70 else v).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2)); c.putalpha(a)
    bb = c.getbbox(); return c.crop(bb)
rich = cut(ImageEnhance.Sharpness(Image.open("out/rich_346.5.png").convert("RGB").crop((600, 0, 1450, 810))).enhance(1.6), hs)
young_src = Image.open("img/muchelsea.jpg").convert("RGB")
w, h = young_src.size; young = cut(young_src.crop((int(w*.28), int(h*.12), int(w*.72), h)), hs, matte=False)
F = "fonts/@fontsource_bebas-neue/package/files/bebas-neue-latin-400-normal.woff"
OS = "fonts/@fontsource_oswald/package/files/oswald-latin-700-normal.woff"
# ---- backgrounds
L = Image.open("img/trapiche.jpg").convert("RGB"); L = ImageOps.fit(L, (W, H), centering=(0.5, 0.6))
L = ImageEnhance.Color(L).enhance(0.15); L = ImageEnhance.Brightness(L).enhance(0.55)
L = Image.fromarray((np.array(L).astype(np.float32) * np.array([0.85, 0.95, 1.1])).clip(0, 255).astype(np.uint8))
R = np.zeros((H, W, 3), np.float32); yy, xx = np.mgrid[0:H, 0:W]
cx, cy = 930, 300; r = np.hypot(xx - cx, yy - cy)
R += (np.clip(1 - r / 900, 0, 1) ** 1.6)[..., None] * np.array([255, 170, 40])
ang = np.arctan2(yy - cy, xx - cx); rays = (0.5 + 0.5 * np.cos(ang * 18)) ** 6 * np.clip(1 - r / 1000, 0, 1)
R += rays[..., None] * np.array([120, 80, 10]); R += np.array([25, 12, 0])
R = Image.fromarray(R.clip(0, 255).astype(np.uint8))
# diagonal split
mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).polygon([(700, 0), (W, 0), (W, H), (560, H)], fill=255)
bg = Image.composite(R, L, mask)
# sparkles on gold side
d = ImageDraw.Draw(bg); rng = np.random.default_rng(4)
for _ in range(60):
    x, y, s = rng.uniform(640, W), rng.uniform(0, H), rng.uniform(1, 4)
    d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 235, 170))
def place(img, h_, x, y, glow=None):
    s = h_ / img.height; im = img.resize((int(img.width * s), h_), Image.LANCZOS)
    if glow:
        a = im.split()[3].filter(ImageFilter.GaussianBlur(14)); g = Image.new("RGBA", im.size, glow); g.putalpha(a.point(lambda v: min(255, v * 2)))
        bg.paste(g, (x - im.width // 2, y), g)
    bg.paste(im, (x - im.width // 2, y), im)
yg = young.copy(); a = yg.split()[3]
yg = ImageEnhance.Color(yg.convert("RGB")).enhance(0.35).convert("RGBA"); yg.putalpha(a)
place(yg, 600, 300, 150, glow=(140, 170, 255, 255))
place(rich, 780, 960, -20, glow=(255, 210, 90, 255))
# split edge
ImageDraw.Draw(bg).line([(700, 0), (560, H)], fill=(255, 255, 255), width=8)
def text(s, font, size, xy, fill, stroke=10, anchor="mm", rot=0):
    f = ImageFont.truetype(font, size)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(lay)
    dd.text((xy[0] + 6, xy[1] + 8), s, font=f, fill=(0, 0, 0, 200), anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
    lay = lay.filter(ImageFilter.GaussianBlur(6)); ImageDraw.Draw(lay).text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))
    if rot: lay = lay.rotate(rot, center=xy, resample=Image.BICUBIC)
    bg.paste(lay, (0, 0), lay)
def gold_text(s, font, size, xy, stroke=10, rot=0):
    f = ImageFont.truetype(font, size)
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).text(xy, s, font=f, fill=255, anchor="mm")
    grad = np.zeros((H, W, 3), np.float32); t = (yy - (xy[1] - size / 2)) / size
    for c, (a0, a1) in enumerate([(255, 230), (245, 150), (140, 30)]): grad[..., c] = a0 + (a1 - a0) * np.clip(t, 0, 1)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).text((xy[0] + 6, xy[1] + 8), s, font=f, fill=(0, 0, 0, 220), anchor="mm", stroke_width=stroke)
    sh = sh.filter(ImageFilter.GaussianBlur(6)); ImageDraw.Draw(sh).text(xy, s, font=f, fill=(0, 0, 0, 255), anchor="mm", stroke_width=stroke)
    gl = Image.fromarray(grad.clip(0, 255).astype(np.uint8)).convert("RGBA"); gl.putalpha(m)
    sh.alpha_composite(gl)
    if rot: sh = sh.rotate(rot, center=xy, resample=Image.BICUBIC)
    bg.paste(sh, (0, 0), sh)
text("ZERO", F, 210, (250, 110), (255, 255, 255), rot=4)
gold_text("BILLIONAIRE", F, 175, (930, 640), stroke=9, rot=-3)
# arrow
ar = Image.new("RGBA", (W, H), (0, 0, 0, 0)); da = ImageDraw.Draw(ar)
pts = [(470, 400), (610, 330), (595, 300), (700, 300), (650, 395), (635, 365), (495, 440)]
da.polygon(pts, fill=(0, 0, 0)); ar = ar.filter(ImageFilter.GaussianBlur(5)); da = ImageDraw.Draw(ar)
da.polygon(pts, fill=(235, 30, 40), outline=(0, 0, 0), width=7)
bg.paste(ar, (0, 0), ar)
# tags
def tag(s, x, y, fill, tc):
    f = ImageFont.truetype(OS, 34); tw = f.getlength(s)
    ImageDraw.Draw(bg).rounded_rectangle([x, y, x + tw + 36, y + 56], radius=8, fill=fill, outline=(0, 0, 0), width=4)
    ImageDraw.Draw(bg).text((x + 18, y + 28), s, font=f, fill=tc, anchor="lm")
tag("ISLAND BOY · MADEIRA", 40, 630, (20, 20, 24), (255, 255, 255))
tag("$1.4 BILLION", 1010, 30, (40, 160, 70), (255, 255, 255))
bg.convert("RGB").save("Thumbnail_Zero_to_Billionaire_1280x720.jpg", quality=93)
