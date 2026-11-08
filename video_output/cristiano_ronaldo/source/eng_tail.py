S.sort(key=lambda s_: s_["t0"])
for i, s_ in enumerate(S): s_["t1"] = S[i + 1]["t0"] if i + 1 < len(S) else TOTAL

# ================= shot rendering =================
VIDS = {}
def vid_for(key, src, off, slow, g):
    if key not in VIDS: VIDS[key] = Vid(src, off, slow, g)
    return VIDS[key]
def paste_panel(base, key, cx, cy, pw, ph, k, t_rel, g="neutral", border=True):
    im = kb_crop(graded(key, g), 1.04 + 0.05 * clamp(t_rel / 4), 0, 0, (pw, ph)).convert("RGBA")
    fr = Image.new("RGBA", (pw + 6, ph + 6), (255, 255, 255, 235 if border else 0)); fr.paste(im, (3, 3))
    arr = np.array(fr); arr[..., 3] = (arr[..., 3] * clamp(k)).astype(np.uint8)
    sh = Image.new("RGBA", (pw + 80, ph + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 50, pw + 40, ph + 50], fill=(0, 0, 0, int(160 * clamp(k))))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (int(cx - pw / 2 - 40), int(cy - ph / 2 - 40)))
    base.alpha_composite(Image.fromarray(arr), (int(cx - pw / 2 - 3), int(cy - ph / 2 - 3)))

def render_shot(s_, t):
    lt = t - s_["t0"]; dur = max(s_["t1"] - s_["t0"], 0.01); p = clamp(lt / dur); k = s_["kind"]
    if k == "vid":
        fr = vid_for(id(s_), s_["src"], s_["off"], s_["slow"], s_["g"]).frame(int(lt * FPS)).astype(np.float32)
        if "dim" in s_: fr *= s_["dim"]
        return fr
    if k == "img":
        z0, z1 = s_["z"]; z = z0 + (z1 - z0) * p
        (px0, py0), (px1, py1) = s_["pan"]; px, py = px0 + (px1 - px0) * p, py0 + (py1 - py0) * p
        if s_["layout"] == "side":
            bg = kb_crop(blurred_bg(s_["key"], s_["g"]), 1.0 + 0.05 * p, 0, 0)
            src = graded(s_["key"], s_["g"]); fh = int(H * z); fw = int(src.width * fh / src.height)
            if fw > W * 0.75: fw = int(W * 0.75); fh = int(src.height * fw / src.width)
            fg = src.resize((fw, fh), Image.BILINEAR)
            cx = W * (0.68 if s_["side"] == "right" else 0.32)
            bg.paste(fg, (int(cx - fw / 2), int(H / 2 - fh / 2 - (fh - H) * 0.15)), feather_mask(fw, fh))
            fr = np.array(bg).astype(np.float32)
            if "bw_at" in s_:
                a0, a1 = s_["bw_at"]; m = eio((t - a0) / (a1 - a0))
                lum = fr @ np.array([0.299, 0.587, 0.114], np.float32)
                bw = np.repeat((128 + (lum - 128) * 1.15)[..., None], 3, 2); fr = fr * (1 - m) + bw * m
        else:
            fr = np.array(kb_crop(graded(s_["key"], s_["g"]), z, px, py)).astype(np.float32)
        if "dark" in s_:
            d0, d1, ta, tb = s_["dark"]; fr *= d0 + (d1 - d0) * eio((t - ta) / max(tb - ta, 0.01))
        return fr
    if k == "ext":
        return vid_for(id(s_), s_["src"], 0.0, 1.0, "none").frame(int(lt * FPS)).astype(np.float32)
    if k == "dark":
        return vid_for(id(s_), f"vid/{s_['bg']}.mp4", 0, 1.0, "warm").frame(int(lt * FPS)).astype(np.float32) * 0.8
    if k == "card": return render_card(s_, t, lt)
    if k == "trip": return render_trip(s_, t, lt)
    if k == "route": return render_route(s_, t, lt)
    if k == "seven": return render_seven(s_, t, lt)
    if k == "vs": return render_vs(s_, t, lt)
    if k == "career": return render_career(s_, t, lt)
    if k == "poll": return render_poll(s_, t, lt)
    if k == "subscribe": return render_subscribe(s_, t, lt)
    if k == "end": return render_end(s_, t, lt)

def render_card(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, s_["bgkey"], s_["bgg"], 0.36), 0, 255).astype(np.uint8)).convert("RGBA")
    t0, t1 = s_["t0"], s_["t1"]
    put(base, text_img(f"CHAPTER  {s_['n']:02d}", "os5", 36, GOLD, track=14), W / 2, 380, win(t, t0 + 0.25, t1 + 0.6, 0.5, 0.5), "mm")
    tw = big_title(base, t, t0 + 0.45, t1 + 0.6, s_["title"].upper(), "bb", 190, 525, WHITE, 30, 8)
    if tw: gold_rules(base, t, t0 + 0.5, t1 + 0.6, 520, tw / 2)
    put(base, text_img(s_["years"], "os5", 38, (225, 225, 225), track=10), W / 2, 665, win(t, t0 + 1.0, t1 + 0.6, 0.5, 0.5), "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def render_trip(s_, t, lt):
    bg = np.array(kb_crop(graded(s_["bg"], "warm"), 1.05 + 0.016 * lt, 0, 0)).astype(np.float32)
    bg *= 1.0 - 0.7 * eio((t - s_["dark_at"]) / 0.6)
    base = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")
    for i, (key, lab, sub, ts) in enumerate(s_["items"]):
        k = eo((t - ts + 0.15) / 0.45)
        if k <= 0: continue
        cx = W / 2 + (i - 1) * 580; cy = 460 + 70 * (1 - k)
        paste_panel(base, key, cx, cy, 500, 340, k, t - ts)
        lk = eo((t - ts - 0.1) / 0.4)
        put(base, text_img(lab, "bb", 64, GOLD), cx, cy + 205 + 10 * (1 - lk), lk, "mt")
        if sub: put(base, text_img(sub, "os5", 28, (220, 220, 220), track=4), cx, cy + 280, lk * 0.85, "mt")
    return np.array(base.convert("RGB")).astype(np.float32)

def button(layer, t, cx, cy, tb, tc, label="SUBSCRIBE"):
    d = ImageDraw.Draw(layer)
    kb = eback((t - tb) / 0.45) if t >= tb else 0
    if kb <= 0: return
    clicked = t >= tc + 0.08
    sc = kb * (1 - 0.06 * math.sin(math.pi * clamp((t - tc) / 0.16)))
    bw_, bh_ = 470 * sc, 112 * sc; col = (62, 62, 66) if clicked else (229, 33, 23)
    btn = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2 + 10, cx + bw_ / 2, cy + bh_ / 2 + 10], radius=bh_ / 2, fill=(0, 0, 0, 110))
    btn = btn.filter(ImageFilter.GaussianBlur(10)); bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle([cx - bw_ / 2, cy - bh_ / 2, cx + bw_ / 2, cy + bh_ / 2], radius=bh_ / 2, fill=col + (255,))
    layer.alpha_composite(btn)
    put(layer, text_img("SUBSCRIBED" if clicked else label, "b", 46, WHITE, track=4, shadow=False), cx, cy + 2, clamp(kb), "mm", scale=max(0.01, sc))
    if clicked:
        rk = clamp((t - tc) / 0.6); rr = 14 + 80 * eo(rk)
        d.ellipse([cx + 60 - rr, cy + 10 - rr, cx + 60 + rr, cy + 10 + rr], outline=(255, 255, 255, int(170 * (1 - rk))), width=3)
        bk = eback((t - tc - 0.25) / 0.4)
        if bk > 0:
            ang = math.sin((t - tc) * 22) * 18 * math.exp(-max(0, t - tc - 0.25) * 3)
            bell = Image.new("RGBA", (140, 140), (0, 0, 0, 0)); bdd = ImageDraw.Draw(bell)
            bdd.ellipse([20, 20, 120, 120], fill=(255, 255, 255, 40), outline=(255, 255, 255, 200), width=3)
            bdd.pieslice([45, 38, 95, 98], 180, 360, fill=WHITE + (255,)); bdd.rectangle([45, 66, 95, 86], fill=WHITE + (255,))
            bdd.polygon([(38, 92), (102, 92), (95, 82), (45, 82)], fill=WHITE + (255,)); bdd.ellipse([62, 92, 78, 106], fill=WHITE + (255,))
            bell = bell.rotate(ang, resample=Image.BICUBIC, center=(70, 30))
            s2 = max(1, int(140 * clamp(bk, 0, 1.2))); bell = bell.resize((s2, s2), Image.BILINEAR)
            layer.alpha_composite(bell, (int(cx + 300 - s2 / 2), int(cy - s2 / 2)))
    if t >= tc - 0.9:
        ck = eio((t - (tc - 0.9)) / 0.8); x = cx + 60 + 420 * (1 - ck); y = cy + 10 + 260 * (1 - ck)
        ca = win(t, tc - 0.9, tc + 1.1, 0.2, 0.35)
        pts = [(x + a_, y + b_) for a_, b_ in [(0, 0), (0, 44), (11, 33), (19, 52), (27, 48), (19, 30), (34, 30)]]
        d.polygon([(a_ + 3, b_ + 4) for a_, b_ in pts], fill=(0, 0, 0, int(110 * ca)))
        d.polygon(pts, fill=(255, 255, 255, int(255 * ca)), outline=(20, 20, 20, int(255 * ca)))

def brand(layer, t, t0, y=300, a_=1.0):
    v = win(t, t0, 1e9, 0.6, 0.01) * a_
    put(layer, text_img("FOUNDER FILES", "bb", 150, WHITE, track=12), W / 2, y, v, "mm")
    d = ImageDraw.Draw(layer); L = int(260 * eio((t - t0 - 0.3) / 0.8))
    d.rectangle([W / 2 - L, y + 72, W / 2 + L, y + 75], fill=GOLD + (int(255 * v),))

def render_subscribe(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, s_["bg"], "warm", 0.24), 0, 255).astype(np.uint8)).convert("RGBA")
    brand(base, t, s_["t0"] + 0.2, 330)
    put(base, text_img("every legend has a story", "pfi4", 46, (235, 235, 235)), W / 2, 450,
        win(t, s_["t0"] + 0.9, 1e9, 0.5, 0.01), "mm")
    button(base, t, W / 2, 600, s_["t0"] + 1.0, s_["t_click"])
    return np.array(base.convert("RGB")).astype(np.float32)

def render_end(s_, t, lt):
    base = Image.fromarray(np.clip(particles_bg(s_, lt, s_["bg"], "warm", 0.2), 0, 255).astype(np.uint8)).convert("RGBA")
    brand(base, t, s_["t0"] + 0.1, 170)
    d = ImageDraw.Draw(base)
    # placeholder frames where YouTube end-screen elements go (video + playlist + subscribe)
    for i, (x, lab) in enumerate([(W / 2 - 430, "WATCH NEXT"), (W / 2 + 430, "MORE LEGENDARY STORIES")]):
        k = eo((t - s_["t0"] - 0.5 - i * 0.2) / 0.6); w_, h_ = 760, 428
        d.rounded_rectangle([x - w_ / 2, 560 - h_ / 2, x + w_ / 2, 560 + h_ / 2], radius=18, outline=(255, 255, 255, int(150 * k)), width=3,
                            fill=(0, 0, 0, int(90 * k)))
        put(base, text_img(lab, "os5", 34, GOLD, track=8), x, 560 + h_ / 2 + 50, k, "mm")
    put(base, text_img("Thanks for watching.", "pfi", 44, WHITE), W / 2, 1000, win(t, s_["t0"] + 1.0, 1e9, 0.6, 0.01), "mm")
    return np.array(base.convert("RGB")).astype(np.float32)

def overlays(layer, t):
    for s_ in S:
        if not (s_["t0"] - 1 <= t <= s_["t1"] + 1): continue
        if s_.get("tag"): chapter_tag(layer, t, s_["t0"] + 0.35, s_["t1"] - 0.1, s_["tag"])
        if s_.get("credit") and s_["t0"] <= t <= s_["t1"]: credit(layer, t, s_["t0"] + 0.2, s_["t1"], s_["credit"])
    for t0, t1, fn in EV:
        if t0 <= t <= t1: fn(layer, t)
    draw_captions(layer, t)

FLASHES = [s_["t0"] for s_ in S if s_.get("flash")]
CUR = {"idx": None}
def frame_at(t, fi):
    idx = max(i for i, s_ in enumerate(S) if s_["t0"] <= t + 1e-9)
    if CUR["idx"] is not None and idx != CUR["idx"]:     # free finished video readers
        keep = {id(S[idx]), id(S[idx - 1]) if idx else None}
        for k_ in list(VIDS):
            if k_ not in keep: VIDS.pop(k_).close()
    CUR["idx"] = idx
    cur = S[idx]; fr = render_shot(cur, t); lt = t - cur["t0"]
    if idx > 0 and cur["xf"] > 0 and lt < cur["xf"]:
        m = eio(lt / cur["xf"]); fr = render_shot(S[idx - 1], t) * (1 - m) + fr * m
    if not (cur["kind"] == "ext" and lt >= cur["xf"]):      # the ident plays untouched
        fr = fr * VIG + GRAIN[fi % 4]
    fr *= clamp(t / 0.5) * clamp((TOTAL - t) / 1.0)
    for ft in FLASHES:
        if ft <= t < ft + 0.45: f = 1 - eo((t - ft) / 0.45); fr = fr * (1 - f) + 255 * f
    base = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert("RGBA")
    overlays(base, t)
    return base.convert("RGB")

def main():
    a_ = sys.argv[1:]
    if a_ and a_[0] == "--still":
        for ts in a_[1:]:
            t = float(ts); frame_at(t, 0).save(f"out/st_{t:06.2f}.jpg", quality=88)
            for v in VIDS.values(): v.close()
            VIDS.clear(); CUR["idx"] = None
        return
    i, n = int(a_[1]), int(a_[2])
    N = int(TOTAL * FPS); n0, n1 = N * i // n, N * (i + 1) // n
    if len(a_) > 3:      # sub-split chunk i into a_[3] pieces, render piece a_[4]
        m, j = int(a_[3]), int(a_[4]); L_ = n1 - n0; n0, n1 = n0 + L_ * j // m, n0 + L_ * (j + 1) // m; i = i * 10 + j
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                            "-threads", "2", f"out/part_{i:02d}.mp4"], stdin=subprocess.PIPE)
    for fi in range(n0, n1):
        enc.stdin.write(frame_at(fi / FPS, fi).tobytes())
        if fi % 300 == 0: print(f"part {i}: {fi/FPS:6.1f}s / {n1/FPS:.1f}", flush=True)
    enc.stdin.close(); enc.wait()

if __name__ == "__main__":
    main()
