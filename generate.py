import requests
from datetime import datetime
import pytz

URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()

events = data.get("events", [])
today = datetime.now(pytz.timezone("Europe/Stockholm")).strftime("%Y-%m-%d")

filtered = []
for e in events:
    if not e.get("registration", {}).get("showing", False):
        continue
    sched = e.get("schedule", {})
    if sched.get("start", {}).get("date") == today:
        filtered.append({
            "time": sched["start"]["time"][:5] + "–" + sched["end"]["time"][:5],
            "course": e.get("name", ""),
            "teacher": e.get("instructorsName", ""),
            "place": e.get("place", "")
        })

# Sortera på starttid
filtered.sort(key=lambda x: x["time"])
light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

def render_events(events):
    html = ""
    for event in events:
        html += f"<div class='event'><strong>{event['course']}</strong><br>{event['time']}<br><em>{event['teacher']}</em></div>"
    return html

# Skapa dagens datum på svenska (utan weekday)
datum_svenska = datetime.now(pytz.timezone("Europe/Stockholm")).strftime("%Y-%m-%d")

html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Dagens Schema – Sollentuna Dans & Scenskola</title>
    <style>
        body {{
            font-family: 'Agrandir', sans-serif;
            background-color: #ffffff;
            color: #000;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
        }}
        .schedule {{
            display: flex;
            gap: 40px;
            justify-content: center;
        }}
        .column {{
            flex: 1;
            max-width: 400px;
        }}
        .event {{
            background-color: #CDDCD1;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema ({datum_svenska})</h1>
    <div class="schedule">
        <div class="column">
            <h2>Light Box</h2>
            {render_events(light_box)}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_events(black_box)}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
