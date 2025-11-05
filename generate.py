import requests
from datetime import datetime
import pytz

def safe_parse_date(datestr):
    """Försöker tolka datum i flera format."""
    if not datestr:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(datestr[:10], "%Y-%m-%d").date()
        except Exception:
            continue
    return None

# === 1️⃣ Hämta schema ===
URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()
events = data.get("events") or data.get("data") or []

# === 2️⃣ Svenska datum & tidszon ===
tz = pytz.timezone("Europe/Stockholm")
now = datetime.now(tz)
today_dow = now.weekday()

veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
månader = ["januari","februari","mars","april","maj","juni","juli","augusti","september","oktober","november","december"]
today_label = f"{veckodagar[today_dow]} {now.day} {månader[now.month - 1]} {now.year}"

# === 3️⃣ Filtrera aktiva klasser ===
filtered = []
skipped_date = 0
skipped_weekday = 0

for e in events:
    sched = e.get("schedule", {})
    if not sched or not sched.get("start") or not sched.get("end"):
        continue

    start_date = safe_parse_date(sched["start"].get("date"))
    end_date = safe_parse_date(sched["end"].get("date"))
    day_of_week = sched["start"].get("dayOfWeek")

    if not (start_date and end_date and day_of_week):
        continue

    # ✅ Bara de som är igång just nu
    if not (start_date <= now.date() <= end_date):
        skipped_date += 1
        continue

    try:
        if int(day_of_week) == (today_dow + 1):
            start_time = sched["start"]["time"][:5]
            end_time = sched["end"]["time"][:5]
            filtered.append({
                "time": f"{start_time}–{end_time}",
                "course": e.get("name", "").strip(),
                "teacher": e.get("instructorsName", "").strip(),
                "place": e.get("place", "").strip() or "Light Box",
            })
        else:
            skipped_weekday += 1
    except Exception:
        continue

print(f"🟢 Hittade {len(filtered)} aktiva kurser för {veckodagar[today_dow]} ({today_label})")
print(f"   ⏳ Filtrerade bort pga datumintervall: {skipped_date}")
print(f"   🚫 Filtrerade bort pga veckodag: {skipped_weekday}")

# === 4️⃣ Sortera & gruppera (endast två salar) ===
filtered.sort(key=lambda x: x["time"])
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
