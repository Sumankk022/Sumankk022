import json,subprocess,re
I=json.load(open("imginfo.json"))
used=json.loads(subprocess.run(["python3","meta.py","--used"],capture_output=True,text=True).stdout.strip().splitlines()[-1])
chap=subprocess.run(["python3","meta.py","--chapters"],capture_output=True,text=True).stdout.strip()
ART={"mallya_wef":"World Economic Forum / Dana Smillie","mallya_goa1":"PIB, Ministry of Information & Broadcasting, Govt. of India",
"mallya_goa2":"PIB, Ministry of Information & Broadcasting, Govt. of India","gopinath":"Ranjit Bhaskar / Al Jazeera English","rcj":"David Castor",
"kftowers":"SerChevalerie","ubcity2":"Wikimedia Commons contributor","a320":"airbus777","tewin":"Peter O'Connor","rupee":"Monito","mallya_300":"Franciscojuanlago"}
lines=[]
for k in used:
    v=I[k]; a=ART.get(k) or re.sub(r"\s+"," ",v["artist"]).strip() or "Wikimedia Commons contributor"
    lines.append(f"• {a} — {v['lic']} — {v['page']}")
out=f"""VIJAY MALLYA — THE KING OF GOOD TIMES  ·  Founder Files

=== YOUTUBE CHAPTERS (paste into description) ===
{chap}

=== PHOTO CREDITS (required — paste into description) ===
Photos via Wikimedia Commons (licences as listed; GODL-India = Government Open Data Licence – India):
""" + "\n".join(lines) + """
Licences: https://creativecommons.org/licenses/ · GODL-India: https://data.gov.in/government-open-data-license-india
Photos were cropped, colour-graded and animated.

=== STOCK FOOTAGE, MUSIC & SFX ===
Stock footage, music and sound effects: Mixkit (mixkit.co) — Mixkit Free License (free for commercial use incl. YouTube, no attribution required).
Music: "Cat Walk" (Arulo), "Epical Drums 05" & "Epical Drums 03" (Grigoriy Nuzhny), "The Journey" (Ahjay Stelino),
"We Will Get It", "Vertigo", "Silent Descent", "Masking the Masters", "The Farewell" (Eugenio Mininni), "I Won't Surrender" (Michael Ramir C.).
Channel intro: Founder Files (own asset).

=== DISCLAIMER ===
This is an independent documentary based on publicly reported information. Allegations described are allegations made by
investigating agencies; Vijay Mallya has denied wrongdoing. Departure-board and permit graphics are illustrative.
Not affiliated with or endorsed by any company or person shown. Brand names are trademarks of their respective owners.
"""
open("CREDITS_AND_LICENSES.txt","w").write(out); print(out)
