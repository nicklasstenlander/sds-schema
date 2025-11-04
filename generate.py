import requests
import datetime
import html
import json

ORG = "sollentunadans"
PW = ""
BASE_URL = "https://dans.se/api/public"

def log(msg):
    print(msg)
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")

def fetch_all_events():
    url = f"{BASE_URL}/events/?org={ORG}&pw={PW}"
    log(f"🔹 Hämtar kurslista: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    with open("debug_events.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data.get("events", [])

def fetch_event_details(event_key):
    url = f"{BASE_URL}/event/?org={ORG}&pw={PW}&verbose=1&key={event_key}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

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
    margin-bottom: 0.2rem;
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


def main():
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    weekday_sv = {
        "Monday": "Måndag", "Tuesday": "Tisdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lördag", "Sunday": "Söndag"
    }[today.strftime("%A")]

    events = fetch_all_events()
    events_today = []

    for i, ev in enumerate(events):
        event_key = ev.get("key")
        if not event_key:
            continue
        log(f"🔍 Hämtar detaljer ({i+1}/{len(events)}): {ev.get('title')}")
        details = fetch_event_details(event_key)
        if "error" in details:
            log(f"⚠️ Misslyckades för {ev.get('title')}: {details['error']}")
            continue

        try:
            occasions = details.get("events", [])[0].get("schedule", {}).get("occasions", [])
            for occ in occasions:
                start = occ.get("startDateTime", "")
                end = occ.get("endDateTime", "")
                if start.startswith(date_str):
                    events_today.append({
                        "name": ev.get("title", ""),
                        "place": details.get("events", [])[0].get("place", ""),
                        "teacher": ", ".join([t.get("name", "") for t in details.get("events", [])[0].get("instructors", [])]),
                        "start": start,
                        "end": end
                    })
        except Exception as e:
            log(f"⚠️ Fel vid parsning av {ev.get('title')}: {e}")

    html_output = generate_html(events_today, date_str, weekday_sv)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    log(f"✅ Genererade {len(events_today)} lektioner för {date_str}.")


if __name__ == "__main__":
    main()
