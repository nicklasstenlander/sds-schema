import requests
from icalendar import Calendar
from datetime import datetime, date
import pytz
import html
import os
import sys

# =========================
# 1️⃣ Konfiguration
# =========================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical" 
TZ = pytz.timezone("Europe/Stockholm")
now = datetime.now(TZ)
TARGET_DATE = now.date() 

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# --- HÅRDKODAD SALMAPPNING (Den enda pålitliga källan för HT25-salar) ---
LOCATION_MAP = {
    # Dessa rader måste uppdateras manuellt om schemat ändras!
    "Jazz Kids 5 - 6": "Light Box",
    "Commercial Hiphop 13+": "Black Box",
    "AP Step 2 Jazz": "Light Box",
    "AP Street/Commercial Step 1 & 2": "Black Box",
    "AT Contemporary": "Light Box", 
    "AT Commercial/Street": "Black Box",
    "AP Jazz Step 1": "Light Box",
    # Lägg till fler kurser här vid behov...
}

# =========================
# 2️⃣ Hämta & Analysera iCal-data
# =========================
print(f"⏳ Hämtar iCal-schema för {today_label}...")
try:
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; InfoScreen/1.0)'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    gcal = Calendar.from_ical(resp.content)
except Exception as e:
    print(f"❌ Kunde inte hämta eller tolka iCal-flödet: {e}")
    # Skapa tom fil för att undvika GitHub Action-fel
    with open("index.html", "w", encoding="utf-8") as f:
         f.write(f"<h1>FEL: KAN INTE HÄMTA SCHEMA! ({datetime.now(TZ).strftime('%H:%M')})</h1>")
    sys.exit(1)

daily_schedule = []

for component in gcal.walk():
    if component.name == "VEVENT":
        summary = str(component.get('summary'))
        
        start_dt = component.get('dtstart').dt
        end_dt = component.get('dtend').dt
        
        # 1. Filtrera på dagens datum
        event_date = start_dt.date() if isinstance(start_dt, datetime) else start_dt
        
        # Vi inkluderar bara händelser med tid (inte heldagshändelser)
        if event_date == TARGET_DATE and isinstance(start_dt, datetime):
            
            # 2. Hämta Salkonfiguration
            location = LOCATION_MAP.get(summary, "!!! SAKNAR SAL !!!")
            
            # 3. Filtrera bort händelser som inte är i en känd sal
            if location == "!!! SAKNAR SAL !!!":
                continue # Hoppa över kurser som inte är mapplitterade
                
            start_time_str = start_dt.strftime('%H:%M')
            end_time_str = end_dt.strftime('%H:%M')
            
            # OBS: iCal-feeden innehåller INTE instruktörsnamn.
            # Vi kan lägga till en statisk instruktörs-mappning här om det behövs,
            # annars får fältet vara tomt.
            teacher_name = "" 
            
            daily_schedule.append({
                'course': summary,
                'time': f"{start_time_str}–{end_time_str}",
                'raw_time': start_time_str,
                'place': location,
                'teacher': teacher_name
            })
            
print(f"🟢 Hittade {len(daily_schedule)} klasser för {today_label}.")

# =========================
# 3️⃣ Sortera & Skapa HTML (Återanvänder din kod)
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
        # Ersätt instruktörsnamnet med en placeholder om det är tomt (från iCal)
        teacher_display = html.escape(r['teacher']) if r['teacher'] else "Instruktör saknas"

        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p class="time">{html.escape(r['time'])}</p>
            <p class="teacher">{teacher_display}</p>
        </div>
        """
    return html_cards

# (Resten av din HTML-struktur är oförändrad)
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
