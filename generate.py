import requests
from datetime import datetime, date
import pytz
import html
import sys

# =========================
# 1️⃣ Konfiguration
# =========================
# Använder den publika JSON-API-slutpunkten för att hämta events
JSON_API_URL_BASE = "https://minaaktiviteter.se/api/public/events/"
ORG_CODE = "sollentunadans" 

TZ = pytz.timezone("Europe/Stockholm")
now = datetime.now(TZ)
TARGET_DATE_STR = now.strftime('%Y-%m-%d') 

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# --- AUTOMATISK HÄMTNING ---
# Salar och instruktörer hämtas nu dynamiskt från API:et.
# Endast kurser i icke-danslokaler (som Teatern) filtreras bort.
FALLBACK_LOCATION = "Light Box" # Används om 'place' saknas i API-datan
EXCLUDE_LOCATION_KEYWORDS = ["teatern", "biblioteket", "gymnastiksalen", "sporthallen", "online"]

# =========================
# 2️⃣ Hämta & Analysera JSON-data
# =========================
print(f"⏳ Hämtar JSON-schema för {today_label}...")

# Parametrar för att hämta alla events för dagens datum.
# regStatus=0 är avgörande för att inkludera de pågående (ej längre anmälningsbara) kurserna.
params = {
    "org": ORG_CODE,
    "regStatus": "0", 
    "minDate": TARGET_DATE_STR,
    "maxDate": TARGET_DATE_STR,
    "maxRows": "200", # Max antal rader att hämta
}

daily_schedule = []

try:
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; InfoScreen/1.0)'}
    resp = requests.get(JSON_API_URL_BASE, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    
    raw_events = data.get('events', [])
    
    for event in raw_events:
        summary = event.get('name', 'Kursnamn saknas')
        
        # 1. Hämta Sal (place)
        location = event.get('place')
        
        # Filtrera bort icke-aktuella lokaler/salar
        if location and any(keyword in location.lower() for keyword in EXCLUDE_LOCATION_KEYWORDS):
             continue 

        # NYTT: Fallback till Light Box om 'place' saknas i API:et
        if not location or location.strip() == "":
            location = FALLBACK_LOCATION

        # Konvertera salnamn till standardiserade format (Light Box/Black Box)
        # Detta är nödvändigt eftersom salnamnen i API:et kan variera (t.ex. "Light Box A" vs "Light Box")
        if "light box" in location.lower():
            location = "Light Box"
        elif "black box" in location.lower():
            location = "Black Box"
        else:
            # Om salnamnet varken är Light Box eller Black Box,
            # använder vi fallback-salen Light Box
            location = FALLBACK_LOCATION 
        
        # 2. Hämta Instruktör (instructorsName)
        instructor = event.get('instructorsName', 'Instruktör okänd')
        if not instructor or instructor.strip() == "":
             instructor = 'Instruktör okänd'
        
        # 3. Hämta Tid (schedule.occasions)
        occasions = event.get('schedule', {}).get('occasions', [])
        
        if occasions:
            occasion = occasions[0] 
            start_dt_str = occasion.get('startDateTime')
            end_dt_str = occasion.get('endDateTime')
            
            try:
                # Parsa tid till Stockholms tidszon
                start_dt = datetime.fromisoformat(start_dt_str.replace("Z", "+00:00")).astimezone(TZ)
                end_dt = datetime.fromisoformat(end_dt_str.replace("Z", "+00:00")).astimezone(TZ)
                
                start_time_str = start_dt.strftime('%H:%M')
                end_time_str = end_dt.strftime('%H:%M')
                time_range_str = f"{start_time_str}–{end_time_str}"
                
                daily_schedule.append({
                    'course': summary,
                    'time': time_range_str,
                    'raw_time': start_time_str,
                    'place': location,
                    'teacher': instructor
                })
            except Exception as e:
                print(f"⚠️ Kunde inte tolka datum/tid för {summary}: {e}")
                continue
        else:
             print(f"⚠️ Saknar tidsinformation för kurs: {summary}")
             continue

except requests.exceptions.HTTPError as errh:
    print(f"❌ HTTP-fel vid API-anrop: {errh}")
    with open("index.html", "w", encoding="utf-8") as f:
         f.write(f"<h1>FEL: KAN INTE HÄMTA SCHEMA VIA API! ({datetime.now(TZ).strftime('%H:%M')})</h1>")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"❌ Anslutningsfel: {e}")
    with open("index.html", "w", encoding="utf-8") as f:
         f.write(f"<h1>FEL: KAN INTE NÅ SCHEMA-API! ({datetime.now(TZ).strftime('%H:%M')})</h1>")
    sys.exit(1)

print(f"🟢 Hittade {len(daily_schedule)} klasser för {today_label} via JSON API.")

# =========================
# 3️⃣ Sortera & Skapa HTML
# =========================
filtered = daily_schedule
filtered.sort(key=lambda x: x["raw_time"] or "23:59")

light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

def render_box(rows):
    if not rows:
        return "<p style='color:#777; font-style:italic;'>Inga klasser i denna sal idag</p>"
    html_cards = ""
    for r in rows:
        teacher_display = html.escape(r['teacher']) if r['teacher'] and r['teacher'] != "Instruktör okänd" else "Instruktör okänd"

        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p class="time">{html.escape(r['time'])}</p>
            <p class="teacher">{teacher_display}</p>
        </div>
        """
    return html_cards

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
            /* Färg: #ee7a9f (Primär färg) */
            background-color: #ee7a9f; 
            color: #000;
            padding: 0.8rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 1.4rem;
            text-align: center;
        }}
        .class-card {{
            /* Färg: #f4d1ce (Sekundär färg) */
            background-color: #f4d1ce; 
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
        .time {{ font-weight: bold; }}
        .teacher {{ font-style: italic; }}
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
# 4️⃣ Spara HTML
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ index.html uppdaterad! ({today_label})")
