import requests
from datetime import datetime
import pytz

# =========================
# 1️⃣ Hämta schema från CogWork
# =========================
URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()

# CogWork kan ha "data" eller "events" beroende på version
events = data.get("events") or data.get("data") or []

# =========================
# 2️⃣ Svenska datum & tidszon
# =========================
tz = pytz.timezone("Europe/Stockholm")
now = datetime.now(tz)
today_dow = now.weekday()  # 0=mån ... 6=sön

veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
månader = [
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december"
]
today_label = f"{veckodagar[today_dow]} {now.day} {månader[now.month - 1]} {now.year}"

# =========================
# 3️⃣ Filtrera dagens klasser (baserat på veckodag)
# =========================
filtered = []
for e in events:
    # ⚙️ vissa är dolda (showing=False) men vi vill ändå inkludera dem om de har schema
    sched = e.get("schedule", {})
    if not sched or not sched.get("start") or not sched.get("end"):
        continue

    # Hoppa över event som inte har veckodag (t.ex. workshops)
    day_of_week = sched.get("start", {}).get("dayOfWeek")
    if not day_of_week:
        continue

    try:
        # CogWork dagOfWeek: 1=mån ... 7=sön
        if int(day_of_week) == (today_dow + 1):
            start_time = sched["start"]["time"][:5]
            end_time = sched["end"]["time"][:5]
            filtered.append({
                "time": f"{start_time}–{end_time}",
                "course": e.get("name", "").strip(),
                "teacher": e.get("instructorsName", "").strip(),
                "place": e.get("place", "").strip() or "Okänd sal",
            })
    except Exception:
        continue

print(f"🟢 Hittade {len(filtered)} kurser för {veckodagar[today_dow]}")

# =========================
# 4️⃣ Sortera & gruppera
# =========================
filtered.sort(key=lambda x: x["time"])
light_box = [f for f in filtered if f["place"].lower() == "light box"]
black_box = [f for f in filtered if f["place"].lower() == "black box"]
other_rooms = [f for f in filtered if f["place"].lower() not in ("light box", "black box")]

# =========================
# 5️⃣ Skapa HTML
# =========================
def render_box(rows):
    html = ""
    for r in rows:
        html += f"""
        <div class='class-card'>
            <h3>{r['course']}</h3>
            <p>{r['time']}</p>
            <p><em>{r['teacher']}</em></p>
        </div>
        """
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
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #ffffff;
            color: #000;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-weight: 600;
        }}
        h2 {{
            text-align: center;
            color: #444;
            font-weight: 400;
            margin-top: 0.2rem;
        }}
        .wrapper {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
            margin-top: 2rem;
        }}
        .column {{
            width: 300px;
            min-width: 280px;
        }}
        .column h2 {{
            background-color: #a3c0b2;
            color: #000;
            padding: 0.8rem;
            border-radius: 0.5rem;
            font-weight: 600;
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
"""

# Lägg till “övriga salar” om det finns
if other_rooms:
    html_content += f"""
        <div class='column'>
            <h2>Övriga salar</h2>
            {render_box(other_rooms)}
        </div>
    """

html_content += """
    </div>
</body>
</html>
"""

# =========================
# 6️⃣ Spara HTML
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ index.html uppdaterad:", today_label)
