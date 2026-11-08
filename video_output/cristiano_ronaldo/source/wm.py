import json, sys, time, urllib.request, urllib.parse
UA = "FounderFilesBot/1.0 (https://github.com/sumankk022; documentary research)"
API = "https://commons.wikimedia.org/w/api.php"
def get(url, tries=5):
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60)
            return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                w = min(int(e.headers.get("retry-after") or 10) + 2, 45); print(f"  429, wait {w}s", file=sys.stderr); time.sleep(w); continue
            raise
    raise RuntimeError("gave up " + url)
def api(**p):
    p.update(format="json"); return json.loads(get(API + "?" + urllib.parse.urlencode(p)))
def search(q, n=20):
    d = api(action="query", list="search", srsearch=q, srnamespace=6, srlimit=n)
    return [x["title"] for x in d["query"]["search"]]
def info(titles):
    out = {}
    for i in range(0, len(titles), 40):
        d = api(action="query", titles="|".join(titles[i:i+40]), prop="imageinfo", iiprop="url|size|extmetadata|mime", iiurlwidth=2400)
        for p in d["query"]["pages"].values():
            if "imageinfo" not in p: continue
            ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
            g = lambda k: m.get(k, {}).get("value", "")
            out[p["title"]] = dict(url=ii["url"], thumb=ii.get("thumburl"), w=ii["width"], h=ii["height"], mime=ii["mime"],
                lic=g("LicenseShortName"), artist=g("Artist"), desc=g("ImageDescription")[:200], date=g("DateTimeOriginal")[:40], dur=ii.get("duration"))
    return out
if __name__ == "__main__":
    res = {}
    for q in sys.argv[2:]:
        for t in search(q): res.setdefault(t, q)
        time.sleep(1)
    I = info(list(res))
    json.dump(I, open(sys.argv[1], "w"), indent=1)
    import re
    for t, v in I.items():
        print(f"{v['w']}x{v['h']} {v['lic'][:14]:14} {t[5:90]} | {re.sub('<[^>]+>','',v['date'])[:20]}")
