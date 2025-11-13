import json
from datetime import datetime

import pytz
import requests


def safe_parse_date(datestr):
    """Försöker tolka datum i flera format."""
    if not datestr:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(datestr[: len(fmt)], fmt)
            return parsed.date()
        except Exception:
            continue

    return None


def parse_datetime(dt_str, tz):
    """Tolka ett datum med tid och konvertera till lokal tidszon."""
    if not dt_str:
        return None

    dt_str = dt_str.strip()
    dt = None

    # Försök med Pythons ISO-parser (hanterar +01:00 osv.)
    try:
        cleaned = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
    except ValueError:
        pass

    if dt is None:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(dt_str, fmt)
                break
            except ValueError:
                continue

    if dt is None:
        return None

    if dt.tzinfo is None:
        return tz.localize(dt)

    return dt.astimezone(tz)

# === 1️⃣ Hämta schema ===
URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="

data = None
try:
    response = requests.get(URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    print("🟢 Hämtade schema från API")
except Exception as exc:
    print("⚠️ Kunde inte hämta schema från API, använder lokal data.json:", exc)
    with open("data.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)

events = data.get("events") or data.get("data") or []

# === 2️⃣ Svenska datum & tidszon ===
tz = pytz.timezone("Europe/Stockholm")
now = datetime.now(tz)
today_dow = now.weekday()

veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
månader = ["januari","februari","mars","april","maj","juni","juli","augusti","september","oktober","november","december"]
today_label = f"{veckodagar[today_dow]} {now.day} {månader[now.month - 1]} {now.year}"

# === 3️⃣ Plocka fram dagens tillfällen ===
filtered = []
stats = {
    "events": len(events),
    "occurrences_total": 0,
    "occurrences_used": 0,
    "fallback_matches": 0,
    "skipped_date": 0,
    "skipped_weekday": 0,
}

for e in events:
    sched = e.get("schedule") or {}
    occasions = sched.get("occasions") or []
    event_name = e.get("name", "").strip()
    place = (e.get("place") or "Light Box").strip()
    teacher = (e.get("instructorsName") or "").strip()

    used_occurrence = False

    if occasions:
        stats["occurrences_total"] += len(occasions)

        for occ in occasions:
            start_dt = parse_datetime(occ.get("startDateTime"), tz)
            end_dt = parse_datetime(occ.get("endDateTime"), tz)

            if not (start_dt and end_dt):
                continue

            if start_dt.date() == now.date():
                filtered.append({
                    "time": f"{start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')}",
                    "course": event_name,
                    "teacher": teacher,
                    "place": place,
                    "sort_key": start_dt,
                    "source": "occurrence",
                })
                used_occurrence = True

        if used_occurrence:
            stats["occurrences_used"] += 1
            continue

    # --- Fallback till schemainfo om vi inte hittade en occurrence ---
    start_info = (sched.get("start") or {})
    end_info = (sched.get("end") or {})
    start_date = safe_parse_date(start_info.get("date"))
    end_date = safe_parse_date(end_info.get("date"))
    day_of_week = start_info.get("dayOfWeek") or end_info.get("dayOfWeek")

    if not (start_date and end_date and day_of_week):
        continue

    if not (start_date <= now.date() <= end_date):
        stats["skipped_date"] += 1
        continue

    try:
        if int(day_of_week) == (today_dow + 1):
            start_time_raw = (start_info.get("time") or "")[:5]
            end_time_raw = (end_info.get("time") or "")[:5]

            if not (start_time_raw and end_time_raw):
                continue

            try:
                start_time_dt = datetime.strptime(start_time_raw, "%H:%M")
                sort_key = tz.localize(datetime.combine(now.date(), start_time_dt.time()))
            except ValueError:
                sort_key = now

            filtered.append({
                "time": f"{start_time_raw}–{end_time_raw}",
                "course": event_name,
                "teacher": teacher,
                "place": place,
                "sort_key": sort_key,
                "source": "schedule",
            })
            stats["fallback_matches"] += 1
        else:
            stats["skipped_weekday"] += 1
    except Exception:
        continue

print(
    "🟢 Hittade",
    len(filtered),
    "aktiva kurser för",
    veckodagar[today_dow],
    f"({today_label})",
)
print(f"   📅 Event med occurrence-lista: {stats['occurrences_total']} (använda idag: {stats['occurrences_used']})")
print(f"   🔁 Fallback via schemainfo: {stats['fallback_matches']}")
print(f"   ⏳ Filtrerade bort pga datumintervall: {stats['skipped_date']}")
print(f"   🚫 Filtrerade bort pga veckodag: {stats['skipped_weekday']}")

# === 4️⃣ Sortera & gruppera (endast två salar) ===
filtered.sort(key=lambda x: x.get("sort_key"))
light_box = [f for f in filtered if f["place"].lower() == "light box"]
black_box = [f for f in filtered if f["place"].lower() == "black box"]

# === 5️⃣ HTML ===
def render_box(rows):
    html = ""
    for r in rows:
        html += f"""
        <div class='class-card'>
            <h3>{r['course']}</h3>
            <p>{r['time']}</p>
            <p><em>{r['teacher']}</em></p>
        </div>"""
    return html or "<p style='color:#777;'>Inga klasser idag</p>"

html_content = f"""
<!DOCTYPE html>
<html lang='sv'>
<head>
<meta charset='UTF-8'>
<meta http-equiv='refresh' content='600'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Dagens schema</title>
<style>
    body {{
        font-family: 'Agrandir', sans-serif;
        background: #fff;
        color: #000;
        padding: 2rem;
    }}
    h1 {{
        text-align: center;
        font-weight: 600;
    }}
    h2 {{
        text-align: center;
        font-weight: 400;
        color: #444;
        margin-top: 0.2rem;
    }}
    .wrapper {{
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin-top: 2rem;
        flex-wrap: wrap;
    }}
    .column {{
        width: 300px;
    }}
    .column h2 {{
        background: #a3c0b2;
        color: #000;
        padding: 0.8rem;
        border-radius: 0.5rem;
        text-align: center;
    }}
    .class-card {{
        background: #CDDCD1;
        padding: 1rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
    }}
</style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <h2>{today_label}</h2>
    <div class='wrapper'>
        <div class='column'>
            <h2>Light Box</h2>
            {render_box(light_box)}
        </div>
        <div class='column'>
            <h2>Black Box</h2>
            {render_box(black_box)}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ index.html uppdaterad:", today_label)
