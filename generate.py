import requests
from datetime import datetime
import pytz

URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()

events = data.get("events", [])
now = datetime.now(pytz.timezone("Europe/Stockholm"))
today_str = now.strftime("%Y-%m-%d")
today_dow = now.weekday()  # Måndag = 0, Söndag = 6

filtered = []
for e in events:
    if not e.get("registration", {}).get("showing", False):
        continue

    sched = e.get("schedule", {})
    start_date = sched.get("start", {}).get("date")
    end_date = sched.get("end", {}).get("date")
    dow = int(sched.get("start", {}).get("dayOfWeek", -1))

    if not start_date or not end_date or dow != today_dow:
        continue

    # Kontrollera att idag är inom kursens datumintervall
    if start_date <= today_str <= end_date:
        filtered.append({
            "time": sched["start"]["time"][:5] + "–" + sched["end"]["time"][:5],
            "course": e.get("name", ""),
            "teacher": e.get("instructorsName", ""),
            "place": e.get("place", "")
        })

# Sortera och rendera
filtered.sort(key=lambda x: x["time"])
light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

def render_column(rows):
    html = ""
    for row in rows:
        html += f"<tr><td>{row['time']}</td><td>{row['course']}</td><td>{row['teacher']}</td></tr>"
    return html

html_content = f"""
<!DOCTYPE html>
<html lang='sv'>
<head>
    <meta charset='UTF-8'>
    <meta http-equiv='refresh' content='600'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Dagens Schema</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #fff;
            color: #000;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 2rem;
        }}
        th {{
            background-color: #a3c0b2;
            padding: 1rem;
            text-align: left;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #ccc;
        }}
        .column {{
            width: 48%;
            float: left;
            margin: 1%;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <div class='column'>
        <table>
            <tr><th colspan='3'>Light Box</th></tr>
            <tr><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>
            {render_column(light_box)}
        </table>
    </div>
    <div class='column'>
        <table>
            <tr><th colspan='3'>Black Box</th></tr>
            <tr><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>
            {render_column(black_box)}
        </table>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
