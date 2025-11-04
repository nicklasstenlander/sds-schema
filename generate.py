import requests
import datetime
import html
import xml.etree.ElementTree as ET

# === Konfiguration ===
ORG = "sollentunadans"
XML_URL = f"https://dans.se/xml/?type=events&pw=&org={ORG}"

def fetch_events():
    """Hämtar alla event från dans.se XML-feed."""
    print("🔹 Hämtar XML-data från dans.se …")
    resp = requests.get(XML_URL)
    resp.raise_for_status()
    xml_text = resp.text
    root = ET.fromstring(xml_text)

    events = []
    for ev in root.findall(".//event"):
        title = ev.findtext("title", "").strip()
        place = ev.findtext("place", "").strip()
        teacher = ev.findtext(".//instructors/combinedTitle", "").strip()
        day_and_time = ev.findtext(".//schedule/dayAndTime", "").strip()
        start_time = ev.findtext(".//schedule/startTime", "").strip()
        end_time = ev.findtext(".//schedule/endTime", "").strip()

        events.append({
            "name": title,
            "place": place,
            "teacher": teacher,
            "day_and_time": day_and_time,
            "start_time": start_time,
            "end_time": end_time
        })

    print(f"✅ {len(events)} event hittade i XML.")
    return events

def generate_html(events_today, date_str, weekday_sv):
    """Bygger HTML med två kolumner (Light Box / Black Box)."""
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
    margin-bottom: 0.2rem;
  }}
  h2 {{
    text-align: center;
    font-size: 1.3rem;
    font-weight: 400;
    margin-bottom: 2rem;
  }}
  .columns {{
    display: flex;
    justify-content: center;
    gap: 3rem;
  }}
  .column {{
    width: 40%;
  }}
  h3 {{
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }}
  .lesson {{
    background-color: #CDDCD1;
    padding: 1rem;
    border-radius: 12px;
    margin-bottom: 1rem;
  }}
  .lesson strong {{
    font-size: 1.1rem;
  }}
  .lesson em {{
    display: block;
    margin-top: 0.3rem;
  }}
</style>
</head>
<body>
<h1>Dagens Schema</h1>
<h2>{weekday_sv} {date_str}</h2>
"""

    if not events_today:
        html_content += "<p>Inga lektioner idag.</p>"
    else:
        # Dela upp efter sal
        halls = {"Light Box": [], "Black Box": []}
        for e in events_today:
            hall = e["place"] or "Light Box"
            if hall not in halls:
                halls[hall] = []
            halls[hall].append(e)

        html_content += '<div class="columns">'
        for hall in ["Light Box", "Black Box"]:
            lessons = sorted(halls.get(hall, []), key=lambda x: x["start_time"])
            html_content += f'<div class="column"><h3>{hall}</h3>'
            for e in lessons:
                html_content += f"""
<div class="lesson">
  <strong>{html.escape(e['name'])}</strong><br>
  {html.escape(e['day_and_time'])} {e['start_time'][:-3]}–{e['end_time'][:-3]}<br>
  <em>{html.escape(e['teacher'])}</em>
</div>
"""
            html_content += "</div>"
        html_content += "</div>"

    html_content += "</body></html>"
    return html_content

def main():
    today = datetime.date.today()
    weekday = today.strftime("%a").lower()
    date_str = today.strftime("%Y-%m-%d")

    swedish_days = {
        "mon": "Måndag",
        "tue": "Tisdag",
        "wed": "Onsdag",
        "thu": "Torsdag",
        "fri": "Fredag",
        "sat": "Lördag",
        "sun": "Söndag",
    }
    weekday_sv = swedish_days.get(weekday, weekday.capitalize())

    events = fetch_events()
    events_today = []
    for e in events:
        if any(e["day_and_time"].startswith(prefix) for prefix in [weekday_sv[:3], weekday_sv[:2]]):
            events_today.append(e)

    html_output = generate_html(events_today, date_str, weekday_sv)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"✅ Genererade schema med {len(events_today)} lektioner för {weekday_sv} ({date_str}).")

if __name__ == "__main__":
    main()
