import requests
import datetime
import html
import xml.etree.ElementTree as ET

ORG = "sollentunadans"
XML_URL = f"https://minaaktiviteter.se/xml/?type=events&org={ORG}&pw="

def log(msg):
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")
    print(msg)

def fetch_events():
    log("🔹 Hämtar XML…")
    resp = requests.get(XML_URL)
    log(f"📡 Statuskod: {resp.status_code}")
    log(f"🔍 Förhandsvisning: {resp.text[:300]}")
    with open("debug_xml.txt", "w", encoding="utf-8") as f:
        f.write(resp.text)

    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    events = []
    for ev in root.findall(".//event"):
        name = ev.findtext("title", "")
        place = ev.findtext("place", "")
        teacher = ev.findtext(".//instructors/combinedTitle", "")
        start_date = ev.findtext(".//schedule/startDate", "")
        end_date = ev.findtext(".//schedule/endDate", "")
        day_time = ev.findtext(".//schedule/dayAndTime", "")
        start_time = ev.findtext(".//schedule/startTime", "")
        end_time = ev.findtext(".//schedule/endTime", "")
        events.append({
            "name": name.strip(),
            "place": place.strip(),
            "teacher": teacher.strip(),
            "start_date": start_date.strip(),
            "end_date": end_date.strip(),
            "day_time": day_time.strip(),
            "start_time": start_time.strip(),
            "end_time": end_time.strip()
        })
    log(f"✅ {len(events)} event hittade.")
    return events

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
        html_content += "<table><tr><th>Salar</th><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>"
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
    events_today = []
    try:
        events = fetch_events()
        weekday_sv = today.strftime("%A")
        for e in events:
            if weekday_sv.lower() in e["day_time"].lower():
                try:
                    start = datetime.datetime.strptime(e["start_date"], "%Y-%m-%d").date()
                    end = datetime.datetime.strptime(e["end_date"], "%Y-%m-%d").date()
                    if start <= today <= end:
                        events_today.append(e)
                except Exception as err:
                    log(f"⚠️ Datumfel i {e['name']}: {err}")
        log(f"🎯 {len(events_today)} event matchar dagens datum ({date_str}).")
    except Exception as e:
        log(f"💥 FEL: {e}")

    # skapa alltid index.html
    html_output = generate_html(events_today, date_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    log("📁 index.html skapad.")

if __name__ == "__main__":
    main()
