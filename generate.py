import requests
from datetime import datetime
import pytz

# =========================
# 1️⃣ Hämta schema från CogWork
# =========================
URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()
events = data.get("events", [])

filtered = []
for e in events:
    if not e.get("registration", {}).get("showing", False):
        continue

    sched = e.get("schedule", {})
    day_of_week = sched.get("start", {}).get("dayOfWeek")

    try:
        # CogWork dagOfWeek: 1=mån ... 7=sön
        if int(day_of_week) == (today_dow + 1):
            filtered.append({
                "time": sched["start"]["time"][:5] + "–" + sched["end"]["time"][:5],
                "course": e.get("name", ""),
                "teacher": e.get("instructorsName", ""),
                "place": e.get("place", ""),
            })
    except (TypeError, ValueError):
        continue

    sched = e.get("schedule", {})
    day_of_week = sched.get("start", {}).get("dayOfWeek")

    try:
        # CogWork använder 1–7 (mån–sön), Python 0–6
        if int(day_of_week) == (today_dow + 1):
            filtered.append({
                "time": sched["start"]["time"][:5] + "–" + sched["end"]["time"][:5],
                "course": e.get("name", ""),
                "teacher": e.get("instructorsName", ""),
                "place": e.get("place", "")
            })
    except (TypeError, ValueError):
        continue

# =========================
# 4️⃣ Sortera & gruppera
# =========================
filtered.sort(key=lambda x: x["time"])
light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

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
            justify-content: space-between;
            gap: 2%;
            margin-top: 2rem;
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
    </div>
</body>
</html>
"""

# =========================
# 6️⃣ Spara fil
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("✅ index.html uppdaterad:", today_label)
