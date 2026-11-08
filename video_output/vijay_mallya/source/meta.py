"""print shots, used photos, chapter list; with --parts KEY.. print chunk ids (of 32) touching those image keys"""
import sys, importlib.util, json
argv = sys.argv[1:]
spec = importlib.util.spec_from_file_location("eng", "engine.py"); E = importlib.util.module_from_spec(spec)
sys.argv = ["engine.py", "--still"]; spec.loader.exec_module(E)
def keys_of(s):
    ks = set()
    if s.get("key"): ks.add(s["key"])
    for f in ("bgkey", "bg"):
        if isinstance(s.get(f), str) and s[f] in E.IMGS: ks.add(s[f])
    for it in s.get("items", []) or []:
        if isinstance(it, tuple) and isinstance(it[0], str) and it[0] in E.IMGS: ks.add(it[0])
    return ks
if argv and argv[0] == "--used":
    used = sorted(set().union(*[keys_of(s) for s in E.S]) | {"a330c", "ubcity"})
    print(json.dumps(used))
elif argv and argv[0] == "--chapters":
    print("0:00 Intro: the King of Good Times")
    for c, s in zip(E.TL["chapters"], E.SEGS[1:]):
        t = s["card"][0]; print(f"{int(t // 60)}:{int(t % 60):02d} Chapter {c['n']}: {c['title']}")
else:
    for s in E.S: print(f"{s['t0']:7.2f}-{s['t1']:7.2f} {s['kind']:6s} {sorted(keys_of(s)) or s.get('src', '')}")
