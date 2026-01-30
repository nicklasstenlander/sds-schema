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
JSON_FILE = "Aktiviteter 2026-01-30-2.json" 

TZ = pytz.timezone("Europe/Stockholm")

# TEST-LÄGE (Ändra till False för live-drift)
TEST_MODE = True

if TEST_MODE:
    now = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ) # Måndag test
else:
    now = datetime.now(TZ)

TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# =========================
# 2️⃣ Ladda in Personal/Salar
# =========================
room_map = {}
teacher_map = {}

print(f"⏳ Läser in {JSON_FILE}...")
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        for event in data.get("events", []):
            # Vi sparar namnet i små bokstäver för att lättare matcha
            name = event.get("name", "").strip()
            if name:
                room_map[name.lower()] = event.get("place", "Light Box")
                teacher_map[name.lower()] = event.get("instructorsName", "Instruktör")
    print(f"✅ Inläst! Hittade {len(room_map)} kurser.")
except Exception as e:
    print(f"❌ Fel vid inläsning av JSON: {e}")

# =========================
# 3️⃣ Hämta tider & Matcha
# =========================
daily_schedule = []

try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=15)
    gcal = Calendar.from_ical(resp.content)
    
    for component in gcal.walk('VEVENT'):
        # Rensa namnet ordentligt
        summary_raw = str(component.get('summary'))
        summary = summary_raw.replace("Kurs: ", "").strip()
        
        start_dt = component.get('dtstart').dt
        end_dt = component.get('dtend').dt
        
        if isinstance(start_dt, datetime):
            start_dt = start_dt.astimezone(TZ)
            if start_dt.date() == TARGET_DATE:
                
                # Sök i kartan med små bokstäver
                search_name = summary.lower()
                location = room_map.get(search_name, "Light Box")
                teacher = teacher_map.get(search_name, "Instruktör")
                
                # Om vi fortfarande inte hittat (kanske pga små skillnader i texten)
                if location == "Light Box" and teacher == "Instruktör":
                    for key in room_map:
                        if key in search_name or search_name in key:
                            location = room_map[key]
                            teacher = teacher_map[key]
                            break

                daily_schedule.append({
                    'course': summary,
                    'time': f"{start_dt.strftime('%H:%M')}–{end_dt.astimezone(TZ).strftime('%H:%M')}",
                    'raw_time': start_dt.strftime('%H:%M'),
                    'place': location,
                    'teacher': teacher
                })
except Exception as e:
    print(f"❌ iCal-fel: {e}")

daily_schedule.sort(key=lambda x: x["raw_time"])

# =========================
# 4️⃣ HTML (Samma design som innan)
# =========================
# ... (resten av HTML-koden från föregående svar)
