import json, re, html
M = json.load(open("media.json"))
src_main = open("eng_scenes.py").read(); src_reel = open("reel_cr.py").read()
def clean(a):
    a = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a or ""))).strip()
    a = re.sub(r"https?://(www\.)?flickr\.com/people/([^/ ]+)/?", r"\2 (Flickr)", a)
    return a[:45]
def grouped(keys):
    g = {}
    for k in keys:
        lic = M[k]["lic"].replace("Attribution", "CC BY 4.0") or "CC"
        a = "Fanny Schertzer (derivative: CHUCAO)" if k == "messi" else clean(M[k]["artist"]); g.setdefault(lic, [])
        if a not in g[lic]: g[lic].append(a)
    return "\n".join(f"{lic}: " + ", ".join(v) for lic, v in sorted(g.items(), key=lambda x: -len(x[1])))
main_keys = [k for k in M if re.search(r'"%s"' % re.escape(k), src_main)] + ["v_thanks", "v_goals"]
main_keys = list(dict.fromkeys(main_keys))
def reel_keys(n):
    blk = src_reel.split(f"    if n == {n}:")[1].split("    if n == ")[0].split("return S")[0]
    ks = re.findall(r'(?:img|vid)\((?:0\.0|A\([^)]*\)), "?([A-Za-z0-9_]+)"?', blk)
    return [k for k in dict.fromkeys({"TH": "v_thanks", "GO": "v_goals"}.get(k, k) for k in ks) if k in M]
CREDIT_FOOT = ("Licences: creativecommons.org/licenses · Images were cropped, colour-graded and animated.\n"
               "Music & SFX: Mixkit (mixkit.co) — free licence.\n"
               "Independent documentary — not affiliated with or endorsed by Cristiano Ronaldo, his clubs, UEFA or FIFA.")

T = json.load(open("out/timeline.json"))
chap = ["0:00 Intro: the boy who left home at 12"]
names = {1: "The Island Boy (Madeira, 1985)", 2: "The Lisbon Test: Sporting CP at 12", 3: "Becoming CR7: Manchester United & Sir Alex Ferguson",
         4: "The Record Breaker: Real Madrid (451 goals)", 5: "New Frontiers: Juventus, Man United & Al Nassr",
         6: "For Portugal: Euro 2016 & Nations League", 7: "More Than Football: the CR7 brand"}
for s in T["segs"][1:]:
    t = s["card"][0]; chap.append(f"{int(t//60)}:{int(t%60):02d} {names[s['n']]}")

MAIN_DESC = f"""He left home at 12 with almost nothing. Today he's one of the most famous athletes on the planet — and football's first billionaire. ⚽👑

This is the full Cristiano Ronaldo story: from a working-class family on the small island of Madeira, to Sporting CP in Lisbon, to Manchester United and the legendary No. 7 shirt, record-breaking years at Real Madrid, Juventus, Al Nassr, Euro 2016 glory with Portugal — and how CR7 became a global brand.

👉 Subscribe to Founder Files — every legend has a story, and we're here to tell it.

⏱️ CHAPTERS
{chr(10).join(chap)}

💬 Team Ronaldo or Team Messi? Tell us in the comments!

In this video:
• Ronaldo's childhood in Funchal, Madeira, and why he left home at 12
• How a 2003 friendly vs Manchester United changed his life
• Sir Alex Ferguson, the No. 7 shirt and his first Ballon d'Or (2008)
• The world-record €94M move to Real Madrid — 451 goals in 438 games
• The Ronaldo vs Messi rivalry
• Juventus, the return to Man United and the move to Al Nassr in Saudi Arabia
• Euro 2016 and the UEFA Nations League with Portugal
• CR7 the brand: fashion, fragrances, hotels and endorsements

#CristianoRonaldo #CR7 #Ronaldo #Football #FounderFiles

—
🎞️ FOOTAGE & PHOTO CREDITS
Video and photos via Wikimedia Commons, used under their Creative Commons licences. Real Madrid C.F. official videos: CC BY 3.0.
{grouped(main_keys)}
{CREDIT_FOOT}"""

MAIN_TAGS = ["cristiano ronaldo", "ronaldo", "cr7", "cristiano ronaldo story", "ronaldo documentary", "cristiano ronaldo documentary",
 "ronaldo life story", "ronaldo biography", "how ronaldo became a billionaire", "ronaldo billionaire", "ronaldo net worth",
 "ronaldo childhood", "ronaldo madeira", "ronaldo sporting cp", "ronaldo manchester united", "ronaldo real madrid",
 "ronaldo juventus", "ronaldo al nassr", "ronaldo vs messi", "ronaldo euro 2016", "ronaldo motivation", "cr7 brand",
 "zero to billionaire", "football documentary", "founder files"]

REELS = {
 1: dict(titles=["He Left Home at Just 12… and Became a Legend 😳 #Shorts", "Ronaldo Left His Family at 12 to Chase One Dream #Shorts"],
         hook="At 12, Cristiano Ronaldo left his family on the island of Madeira to chase one dream in Lisbon. Life wasn't easy — but he refused to give up. ⚽",
         tags=["cristiano ronaldo", "ronaldo", "cr7", "ronaldo shorts", "ronaldo childhood", "ronaldo story", "ronaldo motivation",
               "ronaldo madeira", "ronaldo sporting", "football shorts", "motivation shorts", "never give up", "founder files"],
         hashtags="#Shorts #CristianoRonaldo #CR7 #Ronaldo #Football #Motivation #NeverGiveUp #Madeira"),
 2: dict(titles=["18 Years Old at Manchester United?! 🔴 Ronaldo's Rise #Shorts", "451 Goals in 438 Games?! Ronaldo Is Crazy 🤯 #Shorts"],
         hook="18 years old, the legendary No. 7 shirt at Manchester United, a €94M move to Real Madrid — then 451 goals in 438 games. 🤯",
         tags=["cristiano ronaldo", "ronaldo", "cr7", "ronaldo shorts", "ronaldo manchester united", "ronaldo real madrid",
               "ronaldo number 7", "ronaldo 451 goals", "sir alex ferguson", "ronaldo goals", "football shorts", "founder files"],
         hashtags="#Shorts #CristianoRonaldo #CR7 #ManchesterUnited #RealMadrid #Football #GOAT"),
 3: dict(titles=["How CR7 Became a Billion-Dollar Brand 💰 #Shorts", "Ronaldo's Secret Isn't Talent… It's This #Shorts"],
         hook="Even after winning almost everything, Cristiano Ronaldo kept getting better. Discipline, four leagues — and a name that became a global brand. 💰",
         tags=["cristiano ronaldo", "ronaldo", "cr7", "cr7 brand", "ronaldo business", "ronaldo billionaire", "personal brand",
               "ronaldo discipline", "ronaldo motivation", "ronaldo al nassr", "business shorts", "founder files"],
         hashtags="#Shorts #CristianoRonaldo #CR7 #PersonalBrand #Business #Discipline #Success"),
}
def reel_desc(n):
    r = REELS[n]
    return f"""{r['hook']}

🎬 Watch the full Cristiano Ronaldo story on Founder Files — link in the related video above.
👉 Subscribe for more stories of ambition, success and extraordinary journeys.

{r['hashtags']}

—
Credits (Wikimedia Commons, CC licences; Real Madrid C.F. videos CC BY 3.0):
{grouped(reel_keys(n))}
Music & SFX: Mixkit (free licence). Not affiliated with Cristiano Ronaldo or any club."""
IG = {1: "He left home at just 12 😳\n\nFrom a small island with almost nothing… to one of the greatest footballers in history. Full story on our YouTube — link in bio 🔗",
      2: "18 years old. The No. 7 shirt at Manchester United. Then 451 goals in 438 games for Real Madrid 🤯\n\nFull story on our YouTube — link in bio 🔗",
      3: "Talent got him started. Discipline made him CR7. 💰\n\nHow Ronaldo turned his name into a global brand — full story on our YouTube, link in bio 🔗"}
IGTAGS = "#cristianoronaldo #cr7 #ronaldo #football #soccer #footballreels #motivation #success #goat #founderfiles"

def tagstr(t): return ", ".join(t)
L = ["# Cristiano Ronaldo — YouTube & Reels upload pack (SEO)", "",
 "Channel name: **Founder Files** (as said in the narration). Every title, description and tag list below fits YouTube's limits — lengths are noted.",
 "Upload tips: set the category to **Sports**. Add the 7 chapter timestamps exactly as written (the first one must be 0:00). Pin the Team Ronaldo vs Team Messi question as a comment.",
 "For Shorts: keep #Shorts in the title or description. Use YouTube's **Related video** field on each Short to link the main video.", "",
 "---", "## MAIN VIDEO (7:49 · 16:9 · `cristiano_ronaldo/Cristiano_Ronaldo_Story_1080p.mp4`)", "",
 "**Thumbnail:** `Thumbnail_Zero_to_Billionaire_1280x720.jpg` (A/B test with `Thumbnail_1280x720.jpg` using YouTube's Test & Compare)", "",
 "### Title (pick one — #1 matches the Zero → Billionaire thumbnail)"]
for i, t in enumerate(["From Zero to Billionaire: The Cristiano Ronaldo Story",
                       "Cristiano Ronaldo: The Boy Who Left Home at 12 (Full Story)",
                       "How Cristiano Ronaldo Went From Poor Island Boy to Billionaire Legend"], 1):
    L.append(f"{i}. {t}  _({len(t)} chars)_")
L += ["", f"### Description  _({len(MAIN_DESC)}/5000 chars)_", "```", MAIN_DESC, "```", "",
      f"### Tags  _({len(tagstr(MAIN_TAGS))}/500 chars)_", "```", tagstr(MAIN_TAGS), "```", ""]
covers = {1: "Cover_Reel_Part1_1080x1920.jpg", 2: "Cover_Reel_Part2_1080x1920.jpg", 3: "Cover_Reel_Part3_1080x1920.jpg"}
for n in (1, 2, 3):
    r = REELS[n]; d = reel_desc(n)
    L += ["---", f"## REEL PART {n} (`cristiano_ronaldo_reels/Ronaldo_Reel_Part{n}.mp4` · cover `{covers[n]}`)", "",
          "### YouTube Shorts title (pick one)"] + [f"{i}. {t}  _({len(t)} chars)_" for i, t in enumerate(r["titles"], 1)] + \
         ["", f"### YouTube Shorts description  _({len(d)}/5000 chars)_", "```", d, "```", "",
          f"### Tags  _({len(tagstr(r['tags']))}/500 chars)_", "```", tagstr(r["tags"]), "```", "",
          "### Instagram / TikTok caption", "```", IG[n] + "\n\n" + IGTAGS + "\n\n📸 Credits: see pinned comment (paste the credit lines above).", "```", ""]
L += ["---", "### Fact check before publishing",
      "- **\"Football's first billionaire\" / $1.4B:** this is Bloomberg's October 2025 estimate. Check that it is still current.",
      "- **International retirement in November 2026:** this is from your narration in the main video. I could not confirm it, so check it before publishing."]
out = "\n".join(L) + "\n"
open("/home/user/Sumankk022/video_output/CRISTIANO_RONALDO_TITLES_DESCRIPTIONS_TAGS.md", "w").write(out)
print(len(MAIN_DESC), len(tagstr(MAIN_TAGS)), [len(reel_desc(n)) for n in (1,2,3)], [len(tagstr(REELS[n]['tags'])) for n in (1,2,3)])
