import requests
import datetime
import html

ORG = "sollentunadans"
API_URL = f"https://dans.se/api/public/events/?org={ORG}&pw="

def fetch_events():
    """Hämtar event från CogWork Public API."""
    print("🔹 Hämtar schema från CogWork API...")
    resp = requests.get(API_URL)
    resp.raise_for_status()
    data = resp.json()
    events = data.get("data", [])
    print(f"✅ {len(events)} event mottagna.")
    return events


def filter_today(events):
    """Filtrerar fram event som har occurrence idag."""
    today = datetime.date.today()
    today_events = []

    for ev in events:
        name = ev.get("name", "").strip()
        place = ev.get("place", "").strip() or "Okänd sal"
        teachers = ", ".join(t.strip() for t in ev.get("teachers", []) if t.strip())
        for occ in ev.get("occurrences", []):
            start_str = occ.get("startDateTime", "")
            end_str = occ.get("endDateTime", "")
            if not start_str or not end_str:
                continue
            try:
                start_dt = datetime.datetime.fromisoformat(start_str)
                end_dt = datetime.datetime.fromisoformat(end_str)
            except Exception:
                continue
            if start_dt.date() == today:
                today_events.append({
                    "name": name,
                    "place": place,
                    "teacher": teachers,
                    "start": start_dt.strftime("%H:%M"),
                    "end": end_dt.strftime("%H:%M"),
                })
    print(f"📅 {len(today_events)} lektioner idag.")
    return today_events


def generate_html(events_today, date_str, weekday_sv):
    """Bygger HTML-sida för dagens schema."""
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
    margin: 0;
    padding: 2rem;
  }}
  h1 {{
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 0.3rem;
  }}
  h2 {{
    text-align: center;
    font-weight: normal;
    font-size: 1.2rem;
    margin-bottom: 2rem;
  }}
  .columns {{
    display: flex;
    justify-content: space-between;
    gap: 2rem;
  }}
  .column {{
    width: 48%;
  }}
  h3 {{
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }}
  .class {{
    background-color: #CDDCD1;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1rem;
  }}
  .class strong {{
    display: block;
    font-size: 1.1rem;
    margin-bottom: 0.2rem;
  }}
  .class small {{
    font-style: italic;
    color: #333;
  }}
</style>
</head>
<body>
<h1>Dagens Schema</h1>
<h2>{weekday_sv} {date_str}</h2>
<div class="columns">
"""

    for hall in ["Light Box", "Black Box"]:
        html_content += f'<div class="column"><h3>{hall}</h3>'
        filtered = [e for e in events_today if e["place"].lower() == hall.lower()]
        if filtered:
            for e in sorted(filtered, key=lambda x: x["start"]):
                html_content += f"""
<div class="class">
  <strong>{html.escape(e['name'])}</strong>
  <div>{e['start']}–{e['end']}</div>
  <small>{html.escape(e['teacher'])}</small>
</div>"""
        else:
            html_content += "<p>Inga lektioner.</p>"
        html_content += "</div>"

    html_content += """
</div>
</body>
</html>"""
    return html_content


def main():
    events = fetch_events()
    today_events = filter_today(events)
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")

    swedish_days = {
        "Monday": "Måndag", "Tuesday": "Tisdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag",
        "Saturday": "Lördag", "Sunday": "Söndag"
    }
    weekday_sv = swedish_days.get(today.strftime("%A"), today.strftime("%A"))

    html_output = generate_html(today_events, date_str, weekday_sv)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print("✅ index.html uppdaterad.")


if __name__ == "__main__":
    main()
