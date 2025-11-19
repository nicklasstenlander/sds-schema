import requests
from datetime import datetime, date
import pytz
import html
import json
import sys

# =========================
# 1️⃣ Konfiguration
# =========================
ORG = "sollentunadans"
PW = "" # Lägg in ditt lösenord om det behövs, annars tomt
# Sortera direkt i API-anropet för att få snyggare data, men vi sorterar även i Python
URL = f"https://dans.se/api/public/events/?org={ORG}&pw={PW}"

TZ = pytz.timezone("Europe/Stockholm")

VECKODAGAR = [
    "Måndag", "Tisdag", "Onsdag",
    "Torsdag", "Fredag", "Lördag", "Söndag"
]
MÅNADER = [
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december"
]

def parse_date(d):
    """Försök parsa 'YYYY-MM-DD' till date-objekt, annars None."""
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return None

# =========================
# 2️⃣ Hämta data från CogWork
# =========================
print(f"⏳ Hämtar data från {URL}...")
try:
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"❌ Fel vid hämtning av data: {e}")
    sys.exit(1)

events = data.get("events", [])
print(f"📥 Hämtade totalt {len(events)} event från API.")

now = datetime.now(TZ)
today_date = now.date()
today_str = today_date.strftime("%Y-%m-%d") # För att matcha mot exakta datum-listor
today_dow = now.weekday()  # 0=mån, 6=sön
today_dow_api = today_dow + 1 # API kör 1-7

today_label = f"{VECKODAGAR[today_dow]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

debug_rows = []   
filtered = []     
found_places = set() # För att se vilka salar som faktiskt finns i datat

for e in events:
    name = e.get("name", "Okänt namn")
    place = e.get("place", "") or ""
    # Städa rumsnamnet (ta bort onödiga mellanslag)
    place_clean = place.strip()
    found_places.add(place_clean)
    
    teacher = e.get("instructorsName", "") or ""

    sched = e.get("schedule", {}) or {}
    start_info = sched.get("start", {}) or {}
    end_info = sched.get("end", {}) or {}

    start_time = (start_info.get("time") or "")[:5]  # HH:MM
    end_time = (end_info.get("time") or "")[:5]

    # --- LOGIK FÖR DATUM ---
    # CogWork skickar ofta med en lista "dates" med alla datum kursen går.
    # Detta är säkrare än att gissa baserat på start/slut-datum.
    specific_dates = sched.get("dates", [])
    
    is_today = False
    method = "unknown"

    if specific_dates and isinstance(specific_dates, list):
        # Alternativ A: APIet ger oss exakta datum. Vi kollar om idag är med.
        if today_str in specific_dates:
            is_today = True
            method = "exact_date_match"
        else:
            is_today = False
            method = "exact_date_miss"
    else:
        # Alternativ B: Fallback på din gamla logik (Veckodag + Inom intervall)
        day_of_week = start_info.get("dayOfWeek")
        start_date_str = start_info.get("date")
        end_date_str = end_info.get("date")
        
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        # Matchar veckodag?
        try:
            dow_match = int(day_of_week) == today_dow_api
        except (TypeError, ValueError):
            dow_match = False

        # Inom datumintervall?
        in_term = False
        if start_date and end_date:
            in_term = (start_date <= today_date <= end_date)
        elif start_date:
            in_term = (today_date >= start_date)
        
        if dow_match and in_term:
            is_today = True
            method = "interval_match"
        else:
            method = "interval_miss"

    # --- FILTRERING ---
    # Vi skiter i "showing"-flaggan. Om klassen är schemalagd idag, ska den visas.

    debug_info = {
        "name": name,
        "place": place_clean,
        "is_today": is_today,
        "method": method,
        "start_time": start_time
    }
    debug_rows.append(debug_info)

    if not is_today:
        continue

    # --- SALSKONTROLL ---
    # Normalisera för jämförelse (små bokstäver)
    p_lower = place_clean.lower()
    
    # Acceptera variationer av rumsnamn
    valid_lightbox = "light box" in p_lower or "lightbox" in p_lower
    valid_blackbox = "black box" in p_lower or "blackbox" in p_lower

    final_place_name = ""
    if valid_lightbox:
        final_place_name = "Light Box"
    elif valid_blackbox:
        final_place_name = "Black Box"
    else:
        # Ignorera andra salar
        continue

    filtered.append({
        "time": f"{start_time}–{end_time}" if start_time and end_time else start_time,
        "raw_time": start_time, # För sortering
        "course": name,
        "teacher": teacher,
        "place": final_place_name, # Använd det snygga namnet
    })

print(f"🔎 Hittade salar i datat idag (oavsett filter): {list(found_places)}")
print(f"🟢 Hittade {len(filtered)} klasser för {today_label} efter filtrering.")

# =========================
# 4️⃣ Sortera & gruppera
# =========================
filtered.sort(key=lambda x: x["raw_time"])

light_box_rows = [f for f in filtered if f["place"] == "Light Box"]
black_box_rows = [f for f in filtered if f["place"] == "Black Box"]

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
# 5️⃣ Skapa HTML
# =========================
html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="600">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schema {ORG}</title>
    <style>
        body {{
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #000;
            margin: 0;
            padding: 2rem;
            box-sizing: border-box;
        }}
        h1 {{
            text-align: center;
            font-weight: 700;
            font-size: 2.5rem;
            margin: 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        h2.date-line {{
            text-align: center;
            color: #555;
            font-weight: 400;
            margin-top: 0.5rem;
            margin-bottom: 2.5rem;
            font-size: 1.4rem;
            border-bottom: 1px solid #eee;
            padding-bottom: 1rem;
        }}
        .wrapper {{
            display: flex;
            justify-content: center;
            gap: 4rem;
            flex-wrap: wrap;
        }}
        .column {{
            flex: 1;
            min-width: 300px;
            max-width: 500px;
        }}
        .column h2 {{
            background-color: #000;
            color: #fff;
            padding: 0.8rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 1.3rem;
            text-align: center;
            margin-bottom: 1.5rem;
            text-transform: uppercase;
        }}
        .class-card {{
            background-color: #f4f4f4; /* Ljusare grå för bättre kontrast */
            padding: 1.2rem;
            border-left: 6px solid #000; /* Accentfärg */
            margin-bottom: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .class-card h3 {{
            margin: 0 0 0.5rem 0;
            font-size: 1.2rem;
            font-weight: 700;
        }}
        .time {{
            font-weight: bold;
            font-size: 1.1rem;
            color: #333;
            margin: 0;
        }}
        .teacher {{
            font-style: italic;
            color: #666;
            margin: 0.2rem 0 0 0;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <h2 class="date-line">{today_label}</h2>
    
    <div class="wrapper">
        <div class="column">
            <h2>Light Box</h2>
            {render_box(light_box_rows)}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_box(black_box_rows)}
        </div>
    </div>

    </body>
</html>
"""

# =========================
# 6️⃣ Spara filer
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

with open("debug_schedule.json", "w", encoding="utf-8") as f:
    json.dump(debug_rows, f, indent=2, ensure_ascii=False)

print("✅ index.html uppdaterad")
