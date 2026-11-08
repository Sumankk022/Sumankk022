import json, sys, os, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__)); from wm import get, UA
D = {}
for f in ["ronaldo_imgs.json", "ctx.json", "ctx2.json"]: D.update(json.load(open(os.path.join(os.path.dirname(__file__), f))))
M = dict(l.split("=", 1) for l in open(sys.argv[1]).read().split("\n") if "=" in l)
out = {}
for k, sub in M.items():
    k, sub = k.strip(), sub.strip()
    hits = [t for t in D if sub.lower() in t.lower()]
    if not hits: print("MISSING", k, sub); continue
    t = sorted(hits, key=len)[0]; v = D[t]
    vid = v["mime"].startswith("video") or v["mime"].startswith("application/ogg")
    orig = v["url"].split("?")[0]; name = orig.rsplit("/", 1)[1]
    if vid:
        h = 1080 if v["h"] >= 1080 or v["w"] >= 1920 else 720
        url = orig.replace("/commons/", "/commons/transcoded/") + f"/{name}.{h}p.vp9.webm"; ext = ".webm"
    elif v["w"] > 960:
        tw = 1920 if v["w"] >= 1920 else (1280 if v["w"] >= 1280 else 960)
        tn = name if name.lower().endswith((".jpg", ".jpeg", ".png")) else name + ".jpg"
        url = orig.replace("/commons/", "/commons/thumb/") + f"/{tw}px-{tn}"; ext = os.path.splitext(tn)[1].lower()
    else:
        url = orig; ext = os.path.splitext(name)[1].lower()
    dst = ("vid/" if vid else "img/") + k + ext
    out[k] = dict(title=t, **v, file=dst)
    if os.path.exists(dst) and os.path.getsize(dst) > 1000: continue
    data = b''
    for i in range(3):
        try:
            data = get(url); open(dst, "wb").write(data); break
        except Exception as e:
            print("retry", k, e); time.sleep(5)
    print(k, len(data) // 1024, "KB", t[5:70], flush=True); time.sleep(9)
json.dump(out, open("media.json", "w"), indent=1)
