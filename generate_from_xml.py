import requests
import datetime
import html
import xml.etree.ElementTree as ET

# === Konfiguration ===
ORG = "sollentunadans"
XML_URL = f"https://minaaktiviteter.se/xml/?type=events&org={ORG}"

def fetch_events():
    """Hämtar alla event från XML-feeden"""
    print("🔹 Hämtar event från XML…")
    resp = requests.get(XML_URL)
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
            "name": name,
            "place": place,
            "teacher": teacher,
            "start_date": start_date,
            "end_date": end_date,
            "day_time": day_time,
            "start_time": start_time,
            "end_time": end_time
        })
    print(f"✅ {len(events)} event hittade.")
    return events

def generate_html(events_today, date_str):
    """Skapar HTML för dagens schema"""
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
  .columns {{
    display: flex;
    justify-content: space-between;
    gap: 2rem;
  }}
  .column {{
    width: 48%;
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
<div class="columns">
"""
    if not events_today:
        html_content += "<p>Inga lektioner idag.</p>"
    else:
        for location in ["Light Box", "Black Box"]:
            filtered = [e for e in events_today if e["place"] == location]
            html_content += f"""
  <div class="column">
    <table>
      <tr><th colspan="3">{location}</th></tr>
      <tr><th>Tid</th><th>Kurs</th><th>Lärare</th></tr>
"""
            for e in sorted(filtered, key=lambda x: x["start_time"]):
                html_content += f"""
      <tr>
        <td>{e['start_time'][:-3]}–{e['end_time'][:-3]}</td>
        <td>{html.escape(e['name'])}</td>
        <td>{html.escape(e['teacher'])}</td>
      </tr>
"""
            html_content += "</table></div>"
    html_content += """
</div>
</body>
</html>"""
    return html_content

def main():
    today = datetime.date.today()
    weekday = today.strftime("%a").lower()
    date_str = today.strftime("%A %Y-%m-%d")
    events = fetch_events()
    events_today = []

    # Matcha veckodag med svenska förkortningar i XML (Mån, Tis, Ons, Tors, Fre, Lör, Sön)
    swedish_days = {
        "mon": "Mån", "tue": "Tis", "wed": "Ons",
        "thu": "Tors", "fri": "Fre", "sat": "Lör", "sun": "Sön"
    }
    day_prefix = swedish_days.get(weekday, "")

    for e in events:
        if e["day_time"].startswith(day_prefix):
            events_today.append(e)

    html_output = generate_html(events_today, date_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)

    print(f"✅ Genererade {len(events_today)} lektioner för {date_str}.")

if __name__ == "__main__":
    main()
