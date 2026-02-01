import requests
from icalendar import Calendar
from datetime import datetime
import pytz
import html
import re

# ==========================================
# CONFIG
# ==========================================

ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
EVENTS_URL = "https://dans.se/api/public/events/?org=sollentunadans&pw=DanS4Dan2A"

TZ = pytz.timezone("Europe/Stockholm")

now = datetime.now(TZ)
TARGET_DATE = now.date()

# ==========================================
# NORMALISERING
# ==========================================

def norm_place(s):

    if not s:
        return "Övriga"

    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip().lower()

    if "light" in s and "box" in s:
        return "Light Box"

    if "black" in s and "box" in s:
        return "Black Box"

    return "Övriga"


# ==========================================
# DOWNLOAD EVENTS (JSON)
# ==========================================

def load_events():

    print("Downloading events JSON...")

    r = requests.get(
        EVENTS_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=60,
    )

    print("Status:", r.status_code)

    r.raise_for_status()

    data = r.json()

    print("Events loaded:", len(data.get("events", [])))

    return data["events"]


# ==========================================
# BUILD LOOKUP BY EVENT ID
# ==========================================

def build_event_lookup():

    events = load_events()

    lookup = {}

    for e in events:

        event_id = str(e["id"])

        place = norm_place(e.get("place"))

        teacher = ""

        instructors = e.get("instructors")

        if instructors:
            teacher = instructors.get("combinedTitle") or "Instruktör"

        lookup[event_id] = {
            "place": place,
            "teacher": teacher,
        }

    return lookup


EVENT_LOOKUP = build_event_lookup()

# ==========================================
# ICAL
# ==========================================

def extract_event_id(uid):
    """
    UID ser ut så här:
    262554.event@cogwork.se
    """

    if not uid:
        return None

    match = re.match(r"(\d+)", str(uid))

    return match.group(1) if match else None


print("Downloading iCal...")

gcal = Calendar.from_ical(
    requests.get(ICAL_URL, timeout=60).content
)

daily_schedule = []

for component in gcal.walk("VEVENT"):

    uid = component.get("uid")

    event_id = extract_event_id(uid)

    if not event_id:
        continue

    meta = EVENT_LOOKUP.get(event_id)

    if not meta:
        # Event finns i iCal men inte i API — ovanligt men skippar
        continue

    dtstart = component.get("dtstart").dt
    dtend = component.get("dtend").dt

    if not isinstance(dtstart, datetime):
        continue

    start = dtstart.astimezone(TZ)
    end = dtend.astimezone(TZ)

    # 🔥 KRITISK — filtrera på lokal dag
    if start.date() != TARGET_DATE:
        continue

    summary = str(component.get("summary")).replace("Kurs: ", "").strip()

    is_live = start <= now < end

    daily_schedule.append({
        "course": summary,
        "time": f"{start:%H:%M}–{end:%H:%M}",
        "place": meta["place"],
        "teacher": meta["teacher"],
        "start_dt": start,
        "is_live": is_live
    })


daily_schedule.sort(key=lambda x: x["start_dt"])

print("Schedule generated:", len(daily_schedule), "classes")

# 🔥 STOPPA DEPLOY OM TOMT
if len(daily_schedule) < 3:
    raise Exception("Schedule suspiciously empty — aborting deploy.")


# ==========================================
# SPLIT ROOMS
# ==========================================

light = [c for c in daily_schedule if c["place"] == "Light Box"]
black = [c for c in daily_schedule if c["place"] == "Black Box"]
other = [c for c in daily_schedule if c["place"] == "Övriga"]


# ==========================================
# HTML
# ==========================================

def render_col(title, classes):

    if not classes:
        cards = '<p style="text-align:center;color:#999;margin-top:40px;">Inga lektioner</p>'
    else:
        cards = "".join(
            f"""
            <div class="card {'live' if c['is_live'] else ''}">
                <div class="time">{c['time']}</div>
                <div class="name">{html.escape(c['course'])}</div>
                <div class="teacher">{html.escape(c['teacher'])}</div>
            </div>
            """
            for c in classes
        )

    return f'<div class="column"><h2>{title}</h2>{cards}</div>'


today_label = now.strftime("%A %d %B %Y")

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="300">
<style>

body {{
    font-family: sans-serif;
    background: #fff;
    padding: 20px;
}}

.wrapper {{
    display:flex;
    gap:20px;
}}

.column {{
    flex:1;
}}

h2 {{
    background:#ee7a9f;
    color:white;
    padding:12px;
    border-radius:10px;
}}

.card {{
    background:#f4d1ce;
    padding:18px;
    border-radius:16px;
    margin-bottom:12px;
    border-left:10px solid #ee7a9f;
}}

.card.live {{
    border-left:14px solid #ff4d6d;
    background:#ffe5ec;
}}

.time {{
    font-weight:700;
}}

.name {{
    font-size:1.2rem;
    font-weight:800;
}}

.teacher {{
    font-style:italic;
}}

</style>
</head>

<body>

<h1>Dagens schema</h1>
<p>{today_label}</p>

<div class="wrapper">
{render_col("Light Box", light)}
{render_col("Black Box", black)}
{render_col("Övriga", other)}
</div>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print("index.html generated successfully ✅")
