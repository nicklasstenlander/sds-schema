import requests
from datetime import datetime
import pytz

# === KONSTANTER ===
URL = "https://dans.se/api/public/events/?org=sollentunadans&pw="
WEEKDAY_SV = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]

# === HÄMTA OCH FILTRERA DATA ===
today_dt = datetime.now(pytz.timezone("Europe/Stockholm"))
today_dow = today_dt.weekday()
today_str = today_dt.strftime("%Y-%m-%d")
today_sv = WEEKDAY_SV[today_dow]

response = requests.get(URL)
events = response.json().get("events", [])

filtered = []
for e in events:
    sched = e.get("schedule", {})
    start = sched.get("start", {})
    if start.get("dayOfWeek") == today_dow:
        filtered.append({
            "course": e.get("name", ""),
            "daytime": f"{today_sv[:3]} {start['time'][:5]}–{sched['end']['time'][:5]}",
            "teacher": e.get("instructorsName", ""),
            "place": e.get("place", "")
        })

filtered.sort(key=lambda x: x["daytime"])
light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

# === RENDERING ===
def render_column(cards):
    html = ""
    for c in cards:
        html += f"""
        <div class='course-card'>
            <strong>{c['course']}</strong>
            {c['daytime']}
            <em>{c['teacher']}</em>
        </div>"""
    return html

html_content = f"""<!DOCTYPE html>
<html lang='sv'>
<head>
    <meta charset='UTF-8'>
    <meta http-equiv='refresh' content='600'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>Dagens schema</title>
    <style>
        body {{
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background-color: #fff;
            color: #000;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-size: 2rem;
        }}
        .column {{
            width: 48%;
            float: left;
            margin: 1%;
        }}
        .column h2 {{
            text-align: left;
        }}
        .course-card {{
            background-color: #d3ded6;
            padding: 1rem;
            border-radius: 16px;
            margin-bottom: 1rem;
        }}
        .course-card strong {{
            display: block;
            font-size: 1.2rem;
        }}
        .course-card em {{
            display: block;
            margin-top: 0.3rem;
            font-style: italic;
            color: #333;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema – {today_sv} {today_str}</h1>
    <div class='column'>
        <h2>Light Box</h2>
        {render_column(light_box)}
    </div>
    <div class='column'>
        <h2>Black Box</h2>
        {render_column(black_box)}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
