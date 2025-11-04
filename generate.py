import requests
from datetime import datetime
import pytz

URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()

events = data.get("events", [])

# Hämta dagens veckodag (0=mån, 6=sön)
tz = pytz.timezone("Europe/Stockholm")
now = datetime.now(tz)
today_dow = now.weekday()
today_label = now.strftime("%A %Y-%m-%d")

filtered = []
for e in events:
    if not e.get("registration", {}).get("showing", False):
        continue

    sched = e.get("schedule", {})
    day_of_week = sched.get("start", {}).get("dayOfWeek")

    try:
        # CogWork: Mån=1 ... Sön=7
        if int(day_of_week) == (today_dow + 1):
            filtered.append({
                "course": e.get("name", ""),
                "time": sched["start"]["time"][:5] + "–" + sched["end"]["time"][:5],
                "teacher": e.get("instructorsName", ""),
                "dayAndTimeInfo": sched.get("dayAndTimeInfo", ""),
                "place": e.get("place", "")
            })
    except (TypeError, ValueError):
        continue

# Sortera på tid
filtered.sort(key=lambda x: x["time"])
light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

# Rendera boxar
def render_box(course):
    return f"""
    <div class="box">
        <div class="title">{course['course']}</div>
        <div class="time">{course['dayAndTimeInfo']}</div>
        <div class="teacher">{course['teacher']}</div>
    </div>
    """

html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="600">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dagens schema</title>
    <link href="https://fonts.googleapis.com/css2?family=Agrandir&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #ffffff;
            color: #000000;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-size: 2rem;
            margin-bottom: 2rem;
        }}
        .container {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }}
        .column {{
            width: 45%;
            min-width: 300px;
        }}
        h2 {{
            text-align: center;
            background-color: #a3c0b2;
            padding: 1rem;
            border-radius: 8px;
            font-size: 1.5rem;
        }}
        .box {{
            background-color: #CDDCD1;
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 16px;
        }}
        .title {{
            font-weight: bold;
            font-size: 1.2rem;
        }}
        .time {{
            margin-top: 0.5rem;
        }}
        .teacher {{
            margin-top: 0.5rem;
            font-style: italic;
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema – {today_label}</h1>
    <div class="container">
        <div class="column">
            <h2>Light Box</h2>
            {''.join([render_box(c) for c in light_box])}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {''.join([render_box(c) for c in black_box])}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
