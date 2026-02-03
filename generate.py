import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import json
import re

# ==========================================
# 1) KONFIG
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")

# Testläge: sätt True för att rendera "imorgon" eller valfri tid
TEST_MODE = False
TEST_NOW = datetime(2026, 2, 3, 12, 0, 0, tzinfo=TZ)  # ändra vid behov

now = TEST_NOW if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# ==========================================
# 2) SAL-MAPPNING (din hårdkodning)
# ==========================================
PLACE_MAP = {
    "Barndans med förälder": {
        "Måndag": {"place": "Light Box"},
        "Lördag": {"place": "Light Box"},
        "Söndag": {"place": "Light Box"},
        "default": {"place": "Light Box"}
    },

    # EDUCATION & ADVANCED PROGRAMS
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

    # TALENT & PERFORMANCE
    "Talent Program": {"default": {"place": "Light Box"}},
    "Tillval Talent Program": {"default": {"place": "Light Box"}},
    "Talent Program Jazz": {"default": {"place": "Black Box"}},
    "Talent Program Street": {"default": {"place": "Black Box"}},
    "Performance Intermediate": {"default": {"place": "Black Box"}},
    "Performance Advanced": {"default": {"place": "Light Box"}},

    # BARN & UNGDOM
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

    # ÖVRIGA (13+ & vuxna)
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
# 3) NORMALISERING + LÄRAR-MAPPNING (Data-4.json)
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

def norm_spaces(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def norm_title(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Kurs: ", "")
    s = html.unescape(s)
    s = norm_spaces(s)
    return s.lower()

def parse_teacher_map(json_path: str) -> dict:
    """
    Bygger teacher_map med tre nivåer:
      (course, weekday, startTime) -> instructor
      (course, weekday, None)      -> instructor
      (course, None, None)         -> instructor
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    teacher_map = {}

    # Stöd: olika struktur (rows eller direkt lista)
    rows = data.get("rows")
    if rows is None and isinstance(data, list):
        rows = data
    if rows is None:
        rows = []

    for row in rows:
        event_name = row.get("eventName") or row.get("course") or ""
        course = norm_title(event_name)
        if not course:
            continue

        dow_short = row.get("dayOfWeek") or row.get("day") or ""
        weekday = DOW_MAP.get(dow_short, dow_short if dow_short in VECKODAGAR else None)

        start_time = row.get("startTime") or row.get("start") or None  # "HH:MM"
        instructors = (row.get("instructors") or row.get("teacher") or "").strip()

        if not instructors:
            continue

        if weekday and start_time:
            teacher_map[(course, weekday, start_time)] = instructors
        if weekday:
            teacher_map.setdefault((course, weekday, None), instructors)
        teacher_map.setdefault((course, None, None), instructors)

    return teacher_map

TEACHER_MAP = parse_teacher_map("Data-4.json")

def get_teacher(summary: str, weekday_full: str, start_hhmm: str) -> str:
    c = norm_title(summary)

    t = TEACHER_MAP.get((c, weekday_full, start_hhmm))
    if t:
        return t

    t = TEACHER_MAP.get((c, weekday_full, None))
    if t:
        return t

    t = TEACHER_MAP.get((c, None, None))
    if t:
        return t

    return "Instruktör"

def get_place(summary: str, weekday_full: str) -> str:
    s_norm = norm_title(summary)

    # Längsta nyckeln vinner (minskar felmatchningar)
    keys_sorted = sorted(PLACE_MAP.keys(), key=lambda x: len(x), reverse=True)
    for k in keys_sorted:
        if k.lower() in s_norm:
            info = PLACE_MAP[k].get(weekday_full, PLACE_MAP[k].get("default", {}))
            return info.get("place", "Övriga")

    return "Övriga"

# ==========================================
# 4) TIDSKORRIGERING (din fungerande version)
# ==========================================
def to_stockholm(dt):
    """
    MinaAktiviteter iCal verkar ibland vara UTC-taggad men redan i lokal tid.
    Vi:
      1) konverterar till Stockholm
      2) drar av Stockholms offset (1h vinter / 2h sommar)
    """
    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    local = dt.astimezone(TZ)
    offset = local.utcoffset() or timedelta(0)
    return local - offset

# ==========================================
# 5) HÄMTA ICAL + BYGG DAGENS SCHEMA
# ==========================================
print("Downloading iCal...")

headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(ICAL_URL, headers=headers, timeout=60)
resp.raise_for_status()

gcal = Calendar.from_ical(resp.content)

daily_schedule = []
weekday_full = VECKODAGAR[now.weekday()]

for component in gcal.walk("VEVENT"):
    summary = str(component.get("summary")).replace("Kurs: ", "").strip()
    dtstart = component.get("dtstart").dt
    dtend = component.get("dtend").dt

    start_local = to_stockholm(dtstart) if isinstance(dtstart, datetime) else None
    end_local = to_stockholm(dtend) if isinstance(dtend, datetime) else None
    if not start_local or not end_local:
        continue

    if start_local.date() != TARGET_DATE:
        continue

    start_hhmm = start_local.strftime("%H:%M")
    place = get_place(summary, weekday_full)
    teacher = get_teacher(summary, weekday_full, start_hhmm)
    is_live = (start_local <= now < end_local)

    daily_schedule.append({
        "course": summary,
        "time": f"{start_local:%H:%M}–{end_local:%H:%M}",
        "raw_time": start_hhmm,
        "place": place,
        "teacher": teacher,
        "start_dt": start_local,
        "end_dt": end_local,
        "is_live": is_live
    })

daily_schedule.sort(key=lambda x: x["start_dt"])
print("Schedule generated:", len(daily_schedule), "classes")

# ==========================================
# 6) PÅGÅR NU / NÄSTA
# ==========================================
ongoing = next((c for c in daily_schedule if c["start_dt"] <= now < c["end_dt"]), None)
upcoming = next((c for c in daily_schedule if c["start_dt"] > now), None)


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
    return f"{h} h" if m == 0 else f"{h} h {m} min"


def status_card(label: str, c: dict | None, empty_text: str) -> str:
    # Special: Pågår nu + inget pågår -> Välkommen + nästa starttid (om finns)
    if label == "Pågår nu" and c is None:
        if upcoming:
            return f"""
            <div class="statuscard">
              <div class="statuslabel">Pågår nu</div>
              <div class="statustitle">
                Välkommen! Nästa klass startar {html.escape(upcoming["start_dt"].strftime("%H:%M"))}
              </div>
              <div class="statusmeta">
                {html.escape(upcoming["course"])} • {html.escape(upcoming["place"])} • {html.escape(upcoming["teacher"])}
              </div>
            </div>
            """
        return f"""
        <div class="statuscard">
          <div class="statuslabel">Pågår nu</div>
          <div class="statustitle">{html.escape(empty_text)}</div>
        </div>
        """

    # Standard: kortet saknar data (t.ex. Nästa när inget finns)
    if c is None:
        return f"""
        <div class="statuscard">
          <div class="statuslabel">{html.escape(label)}</div>
          <div class="statustitle">{html.escape(empty_text)}</div>
        </div>
        """

    pill = '<span class="pill">LIVE</span>' if label == "Pågår nu" else ""
    extra = ""
    if label == "Pågår nu":
        extra = f"{format_minutes(minutes_left(c['end_dt']))} kvar"
    elif label == "Nästa":
        extra = f"Startar om {format_minutes(minutes_until(c['start_dt']))}"

    return f"""
    <div class="statuscard">
      <div class="statuslabel">{html.escape(label)}{pill}</div>
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
# 7) HTML (flex + mindre klasskort)
# ==========================================
def render_col(title, classes):
    cards = "".join(
        f"""
        <div class="card {'live' if c.get('is_live') else ''}">
          <div class="time">{c['time']}</div>
          <div class="name">{html.escape(c['course'])}</div>
          <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>
        """
        for c in classes
    ) or '<div class="empty">Inga lektioner</div>'

    return f"""
    <div class="column">
      <div class="coltitle">{title}</div>
      <div class="cards">{cards}</div>
    </div>
    """

light = [c for c in daily_schedule if c["place"] == "Light Box"]
black = [c for c in daily_schedule if c["place"] == "Black Box"]
other = [c for c in daily_schedule if c["place"] not in ("Light Box", "Black Box")]

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="60">
  <style>
    :root {{
      --bg: #fff;
      --text: #333;
      --pink: #ee7a9f;
      --card: #f4d1ce;
      --cardLive: #ffe5ec;
      --shadow: rgba(0,0,0,0.08);

      --pad: 18px;
      --gap: 14px;
      --radius: 16px;

      --h1: 44px;
      --date: 22px;

      --statusLabel: 14px;
      --statusTitle: 24px;
      --statusMeta: 16px;
      --statusExtra: 16px;

      --colTitle: 18px;

      --cardPad: 14px;
      --time: 18px;
      --name: 20px;
      --teacher: 15px;
    }}

    html, body {{
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: sans-serif;
    }}

    .screen {{
      width: 1920px;
      height: 1080px;
      overflow: hidden;
    }}

    .main {{
      padding: var(--pad);
      height: 100%;
      display: flex;
      flex-direction: column;
      box-sizing: border-box;
    }}

    h1 {{
      text-align: center;
      margin: 0;
      font-size: var(--h1);
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }}

    .date {{
      text-align: center;
      color: var(--pink);
      font-size: var(--date);
      margin-top: 6px;
      margin-bottom: 14px;
      font-weight: 800;
    }}

    .statuswrap {{
      display: flex;
      gap: var(--gap);
      justify-content: center;
      margin-bottom: 14px;
    }}

    .statuscard {{
      flex: 1;
      min-width: 0;
      background: #fff7f9;
      border: 2px solid var(--pink);
      border-radius: var(--radius);
      padding: 12px 14px;
      box-shadow: 0 4px 10px var(--shadow);
      box-sizing: border-box;
    }}

    .statuslabel {{
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-size: var(--statusLabel);
      color: var(--pink);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .pill {{
      display: inline-block;
      padding: 3px 10px;
      border-radius: 999px;
      background: var(--pink);
      color: white;
      font-weight: 900;
      font-size: 12px;
    }}

    .statustitle {{
      font-size: var(--statusTitle);
      font-weight: 900;
      margin: 6px 0 2px;
      line-height: 1.05;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .statusmeta {{
      font-size: var(--statusMeta);
      color: #444;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .statusextra {{
      margin-top: 6px;
      font-weight: 900;
      font-size: var(--statusExtra);
      color: #222;
    }}

    .wrapper {{
      display: flex;
      gap: var(--gap);
      flex: 1;
      min-height: 0;
      align-items: stretch;
    }}

    .column {{
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }}

    .coltitle {{
      background: var(--pink);
      color: white;
      padding: 10px 12px;
      border-radius: 12px;
      text-align: center;
      margin: 0 0 10px 0;
      font-size: var(--colTitle);
      font-weight: 900;
    }}

    .cards {{
      overflow: hidden;
      min-height: 0;
    }}

    .card {{
      background: var(--card);
      padding: var(--cardPad);
      border-radius: 16px;
      margin-bottom: 10px;
      border-left: 10px solid var(--pink);
      box-shadow: 0 4px 10px var(--shadow);
      box-sizing: border-box;
    }}

    .card.live {{
      border-left: 14px solid #ff4d6d;
      background: var(--cardLive);
      box-shadow: 0 10px 18px rgba(0,0,0,0.14);
    }}

    .time {{
      font-weight: 900;
      font-size: var(--time);
    }}

    .name {{
      font-size: var(--name);
      font-weight: 900;
      margin: 4px 0 2px;
      line-height: 1.08;
    }}

    .teacher {{
      font-style: italic;
      color: #555;
      font-size: var(--teacher);
    }}

    .empty {{
      text-align: center;
      color: #999;
      margin-top: 30px;
    }}

    .updated {{
      text-align: center;
      color: #999;
      margin-top: 10px;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="screen">
    <div class="main">
      <h1>Dagens schema</h1>
      <div class="date">{today_label}</div>

      {status_html}

      <div class="wrapper">
        {render_col("Light Box", light)}
        {render_col("Black Box", black)}
        {render_col("Övriga", other) if other else ""}
      </div>

      <div class="updated">Uppdaterad {now.strftime('%H:%M')}</div>
    </div>
  </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
