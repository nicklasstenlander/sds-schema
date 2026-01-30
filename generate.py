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

# ==========================================
# 2️⃣ FULLSTÄNDIG MANUELL DATA (Från Data.html)
# ==========================================
DANS_DATA = {
    # EDUCATION & ADVANCED PROGRAMS
    "Education Program 1 (EP Y1)": {"place": "Light Box", "teacher": "Madde/Sofia/Amanda"},
    "Education Program 2 (EP Y2)": {"place": "Light Box", "teacher": "Amanda/Sofia"},
    "Education Program 3 (EP Y3)": {"place": "Light Box", "teacher": "Amanda/Sofia"},
    "Advanced Program Step 1 (AP1)": {"place": "Light Box", "teacher": "Madde/Sofia/Amanda"},
    "Advanced Program Step 2 (AP2)": {"place": "Light Box", "teacher": "Amanda/Sofia"},
    "EP 1 Jazz": {"place": "Light Box", "teacher": "Madde"},
    "EP 2 Jazz": {"place": "Light Box", "teacher": "Madde"}, # KORRIGERAD
    "EP 3 Jazz": {"place": "Light Box", "teacher": "Amanda"},
    "EP 1 Contemporary": {"place": "Black Box", "teacher": "Amanda"},
    "EP 2 Contemporary": {"place": "Black Box", "teacher": "Sofia"},
    "EP 3 Contemporary": {"place": "Black Box", "teacher": "Sofia"},
    "AP Jazz Step 1": {"place": "Black Box", "teacher": "Madde/Sofia/Amanda"},
    "AP Step 2 Jazz": {"place": "Black Box", "teacher": "Amanda"},
    "AP Step 1 Contemporary": {"place": "Black Box", "teacher": "Amanda/Sofia"},
    "AP Step 2 Contemporary": {"place": "Black Box", "teacher": "Sofia"},
    "Technical Skills": {"place": "Black Box", "teacher": "Madde/Sofia/Amanda"},

    # TALENT & PERFORMANCE
    "Talent Program": {"place": "Light Box", "teacher": "Sofia, Hilda"},
    "Tillval Talent Program": {"place": "Light Box", "teacher": "Sofia/Hilda"},
    "Talent Program Jazz": {"place": "Black Box", "teacher": "Sofia"},
    "Talent Program Street": {"place": "Black Box", "teacher": "Hilda"},
    "Performance Intermediate": {"place": "Black Box", "teacher": "Sofia"},
    "Performance Advanced": {"place": "Light Box", "teacher": "Madde"},

    # BARN & UNGDOM
    "Barndans med förälder": {"place": "Light Box", "teacher": "Madde"},
    "Barndans 3-4": {"place": "Black Box", "teacher": "Aline, Livia"},
    "Barndans 4-5": {"place": "Light Box", "teacher": "Madde"},
    "Barndans 5-6": {"place": "Black Box", "teacher": "Aline, Livia"},
    "Barnbalett 5-6": {"place": "Light Box", "teacher": "Madde"},
    "Jazz Kids 5-6": {"place": "Light Box", "teacher": "Hilda"},
    "Popstars 5-6": {"place": "Black Box", "teacher": "Elsa"},
    "Juniorstreet 7-9": {"place": "Light Box", "teacher": "Elsa"},
    "Showjazz 7-9": {"place": "Light Box", "teacher": "Matilda"},
    "Showjazz 8-9": {"place": "Black Box", "teacher": "Amanda"},
    "Balett 7-9": {"place": "Light Box", "teacher": "Alice"},
    "Streetdance 8-9": {"place": "Light Box", "teacher": "Matilda"},
    "Streetdance 10+": {"place": "Light Box", "teacher": "Alice"},
    "K-pop Kids 6-7": {"place": "Black Box", "teacher": "Alice"},
    "K-pop 8-10": {"place": "Black Box", "teacher": "Lova"},
    "K-pop 10+": {"place": "Black Box", "teacher": "Elsa"},
    "Tiktok 8-9": {"place": "Black Box", "teacher": "Elsa"},
    "Tiktok 10+": {"place": "Black Box", "teacher": "Lova"},
    "Cheerdance 7-8": {"place": "Black Box", "teacher": "Elsa"},

    # ÖVRIGA KLASSER
    "Balett 9+": {"place": "Black Box", "teacher": "Sofia"},
    "Jazz 16+": {"place": "Black Box", "teacher": "Sofia"},
    "Contemporary 11+": {"place": "Light Box", "teacher": "Hilda"},
    "Advanced Contemporary": {"place": "Black Box", "teacher": "Amanda"},
    "Commercial Jazz 11+": {"place": "Light Box", "teacher": "Amanda"},
    "Commercial Hiphop 13+": {"place": "Light Box", "teacher": "Hilda"},
    "Jazz & Funk": {"place": "Light Box", "teacher": "Hilda"},
    "Jazz/Balett 55+": {"place": "Light Box", "teacher": "Madde"}
}

# =========================
# 3️⃣ iCal-hämtning & Tidsfix
# =========================
daily_schedule = []
try:
    resp = requests.get(ICAL_URL, timeout=20)
    gcal = Calendar.from_ical(resp.content)
    
    for component in gcal.walk('VEVENT'):
        summary = str(component.get('summary')).replace("Kurs: ", "").strip()
        dtstart = component.get('dtstart').dt
        
        if isinstance(dtstart, datetime):
            # Tidsfix (-1h för att matcha MinaAktiviteter)
            start_local = dtstart.astimezone(TZ) - timedelta(hours=1)
            end_dt = component.get('dtend').dt.astimezone(TZ) - timedelta(hours=1)

            if start_local.date() == TARGET_DATE:
                location, teacher = "Light Box", "Instruktör"
                
                # Matcha mot DANS_DATA
                for key, info in DANS_DATA.items():
                    if key.lower() in summary.lower():
                        location = info["place"]
                        teacher = info["teacher"]
                        break
                
                daily_schedule.append({
                    'course': summary,
                    'time': f"{start_local.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}",
                    'raw_time': start_local.strftime('%H:%M'),
                    'place': location, 
                    'teacher': teacher
                })
except Exception as e:
    print(f"Fel: {e}")

daily_schedule.sort(key=lambda x: x["raw_time"])

# =========================
# 4️⃣ HTML (Samma design)
# =========================
# (Här genereras samma snygga HTML-kod som tidigare...)
