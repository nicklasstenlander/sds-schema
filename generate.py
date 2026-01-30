import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html

# ==========================================
# 1️⃣ KONFIGURATION
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")

# TEST-LÄGE: Sätt till False för live-drift (idag)
TEST_MODE = True
now = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ) if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# ==========================================
# 2️⃣ MASTER-LISTA (Hämtad från Data.html & XML)
# ==========================================
DANS_DATA = {
    # SPECIALFALL: Kurser med olika lärare/salar beroende på dag.
    "Barndans med förälder": {
        "Måndag": {"place": "Light Box", "teacher": "Madde"},
        "Lördag": {"place": "Light Box", "teacher": "Matilda"},
        "Söndag": {"place": "Light Box", "teacher": "Matilda"},
        "default": {"place": "Light Box", "teacher": "Madde"}
    },
    
    # EDUCATION & ADVANCED PROGRAMS
    "EP 1 Jazz": {"default": {"place": "Light Box", "teacher": "Madde"}},
    "EP 2 Jazz": {"default": {"place": "Light Box", "teacher": "Madde"}}, # Fixad!
    "EP 3 Jazz": {"default": {"place": "Light Box", "teacher": "Amanda"}},
    "EP 1 Contemporary": {"default": {"place": "Black Box", "teacher": "Amanda"}},
    "EP 2 Contemporary": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "EP 3 Contemporary": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "AP Jazz Step 1": {"default": {"place": "Black Box", "teacher": "Madde/Sofia/Amanda"}},
    "AP Step 2 Jazz": {"default": {"place": "Black Box", "teacher": "Amanda"}},
    "AP Step 1 Contemporary": {"default": {"place": "Black Box", "teacher": "Amanda/Sofia"}},
    "AP Step 2 Contemporary": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "Technical Skills": {"default": {"place": "Black Box", "teacher": "Madde/Sofia/Amanda"}},
    "Education Program 1": {"default": {"place": "Light Box", "teacher": "Madde/Sofia/Amanda"}},
    "Education Program 2": {"default": {"place": "Light Box", "teacher": "Amanda/Sofia"}},
    "Education Program 3": {"default": {"place": "Light Box", "teacher": "Amanda/Sofia"}},
    "Advanced Program Step 1": {"default": {"place": "Light Box", "teacher": "Madde/Sofia/Amanda"}},
    "Advanced Program Step 2": {"default": {"place": "Light Box", "teacher": "Amanda/Sofia"}},

    # TALENT & PERFORMANCE
    "Talent Program": {"default": {"place": "Light Box", "teacher": "Sofia, Hilda"}},
    "Tillval Talent Program": {"default": {"place": "Light Box", "teacher": "Sofia/Hilda"}},
    "Talent Program Jazz": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "Talent Program Street": {"default": {"place": "Black Box", "teacher": "Hilda"}},
    "Performance Intermediate": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "Performance Advanced": {"default": {"place": "Light Box", "teacher": "Madde"}},

    # BARN & UNGDOM (7-12 år)
    "Barndans 3-4": {"default": {"place": "Black Box", "teacher": "Aline, Livia"}},
    "Barndans 4-5": {"default": {"place": "Light Box", "teacher": "Madde"}},
    "Barndans 5-6": {"default": {"place": "Black Box", "teacher": "Aline, Livia"}},
    "Barnbalett 5-6": {"default": {"place": "Light Box", "teacher": "Madde"}},
    "Jazz Kids 5-6": {"default": {"place": "Light Box", "teacher": "Hilda"}},
    "Popstars 5-6": {"default": {"place": "Black Box", "teacher": "Elsa"}},
    "Juniorstreet 7-9": {"default": {"place": "Light Box", "teacher": "Elsa"}},
    "Showjazz 7-9": {"default": {"place": "Light Box", "teacher": "Matilda"}},
    "Showjazz 8-9": {"default": {"place": "Black Box", "teacher": "Amanda"}},
    "Balett 7-9": {"default": {"place": "Light Box", "teacher": "Alice"}},
    "Streetdance 8-9": {"default": {"place": "Light Box", "teacher": "Matilda"}},
    "Streetdance 10+": {"default": {"place": "Light Box", "teacher": "Alice"}},
    "K-pop Kids 6-7": {"default": {"place": "Black Box", "teacher": "Alice"}},
    "K-pop 8-10": {"default": {"place": "Black Box", "teacher": "Lova"}},
    "K-pop 10+": {"default": {"place": "Black Box", "teacher": "Elsa"}},
    "Tiktok 8-9": {"default": {"place": "Black Box", "teacher": "Elsa"}},
    "Tiktok 10+": {"default": {"place": "Black Box", "teacher": "Lova"}},
    "Cheerdance 7-8": {"default": {"place": "Black Box", "teacher": "Elsa"}},

    # ÖVRIGA KLASSER (13+ & VUXNA)
    "Balett 9+": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "Jazz 16+": {"default": {"place": "Black Box", "teacher": "Sofia"}},
    "Contemporary 11+": {"default": {"place": "Light Box", "teacher": "Hilda"}},
    "Advanced Contemporary": {"default": {"place": "Black Box", "teacher": "Amanda"}},
    "Commercial Jazz 11+": {"default": {"place": "Light Box", "teacher": "Amanda"}},
    "Commercial Hiphop 13+": {"default": {"place": "Light Box", "teacher": "Hilda"}},
    "Jazz & Funk": {"default": {"place": "Light Box", "teacher": "Hilda"}},
    "Jazz/Balett 55+": {"default": {"place": "Light Box", "teacher": "Madde"}}
}

# ==========================================
# 3️⃣ SCHEMA-LOGIK
# ==========================================
daily_schedule = []
current_day_name = VECKODAGAR[now.weekday()]

try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    gcal = Calendar.from_ical(resp.content)
    
    for component in gcal.walk('VEVENT'):
        summary = str(component.get('summary')).replace("Kurs: ", "").strip()
        dtstart = component.get('dtstart').dt
        dtend = component.get('dtend').dt
        
        if isinstance(dtstart, datetime):
            # Tidsjustering (-1h för iCal vintertid)
            start_local = dtstart.astimezone(TZ) - timedelta(hours=1)
            end_local = dtend.astimezone(TZ) - timedelta(hours=1)

            if start_local.date() == TARGET_DATE:
                location, teacher = "Light Box", "Instruktör"
                
                # Matcha mot DANS_DATA med veckodagssupport
                for key, days in DANS_DATA.items():
                    if key.lower() in summary.lower():
                        info = days.get(current_day_name, days.get("default"))
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
    print(f"Fel vid hämtning: {e}")

daily_schedule.sort(key=lambda x: x["raw_time"])

# ==========================================
# 4️⃣ HTML (Samma design som tidigare)
# ==========================================


# ==========================================
# 4️⃣ HTML-GENERERING
# ==========================================
def render_col(title, classes):
    cards = "".join([f"""
        <div class="card">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>""" for c in classes]) or '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; color: #333; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.5rem; text-transform: uppercase; }}
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 30px; font-weight: bold; }}
        .wrapper {{ display: flex; gap: 20px; justify-content: center; }}
        .column {{ flex: 1; min-width: 320px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 0; }}
        .card {{ background: #f4d1ce; padding: 20px; border-radius: 18px; margin-bottom: 15px; border-left: 12px solid #ee7a9f; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .time {{ font-weight: bold; font-size: 1.3rem; }}
        .name {{ font-size: 1.4rem; font-weight: 800; margin: 5px 0; line-height: 1.1; }}
        .teacher {{ font-style: italic; color: #555; font-size: 1.1rem; }}
    </style>
</head>
<body>
    <h1>Sollentuna Dans & Scenskola</h1>
    <div class="date">{today_label}</div>
    <div class="wrapper">
        {render_col("Light Box", [c for c in daily_schedule if c["place"] == "Light Box"])}
        {render_col("Black Box", [c for c in daily_schedule if c["place"] == "Black Box"])}
    </div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)
