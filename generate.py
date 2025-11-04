import requests
import datetime
import html
import xml.etree.ElementTree as ET

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
        start_date = ev.findtext(".//schedule/startDate", "").strip()
        end_date = ev.findtext(".//schedule/endDate", "").strip()
        day_and_time = ev.findtext(".//schedule/dayAndTime", "").strip()
        start_time = ev.findtext(".//schedule/startTime", "").strip()
        end_time = ev.findtext(".//schedule/endTime", "").strip()

        events.append({
            "name": title,
            "place": place,
            "teacher": teacher,
            "start_date": start_date,
            "end_date": end_date,
            "day_and_time": day_and_time,
            "start_time": start_time,
            "end_time": end_time
        })
    log(f"✅ {len(events)} event hittade i XML.")
    return events

def generate_html(events_today, date_str):
    """Bygger HTML-sida för dagens schema."""
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
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th {{
    background-color: #a3c0b2;
    text-align: left;
    padding: 0.75rem;
  }}
  td {{
    border-bottom: 1px solid #ccc;
    padding: 0.6rem;
  }}
</style>
</head>
<body>
<h1>Dagens schema – {date_str}</h1>
"""
    if not events_today:
        html_content += "<p>Inga lektioner idag.</p>"
    else:
        html_content += "<table><tr><th>Sal</th><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>"
        for e in sorted(events_today, key=lambda x: x["start_time"]):
            html_content += f"""
<tr>
  <td>{html.escape(e['place'])}</td>
  <td>{e['start_time'][:-3]}–{e['end_time'][:-3]}</td>
  <td>{html.escape(e['name'])}</td>
  <td>{html.escape(e['teacher'])}</td>
</tr>"""
        html_content += "</table>"
    html_content += "</body></html>"
    return html_content

def main():
    today = datetime.date.today()
    date_str = today.strftime("%A %Y-%m-%d")
    events = fetch_events()
    events_today = []

    swedish_days = {
        "Mon": "Mån", "Tue": "Tis", "Wed": "Ons", "Thu": "Tors",
        "Fri": "Fre", "Sat": "Lör", "Sun": "Sön"
    }
    today_prefix = swedish_days.get(today.strftime("%a"), "")

    for e in events:
        if e["day_and_time"].startswith(today_prefix):
            events_today.append(e)

    html_output = generate_html(events_today, date_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    log(f"📄 index.html genererad – {len(events_today)} lektioner för {date_str}")

if __name__ == "__main__":
    main()
