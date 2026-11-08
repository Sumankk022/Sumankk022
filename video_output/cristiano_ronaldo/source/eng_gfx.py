
# ================= Ronaldo-specific graphics =================
MEDIA = json.load(open("media.json"))
def _artist(k):
    a_ = re.sub(r"<[^>]+>", "", MEDIA[k].get("artist", "")).strip()
    a_ = re.sub(r"\s+", " ", a_)
    return (a_[:48] + "…") if len(a_) > 49 else (a_ or "Unknown")
def CRED(k):
    if k not in MEDIA: return None
    lic = MEDIA[k]["lic"] or "see description"
    kind = "Video" if MEDIA[k]["file"].startswith("vid/") else "Photo"
    return f"{kind}: {_artist(k)} · {lic} · Wikimedia Commons"

def YEAR(t0, text, dur=2.6, x=110, y=800):
    def fn(layer, t):
        v = win(t, t0, t0 + dur, 0.3, 0.5); k = eo((t - t0) / 0.55)
        put(layer, text_img(text, "bb", 230, WHITE), x, y + 40 * (1 - k), v * 0.96, "lb")
        d = ImageDraw.Draw(layer); L = int(260 * eio((t - t0 - 0.15) / 0.7))
        d.rectangle([x + 6, y + 18, x + 6 + L, y + 25], fill=GOLD + (int(255 * v),))
    ev(t0 - 0.05, t0 + dur, fn)

def TITLE(t0, t1, text, size=210, y=530, sub=None, above=None, color=WHITE, hide=True):
    def fn(layer, t):
        if above: put(layer, text_img(above, "os5", 44, WHITE, track=16), W / 2, y - size * 0.52 - 40, win(t, t0 - 0.3, t1, 0.4, 0.3), "mm")
        tw = big_title(layer, t, t0, t1, text, "bb", size, y, color, 40, 12)
        if tw: gold_rules(layer, t, t0, t1, y, tw / 2)
        if sub: put(layer, text_img(sub, "os5", 34, GOLD, track=10), W / 2, y + 130, win(t, t0 + 0.45, t1, 0.45, 0.3), "mm")
    ev(t0 - 0.5, t1, fn)
    if hide: HIDE.append((t0 - 0.3, t1))

@functools.lru_cache(None)
def scrim_img(w, h, a=185):
    yy_, xx_ = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx_ - w / 2) / (w / 2)) ** 2 + ((yy_ - h / 2) / (h / 2)) ** 2)
    al = (np.clip(1 - r, 0, 1) ** 0.8 * a).astype(np.uint8)
    arr = np.zeros((h, w, 4), np.uint8); arr[..., 3] = al
    return Image.fromarray(arr)
def scrim(layer, x, y, w, h, v, a=185):
    if v <= 0.01: return
    im = scrim_img(int(w), int(h), int(a * v))
    layer.alpha_composite(im, (int(x - w / 2), int(y - h / 2)))
def STAT(t0, t1, target, label, prefix="", suffix="", y=470, color=GOLD, hide=True, x=W / 2, size=330, sub=None):
    def fn(layer, t):
        v = win(t, t0, t1, 0.25, 0.35); k = eio((t - t0) / 1.1)
        scrim(layer, x, y + size * 0.12, size * 2.6 + 300, size * 2.2, v)
        val = int(round(target * k))
        sc = 1.0 + 0.06 * math.sin(math.pi * clamp((t - t0 - 1.1) / 0.25))
        put(layer, text_img(f"{prefix}{val}{suffix}", "bb", size, color), x, y, v, "mm", scale=sc)
        put(layer, text_img(label, "os5", 46, WHITE, track=12), x, y + size * 0.55, v * eo((t - t0 - 0.4) / 0.5), "mm")
        if sub: put(layer, text_img(sub, "os5", 30, (215, 215, 215), track=8), x, y + size * 0.55 + 60, v * eo((t - t0 - 0.7) / 0.5), "mm")
    ev(t0, t1, fn)
    if hide: HIDE.append((t0, t1))

def LOWER3(t0, t1, name, role):
    def fn(layer, t):
        v = win(t, t0, t1, 0.4, 0.35); k = eo((t - t0) / 0.6)
        d = ImageDraw.Draw(layer); x0, y0 = 110, 760
        bw = 20 + (text_w(name, "bb", 96) + 40) * k
        d.rectangle([x0, y0, x0 + 10, y0 + 140], fill=GOLD + (int(255 * v),))
        put(layer, text_img(name, "bb", 96, WHITE), x0 + 34 - 30 * (1 - k), y0 + 52, v * k, "lm")
        put(layer, text_img(role, "os5", 32, GOLD, track=8), x0 + 36, y0 + 118, v * eo((t - t0 - 0.3) / 0.5), "lm")
    ev(t0, t1, fn)

def KICKER(t0, t1, text, y=180, color=GOLD):
    """small spaced label at the top"""
    def fn(layer, t):
        put(layer, text_img(text, "os5", 36, color, track=14), W / 2, y, win(t, t0, t1, 0.35, 0.3), "mm")
    ev(t0, t1, fn)

def PUNCH(items, t1, y=520, size=150, hide=True, gap=1.0):
    """items: (t, text, color). Words punch in with a scale overshoot, laid out on one line."""
    def fn(layer, t):
        sp = 40; ws = [text_w(x[1], "bb", size) for x in items]; tot = sum(ws) + sp * (len(ws) - 1)
        x = W / 2 - tot / 2
        for (ta, txt, col), w_ in zip(items, ws):
            if t >= ta - 0.02:
                k = eback((t - ta) / 0.35); v = win(t, ta, t1, 0.12, 0.3)
                put(layer, text_img(txt, "bb", size, col), x + w_ / 2, y, v, "mm", scale=max(0.05, 0.6 + 0.4 * k))
            x += w_ + sp
    ev(items[0][0] - 0.05, t1, fn)
    if hide: HIDE.append((items[0][0] - 0.1, t1))

def STACK(items, t1, x=W / 2, y=520, size=96, hide=True, anchor="m"):
    """vertical list that builds line by line"""
    def fn(layer, t):
        n = len(items)
        sv = win(t, items[0][0], t1, 0.3, 0.3)
        scrim(layer, x + (500 if anchor == "l" else 0), y, 1500, size * n * 1.6 + 200, sv, 200)
        for i, (ta, txt, col) in enumerate(items):
            if t < ta - 0.02: continue
            k = eo((t - ta) / 0.35); v = win(t, ta, t1, 0.15, 0.3)
            yy_ = y + (i - (n - 1) / 2) * (size * 0.98)
            put(layer, text_img(txt, "bb", size, col), x - 40 * (1 - k), yy_, v * k, anchor + "m")
    ev(items[0][0] - 0.05, t1, fn)
    if hide: HIDE.append((items[0][0] - 0.1, t1))

def ITALIC(t0, t1, text, size=110, y=520, color=WHITE):
    def fn(layer, t):
        put(layer, text_img(text, "pfi", size, color), W / 2, y, win(t, t0, t1, 0.45, 0.3), "mm", scale=1.0 + 0.04 * clamp((t - t0) / max(t1 - t0, .1)))
    ev(t0, t1, fn); HIDE.append((t0 - 0.2, t1))

def PILL(t0, t1, text, x, y, color=GOLD, size=40):
    def fn(layer, t):
        k = eback((t - t0) / 0.4) if t >= t0 else 0; v = win(t, t0, t1, 0.1, 0.3)
        if k <= 0: return
        w_ = (text_w(text, "os7", size, 4) + 60) * clamp(k, 0, 1.1); h_ = (size + 34) * clamp(k, 0, 1.1)
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle([x - w_ / 2, y - h_ / 2, x + w_ / 2, y + h_ / 2], radius=h_ / 2, fill=color + (int(235 * v),))
        put(layer, text_img(text, "os7", size, (18, 18, 20), track=4, shadow=False), x, y + 2, v * clamp(k), "mm", scale=max(0.05, clamp(k, 0, 1.1)))
    ev(t0, t1, fn)

# ---- dust / light-leak background (procedural replacement for a particles clip)
_rng2 = np.random.default_rng(11)
DUST = _rng2.random((70, 4))
def particles_bg(s_, lt, key, g="warm", dark=0.3, amt=0.35):
    bg = np.array(kb_crop(blurred_bg(key, g, dark), 1.0 + 0.012 * lt, 0, 0)).astype(np.float32)
    glow = np.exp(-(((xx - W * (0.2 + 0.6 * (0.5 + 0.5 * math.sin(lt * 0.35)))) / (W * 0.35)) ** 2 + ((yy - H * 0.35) / (H * 0.6)) ** 2))
    bg += glow[..., None] * np.array([60, 42, 12], np.float32) * amt * 2
    im = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for px_, py_, sz_, sp_ in DUST:
        x = (px_ * W + lt * 18 * (sp_ - 0.3)) % W; y = (py_ * H - lt * 25 * (0.3 + sp_)) % H; r = 1.5 + sz_ * 4
        a_ = int(40 + 120 * sz_ * (0.6 + 0.4 * math.sin(lt * 2 + px_ * 9)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 220, 150, a_))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))
    return np.array(im.convert("RGB")).astype(np.float32)

def dark_base(s_, lt, key, g="warm", dark=0.3):
    return Image.fromarray(np.clip(particles_bg(s_, lt, key, g, dark), 0, 255).astype(np.uint8)).convert("RGBA")

def render_route(s_, t, lt):
    """Madeira -> Lisbon flight path"""
    base = dark_base(s_, lt, s_["bg"], "cool", 0.28); d = ImageDraw.Draw(base)
    A_ = (520, 720); B_ = (1420, 330); t0 = s_["t0"]
    def bez(u):
        cx, cy = 900, 360
        return ((1 - u) ** 2 * A_[0] + 2 * (1 - u) * u * cx + u ** 2 * B_[0], (1 - u) ** 2 * A_[1] + 2 * (1 - u) * u * cy + u ** 2 * B_[1])
    for P, lab, sub, ta in [(A_, "MADEIRA", "FUNCHAL · HOME", t0 + 0.2), (B_, "LISBON", "SPORTING CP", s_["t_b"])]:
        k = eback((t - ta) / 0.45) if t >= ta else 0
        if k <= 0: continue
        for rr, al in [(46, 40), (30, 80)]:
            r = rr * clamp(k, 0, 1.2) * (1 + 0.15 * math.sin(lt * 4)); d.ellipse([P[0] - r, P[1] - r, P[0] + r, P[1] + r], fill=GOLD + (al,))
        r = 14 * clamp(k, 0, 1.2); d.ellipse([P[0] - r, P[1] - r, P[0] + r, P[1] + r], fill=GOLD + (255,), outline=WHITE + (255,), width=3)
        put(base, text_img(lab, "bb", 110, WHITE), P[0], P[1] + (90 if P is A_ else -95), clamp(k), "mm")
        put(base, text_img(sub, "os5", 30, GOLD, track=10), P[0], P[1] + (155 if P is A_ else -160), clamp(k) * 0.9, "mm")
    u1 = eio((t - s_["t_line"]) / 1.6)
    if u1 > 0:
        pts = [bez(i / 80 * u1) for i in range(81)]
        for i in range(0, 80, 2):
            d.line([pts[i], pts[i + 1]], fill=WHITE + (230,), width=5)
        px, py = pts[-1]; d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=WHITE + (255,))
        put(base, text_img("~1,000 KM", "os7", 40, WHITE, track=6), 1000, 560, eo((t - s_["t_line"] - 0.8) / 0.5), "mm")
    if "t_age" in s_ and t >= s_["t_age"]:
        k = eback((t - s_["t_age"]) / 0.5)
        put(base, text_img("AGE 12", "bb", 170, GOLD), 1560, 760, clamp(k), "mm", scale=max(0.05, clamp(k, 0, 1.15)))
    return np.array(base.convert("RGB")).astype(np.float32)

def render_seven(s_, t, lt):
    """the No. 7 shirt reveal"""
    base = dark_base(s_, lt, s_["bg"], "warm", 0.22)
    k = eo((t - s_["t0"] - 0.1) / 0.9); sc = 1.25 - 0.25 * k
    big = text_img("7", "bb", 640, GOLD)
    put(base, big, W / 2, 500, k, "mm", scale=sc)
    put(base, text_img("THE NUMBER", "os5", 46, WHITE, track=22), W / 2, 150, eo((t - s_["t0"] - 0.4) / 0.5), "mm")
    if "t_legends" in s_:
        names = ["GEORGE BEST", "BRYAN ROBSON", "ERIC CANTONA", "DAVID BECKHAM"]
        for i, n_ in enumerate(names):
            ta = s_["t_legends"] + i * 0.28; kk = eo((t - ta) / 0.4)
            x = W / 2 + (i - 1.5) * 420
            put(base, text_img(n_, "os5", 34, (230, 230, 230), track=6), x, 930 + 20 * (1 - kk), kk, "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_vs(s_, t, lt):
    base = Image.fromarray(RADIAL.astype(np.uint8)).convert("RGBA")
    for i, (key, lab, ts, py) in enumerate(s_["items"]):
        k = eo((t - ts) / 0.55)
        if k <= 0: continue
        im = kb_crop(graded(key, "neutral"), 1.06 + 0.03 * clamp((t - ts) / 4), 0, py, (W // 2 - 4, H)).convert("RGBA")
        arr = np.array(im); arr[..., 3] = int(255 * k)
        x = 0 if i == 0 else W // 2 + 4
        base.alpha_composite(Image.fromarray(arr), (x + int((-90 if i == 0 else 90) * (1 - k)), 0))
    dk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(dk)
    for yy_ in range(600, H, 4): dd.rectangle([0, yy_, W, yy_ + 4], fill=(0, 0, 0, int(min(210, (yy_ - 600) * 0.55))))
    base.alpha_composite(dk)
    d = ImageDraw.Draw(base); d.rectangle([W // 2 - 3, 0, W // 2 + 3, H], fill=GOLD + (230,))
    for i, (key, lab, ts, py) in enumerate(s_["items"]):
        lk = eo((t - ts - 0.15) / 0.45)
        put(base, text_img(lab, "bb", 120, WHITE if i else GOLD), W / 4 if i == 0 else 3 * W / 4, 900 + 20 * (1 - lk), lk, "mm")
    tv = s_["t_vs"]
    if t >= tv:
        k = eback((t - tv) / 0.45); r = 110 * clamp(k, 0, 1.2)
        d.ellipse([W / 2 - r, 520 - r, W / 2 + r, 520 + r], fill=(16, 16, 18, 255), outline=GOLD + (255,), width=6)
        put(base, text_img("VS", "bb", 120, GOLD, shadow=False), W / 2, 524, clamp(k), "mm", scale=max(0.05, clamp(k, 0, 1.2)))
    return np.array(base.convert("RGB")).astype(np.float32)

def render_career(s_, t, lt):
    base = dark_base(s_, lt, s_["bg"], "warm", 0.3); d = ImageDraw.Draw(base)
    y = 560; xL, xR = 170, W - 170; items = s_["items"]; n = len(items)
    L = eio((t - items[0][2] + 0.4) / 2.2)
    d.rectangle([xL, y - 3, xL + (xR - xL) * L, y + 3], fill=(255, 255, 255, 190))
    for i, (club, yr, ts) in enumerate(items):
        x = xL + (xR - xL) * (i + 0.5) / n; k = eback((t - ts) / 0.45) if t >= ts else 0
        if k <= 0: continue
        r = 18 * clamp(k, 0, 1.2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD + (255,), outline=(255, 255, 255, 255), width=3)
        up = i % 2 == 0
        put(base, text_img(club, "bb", 64, WHITE), x, y + (-110 if up else 110), clamp(k), "mm")
        put(base, text_img(yr, "os5", 32, GOLD, track=6), x, y + (-60 if up else 165), clamp(k) * 0.9, "mm")
    put(base, text_img(s_.get("head", "THE JOURNEY"), "os5", 40, GOLD, track=16), W / 2, 170, eo(lt / 0.5), "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_poll(s_, t, lt):
    base = Image.fromarray(RADIAL.astype(np.uint8)).convert("RGBA")
    for i, (key, lab, ts, py) in enumerate(s_["items"]):
        k = eo((t - ts) / 0.5)
        if k <= 0: continue
        im = kb_crop(graded(key, "neutral"), 1.05 + 0.03 * clamp((t - ts) / 4), 0, py, (W // 2 - 4, H)).convert("RGBA")
        arr = np.array(im).astype(np.float32); arr[..., :3] *= 0.75; arr = arr.astype(np.uint8); arr[..., 3] = int(255 * k)
        base.alpha_composite(Image.fromarray(arr), ((0 if i == 0 else W // 2 + 4) + int((-90 if i == 0 else 90) * (1 - k)), 0))
    dk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(dk)
    for yy_ in range(520, H, 4): dd.rectangle([0, yy_, W, yy_ + 4], fill=(0, 0, 0, int(min(220, (yy_ - 520) * 0.5))))
    base.alpha_composite(dk); d = ImageDraw.Draw(base); d.rectangle([W // 2 - 3, 0, W // 2 + 3, H], fill=GOLD + (230,))
    put(base, text_img("WHO'S THE GOAT?", "bb", 110, WHITE), W / 2, 130, eo(lt / 0.5), "mm")
    for i, (key, lab, ts, py) in enumerate(s_["items"]):
        lk = eback((t - ts - 0.1) / 0.45) if t >= ts else 0
        cx = W / 4 if i == 0 else 3 * W / 4
        put(base, text_img("TEAM", "os5", 44, (230, 230, 230), track=16), cx, 770, clamp(lk), "mm")
        put(base, text_img(lab, "bb", 150, GOLD if i == 0 else WHITE), cx, 870, clamp(lk), "mm", scale=max(0.05, 0.7 + 0.3 * clamp(lk, 0, 1.1)))
    tc = s_["t_comment"]
    if t >= tc - 0.1:
        kb = eback((t - tc) / 0.45); cx, cy = W / 2, 330
        w_, h_ = 600 * clamp(kb, 0, 1.1), 92 * clamp(kb, 0, 1.1)
        d.rounded_rectangle([cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2], radius=h_ / 2, fill=(255, 255, 255, 240))
        d.polygon([(cx - 40, cy + h_ / 2 - 2), (cx - 10, cy + h_ / 2 - 2), (cx - 46, cy + h_ / 2 + 26 * clamp(kb))], fill=(255, 255, 255, 240))
        put(base, text_img("COMMENT BELOW 👇".replace(" 👇", ""), "os7", 40, (20, 20, 24), track=4, shadow=False), cx, cy + 2, clamp(kb), "mm", scale=max(0.05, clamp(kb, 0, 1.1)))
    return np.array(base.convert("RGB")).astype(np.float32)
