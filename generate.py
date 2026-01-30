import requests
import json
import os
from icalendar import Calendar
from datetime import datetime
import pytz
import html

# =========================
# 1️⃣ Inställningar
# =========================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
# Här använder vi din senaste fil:
JSON_FILE = "Aktiviteter 2026-01-30-2.json" 

TZ = pytz.timezone("Europe/Stockholm")

# TEST-LÄGE (Ändra till False för live-drift)
TEST_MODE = True

if TEST_MODE:
    # Vi testar med måndagen den 2 februari 2026
    now = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ)
else:
    now = datetime.now(TZ)

TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# =========================
# 2️⃣ Ladda in Personal/Salar från JSON
# =========================
room_map = {}
teacher_map = {}

print(f"⏳ Läser in personal- och salsinfo från {JSON_FILE}...")
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for event in data.get("events", []):
            name = event.get("name", "").strip()
            if name:
                room_map[name] = event.get("place", "Light Box")
                teacher_map[name] = event.get("instructorsName", "Instruktör")
    print(f"✅ Klart! Hittade information om {len(room_map)} kurser.")
except Exception as e:
    print(f"⚠️ Kunde inte läsa JSON-filen: {e}")

# =========================
# 3️⃣ Hämta tider från iCal
# =========================
daily_schedule = []
print(f"⏳ Hämtar schema för {TARGET_DATE}...")

try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=15)
    gcal = Calendar.from_ical(resp.content)
    
    for component in gcal.walk('VEVENT'):
        summary = str(component.get('summary')).replace("Kurs: ", "").strip()
        start_dt = component.get('dtstart').dt
        end_dt = component.get('dtend').dt
        
        if isinstance(start_dt, datetime):
            start_dt = start_dt.astimezone(TZ)
            if start_dt.date() == TARGET_DATE:
                # Mappning med fallback om kursnamnet skiljer sig lite
                location = room_map.get(summary, "Light Box")
                teacher = teacher_map.get(summary, "Instruktör")
                
                daily_schedule.append({
                    'course': summary,
                    'time': f"{start_dt.strftime('%H:%M')}–{end_dt.astimezone(TZ).strftime('%H:%M')}",
                    'raw_time': start_dt.strftime('%H:%M'),
                    'place': location,
                    'teacher': teacher
                })
except Exception as e:
    print(f"❌ Fel vid iCal-hämtning: {e}")

daily_schedule.sort(key=lambda x: x["raw_time"])

# =========================
# 4️⃣ Bygg HTML (Döljer tomma kolumner)
# =========================
light_box = [c for c in daily_schedule if c["place"] == "Light Box"]
black_box = [c for c in daily_schedule if c["place"] == "Black Box"]
others = [c for c in daily_schedule if c["place"] not in ["Light Box", "Black Box"]]

def render_col(title, classes, is_other=False):
    # Logik: Om kolumnen "Övriga" är tom, returnera inget (döljer den)
    if is_other and not classes: return ""
    
    cards = ""
    if not classes:
        cards = '<p style="text-align:center; color:#999; margin-top:40px;">Inga fler lektioner</p>'
    else:
        for c in classes:
            # Visa bara sal-taggen i kolumnen "Övriga"
            room_info = f"<div class='room-tag'>{c['place']}</div>" if is_other else ""
            cards += f"""
            <div class="card">
                <div class="time">{c['time']}</div>
                <div class="name">{html.escape(c['course'])}</div>
                <div class="teacher">{html.escape(c['teacher'])}</div>
                {room_info}
            </div>"""
    
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

html_out = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #fff; margin: 0; padding: 25px; }}
        h1 {{ text-align: center; margin: 0; font-size: 3rem; font-weight: 900; text-transform: uppercase; }}
        .date {{ text-align: center; color: #555; font-size: 1.4rem; margin-bottom: 30px; }}
        .wrapper {{ display: flex; gap: 20px; justify-content: center; }}
        .column {{ flex: 1; min-width: 300px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-top: 0; font-size: 1.8rem; }}
        .card {{ background: #f4d1ce; padding: 18px; border-radius: 15px; margin-bottom: 20px; border-left: 12px solid #ee7a9f; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .time {{ font-weight: bold; font-size: 1.3rem; color: #000; }}
        .name {{ font-size: 1.5rem; font-weight: 800; margin: 6px 0; line-height: 1.1; }}
        .teacher {{ font-style: italic; font-size: 1.1rem; color: #333; }}
        .room-tag {{ display: inline-block; background: #fff; padding: 3px 10px; border-radius: 6px; font-size: 0.9rem; margin-top: 10px; font-weight: bold; border: 1px solid #ee7a9f; }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <div class="date">{today_label}</div>
    <div class="wrapper">
        {render_col("Light Box", light_box)}
        {render_col("Black Box", black_box)}
        {render_col("Övriga lokaler", others, True)}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("🚀 index.html har genererats med den nya listan!")
