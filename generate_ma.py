import requests
import datetime
import html
import xml.etree.ElementTree as ET
import json

# === Konfiguration ===
ORG = "sollentunadans"
PW = ""  # lämnas tom enligt din setup
BASE = "https://minaaktiviteter.se/api/public"
XML_URL = f"https://minaaktiviteter.se/xml/?type=events&org={ORG}"

# === Hämta alla event från XML ===
def fetch_event_keys():
    print("🔹 Hämtar eventlista från XML...")
    response = requests.get(XML_URL)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    events = []
    for ev in root.findall(".//event"):
        key = ev.get("key")
        title = ev.findtext("title", default="Okänd kurs")
        place = ev.findtext("place", default="")
        teacher = ev.find(".//instructors/combinedTitle")
        teacher_name = teacher.text if teacher is not None else ""
        events.append({
            "key": key,
            "name": title,
            "place": place,
            "teacher": teacher_name
        })
    print(f"✅ Hittade {len(events)} event i XML-feed.")
    return events

# === Hämta detaljer (inkl. occasions) från API ===
def fetch_event_details(event_key):
    url = f"{BASE}/event/?org={ORG}&pw={PW}&key={event_key}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    if "events" not in data:
        return None
    return data["events"][0] if data["events"] else None

# === Skapa HTML för dagens schema ===
def generate_html(events_today, date_str):
    html_content = f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<title>Dagens schema | Sollentuna Dans & Scenskola</title>
<link href="https://fonts.googleapis.com/css2?family=Agrandir&display=swap" rel="stylesheet">
<meta http-equiv="refresh" content="600">
<style>
  body {{
    font-family: 'Agrandir', sans-serif;
    background-color: #fff;
    color: #000;
    margin: 0;
    padding: 2rem;
  }}
  h1 {{
    color: #000;
    font-size: 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }}
  .card {{
    background-color: #CDDCD1;
    border-radius: 20px;
    padding: 1.2rem 1.5rem;
    box-shadow: 0 3px 6px rgba(0,0,0,0.1);
  }}
  .time {{
    font-weight: bold;
    color: #000;
  }}
  .name {{
    font-size: 1.1rem;
    margin-top: 0.3rem;
  }}
  .teacher, .place {{
    color: #333;
    font-size: 0.95rem;
    margin-top: 0.2rem;
  }}
</style>
</head>
<body>
<h1>Dagens schema – {date_str}</h1>
<div class="grid">
"""
    if not events_today:
        html_content += "<p>Inga lektioner idag.</p>"
    else:
        for e in sorted(events_today, key=lambda x: x['start']):
            start = e['start'].split(' ')[1][:-3]
            end = e['end'].split(' ')[1][:-3]
            html_content += f"""
  <div class="card">
    <div class="time">{start}–{end}</div>
    <div class="name">{html.escape(e['name'])}</div>
    <div class="teacher">{html.escape(e['teacher'] or '')}</div>
    <div class="place">{html.escape(e['place'] or '')}</div>
  </div>
"""
    html_content += """
</div>
</body>
</html>"""
    return html_content


# === Huvudfunktion ===
def main():
    today = datetime.date.today().isoformat()
    today_str = datetime.date.today().strftime("%A %Y-%m-%d")
    events_today = []
    debug_data = []

    events = fetch_event_keys()

    for ev in events:
        key = ev["key"]
        details = fetch_event_details(key)
        if not details:
            continue

        schedule = details.get("schedule", {})
        occasions = schedule.get("occasions", [])
        if occasions:
            debug_data.append({"event": ev["name"], "occasions": occasions})

        for occ in occasions:
            start = occ.get("startDateTime", "")
            if start.startswith(today):
                events_today.append({
                    "name": ev["name"],
                    "teacher": ev["teacher"],
                    "place": ev["place"],
                    "start": occ.get("startDateTime"),
                    "end": occ.get("endDateTime")
                })

    # --- Debug-logg ---
    with open("debug_ma.json", "w", encoding="utf-8") as f:
        json.dump(debug_data, f, indent=2, ensure_ascii=False)

    # --- Skapa HTML ---
    html_output = generate_html(events_today, today_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"✅ Genererade {len(events_today)} lektioner för dagens datum {today}.")


if __name__ == "__main__":
    main()
