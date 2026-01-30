import requests
from icalendar import Calendar
from datetime import datetime, date
import pytz
import html
import sys

# =========================
# 1️⃣ Konfiguration & Test
# =========================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical" 
TZ = pytz.timezone("Europe/Stockholm")

# --- TEST-LÄGE: MÅNDAG 2 FEBRUARI 2026 ---
# För live-drift, ändra till: now = datetime.now(TZ)
now = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ) 
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# --- AUTOMATISKT GENERERAD MAPPNING FRÅN DIN FIL ---
LOCATION_MAP = {
    "Talent Program": "Light Box",
    "Performance Intermediate": "Black Box",
    "Education Program 1 (EP Y1)": "Light Box",
    "Advanced Program Step 2 (AP2)": "Light Box",
    "Education Program 2 (EP Y2)": "Light Box",
    "Tillval Talent Program - Technical Skills": "Light Box",
    "Advanced Program Step 1 (AP1)": "Light Box",
    "Education Program 3 (EP Y3)": "Light Box",
    "Performance Advanced": "Light Box",
    "Barndans med förälder 1-3": "Light Box",
    "Barndans 3-4": "Black Box",
    "Barndans 4-5": "Light Box",
    "Barndans 5-6": "Black Box",
    "Barnbalett 5-6 år": "Light Box",
    "Balett 7-9": "Light Box",
    "Balett 9+": "Black Box",
    "Tiktok 8-9": "Black Box",
    "Tiktok 10+": "Black Box",
    "Popstars 5-6": "Black Box",
    "Jazz Kids 5 - 6": "Light Box",
    "Juniorstreet 7 - 9": "Light Box",
    "Talent Program Jazz": "Black Box",
    "EP 1 Jazz": "Light Box",
    "AP Step 2 Jazz": "Black Box",
    "EP 2 Jazz": "Light Box",
    "EP 3 Jazz": "Light Box",
    "AP Jazz Step 1": "Black Box",
    "Jazz 16+": "Black Box",
    "EP 1 & EP2 Street/Commercial": "Light Box",
    "EP 3 Street/Commercial": "Light Box",
    "Commercial Jazz 11+": "Light Box",
    "AP Street/Commercial Step 1": "Light Box",
    "AP Street/Commercial Step 2": "Light Box",
    "Talent Program Street": "Black Box",
    "Streetdance 8-9": "Light Box",
    "Streetdance 10+": "Light Box",
    "Commercial Hiphop 13+": "Light Box",
    "EP 3 Contemporary": "Black Box",
    "EP 1 Contemporary": "Black Box",
    "EP 2 Contemporary": "Black Box",
    "AP Step 2 Contemporary": "Black Box",
    "AP Step 1 Contemporary": "Black Box",
    "Contemporary 11+": "Light Box",
    "Advanced Contemporary": "Black Box",
    "Jazz & Funk Open level": "Light Box",
    "Showjazz 7-9": "Light Box",
    "Showjazz 8-9": "Black Box",
    "EP 2 & EP 3 Technical Skills": "Black Box",
    "EP 1 Technical Skills": "Light Box",
    "AP Technical Skills Step 1 & 2": "Black Box",
    "Jazz/Balett 55+": "Light Box",
    "Danskalas": "Light Box",
    "Dance Camp V9": "Sollentuna Dans & Scenskola",
    "PROGRAM-WORKSHOPS V.9 DAG 1": "Black Box",
    "PROGRAM-WORKSHOPS V.9 DAG 2": "Black Box",
    "JANUARY WORKSHOPS TP+EP1": "Black Box",
    "ALLA JANUARY WORKSHOPS TP+EP1": "Black Box",
    "JANUARY WORKSHOPS EP2+EP3+AP": "Black Box",
    "ALLA JANUARY WORKSHOPS EP2+EP3+AP": "Black Box",
    "K-pop Kids 6-7": "Black Box",
    "Cheerdance 7-8": "Black Box",
    "K-pop 8-10": "Black Box",
    "K-pop 10+": "Black Box"
}

INSTRUCTOR_MAP = {
    "Talent Program": "Sofia, Hilda",
    "Performance Intermediate": "Sofia",
    "Tillval Talent Program - Technical Skills": "Sofia",
    "Performance Advanced": "Madde",
    "Barndans med förälder 1-3": "Madde",
    "Barndans 3-4": "Aline, Livia",
    "Barndans 4-5": "Madde",
    "Barndans 5-6": "Aline, Livia",
    "Barnbalett 5-6 år": "Madde",
    "Balett 7-9": "Alice",
    "Balett 9+": "Sofia",
    "Tiktok 8-9": "Elsa",
    "Tiktok 10+": "Lova",
    "Popstars 5-6": "Elsa",
    "Jazz Kids 5 - 6": "Hilda",
    "Juniorstreet 7 - 9": "Elsa",
    "Talent Program Jazz": "Sofia",
    "EP 1 Jazz": "Madde",
    "AP Step 2 Jazz": "Amanda",
    "EP 2 Jazz": "Amanda",
    "EP 3 Jazz": "Sofia",
    "AP Jazz Step 1": "Madde, Sofia, Amanda",
    "Jazz 16+": "Sofia",
    "Commercial Jazz 11+": "Amanda",
    "AP Street/Commercial Step 1": "Isabella, Jennifer",
    "AP Street/Commercial Step 2": "Isabella, Jennifer",
    "Talent Program Street": "Hilda",
    "Streetdance 8-9": "Matilda",
    "Streetdance 10+": "Alice",
    "Commercial Hiphop 13+": "Hilda",
    "EP 3 Contemporary": "Sofia",
    "EP 1 Contemporary": "Amanda",
    "EP 2 Contemporary": "Sofia",
    "AP Step 2 Contemporary": "Sofia",
    "AP Step 1 Contemporary": "Amanda, Sofia",
    "Contemporary 11+": "Hilda",
    "Advanced Contemporary": "Amanda",
    "Jazz & Funk Open level": "Hilda",
    "Showjazz 7-9": "Matilda",
    "Showjazz 8-9": "Amanda",
    "EP 2 & EP 3 Technical Skills": "Madde",
    "EP 1 Technical Skills": "Sofia",
    "AP Technical Skills Step 1 & 2": "Amanda",
    "Jazz/Balett 55+": "Madde",
    "PROGRAM-WORKSHOPS V.9 DAG 1": "Ellen Johansson",
    "JANUARY WORKSHOPS TP+EP1": "Amanda & Miranda",
    "JANUARY WORKSHOPS EP2+EP3+AP": "Mille & Miranda",
    "K-pop Kids 6-7": "Alice",
    "Cheerdance 7-8": "Elsa",
    "K-pop 8-10": "Lova",
    "K-pop 10+": "Elsa"
}

# =========================
# 2️⃣ Hämta & Analysera iCal
# =========================
try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    gcal = Calendar.from_ical(resp.content)
except Exception as e:
    sys.exit(1)

daily_schedule = []
for component in gcal.walk('VEVENT'):
    summary = str(component.get('summary')).replace("Kurs: ", "").strip()
    start_dt = component.get('dtstart').dt
    end_dt = component.get('dtend').dt
    
    if isinstance(start_dt, datetime):
        if start_dt.date() == TARGET_DATE:
            # Hämta info med fallback
            location = LOCATION_MAP.get(summary, "Light Box")
            teacher = INSTRUCTOR_MAP.get(summary, "Instruktör okänd")
            
            daily_schedule.append({
                'course': summary,
                'time': f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}",
                'raw_time': start_dt.strftime('%H:%M'),
                'place': location,
                'teacher': teacher
            })

# =========================
# 3️⃣ Sortera & Kolumnlogik
# =========================
daily_schedule.sort(key=lambda x: x["raw_time"])

light_box = [f for f in daily_schedule if f["place"] == "Light Box"]
black_box = [f for f in daily_schedule if f["place"] == "Black Box"]
others = [f for f in daily_schedule if f["place"] not in ["Light Box", "Black Box"]]

show_others = len(others) > 0

def render_col(rows, show_room=False):
    if not rows: return "<p class='empty'>Inga klasser</p>"
    cards = ""
    for r in rows:
        room_tag = f"<div class='room-tag'>{r['place']}</div>" if show_room else ""
        cards += f"""
        <div class="card">
            <div class="time">{r['time']}</div>
            <div class="name">{html.escape(r['course'])}</div>
            <div class="teacher">{html.escape(r['teacher'])}</div>
            {room_tag}
        </div>"""
    return cards

# =========================
# 4️⃣ HTML & CSS
# =========================
html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; margin-bottom: 5px; font-size: 2.5rem; }}
        .date-line {{ text-align: center; color: #555; font-size: 1.2rem; margin-bottom: 30px; }}
        .wrapper {{ display: flex; gap: 20px; justify-content: center; }}
        .column {{ flex: 1; min-width: 300px; }}
        h2 {{ background: #ee7a9f; padding: 15px; border-radius: 8px; text-align: center; margin-top: 0; }}
        .card {{ background: #f4d1ce; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 10px solid #ee7a9f; }}
        .time {{ font-weight: bold; font-size: 1.1rem; color: #333; }}
        .name {{ font-size: 1.3rem; font-weight: bold; margin: 5px 0; }}
        .teacher {{ font-style: italic; color: #444; }}
        .empty {{ text-align: center; color: #999; font-style: italic; }}
        .room-tag {{ background: #fff; display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-top: 10px; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <div class="date-line">{today_label}</div>
    <div class="wrapper">
        <div class="column">
            <h2>Light Box</h2>
            {render_col(light_box)}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_col(black_box)}
        </div>
        {f'<div class="column"><h2>Övriga</h2>{render_col(others, True)}</div>' if show_others else ''}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ Klar! Uppdaterad med exakt data från din JSON.")
