import json
import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import re

# ==========================================
# 1) KONFIG
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"

# Events-API (JSON) – innehåller place per event-id
EVENTS_URL = "https://dans.se/api/public/events/?org=sollentunadans&pw=DanS4Dan2A"

DATA4_PATH = "Data-4.json"
TZ = pytz.timezone("Europe/Stockholm")

TEST_MODE = False
TEST_NOW = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ)  # ändra om du vill testa annan dag

now = TEST_NOW if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

DOW_MAP = {
    "Mån": "Måndag",
    "Tis": "Tisdag",
    "Ons": "Onsdag",
    "Tors": "Torsdag",
    "Fre": "Fredag",
    "Lör": "Lördag",
    "Sön": "Söndag",
}

# ==========================================
# 2) NORMALISERING
# ==========================================
def norm_spaces(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00A0", " ")  # NBSP -> space
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def norm_title(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Kurs: ", "")
    s = html.unescape(s)
    s = norm_spaces(s)
    return s.lower()

def norm_place(s: str) -> str:
    """
    Gör platsen kanonisk så filtering alltid funkar.
    Returnerar: "Light Box", "Black Box" eller original (för Övriga).
    """
    s = norm_spaces(html.unescape(s))
    low = s.lower()
    if "light" in low and "box" in low:
        return "Light Box"
    if "black" in low and "box" in low:
        return "Black Box"
    return s

# ==========================================
# 3) iCal tids-bugg fix (behåller din tidigare logik)
# ==========================================
def to_stockholm(dt):
    """
    MinaAktiviteter iCal verkar ibland vara UTC-taggad men redan i lokal tid.
    Vi gör:
    1) konvertera till Stockholm
    2) dra av Stockholms aktuella offset (1h vinter, 2h sommar)
    """
    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    local = dt.astimezone(TZ)
    offset = local.utcoffset() or timedelta(0)
    return local - offset

# ==========================================
# 4) EVENT-ID från UID
# ==========================================
def extract_event_id(uid) -> int | None:
    """
    UID ser ofta ut: 262554.event@cogwork.se
    Vi tar första sifferblocket.
    """
    if not uid:
        return None
    m = re.match(r"(\d+)", str(uid))
    return int(m.group(1)) if m else None

# ==========================================
# 5) LÄS EVENTS (JSON) -> event_id -> place
# ==========================================
def load_events_json() -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    r = requests.get(EVENTS_URL, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

def build_place_lookup() -> dict[int, str]:
    data = load_events_json()
    events = data.get("events", [])
    print(f"Events loaded: {len(events)}")

    lookup = {}
    for e in events:
        eid = e.get("id")
        if not eid:
            continue
        place = e.get("place") or ""
        lookup[int(eid)] = norm_place(place) if place else ""
    return lookup

# ==========================================
# 6) LÄS Data-4.json -> teacher-map
# ==========================================
def load_teacher_map(path: str) -> dict:
    """
    Nycklar (mest specifik först):
      (event_norm, weekday_full, "HH:MM") -> instructors
      (event_norm, weekday_full, None)    -> instructors
      (event_norm, None, None)            -> instructors
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    teacher_map = {}
    for row in data.get("rows", []):
        event = norm_title(row.get("eventName", ""))
        if not event:
            continue

        weekday = DOW_MAP.get(row.get("dayOfWeek"))  # "Mån" -> "Måndag"
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
    e = norm_title(course_summary)

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

# ==========================================
# 7) PÅGÅR NU / NÄSTA helpers
# ==========================================
def minutes_until(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def minutes_left(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def format_minutes(mins: int) -> str:
    mins = max(0, int(mins))
    if mins < 60:
        return f"{mins} min"
    h = mins // 60
    m = mins % 60
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"

def status_card(label, c, empty_text, upcoming):
    # Special: “Pågår nu” när inget pågår -> Välkommen + nästa starttid
    if label == "Pågår nu" and not c:
        if upcoming:
            return f"""
            <div class="statuscard">
                <div class="statuslabel">Pågår nu</div>
                <div class="statustitle">Välkommen! Nästa klass startar {html.escape(upcoming['start_dt'].strftime('%H:%M'))}</div>
                <div class="statusmeta">{html.escape(upcoming['course'])} • {html.escape(upcoming['place'])} • {html.escape(upcoming['teacher'])}</div>
            </div>
            """
        return """
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

    return f"""
    <div class="statuscard">
        <div class="statuslabel">{label}{'<span class="pill">LIVE</span>' if label == 'Pågår nu' else ''}</div>
        <div class="statustitle">{html.escape(c['course'])}</div>
        <div class="statusmeta">{html.escape(c['time'])} • {html.escape(c['place'])} • {html.escape(c['teacher'])}</div>
        <div class="statusextra">{html.escape(extra)}</div>
    </div>
    """

# ==========================================
# 8) BYGG SCHEMA (iCal) + place+teacher
# ==========================================
print("Downloading events JSON...")
PLACE_LOOKUP = build_place_lookup()

print("Loading teachers (Data-4.json)...")
TEACHER_MAP = load_teacher_map(DATA4_PATH)

print("Downloading iCal...")
resp = requests.get(ICAL_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
resp.raise_for_status()
gcal = Calendar.from_ical(resp.content)

daily_schedule = []
weekday_full = VECKODAGAR[now.weekday()]

for component in gcal.walk("VEVENT"):
    summary = str(component.get("summary") or "").replace("Kurs: ", "").strip()
    if not summary:
        continue

    uid = component.get("uid")
    event_id = extract_event_id(uid)

    dtstart = component.get("dtstart").dt if component.get("dtstart") else None
    dtend = component.get("dtend").dt if component.get("dtend") else None

    start_local = to_stockholm(dtstart) if isinstance(dtstart, datetime) else None
    end_local = to_stockholm(dtend) if isinstance(dtend, datetime) else None

    if not start_local or not end_local:
        continue

    if start_local.date() != TARGET_DATE:
        continue

    start_hhmm = start_local.strftime("%H:%M")

    # Place: via event_id -> events JSON
    place_raw = PLACE_LOOKUP.get(event_id, "") if event_id is not None else ""
    place = norm_place(place_raw) if place_raw else "Övriga"

    # Teacher: via Data-4.json mapping
    teacher = get_teacher(summary, weekday_full, start_hhmm, TEACHER_MAP)

    is_live = start_local <= now < end_local

    daily_schedule.append(
        {
            "course": summary,
            "time": f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}",
            "place": place if place in ("Light Box", "Black Box") else "Övriga",
            "teacher": teacher,
            "start_dt": start_local,
            "end_dt": end_local,
            "is_live": is_live,
            "raw_time": start_hhmm,
        }
    )

daily_schedule.sort(key=lambda x: x["raw_time"])
print(f"Schedule generated: {len(daily_schedule)} classes")

# ==========================================
# 9) PÅGÅR NU / NÄSTA
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

status_html = f"""
<div class="statuswrap">
    {status_card("Pågår nu", ongoing, "Ingen lektion pågår just nu", upcoming)}
    {status_card("Nästa", upcoming, "Inget mer schemalagt idag", upcoming)}
</div>
"""

# ==========================================
# 10) HTML
# ==========================================
def render_col(title, classes):
    cards = "".join(
        [
            f"""
        <div class="card {'live' if c.get('is_live') else ''}">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>"""
            for c in classes
        ]
    ) or '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

light = [c for c in daily_schedule if c["place"] == "Light Box"]
black = [c for c in daily_schedule if c["place"] == "Black Box"]
other = [c for c in daily_schedule if c["place"] == "Övriga"]

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; color: #333; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.5rem; text-transform: uppercase; }}
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 30px; font-weight: bold; }}
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

        .statuswrap {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; }}
        .statuscard {{ flex: 1; min-width: 320px; background: #fff7f9; border: 2px solid #ee7a9f; border-radius: 18px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); }}
        .statuslabel {{ font-weight: 900; text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.95rem; color: #ee7a9f; }}
        .statustitle {{ font-size: 1.6rem; font-weight: 900; margin: 6px 0 2px; line-height: 1.1; }}
        .statusmeta {{ font-size: 1.1rem; color: #444; }}
        .statusextra {{ margin-top: 8px; font-weight: 900; font-size: 1.05rem; color: #222; }}
        .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #ee7a9f; color: white; font-weight: 800; font-size: 0.95rem; margin-left: 8px; vertical-align: middle; }}
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
