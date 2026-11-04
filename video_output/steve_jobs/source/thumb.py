import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render as R
src = R.graded("headshot2010", "warm"); sc = 1.22 * R.H / src.height
fg = src.resize((int(src.width * sc), int(src.height * sc)), Image.LANCZOS)
canvas = Image.new("RGB", (R.W, R.H), (6, 8, 22))
canvas.paste(fg, (R.W - fg.width + 330, -int(0.06 * fg.height)))
a = np.array(canvas).astype(np.float32)
xx = np.linspace(0, 1, R.W)[None, :, None]
a *= (0.15 + 0.85 * np.clip((xx - 0.36) / 0.3, 0, 1))      # fade left side into dark for text
a *= R.VIG ** 0.6
base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
R.put(base, R.text_img("FIRED FROM", "xb", 120, R.WHITE), 90, 250, 1, "lm")
R.put(base, R.text_img("HIS OWN", "xb", 120, R.WHITE), 90, 390, 1, "lm")
R.put(base, R.text_img("COMPANY.", "xb", 150, R.RED), 90, 545, 1, "lm")
d = ImageDraw.Draw(base); d.rectangle([92, 650, 92 + 520, 658], fill=R.GOLD + (255,))
R.put(base, R.text_img("Then he changed the world.", "pfi", 62, R.GOLD), 90, 730, 1, "lm")
R.put(base, R.text_img("STEVE JOBS", "sb", 40, R.WHITE, track=12), 90, 860, 0.9, "lm")
base.convert("RGB").resize((1280, 720), Image.LANCZOS).save("out/thumbnail_1280x720.jpg", quality=92)
