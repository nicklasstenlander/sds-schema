import requests
from datetime import datetime, date
import pytz
import html
import json

# =========================
# 1️⃣ Konfiguration
# =========================
ORG = "sollentunadans"
PW = ""
URL = f"https://dans.se/api/public/events/?org={ORG}&pw={PW}"

TZ = pytz.timezone("Europe/Stockholm")

VECKODAGAR = [
    "Måndag", "Tisdag", "Onsdag",
    "Torsdag", "Fredag", "Lördag", "Söndag"
]
MÅNADER = [
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december"
]

def parse_date(d):
    """Försök parsa 'YYYY-MM-DD' till date-objekt, annars None."""
    if not d:
        return None
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return None

# =========================
# 2️⃣ Hämta data från CogWork
# =========================
resp = requests.get(URL)
resp.raise_for_status()
data = resp.json()
events = data.get("events", [])

now = datetime.now(TZ)
today_date: date = now.date()
today_dow = now.weekday()  # 0=mån, 6=sön

today_label = f"{VECKODAGAR[today_dow]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

debug_rows = []   # för debugfil
filtered = []     # klasser som ska visas

for e in events:
    name = e.get("name", "")
    place = e.get("place", "") or ""
    teacher = e.get("instructorsName", "") or ""

    reg = e.get("registration", {}) or {}
    showing = reg.get("showing", False)

    sched = e.get("schedule", {}) or {}
    start_info = sched.get("start", {}) or {}
    end_info = sched.get("end", {}) or {}

    start_time = (start_info.get("time") or "")[:5]  # HH:MM
    end_time = (end_info.get("time") or "")[:5]

    day_of_week = start_info.get("dayOfWeek")

    start_date_str = start_info.get("date")
    end_date_str = end_info.get("date")

    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    # --- 2.1: Är det rätt veckodag? (CogWork: 1=mån ... 7=sön) ---
    try:
        dow_match = int(day_of_week) == (today_dow + 1)
    except (TypeError, ValueError):
        dow_match = False

    # --- 2.2: Ligger idag inom kursens start/slut-datum? ---
    in_term = True
    if start_date and end_date:
        in_term = (start_date <= today_date <= end_date)
    elif start_date and not end_date:
        in_term = (today_date >= start_date)
    elif end_date and not start_date:
        in_term = (today_date <= end_date)

    # --- 2.3: Endast aktuella, visade event ---
    include = bool(showing and dow_match and in_term)

    debug_rows.append({
        "name": name,
        "place": place,
        "teacher": teacher,
        "start_time": start_time,
        "end_time": end_time,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "dayOfWeek": day_of_week,
        "showing": showing,
        "dow_match": dow_match,
        "in_term": in_term,
        "included": include,
    })

    if not include:
        continue

    # =========================
    # 3️⃣ Endast Light Box / Black Box
    # =========================
    place_lower = place.lower()
    if place_lower not in ("light box", "black box"):
        # Ignorera andra salar
        continue

    filtered.append({
        "time": f"{start_time}–{end_time}" if start_time and end_time else "",
        "course": name,
        "teacher": teacher,
        "place": place,
    })

print(f"🟢 Hittade {len(filtered)} klasser för {VECKODAGAR[today_dow]} ({today_date})")

# =========================
# 4️⃣ Sortera & gruppera per sal
# =========================
filtered.sort(key=lambda x: x["time"])

light_box = [f for f in filtered if f["place"].lower() == "light box"]
black_box = [f for f in filtered if f["place"].lower() == "black box"]

def render_box(rows):
    if not rows:
        return "<p style='color:#777;'>Inga klasser idag</p>"
    html_cards = ""
    for r in rows:
        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p>{html.escape(r['time'])}</p>
            <p><em>{html.escape(r['teacher'])}</em></p>
        </div>
        """
    return html_cards

# =========================
# 5️⃣ Skapa HTML
# =========================
html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="600">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dagens schema</title>
    <style>
        body {{
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #ffffff;
            color: #000;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-weight: 600;
            font-size: 2.5rem;
            margin-bottom: 0.2rem;
        }}
        h2.date-line {{
            text-align: center;
            color: #444;
            font-weight: 400;
            margin-top: 0.2rem;
            margin-bottom: 2rem;
            font-size: 1.3rem;
        }}
        .wrapper {{
            display: flex;
            justify-content: space-between;
            gap: 2%;
            margin-top: 1rem;
        }}
        .column {{
            width: 48%;
        }}
        .column h2 {{
            background-color: #a3c0b2;
            color: #000;
            padding: 0.8rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 1.4rem;
            text-align: center;
        }}
        .class-card {{
            background-color: #CDDCD1;
            padding: 1rem 1.2rem;
            border-radius: 1rem;
            margin-bottom: 1rem;
        }}
        .class-card h3 {{
            margin: 0;
            font-size: 1.2rem;
        }}
        .class-card p {{
            margin: 0.2rem 0;
            font-size: 1rem;
        }}
        em {{
            font-style: italic;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <h2 class="date-line">{today_label}</h2>
    <div class="wrapper">
        <div class="column">
            <h2>Light Box</h2>
            {render_box(light_box)}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_box(black_box)}
        </div>
    </div>
</body>
</html>
"""

# =========================
# 6️⃣ Spara HTML + debug
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

with open("debug_schedule.json", "w", encoding="utf-8") as f:
    json.dump(debug_rows, f, indent=2, ensure_ascii=False)

print("✅ index.html uppdaterad:", today_label)
print("📝 debug_schedule.json skapad för felsökning")
