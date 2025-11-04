import requests
import datetime
import html
import xml.etree.ElementTree as ET

ORG = "sollentunadans"
XML_URL = f"https://minaaktiviteter.se/xml/?type=events&org={ORG}&pw="

def fetch_events():
    """Hämtar alla event från XML-flödet"""
    print("🔹 Hämtar event från MinaAktiviteter …")
    resp = requests.get(XML_URL)
    resp.raise_for_status()
    xml_text = resp.text

    # Debug
    print(f"📡 Statuskod: {resp.status_code}")
    print(f"🔍 Förhandsvisning av svar: {xml_text[:500]}")

    root = ET.fromstring(xml_text)
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

    print(f"✅ {len(events)} event hittade.")
    return events


def generate_html(events_today, date_str):
    """Skapar HTML med dagens schema"""
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
    font-size: 1.1rem;
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
</tr>
"""
        html_content += "</table>"
    html_content += "</body></html>"
    return html_content


def main():
    today = datetime.date.today()
    date_str = today.strftime("%A %Y-%m-%d")
    events = fetch_events()

    events_today = []
    weekday_sv = today.strftime("%A")  # "Tisdag"
    for e in events:
        # 1. matcha veckodag i day_time
        if weekday_sv.lower() in e["day_time"].lower():
            # 2. kolla om vi är mellan start och slutdatum
            try:
                start = datetime.datetime.strptime(e["start_date"], "%Y-%m-%d").date()
                end = datetime.datetime.strptime(e["end_date"], "%Y-%m-%d").date()
                if start <= today <= end:
                    events_today.append(e)
            except Exception:
                pass

    html_output = generate_html(events_today, date_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"✅ Genererade {len(events_today)} lektioner för {date_str}.")


if __name__ == "__main__":
    main()
