import requests
import datetime
import html
import json

# === KONFIGURATION ===
ORG = "sollentunadans"
API_URL = f"https://dans.se/api/public/events/?org={ORG}&pw="
DATE_FORMAT = "%Y-%m-%d"

# === Hjälpfunktion för loggning ===
def log(msg):
    print(msg)
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")

# === Hämta event från CogWork JSON API ===
def fetch_events():
    log("🔹 Hämtar data från CogWork JSON API...")
    resp = requests.get(API_URL)
    resp.raise_for_status()
    data = resp.json()

    with open("debug_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    events = []
    for ev in data.get("events", []):
        name = ev.get("title", "")
        place = ev.get("place", "")
        teacher = ", ".join([t.get("name", "") for t in ev.get("instructors", [])])
        occasions = ev.get("occasions", [])
        for occ in occasions:
            start = occ.get("startDateTime")
            end = occ.get("endDateTime")
            if not (start and end):
                continue
            events.append({
                "name": name,
                "place": place,
                "teacher": teacher,
                "start": start,
                "end": end
            })
    log(f"✅ Totalt {len(events)} schemalagda tillfällen hittade.")
    return events

# === Skapa HTML för dagens schema ===
def generate_html(events_today, date_str, weekday_sv):
    html_content = f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<title>Dagens Schema | Sollentuna Dans & Scenskola</title>
<link href="https://fonts.googleapis.com/css2?family=Agrandir&display=swap" rel="stylesheet">
<meta http-equiv="refresh" content="600">
<style>
  body {{
    font-family: 'Agrandir', sans-serif;
    background-color: #fff;
    color: #000;
    margin: 2rem;
  }}
  h1 {{
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
  }}
  h2 {{
    text-align: center;
    font-size: 1.3rem;
    color: #333;
    margin-top: 0;
    margin-bottom: 2rem;
  }}
  .columns {{
    display: flex;
    justify-content: space-between;
    gap: 2rem;
  }}
  .column {{
    flex: 1;
  }}
  h3 {{
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }}
  .lesson {{
    background-color: #CDDCD1;
    padding: 1rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1rem;
  }}
  .lesson strong {{
    display: block;
    font-size: 1.1rem;
  }}
  .lesson em {{
    color: #333;
  }}
</style>
</head>
<body>
<h1>Dagens Schema</h1>
<h2>{weekday_sv} {date_str}</h2>
<div class="columns">
"""

    if not events_today:
        html_content += "<p>Inga lektioner idag.</p>"
    else:
        halls = {"Light Box": [], "Black Box": []}
        for e in events_today:
            hall = e["place"] or "Light Box"
            if hall not in halls:
                halls[hall] = []
            halls[hall].append(e)

        for hall_name in ["Light Box", "Black Box"]:
            html_content += f"<div class='column'><h3>{hall_name}</h3>"
            lessons = sorted(halls.get(hall_name, []), key=lambda x: x["start"])
            for e in lessons:
                start_time = e["start"][11:16]
                end_time = e["end"][11:16]
                html_content += f"""
  <div class="lesson">
    <strong>{html.escape(e['name'])}</strong>
    <div>{start_time}–{end_time}</div>
    <em>{html.escape(e['teacher'])}</em>
  </div>"""
            html_content += "</div>"

    html_content += """
</div>
</body>
</html>"""
    return html_content

# === Huvudflöde ===
def main():
    today = datetime.date.today()
    date_str = today.strftime(DATE_FORMAT)

    weekday_sv = {
        "Monday": "Måndag", "Tuesday": "Tisdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lördag", "Sunday": "Söndag"
    }[today.strftime("%A")]

    events = fetch_events()

    # Filtrera ut dagens
    events_today = []
    for e in events:
        if e["start"].startswith(date_str):
            events_today.append(e)

    html_output = generate_html(events_today, date_str, weekday_sv)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    log(f"✅ Genererade {len(events_today)} lektioner för {date_str}.")

if __name__ == "__main__":
    main()
