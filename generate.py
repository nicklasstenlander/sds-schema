import requests
import datetime
import html
import xml.etree.ElementTree as ET

# === Grundinställningar ===
ORG = "sollentunadans"
XML_URL = f"https://minaaktiviteter.se/xml/?type=events&org={ORG}&pw="

def log(msg):
    """Skriv debug-logg till fil och terminal."""
    print(msg)
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")

def fetch_events():
    """Hämtar alla event från MinaAktiviteter XML-feed."""
    log("🔹 Hämtar XML-data…")
    resp = requests.get(XML_URL)
    resp.raise_for_status()
    xml_text = resp.text
    with open("debug_xml.txt", "w", encoding="utf-8") as f:
        f.write(xml_text)

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

    log(f"✅ {len(events)} event hittade i XML.")
    return events

def generate_html(events_today, date_str, weekday_sv):
    """Bygger HTML-sida för dagens schema, med layout som i exemplet."""
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
    background-color: #ffffff;
    color: #000;
    margin: 0;
    padding: 2rem;
  }}
  h1 {{
    text-align: center;
    font-size: 2.8rem;
    margin: 0;
  }}
  h2.date {{
    text-align: center;
    font-size: 1.4rem;
    margin-top: 0.4rem;
    color: #333;
  }}
  .wrapper {{
    display: flex;
    justify-content: space-between;
    gap: 2rem;
    margin-top: 3rem;
  }}
  .column {{
    width: 48%;
  }}
  .column h2 {{
    font-size: 1.6rem;
    margin-bottom: 1rem;
  }}
  .lesson {{
    background-color: #CDDCD1;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
  }}
  .lesson strong {{
    display: block;
    font-size: 1.2rem;
    margin-bottom: 0.3rem;
  }}
  .lesson .time {{
    font-size: 1rem;
    margin-bottom: 0.2rem;
  }}
  .lesson .teacher {{
    font-style: italic;
    font-size: 1rem;
  }}
</style>
</head>
<body>
  <h1>Dagens Schema</h1>
  <h2 class="date">{weekday_sv} {date_str}</h2>
"""

    # Filtrera bara Light Box och Black Box
    filtered = [e for e in events_today if e["place"] in ["Light Box", "Black Box"]]
    halls = {"Light Box": [], "Black Box": []}
    for e in filtered:
        halls.setdefault(e["place"], []).append(e)

    html_content += '<div class="wrapper">'
    for hall in ["Light Box", "Black Box"]:
        lessons = halls.get(hall, [])
        html_content += f'<div class="column"><h2>{hall}</h2>'
        for e in sorted(lessons, key=lambda x: x["start_time"]):
            html_content += f"""
    <div class="lesson">
      <strong>{html.escape(e['name'])}</strong>
      <div class="time">{weekday_sv[:3]} {e['start_time'][:-3]}–{e['end_time'][:-3]}</div>
      <div class="teacher">{html.escape(e['teacher'])}</div>
    </div>
"""
        html_content += "</div>"
    html_content += "</div></body></html>"
    return html_content

def main():
    today = datetime.date.today()
    weekday_en = today.strftime("%a")
    weekday_sv = {
        "Mon": "Måndag", "Tue": "Tisdag", "Wed": "Onsdag",
        "Thu": "Torsdag", "Fri": "Fredag", "Sat": "Lördag", "Sun": "Söndag"
    }.get(weekday_en, weekday_en)

    date_str = today.strftime("%Y-%m-%d")
    events = fetch_events()
    events_today = []

    swedish_days = {
        "Mon": "Mån", "Tue": "Tis", "Wed": "Ons", "Thu": "Tors",
        "Fri": "Fre", "Sat": "Lör", "Sun": "Sön"
    }
    today_prefix = swedish_days.get(weekday_en, "")

    for e in events:
        if e["day_and_time"].startswith(today_prefix):
            events_today.append(e)

    html_output = generate_html(events_today, date_str, weekday_sv)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    log(f"📄 index.html genererad – {len(events_today)} lektioner för {weekday_sv} {date_str}")

if __name__ == "__main__":
    main()
