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
# [Här genereras din index.html med kolumner för Light Box och Black Box]
# (Jag utelämnar HTML-koden här för att spara plats, men den är identisk med förra versionen)
