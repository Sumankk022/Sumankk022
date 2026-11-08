
# ================= shots =================
S = []
def shot(t0, kind, xf=0.35, **kw): S.append(dict(t0=t0, kind=kind, xf=xf, **kw))
def IMG(t0, key, layout="cover", g="warm", z=(1.02, 1.12), pan=((0, 0), (0, 0)), xf=0.35, tag=None, side="right", **kw):
    shot(t0, "img", xf=xf, key=key, layout=layout, g=g, z=z, pan=pan, tag=tag, side=side, credit=CRED(key), **kw)
def VID(t0, key, off=0.0, slow=1.0, g="neutral", xf=0.35, tag=None, **kw):
    shot(t0, "vid", xf=xf, src=f"vid/{key}.webm", off=off, slow=slow, g=g, tag=tag, credit=CRED(key), **kw)
def CARDSHOT(ch, bgkey, bgg="warm"):
    c = TL["chapters"][ch - 1]
    shot(CARD(ch), "card", xf=0.5, n=ch, title=c["title"], years=c["years"], bgkey=bgkey, bgg=bgg, flash=True)
TH = "v_thanks"; GO = "v_goals"

# ---------------------------------------------------------------- INTRO (ch 0)
a = lambda p, occ=0, edge="s", d=0.0: A(p, 0, occ, edge, d)
IMG(0.0, "trapiche", g="faded", z=(1.12, 1.02), pan=((0.2, 0.1), (0, 0)), xf=0.0, tag="SANTO ANTÓNIO  ·  FUNCHAL, MADEIRA")
VID(a("leaving home", d=-0.15), "v_takeoff", off=70.0, g="teal")
IMG(a("and dreaming", d=-0.15), "hero16", "side", side="right", g="neutral", z=(1.0, 1.06))
shot(a("sounds impossible", d=-0.2), "img", xf=0.25, key="euro16b", layout="cover", g="bw", z=(1.25, 1.35), pan=((0, -0.4), (0, -0.45)), tag=None,
     side="right", credit=CRED("euro16b"), dark=(0.45, 0.45, 0, 1))
PUNCH([(a("sounds"), "SOUNDS", WHITE), (a("impossible"), "IMPOSSIBLE?", RED)], a("but that's exactly", d=-0.1), size=170)
VID(a("but that's exactly", d=-0.1), TH, off=195.0, g="neutral", xf=0.0, flash=True)
TITLE(a("cristiano ronaldo"), a("today", d=-0.2), "CRISTIANO RONALDO", size=190, sub="FROM MADEIRA TO THE WORLD")
VID(a("today", d=-0.1), TH, off=221.5, g="neutral")
STACK([(a("millions of fans"), "MILLIONS OF FANS", WHITE), (a("countless records"), "COUNTLESS RECORDS", GOLD),
       (a("and a global brand"), "A GLOBAL BRAND", WHITE)], a("but his journey", d=-0.2), size=120)
VID(a("countless", d=-0.15), TH, off=346.0, g="neutral", dim=0.55)
VID(a("but his journey", d=-0.15), "v_statue", off=0.0, slow=1.1, g="warm", tag="MADEIRA, PORTUGAL")
IMG(a("and trust me", d=-0.15), "por26a", g="neutral", z=(1.15, 1.05), pan=((0, -0.2), (0, -0.2)), xf=0.25, dark=(1.0, 0.4, a("the story behind", d=-0.2), a("the story behind", d=0.3)))
TITLE(a("the story behind", d=0.0), a("is much more", d=0.6), "CR7", size=380, y=560, above="THE STORY BEHIND")
VID(a("is much more", d=0.5), GO, off=26.5, g="neutral")

IDENT = TL["ident"]
shot(IDENT[0], "ext", xf=0.35, src="vid/intro.mp4")

# ---------------------------------------------------------------- CH1 The Island Boy
a = lambda p, occ=0, edge="s", d=0.0: A(p, 1, occ, edge, d)
CARDSHOT(1, "laranjal")
VID(a("cristiano ronaldo was born", d=-0.1), "v_statue", off=9.0, slow=1.15, g="warm", xf=0.6, tag="FUNCHAL, MADEIRA")
YEAR(a("1985"), "1985")
PILL(a("february"), a("on a small", d=-0.2), "5 FEBRUARY 1985", W - 330, 160)
IMG(a("on a small", d=-0.1), "laranjal", g="warm", z=(1.02, 1.14), pan=((-0.4, 0), (0.4, 0)), tag="MADEIRA  ·  PORTUGAL")
IMG(a("he grew up", d=-0.15), "trapiche", g="faded", z=(1.15, 1.03), pan=((0.3, 0.2), (-0.2, 0.0)), tag="SANTO ANTÓNIO  ·  WHERE HE GREW UP")
VID(a("but from a very young age", d=-0.15), TH, off=296.5, slow=1.3, g="warm", dim=0.6)
PUNCH([(a("one obsession"), "ONE OBSESSION:", WHITE), (a("football.", edge="s"), "FOOTBALL", GOLD)], a("he spent hours", d=-0.15), size=150)
VID(a("he spent hours", d=-0.15), "v_train", off=36.0, g="warm")
VID(a("dreaming about", d=-0.15), "v_train", off=45.0, g="warm")
IMG(a("his talent was noticed", d=-0.15), "spafl", g="warm", z=(1.0, 1.15), pan=((0, -0.2), (0, 0.1)), tag="HIS SPORTING CP REGISTRATION  ·  1997/98")
IMG(a("sporting cp", d=-0.1), "alvalade", g="neutral", z=(1.02, 1.12), tag="SPORTING CP  ·  LISBON")
shot(a("but there was one big", d=-0.15), "img", xf=0.25, key="alvalade", layout="cover", g="bw", z=(1.12, 1.18), pan=((0, 0), (0, 0)), tag=None,
     side="right", credit=CRED("alvalade"), dark=(0.4, 0.4, 0, 1))
PUNCH([(a("one big"), "ONE BIG", WHITE), (a("challenge"), "CHALLENGE", RED)], a("the club was based", d=-0.15), size=170)
shot(a("the club was based", d=-0.15), "route", xf=0.35, bg="lisbon", t_b=a("lisbon"), t_line=a("far away"), t_age=a("12 years old", d=-0.3),
     credit=None)
HIDE.append((a("the club was based", d=-0.15), a("imagine leaving", d=-0.2)))
VID(a("imagine leaving", d=-0.15), "v_takeoff", off=118.0, g="faded")
IMG(a("that's exactly what he did"), "lisbon", g="warm", z=(1.0, 1.08), pan=((-0.3, 0), (0.3, 0)), tag="LISBON")

# ---------------------------------------------------------------- CH2 The Lisbon Test
a = lambda p, occ=0, edge="s", d=0.0: A(p, 2, occ, edge, d)
CARDSHOT(2, "lisbon")
IMG(a("life in lisbon", d=-0.1), "lisbon", g="cool", z=(1.12, 1.02), pan=((0.4, 0), (0, 0)), xf=0.6, tag="LISBON  ·  1997")
IMG(a("ronaldo was away", d=-0.15), "sp28", g="warm", z=(1.0, 1.12), pan=((0, -0.3), (0, 0)), tag="HIS SPORTING CP No. 28 SHIRT  ·  CLUB MUSEUM")
VID(a("but he had something", d=-0.15), TH, off=104.5, g="neutral", slow=1.15)
IMG(a("he hated", d=-0.12), "mu2008", g="bw", z=(1.15, 1.22), pan=((0.2, -0.2), (0.2, -0.2)), xf=0.15, dark=(0.5, 0.5, 0, 1))
PUNCH([(a("he hated"), "HE HATED", WHITE), (a("losing"), "LOSING.", RED)], a("he trained hard", d=-0.15), size=190)
IMG(a("he trained hard", d=-0.15), "rmtrain", g="warm", z=(1.0, 1.1), pan=((0.3, 0), (-0.2, 0)))
VID(a("improved his skills", d=-0.15), "v_train", off=21.0, g="warm")
IMG(a("in 2003", d=-0.1), "alvalade", g="warm", z=(1.12, 1.02), tag="ESTÁDIO JOSÉ ALVALADE  ·  AUGUST 2003")
YEAR(a("2003"), "2003")
IMG(a("and ronaldo absolutely", d=-0.15), "muscores", "side", side="right", g="neutral", z=(1.0, 1.06), flash=True)
VID(a("his speed", d=-0.15), GO, off=106.0, g="neutral")
STACK([(a("speed"), "SPEED", WHITE), (a("dribbling"), "DRIBBLING", GOLD), (a("and confidence"), "CONFIDENCE", WHITE)],
      a("caught the attention", d=-0.1), x=170, size=140, anchor="l")
IMG(a("caught the attention", d=-0.1), "ferguson", "side", side="right", g="warm", z=(1.0, 1.06))
LOWER3(a("legendary manager"), a("manchester united decided", d=-0.2), "SIR ALEX FERGUSON", "MANCHESTER UNITED MANAGER  ·  1986–2013")
IMG(a("manchester united decided", d=-0.15), "oldtraf", g="neutral", z=(1.02, 1.12), tag="OLD TRAFFORD  ·  MANCHESTER")
IMG(a("and suddenly", d=-0.15), "mu2006", g="neutral", z=(1.05, 1.15), pan=((0, -0.2), (0.1, -0.2)), tag="MANCHESTER UNITED  ·  2006")
IMG(a("but there was one more", d=-0.15), "oldtraf23", g="cool", z=(1.1, 1.15), dark=(0.8, 0.4, a("but there was one more"), a("surprise")))
shot(a("he was given", d=-0.15), "seven", xf=0.3, bg="mu2009", t_legends=a("previously worn"), flash=True)
HIDE.append((a("he was given", d=-0.1), a("that's when", d=-0.2)))
IMG(a("that's when", d=-0.15), "mu2009", "side", side="right", g="neutral", z=(1.0, 1.08))
TITLE(a("noticing"), a("noticing", d=2.0), "CR7", size=300, y=560, hide=True)

# ---------------------------------------------------------------- CH3 Becoming CR7
a = lambda p, occ=0, edge="s", d=0.0: A(p, 3, occ, edge, d)
CARDSHOT(3, "oldtraf")
IMG(a("when ronaldo first", d=-0.1), "muchelsea", g="neutral", z=(1.15, 1.05), pan=((0.2, -0.1), (0.1, -0.1)), xf=0.6, tag="MAN UTD vs CHELSEA  ·  2006")
IMG(a("fancy skills", d=-0.2), "muscores", g="neutral", z=(1.2, 1.3), pan=((0, -0.4), (0, -0.3)))
IMG(a("but he wasn't", d=-0.15), "mushev", "side", side="left", g="warm", z=(1.0, 1.07), tag="2007")
IMG(a("under sir alex", d=-0.15), "ferguson", g="warm", z=(1.05, 1.15), pan=((0, -0.3), (0, -0.3)))
VID(a("he developed into", d=-0.1), GO, off=104.0, g="neutral", dim=0.6)
PUNCH([(a("serious"), "GOALSCORING", WHITE), (a("goalscoring", d=0.2), "MACHINE", GOLD)], a("he improved", d=-0.15), size=170)
VID(a("he improved", d=-0.15), GO, off=176.0, g="neutral", dim=0.55)
STACK([(a("finishing"), "FINISHING", WHITE), (a("physical"), "PHYSICAL STRENGTH", GOLD), (a("and decision-making"), "DECISION-MAKING", WHITE)],
      a("and the results", d=-0.1), x=170, size=130, anchor="l")
IMG(a("and the results", d=-0.15), "mu2008", g="neutral", z=(1.05, 1.15), pan=((0.1, -0.2), (0.1, -0.2)), tag="MANCHESTER UNITED  ·  2008")
shot(a("during the", d=-0.15), "img", xf=0.3, key="moscowfans", layout="cover", g="warm", z=(1.05, 1.12), pan=((0, 0), (0, 0)), tag=None,
     side="right", credit=CRED("moscowfans"), dark=(0.45, 0.45, 0, 1))
STAT(a("scored 42", d=0.0), a("manchester united won", d=-0.15), 42, "GOALS", sub="2007–08  ·  ALL COMPETITIONS")
IMG(a("manchester united won", d=-0.15), "moscow41", g="warm", z=(1.03, 1.12), tag="UEFA CHAMPIONS LEAGUE FINAL  ·  MOSCOW, MAY 2008", flash=True)
PILL(a("premier league"), a("and at just", d=-0.1), "PREMIER LEAGUE ✓".replace(" ✓", ""), 520, 180)
PILL(a("champions league"), a("and at just", d=-0.1), "CHAMPIONS LEAGUE", 1400, 180)
IMG(a("and at just", d=-0.15), "ballon08", "side", side="right", g="warm", z=(1.0, 1.08))
STAT(a("23 years"), a("he had officially", d=-0.15), 23, "YEARS OLD", sub="FIRST BALLON D'OR  ·  2008", x=W * 0.3, hide=True)
IMG(a("he had officially", d=-0.15), "mu2008p", g="neutral", z=(1.02, 1.1), pan=((0, -0.3), (0, -0.2))) if "mu2008p" in MEDIA else \
    IMG(a("he had officially", d=-0.15), "mu2009", g="neutral", z=(1.15, 1.25), pan=((0, -0.4), (0, -0.3)))
IMG(a("but just when", d=-0.15), "oldtraf23", g="cool", z=(1.0, 1.1), pan=((-0.3, 0), (0.3, 0)))
IMG(a("real madrid wanted", d=-0.15), "bernabeu", g="neutral", z=(1.02, 1.12), flash=True, tag="SANTIAGO BERNABÉU  ·  MADRID")
TITLE(a("real madrid wanted"), a("and they were ready", d=-0.1), "REAL MADRID", size=230, sub="WANTED HIM")
VID(a("and they were ready", d=-0.15), TH, off=8.5, g="neutral")

# ---------------------------------------------------------------- CH4 The Record Breaker
a = lambda p, occ=0, edge="s", d=0.0: A(p, 4, occ, edge, d)
CARDSHOT(4, "bernabeu")
VID(a("in 2009", d=-0.1), TH, off=8.0, g="neutral", xf=0.6, tag="PRESENTATION  ·  SANTIAGO BERNABÉU, JULY 2009")
YEAR(a("2009"), "2009", dur=2.0)
STAT(a("94 million"), a("and this is where", d=0.1), 94, "MILLION EUROS", prefix="€", sub="WORLD-RECORD TRANSFER AT THE TIME", hide=True)
VID(a("went to another", d=-0.3), TH, off=43.0, g="neutral")
VID(a("he wasn't just", d=-0.15), GO, off=109.0, g="neutral")
PUNCH([(a("breaking"), "BREAKING", WHITE), (a("records"), "RECORDS", GOLD)], a("season after", d=-0.15), size=170)
VID(a("season after", d=-0.15), TH, off=326.5, g="neutral", tag="BICYCLE KICK vs JUVENTUS  ·  2018")
VID(a("he helped real madrid", d=-0.15), TH, off=362.0, g="neutral")
STAT(a("four champions"), a("and became the club's", d=-0.15), 4, "CHAMPIONS LEAGUE TITLES", sub="2014  ·  2016  ·  2017  ·  2018", hide=True)
VID(a("and became the club's", d=-0.15), GO, off=170.0, g="neutral", dim=0.4)
STAT(a("451"), a("he also won", d=-0.2), 451, "GOALS", x=W * 0.3, hide=True)
STAT(a("438"), a("he also won", d=-0.2), 438, "APPEARANCES", x=W * 0.7, color=WHITE, hide=False)
VID(a("he also won", d=-0.15), TH, off=344.5, g="neutral")
STAT(a("four more", d=0.1), a("during this period", d=-0.2), 5, "BALLON D'OR AWARDS", sub="2008  ·  2013  ·  2014  ·  2016  ·  2017", x=W * 0.68, size=280, hide=True)
IMG(a("during this period", d=-0.15), "mr2011", g="neutral", z=(1.1, 1.2), pan=((0, -0.3), (0, -0.2)), tag="PORTUGAL vs ARGENTINA  ·  2011")
shot(a("cristiano ronaldo vs", d=-0.2), "vs", xf=0.25, t_vs=a("vs"), flash=True,
     items=[("hero16", "RONALDO", a("cristiano"), -0.6), ("messi", "MESSI", a("lionel"), -0.5)],
     credit=f"{CRED('hero16')}  |  {CRED('messi')}")
HIDE.append((a("cristiano ronaldo vs", d=-0.2), a("two extraordinary", d=-0.1)))
IMG(a("two extraordinary", d=-0.15), "mr2011", g="neutral", z=(1.02, 1.1))
VID(a("fans debated", d=-0.15), TH, off=230.0, g="neutral")
VID(a("newspapers", d=-0.15), TH, off=281.0, g="neutral", tag=None)
VID(a("but after", d=-0.15), TH, off=383.0, g="neutral", slow=1.2)
PILL(a("9 incredible"), a("decided", d=0.5), "9 SEASONS  ·  2009–2018", W / 2, 180)

# ---------------------------------------------------------------- CH5 New Frontiers
a = lambda p, occ=0, edge="s", d=0.0: A(p, 5, occ, edge, d)
CARDSHOT(5, "allianz")
IMG(a("in 2018", d=-0.1), "juve19", "side", side="right", g="neutral", z=(1.0, 1.07), xf=0.6, tag="JUVENTUS  ·  TURIN, ITALY")
YEAR(a("2018"), "2018")
IMG(a("he continued", d=-0.15), "juveatl13", g="neutral", z=(1.05, 1.15), pan=((0, 0), (0.2, -0.1)))
PILL(a("league titles"), a("then", d=0.3), "2× SERIE A CHAMPION", W / 2, 180)
IMG(a("then", d=-0.15), "mu21new8", g="neutral", z=(1.02, 1.12), tag="THE RETURN  ·  OLD TRAFFORD, SEPTEMBER 2021", flash=True)
YEAR(a("2021"), "2021")
IMG(a("fans were excited", d=-0.15), "mu21new24", g="neutral", z=(1.05, 1.14))
IMG(a("but this time", d=-0.15), "mu21ev", "side", side="right", g="cool", z=(1.0, 1.06))
IMG(a("after disagreements", d=-0.15), "mu22bre22", g="bw", z=(1.08, 1.0))
YEAR(a("in 2022", d=0.1), "2022")
IMG(a("and then came", d=-0.15), "riyadh", g="cool", z=(1.1, 1.15), dark=(0.5, 0.5, 0, 1))
PUNCH([(a("another surprising"), "ANOTHER", WHITE), (a("surprising"), "SURPRISE", GOLD)], a("in january", d=-0.15), size=170)
IMG(a("in january", d=-0.1), "nassr40", g="neutral", z=(1.02, 1.12), tag="AL NASSR  ·  RIYADH, SAUDI ARABIA", flash=True)
YEAR(a("2023"), "2023")
IMG(a("many people", d=-0.15), "riyadh", g="warm", z=(1.0, 1.1), pan=((-0.3, 0), (0.3, 0)))
IMG(a("but ronaldo continued", d=-0.15), "nassrp", g="neutral", z=(1.02, 1.1))
IMG(a("scoring goals and", occ=1, d=-0.15), "nassr44", g="neutral", z=(1.05, 1.15))
IMG(a("his arrival", d=-0.15), "alawwal", g="warm", z=(1.0, 1.1), tag="AL-AWWAL PARK  ·  RIYADH")

# ---------------------------------------------------------------- CH6 For Portugal
a = lambda p, occ=0, edge="s", d=0.0: A(p, 6, occ, edge, d)
CARDSHOT(6, "por26a")
IMG(a("but there was something", d=-0.1), "por13", "side", side="right", g="neutral", z=(1.0, 1.07), xf=0.6, tag="PORTUGAL")
IMG(a("to win a major", d=-0.15), "por11", g="neutral", z=(1.05, 1.15), pan=((0, -0.2), (0.1, -0.2)))
IMG(a("in 2016", d=-0.1), "sdf", g="cool", z=(1.02, 1.12), tag="STADE DE FRANCE  ·  EURO 2016 FINAL, 10 JULY 2016")
YEAR(a("2016"), "2016")
PILL(a("against france"), a("but disaster", d=-0.1), "PORTUGAL  vs  FRANCE", W / 2, 180)
shot(a("but disaster", d=-0.15), "img", xf=0.15, key="euro16b", layout="cover", g="bw", z=(1.2, 1.3), pan=((0, -0.4), (0, -0.4)), tag=None,
     side="right", credit=CRED("euro16b"), dark=(0.45, 0.45, 0, 1), flash=True)
PUNCH([(a("disaster"), "DISASTER", RED), (a("struck"), "STRUCK.", WHITE)], a("ronaldo picked", d=-0.15), size=190)
IMG(a("ronaldo picked", d=-0.15), "euro16b", "side", side="right", g="bw", z=(1.0, 1.06))
IMG(a("however", d=-0.15), "euro16modric", "side", side="left", g="neutral", z=(1.0, 1.06))
IMG(a("and portugal eventually", d=-0.15), "euro16fans", g="warm", z=(1.02, 1.12), flash=True, tag="FANS IN LISBON  ·  EURO 2016")
TITLE(a("for the first time"), a("it was one of", d=-0.15), "EUROPEAN CHAMPIONS", size=170, sub="PORTUGAL  ·  EURO 2016", color=GOLD)
IMG(a("for the first time", d=-0.15), "hero16", g="warm", z=(1.2, 1.3), pan=((0, -0.5), (0, -0.45)), dark=(0.5, 0.5, 0, 1))
IMG(a("it was one of", d=-0.15), "hero16", "side", side="right", g="warm", z=(1.0, 1.06))
IMG(a("he also helped", d=-0.15), "nltrophy", "side", side="left", g="warm", z=(1.0, 1.08))
PILL(a("2019"), a("after representing", d=-0.2), "2019", 1250, 450)
PILL(a("2025"), a("after representing", d=-0.2), "2025", 1250, 560)
KICKER(a("uefa nations"), a("after representing", d=-0.2), "UEFA NATIONS LEAGUE", y=340)
IMG(a("after representing", d=-0.15), "por25a", g="neutral", z=(1.02, 1.12))
IMG(a("ronaldo announced", d=-0.15), "por26b", g="warm", z=(1.05, 1.15), pan=((0, -0.2), (0, -0.2)), tag="CROATIA vs PORTUGAL  ·  JULY 2026")
PILL(a("november"), a("retirement", d=2.0), "INTERNATIONAL RETIREMENT  ·  NOV 2026", W / 2, 180)

# ---------------------------------------------------------------- CH7 More Than Football + CTA
a = lambda p, occ=0, edge="s", d=0.0: A(p, 7, occ, edge, d)
CARDSHOT(7, "hotelf")
IMG(a("but here's", d=-0.1), "museucr7", g="warm", z=(1.02, 1.12), xf=0.6, tag="MUSEU CR7  ·  FUNCHAL", dark=(1.0, 0.4, a("he built", d=-0.3), a("a global brand")))
PUNCH([(a("a global brand", d=0.0), "A GLOBAL", WHITE), (a("brand.", d=0.0), "BRAND", GOLD)], a("from fashion", d=-0.2), size=170, y=540)
shot(a("from fashion", d=-0.15), "trip", bg="hotelf", dark_at=a("from fashion"), xf=0.3,
     items=[("museucr7", "FASHION & FRAGRANCES", "", a("fashion")), ("hotelf", "HOTELS", "PESTANA CR7  ·  FUNCHAL", a("hotels")),
            ("hotelm", "ENDORSEMENTS", "", a("major endorsements"))],
     credit=f"Photos: {_artist('museucr7')} · {_artist('hotelf')} · {_artist('hotelm')} — CC BY-SA 4.0 / CC0 · Wikimedia Commons")
IMG(a("cr7 became", d=-0.15), "hotelm", "side", side="right", g="warm", z=(1.0, 1.07), tag="PESTANA CR7  ·  MADRID")
VID(a("his massive", d=-0.15), TH, off=278.0, g="neutral")
VID(a("and that's what", d=-0.15), "v_statue", off=13.0, slow=1.1, g="warm")
IMG(a("he started as", d=-0.15), "laranjal", g="faded", z=(1.0, 1.1), pan=((0.3, 0), (-0.3, 0)))
shot(a("he left home", d=-0.15), "career", xf=0.3, bg="bernabeu", head="ONE CAREER  ·  SIX CLUBS",
     items=[("SPORTING CP", "2002", a("he left home")), ("MAN UNITED", "2003", a("faced")), ("REAL MADRID", "2009", a("competed")),
            ("JUVENTUS", "2018", a("the world's best")), ("MAN UNITED", "2021", a("and built")), ("AL NASSR", "2023", a("millions could"))])
HIDE.append((a("he left home", d=-0.1), a("people can", d=-0.2)))
IMG(a("people can", d=-0.15), "mr2011", g="neutral", z=(1.15, 1.05))
IMG(a("but one thing", d=-0.15), "por25b", g="bw", z=(1.1, 1.15), dark=(0.7, 0.5, 0, 1))
VID(a("cristiano ronaldo turned", d=-0.15), TH, off=302.5, g="neutral", dim=0.55, slow=1.2)
PUNCH([(a("talent"), "TALENT.", WHITE), (a("discipline"), "DISCIPLINE.", GOLD), (a("and ambition"), "AMBITION.", WHITE)],
      a("and perhaps", d=-0.15), size=150)
VID(a("and perhaps", d=-0.15), "v_statue", off=4.0, g="warm")
VID(a("you don't need", d=-0.15), TH, off=18.0, g="warm", dim=0.4, slow=1.3)
def _quote(layer, t, t0=a("you don't need", d=-0.1), t1=a("keep going", edge="e", d=0.4), tm=a("you just need", d=-0.1)):
    v1 = win(t, t0, t1, 0.5, 0.4); v2 = win(t, tm, t1, 0.5, 0.4)
    put(layer, text_img("“You don’t need to start with everything.", "pfi", 72, WHITE), W / 2, 440, v1, "mm")
    put(layer, text_img("You just need a dream.”", "pfi", 84, GOLD), W / 2, 560, v2, "mm")
ev(a("you don't need", d=-0.1), a("keep going", edge="e", d=0.4), _quote)
HIDE.append((a("you don't need", d=-0.15), a("keep going", edge="e", d=0.4)))
IMPACT7 = SEGS[7]["impact"]
VID(a("keep going", edge="e", d=0.3), TH, off=248.0, g="warm", dim=0.6, xf=0.6)
def _yt(layer, t, t0=a("keep going", edge="e", d=0.8), t1=IMPACT7):
    txt = "NOW, YOUR TURN..."; n_ = int(clamp((t - t0 - 0.1) / 1.0) * len(txt)) + 1
    s_ = 1.0 + 0.25 * eio((t - (t1 - 0.45)) / 0.45)
    if t0 <= t <= t1:
        put(layer, text_img(txt[:n_], "bb", 110, WHITE), W / 2 - text_w(txt, "bb", 110) * s_ / 2, 540, win(t, t0, t1, 0.2, 0.12), "lm", scale=s_)
ev(a("keep going", edge="e", d=0.8), IMPACT7, _yt)
shot(IMPACT7, "poll", xf=0.0, flash=True, t_comment=a("tell us"),
     items=[("euro16", "RONALDO", a("team ronaldo"), -0.7), ("messi", "MESSI", a("team messi"), -0.55)],
     credit=f"{CRED('euro16')}  |  {CRED('messi')}")
HIDE.append((IMPACT7, a("and if you enjoy", d=-0.2)))
shot(a("and if you enjoy", d=-0.15), "subscribe", xf=0.5, t_click=a("subscribe", d=0.35), bg="hero16")
shot(END0, "end", xf=0.6, bg="bernabeu")
