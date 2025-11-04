import requests
import datetime
import html

ORG = "sollentunadans"
PW = ""
BASE = "https://dans.se/api/public"

def fetch_events():
    """Hämtar alla event."""
    resp = requests.get(f"{BASE}/events/?org={ORG}&pw={PW}")
    data = resp.json()
    return data.get("events", [])

def fetch_event_details(event_key):
    """Hämtar detaljer (inklusive occasions) för ett specifikt event."""
    resp = requests.get(f"{BASE}/event/?org={ORG}&pw={PW}&key={event_key}")
    data = resp.json()
    events = data.get("events", [])
    return events[0] if events else None

def generate_html(events_today):
    """Skapar HTML-sida med dagens schema."""
    html_content = """<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<title>Dagens schema | Sollentuna Dans & Scenskola</title>
<link href="https://fonts.googleapis.com/css2?family=Agrandir&display=swap" rel="stylesheet">
<style>
  body {
    font-family: 'Agrandir', sans-serif;
    background-color: #fff;
    color: #000;
    margin: 0;
    padding: 2rem;
  }
  h1 {
    color: #000;
    font-size: 2rem;
    margin-bottom: 1.5rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1.5rem;
  }
  .card {
    background-color: #CDDCD1;
    border-radius: 20px;
    padding: 1rem 1.2rem;
    box-shadow: 0 3px 6px rgba(0,0,0,0.1);
  }
  .time {
    font-weight: bold;
    color: #000;
  }
  .teacher {
    color: #333;
    font-size: 0.95rem;
  }
  .place {
    color: #000;
    font-size: 0.95rem;
    margin-top: 0.4rem;
  }
</style>
</head>
<body>
<h1>Dagens schema</h1>
<div class="grid">
"""
    if not events_today:
        html_content += "<p>Inga lektioner idag.</p>"
    else:
        for e in sorted(events_today, key=lambda x: x['start']):
            html_content += f"""
    <div class="card">
      <div class="time">{e['start'].split(' ')[1][:-3]}–{e['end'].split(' ')[1][:-3]}</div>
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


def main():
    today = datetime.date.today().isoformat()
    events = fetch_events()
    events_today = []

    print(f"Hämtar schema för {today}... ({len(events)} event funna)")

    for ev in events:
        key = ev.get("key")
        if not key:
            continue

        details = fetch_event_details(key)
        if not details:
            continue

        schedule = details.get("schedule", {})
        occasions = schedule.get("occasions", [])
        for occ in occasions:
            if occ.get("startDateTime", "").startswith(today):
                events_today.append({
                    "name": details.get("name", "Okänd kurs"),
                    "teacher": details.get("instructorsName", ""),
                    "place": details.get("place", ""),
                    "start": occ.get("startDateTime"),
                    "end": occ.get("endDateTime")
                })

    html_output = generate_html(events_today)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"Genererade {len(events_today)} lektioner i dagens schema.")


if __name__ == "__main__":
    main()
