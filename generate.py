import requests
from bs4 import BeautifulSoup
import datetime
import html

URL = "https://dans.se/view/schedule/?org=sollentunadans&theme=light"

def fetch_schedule():
    """Hämtar och tolkar schemat från dans.se (strukturbaserad parsing)."""
    print("🔹 Hämtar schema från dans.se...")
    resp = requests.get(URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    halls = {"Light Box": [], "Black Box": []}
    current_hall = None

    # Hitta alla rubriker (Light box, Black box)
    for hall_title in soup.find_all(["h2", "h3", "b"]):
        if hall_title.get_text(strip=True).lower() in ["light box", "black box"]:
            current_hall = hall_title.get_text(strip=True).title()
            next_sibling = hall_title.find_next_sibling()
            while next_sibling:
                if next_sibling.name == "div" and next_sibling.get_text(strip=True):
                    text = next_sibling.get_text(" ", strip=True)
                    # Typiskt format: "17.15 AP Step 2 Jazz"
                    if any(ch.isdigit() for ch in text):
                        parts = text.split(" ", 1)
                        if len(parts) == 2:
                            time, name = parts
                        else:
                            time, name = "", text
                        halls[current_hall].append({
                            "name": name.strip(),
                            "time": time.strip(),
                            "teacher": ""
                        })
                elif next_sibling.name in ["h2", "h3", "b"] and next_sibling.get_text(strip=True).lower() in ["light box", "black box"]:
                    break
                next_sibling = next_sibling.find_next_sibling()
    print(f"✅ Hittade {sum(len(v) for v in halls.values())} klasser totalt.")
    return halls


def generate_html(halls, date_str, weekday_sv):
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
    margin-bottom: 0.5rem;
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
        if hall in halls and halls[hall]:
            for cls in halls[hall]:
                html_content += f"""
<div class="class">
  <strong>{html.escape(cls['name'])}</strong>
  <div>{html.escape(cls['time'])}</div>
  <small>{html.escape(cls['teacher'])}</small>
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
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")

    swedish_days = {
        "Monday": "Måndag", "Tuesday": "Tisdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lördag", "Sunday": "Söndag"
    }
    weekday_en = today.strftime("%A")
    weekday_sv = swedish_days.get(weekday_en, weekday_en)

    halls = fetch_schedule()
    html_output = generate_html(halls, date_str, weekday_sv)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("✅ Skapade index.html med uppdaterat schema.")


if __name__ == "__main__":
    main()
