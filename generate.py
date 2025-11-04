import requests
from datetime import datetime
import pytz

# === Grundinställningar ===
ORG = "sollentunadans"
PW = ""
URL = f"https://dans.se/api/public/events/?org={ORG}&pw={PW}"

# === Hämta data från CogWork API ===
response = requests.get(URL)
data = response.json()
events = data.get("events", [])

# === Hämta dagens datum ===
tz = pytz.timezone("Europe/Stockholm")
today = datetime.now(tz).strftime("%Y-%m-%d")

# === Filtrera fram dagens lektionstillfällen ===
todays = []
for event in events:
    if not event.get("registration", {}).get("showing", False):
        continue

    place = event.get("place", "")
    course = event.get("name", "")
    teacher = event.get("instructorsName", "")

    # Hämta alla individuella tillfällen
    occasions = event.get("schedule", {}).get("occasions", [])
    for occ in occasions:
        start_str = occ.get("startDateTime")
        end_str = occ.get("endDateTime")
        if not start_str or not end_str:
            continue

        start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")

        if start.strftime("%Y-%m-%d") == today:
            todays.append({
                "time": f"{start.strftime('%H.%M')}–{end.strftime('%H.%M')}",
                "course": course,
                "teacher": teacher,
                "place": place
            })

# === Sortera efter tid ===
todays.sort(key=lambda x: x["time"])

# === Dela upp i salar ===
light_box = [t for t in todays if "Light" in t["place"]]
black_box = [t for t in todays if "Black" in t["place"]]
other = [t for t in todays if t not in light_box + black_box]

# === HTML-generator ===
def render_column(title, rows):
    if not rows:
        return f"<p><em>Inga klasser i {title} idag</em></p>"
    html = f"<table><tr><th colspan='3'>{title}</th></tr><tr><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>"
    for row in rows:
        html += f"<tr><td>{row['time']}</td><td>{row['course']}</td><td>{row['teacher']}</td></tr>"
    html += "</table>"
    return html

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
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            color: #000;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 2rem;
        }}
        th {{
            background-color: #a3c0b2;
            color: #000;
            padding: 1rem;
            text-align: left;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #ccc;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .columns {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-around;
            gap: 2rem;
        }}
        .column {{
            flex: 1 1 45%;
            min-width: 320px;
        }}
    </style>
</head>
<body>
    <h1>Dagens schema – {today}</h1>
    <div class='columns'>
        <div class='column'>{render_column("Light Box", light_box)}</div>
        <div class='column'>{render_column("Black Box", black_box)}</div>
    </div>
    <div class='column'>{render_column("Övriga salar", other)}</div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
