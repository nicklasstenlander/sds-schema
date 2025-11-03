import requests
from datetime import datetime, timedelta
import pytz

URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
response = requests.get(URL)
data = response.json()

events = data.get("events", [])
tz = pytz.timezone("Europe/Stockholm")

# Hitta första dag med synliga kurser
target_date = None
filtered = []
for offset in range(0, 7):
    date_to_check = (datetime.now(tz) + timedelta(days=offset)).strftime("%Y-%m-%d")
    filtered = [
        {
            "time": e["schedule"]["start"]["time"][:5] + "–" + e["schedule"]["end"]["time"][:5],
            "course": e.get("name", ""),
            "teacher": e.get("instructorsName", ""),
            "place": e.get("place", "")
        }
        for e in events
        if e.get("registration", {}).get("showing", False)
        and e.get("schedule", {}).get("start", {}).get("date") == date_to_check
    ]
    if filtered:
        target_date = date_to_check
        break

# Sortera och dela upp per sal
filtered.sort(key=lambda x: x["time"])
light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

# Render HTML per kolumn
def render_column(title, rows):
    html = f"<div class='column'><table><tr><th colspan='3'>{title}</th></tr><tr><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>"
    for row in rows:
        html += f"<tr><td>{row['time']}</td><td>{row['course']}</td><td>{row['teacher']}</td></tr>"
    html += "</table></div>"
    return html

# HTML-sida
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #fff;
            color: #000;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .columns {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 2rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th {{
            background-color: #a3c0b2;
            padding: 1rem;
            text-align: left;
            font-size: 1.25rem;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #ccc;
            font-size: 1.1rem;
        }}
        .column {{
            width: 45%;
            min-width: 300px;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema {f"({target_date})" if target_date else ""}</h1>
    <div class="columns">
        {render_column("Light Box", light_box)}
        {render_column("Black Box", black_box)}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
