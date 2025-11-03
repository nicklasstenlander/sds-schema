import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

# Hämta JSON-data från dans.se API
url = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(url)
data = response.json()

# Filtrera ut endast schemalagda händelser för idag, där "showing": true
today = datetime.now().date()
events_today = defaultdict(list)

for event in data.get("events", []):
    reg = event.get("registration", {})
    schedule = event.get("schedule", {})
    if not reg.get("showing", False):
        continue
    try:
        event_date = datetime.strptime(schedule["start"]["date"], "%Y-%m-%d").date()
        if event_date == today:
            room = event.get("place", "Övrigt")
            time = schedule["start"]["time"][:5]
            name = event.get("name", "Okänd kurs")
            teacher = event.get("instructorsName", "")
            events_today[room].append({
                "time": time,
                "name": name,
                "teacher": teacher
            })
    except Exception:
        continue

# Sortera tiderna inom varje sal
for room in events_today:
    events_today[room].sort(key=lambda x: x["time"])

# HTML-skelett
html = """<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Dagens Schema</title>
    <meta http-equiv="refresh" content="600">
    <style>
        body {
            font-family: sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin: 40px;
        }
        h1 {
            text-align: center;
            color: #a3c0b2;
            font-size: 40px;
        }
        .container {
            display: flex;
            justify-content: space-around;
            gap: 40px;
        }
        .room {
            flex: 1;
            border: 1px solid #CDDCD1;
            border-radius: 8px;
            padding: 20px;
            background-color: #f9f9f9;
        }
        .room h2 {
            text-align: center;
            color: #a3c0b2;
            margin-top: 0;
        }
        .event {
            padding: 10px;
            margin-bottom: 10px;
            border-bottom: 1px solid #dadada;
        }
        .time {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <div class="container">
"""

for room in sorted(events_today):
    html += f'<div class="room">
<h2>{room}</h2>
'
    for event in events_today[room]:
        html += f'<div class="event"><div class="time">{event["time"]}</div><div class="name">{event["name"]}</div><div class="teacher">{event["teacher"]}</div></div>
'
    html += "</div>
"

html += """
    </div>
</body>
</html>
"""

# Spara som index.html
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
