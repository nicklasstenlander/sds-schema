import requests
from icalendar import Calendar
from datetime import datetime
import pytz
import html
import sys

# =========================
# 1️⃣ Konfiguration
# =========================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical" 
TZ = pytz.timezone("Europe/Stockholm")

# TEST-LÄGE: Måndag 2 februari 2026 (Ändra till False för live)
TEST_MODE = True
now = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ) if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# =========================
# 2️⃣ DIN DATA (Hårdkodad för 100% precision)
# =========================
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
    "K-pop Kids 6-7": "Black Box",
    "Cheerdance 7-8": "Black Box",
    "K-pop 8-10": "Black Box",
    "K-pop 10+": "Black Box"
}

INSTRUCTOR_MAP = {
    "Talent Program": "Sofia, Hilda",
    "Performance Intermediate": "Sofia",
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
    "K-pop Kids 6-7": "Alice",
    "Cheerdance 7-8": "Elsa",
    "K-pop 8-10": "Lova",
    "K-pop 10+": "Elsa"
}

# =========================
# 3️⃣ iCal-hämtning & Matchning (Fixad tidszon)
# =========================
daily_schedule = []
try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    gcal = Calendar.from_ical(resp.content)
    
    for component in gcal.walk('VEVENT'):
        summary = str(component.get('summary')).replace("Kurs: ", "").strip()
        
        # Hämta start- och sluttid
        dtstart = component.get('dtstart').dt
        dtend = component.get('dtend').dt
        
        if isinstance(dtstart, datetime):
            # Tvinga konvertering till Stockholms-tid oavsett hur filen ser ut
            start_local = dtstart.astimezone(TZ)
            end_local = dtend.astimezone(TZ)
            
            if start_local.date() == TARGET_DATE:
                
                # --- Matchning mot LOCATION_MAP ---
                location = "Light Box" 
                teacher = "Instruktör"
                
                for key in LOCATION_MAP:
                    if key.lower() in summary.lower() or summary.lower() in key.lower():
                        location = LOCATION_MAP[key]
                        teacher = INSTRUCTOR_MAP.get(key, "Instruktör")
                        break
                
                daily_schedule.append({
                    'course': summary,
                    'time': f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}",
                    'raw_time': start_local.strftime('%H:%M'),
                    'place': location,
                    'teacher': teacher
                })
except Exception as e:
    print(f"Fel: {e}")

# =========================
# 4️⃣ HTML & Design
# =========================
light_box = [c for c in daily_schedule if c["place"] == "Light Box"]
black_box = [c for c in daily_schedule if c["place"] == "Black Box"]
others = [c for c in daily_schedule if c["place"] not in ["Light Box", "Black Box"]]

def render_col(title, classes, is_other=False):
    if is_other and not classes: return ""
    cards = ""
    if not classes:
        cards = '<p style="text-align:center; color:#999; margin-top:40px;">Inga fler lektioner</p>'
    else:
        for c in classes:
            room_tag = f"<div class='room-tag'>{c['place']}</div>" if is_other else ""
            cards += f"""
            <div class="card">
                <div class="time">{c['time']}</div>
                <div class="name">{html.escape(c['course'])}</div>
                <div class="teacher">{html.escape(c['teacher'])}</div>
                {room_tag}
            </div>"""
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #fff; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.8rem; font-weight: 900; }}
        .date-line {{ text-align: center; color: #666; font-size: 1.3rem; margin-bottom: 30px; }}
        .wrapper {{ display: flex; gap: 20px; justify-content: center; }}
        .column {{ flex: 1; min-width: 300px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-top: 0; }}
        .card {{ background: #f4d1ce; padding: 18px; border-radius: 15px; margin-bottom: 20px; border-left: 12px solid #ee7a9f; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .time {{ font-weight: bold; font-size: 1.2rem; }}
        .name {{ font-size: 1.4rem; font-weight: 800; margin: 5px 0; line-height: 1.1; }}
        .teacher {{ font-style: italic; color: #333; }}
        .room-tag {{ background: #fff; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-top: 10px; font-weight: bold; display: inline-block; border: 1px solid #ee7a9f; }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <div class="date-line">{today_label}</div>
    <div class="wrapper">
        {render_col("Light Box", light_box)}
        {render_col("Black Box", black_box)}
        {render_col("Övriga lokaler", others, True)}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
