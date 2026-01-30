import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html

# =========================
# 1️⃣ Inställningar
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
# 2️⃣ Komplett Manuell Lista (Från XML)
# =========================
DANS_DATA = {
    "Talent Program": {"place": "Light Box", "teacher": "Sofia, Hilda"},
    "Performance Intermediate": {"place": "Black Box", "teacher": "Sofia"},
    "Education Program 1 (EP Y1)": {"place": "Light Box", "teacher": "Madde/Sofia/Amanda"},
    "Advanced Program Step 2 (AP2)": {"place": "Light Box", "teacher": "Amanda/Sofia"},
    "Education Program 2 (EP Y2)": {"place": "Light Box", "teacher": "Amanda/Sofia"},
    "Tillval Talent Program": {"place": "Light Box", "teacher": "Sofia/Hilda"},
    "Advanced Program Step 1 (AP1)": {"place": "Light Box", "teacher": "Madde/Sofia/Amanda"},
    "Education Program 3 (EP Y3)": {"place": "Light Box", "teacher": "Amanda/Sofia"},
    "Performance Advanced": {"place": "Light Box", "teacher": "Madde"},
    "Barndans med förälder": {"place": "Light Box", "teacher": "Madde"},
    "Barndans 3-4": {"place": "Black Box", "teacher": "Aline, Livia"},
    "Barndans 4-5": {"place": "Light Box", "teacher": "Madde"},
    "Barndans 5-6": {"place": "Black Box", "teacher": "Aline, Livia"},
    "Barnbalett": {"place": "Light Box", "teacher": "Madde"},
    "Balett 7-9": {"place": "Light Box", "teacher": "Alice"},
    "Balett 9+": {"place": "Black Box", "teacher": "Sofia"},
    "Tiktok 8-9": {"place": "Black Box", "teacher": "Elsa"},
    "Tiktok 10+": {"place": "Black Box", "teacher": "Lova"},
    "Popstars 5-6": {"place": "Black Box", "teacher": "Elsa"},
    "Jazz Kids": {"place": "Light Box", "teacher": "Hilda"},
    "Juniorstreet": {"place": "Light Box", "teacher": "Elsa"},
    "Talent Program Jazz": {"place": "Black Box", "teacher": "Sofia"},
    "EP 1 Jazz": {"place": "Light Box", "teacher": "Madde"},
    "AP Step 2 Jazz": {"place": "Black Box", "teacher": "Amanda"},
    "EP 2 Jazz": {"place": "Light Box", "teacher": "Amanda"},
    "EP 3 Jazz": {"place": "Light Box", "teacher": "Amanda"},
    "AP Jazz Step 1": {"place": "Black Box", "teacher": "Madde/Sofia/Amanda"},
    "Jazz 16+": {"place": "Black Box", "teacher": "Sofia"},
    "Commercial Jazz": {"place": "Light Box", "teacher": "Amanda"},
    "Talent Program Street": {"place": "Black Box", "teacher": "Hilda"},
    "Streetdance 8-9": {"place": "Light Box", "teacher": "Matilda"},
    "Streetdance 10+": {"place": "Light Box", "teacher": "Alice"},
    "Commercial Hiphop": {"place": "Light Box", "teacher": "Hilda"},
    "EP 3 Contemporary": {"place": "Black Box", "teacher": "Sofia"},
    "EP 1 Contemporary": {"place": "Black Box", "teacher": "Amanda"},
    "EP 2 Contemporary": {"place": "Black Box", "teacher": "Sofia"},
    "AP Step 2 Contemporary": {"place": "Black Box", "teacher": "Sofia"},
    "AP Step 1 Contemporary": {"place": "Black Box", "teacher": "Amanda/Sofia"},
    "Contemporary 11+": {"place": "Light Box", "teacher": "Hilda"},
    "Advanced Contemporary": {"place": "Black Box", "teacher": "Amanda"},
    "Jazz & Funk": {"place": "Light Box", "teacher": "Hilda"},
    "Showjazz 7-9": {"place": "Light Box", "teacher": "Matilda"},
    "Showjazz 8-9": {"place": "Black Box", "teacher": "Amanda"},
    "Technical Skills": {"place": "Black Box", "teacher": "Madde/Sofia/Amanda"},
    "Jazz/Balett 55+": {"place": "Light Box", "teacher": "Madde"},
    "K-pop Kids": {"place": "Black Box", "teacher": "Alice"},
    "Cheerdance": {"place": "Black Box", "teacher": "Elsa"},
    "K-pop 8-10": {"place": "Black Box", "teacher": "Lova"},
    "K-pop 10+": {"place": "Black Box", "teacher": "Elsa"}
}

# =========================
# 3️⃣ iCal-hämtning & Matchning
# =========================
daily_schedule = []
try:
    resp = requests.get(ICAL_URL, timeout=20)
    gcal = Calendar.from_ical(resp.content)
    
    for component in gcal.walk('VEVENT'):
        summary = str(component.get('summary')).replace("Kurs: ", "").strip()
        dtstart = component.get('dtstart').dt
        dtend = component.get('dtend').dt
        
        if isinstance(dtstart, datetime):
            # Korrigering av tid (-1h för att matcha MinaAktiviteter iCal-export)
            start_local = dtstart.astimezone(TZ) - timedelta(hours=1)
            end_local = dtend.astimezone(TZ) - timedelta(hours=1)

            if start_local.date() == TARGET_DATE:
                location, teacher = "Light Box", "Instruktör"
                
                # Sök efter matchning (vi kollar om namnet i listan finns i schemanmnet)
                for key, info in DANS_DATA.items():
                    if key.lower() in summary.lower():
                        location = info["place"]
                        teacher = info["teacher"]
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

daily_schedule.sort(key=lambda x: x["raw_time"])

# =========================
# 4️⃣ HTML-generering
# =========================
light_box = [c for c in daily_schedule if c["place"] == "Light Box"]
black_box = [c for c in daily_schedule if c["place"] == "Black Box"]
others = [c for c in daily_schedule if c["place"] not in ["Light Box", "Black Box"]]

def render_col(title, classes, is_other=False):
    if is_other and not classes: return ""
    cards = ""
    for c in classes:
        cards += f"""
        <div class="card">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
            {f"<div class='room-tag'>{c['place']}</div>" if is_other else ""}
        </div>"""
    if not cards:
        cards = '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.5rem; font-weight: 900; text-transform: uppercase; }}
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 30px; font-weight: bold; }}
        .wrapper {{ display: flex; gap: 20px; justify-content: center; align-items: flex-start; }}
        .column {{ flex: 1; min-width: 320px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 0; }}
        .card {{ background: #f4d1ce; padding: 20px; border-radius: 18px; margin-bottom: 15px; border-left: 12px solid #ee7a9f; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
        .time {{ font-weight: bold; font-size: 1.3rem; }}
        .name {{ font-size: 1.4rem; font-weight: 800; margin: 5px 0; line-height: 1.1; color: #111; }}
        .teacher {{ font-style: italic; color: #444; font-size: 1.1rem; }}
    </style>
</head>
<body>
    <h1>Sollentuna Dans & Scenskola</h1>
    <div class="date">{today_label}</div>
    <div class="wrapper">
        {render_col("Light Box", light_box)}
        {render_col("Black Box", black_box)}
        {render_col("Övriga", others, True)}
    </div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)
