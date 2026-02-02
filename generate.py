import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import json
import re

# ==========================================
# 1️⃣ KONFIGURATION
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")

TEST_MODE = False
now = datetime(2026, 2, 3, 12, 0, 0, tzinfo=TZ) if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"
current_day_name = VECKODAGAR[now.weekday()]

# ==========================================
# 2️⃣ SAL-MAPPNING (manuell)
# ==========================================
PLACE_MAP = {
    "Barndans med förälder": {
        "Måndag": {"place": "Light Box"},
        "Lördag": {"place": "Light Box"},
        "Söndag": {"place": "Light Box"},
        "default": {"place": "Light Box"}
    },

    "EP 1 Jazz": {"default": {"place": "Light Box"}},
    "EP 2 Jazz": {"default": {"place": "Light Box"}},
    "EP 3 Jazz": {"default": {"place": "Light Box"}},
    "EP 1 Contemporary": {"default": {"place": "Black Box"}},
    "EP 2 Contemporary": {"default": {"place": "Black Box"}},
    "EP 3 Contemporary": {"default": {"place": "Black Box"}},
    "AP Jazz Step 1": {"default": {"place": "Black Box"}},
    "AP Step 2 Jazz": {"default": {"place": "Black Box"}},
    "AP Step 1 Contemporary": {"default": {"place": "Black Box"}},
    "AP Step 2 Contemporary": {"default": {"place": "Black Box"}},
    "Technical Skills": {"default": {"place": "Black Box"}},
    "Education Program 1": {"default": {"place": "Light Box"}},
    "Education Program 2": {"default": {"place": "Light Box"}},
    "Education Program 3": {"default": {"place": "Light Box"}},
    "Advanced Program Step 1": {"default": {"place": "Light Box"}},
    "Advanced Program Step 2": {"default": {"place": "Light Box"}},

    "Talent Program": {"default": {"place": "Light Box"}},
    "Tillval Talent Program": {"default": {"place": "Light Box"}},
    "Talent Program Jazz": {"default": {"place": "Black Box"}},
    "Talent Program Street": {"default": {"place": "Black Box"}},
    "Performance Intermediate": {"default": {"place": "Black Box"}},
    "Performance Advanced": {"default": {"place": "Light Box"}},

    "Barndans 3-4": {"default": {"place": "Black Box"}},
    "Barndans 4-5": {"default": {"place": "Light Box"}},
    "Barndans 5-6": {"default": {"place": "Black Box"}},
    "Barnbalett 5-6": {"default": {"place": "Light Box"}},
    "Jazz Kids 5-6": {"default": {"place": "Light Box"}},
    "Popstars 5-6": {"default": {"place": "Black Box"}},
    "Juniorstreet 7-9": {"default": {"place": "Light Box"}},
    "Showjazz 7-9": {"default": {"place": "Light Box"}},
    "Showjazz 8-9": {"default": {"place": "Black Box"}},
    "Balett 7-9": {"default": {"place": "Light Box"}},
    "Streetdance 8-9": {"default": {"place": "Light Box"}},
    "Streetdance 10+": {"default": {"place": "Light Box"}},
    "K-pop Kids 6-7": {"default": {"place": "Black Box"}},
    "K-pop 8-10": {"default": {"place": "Black Box"}},
    "K-pop 10+": {"default": {"place": "Black Box"}},
    "Tiktok 8-9": {"default": {"place": "Black Box"}},
    "Tiktok 10+": {"default": {"place": "Black Box"}},
    "Cheerdance 7-8": {"default": {"place": "Black Box"}},

    "Balett 9+": {"default": {"place": "Black Box"}},
    "Jazz 16+": {"default": {"place": "Black Box"}},
    "Contemporary 11+": {"default": {"place": "Light Box"}},
    "Advanced Contemporary": {"default": {"place": "Black Box"}},
    "Commercial Jazz 11+": {"default": {"place": "Light Box"}},
    "Commercial Hiphop 13+": {"default": {"place": "Light Box"}},
    "Jazz & Funk": {"default": {"place": "Light Box"}},
    "Jazz/Balett 55+": {"default": {"place": "Light Box"}},
}

# ==========================================
# 3️⃣ LÄRAR-MAPPNING (från Data-3.json)
# ==========================================
DOW_MAP = {
    "Mån": "Måndag",
    "Tis": "Tisdag",
    "Ons": "Onsdag",
    "Tors": "Torsdag",
    "Fre": "Fredag",
    "Lör": "Lördag",
    "Sön": "Söndag",
}

def norm_name(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Kurs: ", "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def parse_teacher_map(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    teacher_map = {}
    for row in data.get("rows", []):
        event = norm_name(row.get("eventName", ""))
        if not event:
            continue

        weekday = DOW_MAP.get(row.get("dayOfWeek"))
        start_time = (row.get("startTime") or "").strip()  # "HH:MM"
        instructors = (row.get("instructors") or "").strip()
        if not instructors:
            continue

        if weekday and start_time:
            teacher_map[(event, weekday, start_time)] = instructors
        if weekday:
            teacher_map.setdefault((event, weekday, None), instructors)
        teacher_map.setdefault((event, None, None), instructors)

    return teacher_map

def get_teacher(course_summary: str, weekday_full: str, start_hhmm: str, teacher_map: dict) -> str:
    e = norm_name(course_summary)

    t = teacher_map.get((e, weekday_full, start_hhmm))
    if t:
        return t
    t = teacher_map.get((e, weekday_full, None))
    if t:
        return t
    t = teacher_map.get((e, None, None))
    if t:
        return t
    return "Instruktör"

TEACHER_MAP = parse_teacher_map("Data-3.json")

# ==========================================
# 4️⃣ HJÄLPFUNKTIONER
# ==========================================
def to_stockholm(dt):
    """
    iCal verkar ibland vara UTC-taggad men redan lokal.
    Vi drar bort Stockholms offset efter konvertering.
    """
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    local = dt.astimezone(TZ)
    offset = local.utcoffset() or timedelta(0)
    return local - offset

def get_place(course_summary: str, weekday_full: str) -> str:
    summary_norm = norm_name(course_summary)
    keys_sorted = sorted(PLACE_MAP.keys(), key=lambda x: len(x), reverse=True)
    for k in keys_sorted:
        if k.lower() in summary_norm:
            info = PLACE_MAP[k].get(weekday_full, PLACE_MAP[k].get("default"))
            return info.get("place", "Övriga")
    return "Övriga"

def format_minutes(mins: int) -> str:
    mins = max(0, int(mins))
    if mins < 60:
        return f"{mins} min"
    h = mins // 60
    m = mins % 60
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"

def minutes_until(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def minutes_left(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

# ==========================================
# 5️⃣ SCHEMA-LOGIK
# ==========================================
daily_schedule = []

headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(ICAL_URL, headers=headers, timeout=30)
resp.raise_for_status()
gcal = Calendar.from_ical(resp.content)

for component in gcal.walk('VEVENT'):
    summary = str(component.get('summary')).replace("Kurs: ", "").strip()
    dtstart = component.get('dtstart').dt
    dtend = component.get('dtend').dt

    start_local = to_stockholm(dtstart) if isinstance(dtstart, datetime) else None
    end_local = to_stockholm(dtend) if isinstance(dtend, datetime) else None
    if not start_local or not end_local:
        continue

    if start_local.date() != TARGET_DATE:
        continue

    start_hhmm = start_local.strftime("%H:%M")

    location = get_place(summary, current_day_name)
    teacher = get_teacher(summary, current_day_name, start_hhmm, TEACHER_MAP)

    daily_schedule.append({
        'course': summary,
        'time': f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}",
        'raw_time': start_hhmm,
        'place': location,
        'teacher': teacher,
        'start_dt': start_local,
        'end_dt': end_local,
        'is_live': (start_local <= now < end_local),
    })

daily_schedule.sort(key=lambda x: x["raw_time"])

# ==========================================
# 6️⃣ PÅGÅR NU / NÄSTA
# ==========================================
ongoing = None
upcoming = None

for c in daily_schedule:
    if c["start_dt"] <= now < c["end_dt"]:
        ongoing = c
        break

for c in daily_schedule:
    if c["start_dt"] > now:
        upcoming = c
        break

def status_card(label, c, empty_text):
    # Pågår nu + inget pågår => välkommen + nästa starttid
    if label == "Pågår nu" and not c:
        if upcoming:
            return f"""
            <div class="statuscard">
                <div class="statuslabel">Pågår nu</div>
                <div class="statustitle">Välkommen! Nästa klass startar {html.escape(upcoming['start_dt'].strftime('%H:%M'))}</div>
                <div class="statusmeta">{html.escape(upcoming['course'])} • {html.escape(upcoming['place'])} • {html.escape(upcoming['teacher'])}</div>
            </div>
            """
        return f"""
        <div class="statuscard">
            <div class="statuslabel">Pågår nu</div>
            <div class="statustitle">Välkommen! Inget mer schemalagt idag</div>
        </div>
        """

    if not c:
        return f"""
        <div class="statuscard">
            <div class="statuslabel">{label}</div>
            <div class="statustitle">{html.escape(empty_text)}</div>
        </div>
        """

    extra = ""
    if label == "Pågår nu":
        extra = f"{format_minutes(minutes_left(c['end_dt']))} kvar"
    elif label == "Nästa":
        extra = f"Startar om {format_minutes(minutes_until(c['start_dt']))}"

    live_pill = '<span class="pill">LIVE</span>' if label == "Pågår nu" and c.get("is_live") else ""

    return f"""
    <div class="statuscard">
        <div class="statuslabel">{label} {live_pill}</div>
        <div class="statustitle">{html.escape(c['course'])}</div>
        <div class="statusmeta">{html.escape(c['time'])} • {html.escape(c['place'])} • {html.escape(c['teacher'])}</div>
        <div class="statusextra">{html.escape(extra)}</div>
    </div>
    """

status_html = f"""
<div class="statuswrap">
    {status_card("Pågår nu", ongoing, "Ingen lektion pågår just nu")}
    {status_card("Nästa", upcoming, "Inget mer schemalagt idag")}
</div>
"""

# ==========================================
# 7️⃣ HTML-GENERERING
# ==========================================
def render_col(title, classes):
    cards = "".join([f"""
        <div class="card {'live' if c.get('is_live') else ''}">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>""" for c in classes]) or '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

light = [c for c in daily_schedule if c["place"] == "Light Box"]
black = [c for c in daily_schedule if c["place"] == "Black Box"]
other = [c for c in daily_schedule if c["place"] not in ("Light Box", "Black Box")]

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; color: #333; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.5rem; text-transform: uppercase; }}
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 18px; font-weight: bold; }}

        .statuswrap {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 18px; }}
        .statuscard {{ flex: 1; min-width: 320px; background: #fff7f9; border: 2px solid #ee7a9f; border-radius: 18px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); }}
        .statuslabel {{ font-weight: 900; text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.95rem; color: #ee7a9f; display:flex; align-items:center; gap:10px; }}
        .statustitle {{ font-size: 1.6rem; font-weight: 900; margin: 6px 0 2px; line-height: 1.1; }}
        .statusmeta {{ font-size: 1.1rem; color: #444; }}
        .statusextra {{ margin-top: 8px; font-weight: 900; font-size: 1.05rem; color: #222; }}
        .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #ee7a9f; color: white; font-weight: 800; font-size: 0.95rem; }}

        .wrapper {{ display: flex; gap: 20px; justify-content: center; align-items: flex-start; }}
        .column {{ flex: 1; min-width: 320px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 0; }}
        .card {{ background: #f4d1ce; padding: 20px; border-radius: 18px; margin-bottom: 15px; border-left: 12px solid #ee7a9f; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card.live {{
            border-left: 16px solid #ff4d6d;
            background: #ffe5ec;
            transform: scale(1.02);
            box-shadow: 0 8px 18px rgba(0,0,0,0.15);
        }}
        .time {{ font-weight: bold; font-size: 1.3rem; }}
        .name {{ font-size: 1.4rem; font-weight: 800; margin: 5px 0; line-height: 1.1; }}
        .teacher {{ font-style: italic; color: #555; font-size: 1.1rem; }}
    </style>
</head>
<body>
    <h1>Dagens schema</h1>
    <div class="date">{today_label}</div>

    {status_html}

    <div class="wrapper">
        {render_col("Light Box", light)}
        {render_col("Black Box", black)}
        {render_col("Övriga", other) if other else ""}
    </div>

    <div style="text-align:center;color:#999;margin-top:20px;font-size:0.9rem;">
        Uppdaterad {now.strftime('%H:%M')}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
