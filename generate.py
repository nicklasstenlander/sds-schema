import requests
from datetime import datetime
import pytz
import html
import json

# =========================
# 1️⃣ Konfiguration
# =========================
ORG = "sollentunadans"
PW = "" # Lägg in lösenordet här om det behövs
# Ny URL för att hämta DAGENS schema
# Vi skickar med dagens datum i queryn
TZ = pytz.timezone("Europe/Stockholm")
now = datetime.now(TZ)
today_date_str = now.strftime("%Y-%m-%d")

# NY URL: Hämtar det faktiska schemat för en given dag
URL = f"https://dans.se/api/public/schedule/?org={ORG}&date={today_date_str}&pw={PW}"

VECKODAGAR = [
    "Måndag", "Tisdag", "Onsdag",
    "Torsdag", "Fredag", "Lördag", "Söndag"
]
MÅNADER = [
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december"
]

today_dow = now.weekday()  # 0=mån, 6=sön
today_label = f"{VECKODAGAR[today_dow]} {now.day} {MÅNADER[now.month - 1]} {now.year}"


# =========================
# 2️⃣ Hämta data från CogWork Schedule API
# =========================
print(f"⏳ Hämtar dagens schema ({today_date_str}) från CogWork...")
try:
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"❌ Fel vid hämtning av schema: {e}")
    # Avsluta om API-anropet misslyckas
    exit(1)

# /schedule/ API:et returnerar en lista med 'events' direkt
schedule_items = data.get("schedule", [])
print(f"📥 Hittade {len(schedule_items)} schemaposter för idag.")

filtered = []     

for item in schedule_items:
    # Schedule-API:et har en annorlunda struktur jämfört med /events/
    name = item.get("name", "Okänd kurs")
    # Tiderna ligger på rotnivå i schedule-itemet
    start_time = item.get("startTime", "")[:5]
    end_time = item.get("endTime", "")[:5]
    place = item.get("place", "") or ""
    teacher = item.get("instructorsName", "") or ""

    # Städa rumsnamnet för jämförelse
    place_clean = place.strip().lower()

    # Vi behåller din strikta filtrering på Light Box och Black Box
    final_place_name = ""
    if "light box" in place_clean or "lightbox" in place_clean:
        final_place_name = "Light Box"
    elif "black box" in place_clean or "blackbox" in place_clean:
        final_place_name = "Black Box"
    else:
        # Ignorera alla andra salar, t.ex. "Teatern"
        continue

    # Vi inkluderar allt som matchar sal, eftersom /schedule/ bara returnerar aktiva lektioner
    filtered.append({
        "time": f"{start_time}–{end_time}" if start_time and end_time else start_time,
        "raw_time": start_time,
        "course": name,
        "teacher": teacher,
        "place": final_place_name,
    })

print(f"🟢 Hittade {len(filtered)} klasser för {today_label} efter filtrering på sal.")

# =========================
# 3️⃣ Sortera & gruppera per sal
# =========================
filtered.sort(key=lambda x: x["raw_time"])

light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

def render_box(rows):
    if not rows:
        return "<p style='color:#777; font-style:italic;'>Inga klasser i denna sal idag</p>"
    html_cards = ""
    for r in rows:
        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p class="time">{html.escape(r['time'])}</p>
            <p class="teacher">{html.escape(r['teacher'])}</p>
        </div>
        """
    return html_cards

# =========================
# 4️⃣ Skapa HTML
# =========================
# (HTML-koden är densamma som i din ursprungliga version, så den är utelämnad här för korthet)

html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="600">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dagens schema</title>
    <style>
        body {{
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #000;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-weight: 600;
            font-size: 2.5rem;
            margin-bottom: 0.2rem;
        }}
        h2.date-line {{
            text-align: center;
            color: #444;
            font-weight: 400;
            margin-top: 0.2rem;
            margin-bottom: 2rem;
            font-size: 1.3rem;
        }}
        .wrapper {{
            display: flex;
            justify-content: space-between;
            gap: 2%;
            margin-top: 1rem;
        }}
        .column {{
            width: 48%;
        }}
        .column h2 {{
            background-color: #a3c0b2;
            color: #000;
            padding: 0.8rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 1.4rem;
            text-align: center;
        }}
        .class-card {{
            background-color: #CDDCD1;
            padding: 1rem 1.2rem;
            border-radius: 1rem;
            margin-bottom: 1rem;
        }}
        .class-card h3 {{
            margin: 0;
            font-size: 1.2rem;
        }}
        .class-card p {{
            margin: 0.2rem 0;
            font-size: 1rem;
        }}
        .teacher {{
            font-style: italic;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <h2 class="date-line">{today_label}</h2>
    <div class="wrapper">
        <div class="column">
            <h2>Light Box</h2>
            {render_box(light_box)}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_box(black_box)}
        </div>
    </div>
</body>
</html>
"""

# =========================
# 5️⃣ Spara HTML
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

# Vi kan skippa debugfilen i denna iteration eftersom /schedule/ är mycket mer direkt
print(f"✅ index.html uppdaterad: Visar schemat för {today_label}")
