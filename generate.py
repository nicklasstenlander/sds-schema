import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date
import pytz
import html

# =========================
# 1️⃣ Konfiguration
# =========================
ORG = "sollentunadans"
# Vi använder XML-feeden eftersom den innehåller mer komplett veckodata
URL = f"https://minaaktiviteter.se/xml/?type=events&pw=&org={ORG}"

TZ = pytz.timezone("Europe/Stockholm")
now = datetime.now(TZ)
today_date = now.date()

# CogWork XML använder siffror: 1=Måndag ... 7=Söndag
# Python använder: 0=Måndag ... 6=Söndag
# Så vi plussar på 1 på Pythons siffra.
today_dow_cogwork = str(now.weekday() + 1) 

VECKODAGAR = [
    "Måndag", "Tisdag", "Onsdag",
    "Torsdag", "Fredag", "Lördag", "Söndag"
]
MÅNADER = [
    "januari", "februari", "mars", "april", "maj", "juni",
    "juli", "augusti", "september", "oktober", "november", "december"
]

today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

def parse_xml_date(d_str):
    """Parsar datum från XML (ofta YYYY-MM-DD eller med tid)."""
    if not d_str: return None
    # Ta bara de första 10 tecknen (YYYY-MM-DD)
    clean_date = d_str[:10]
    try:
        return datetime.strptime(clean_date, "%Y-%m-%d").date()
    except ValueError:
        return None

# =========================
# 2️⃣ Hämta XML-data
# =========================
print(f"⏳ Hämtar XML-schema för {today_label}...")
try:
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; InfoScreen/1.0)'}
    resp = requests.get(URL, headers=headers, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
except Exception as e:
    print(f"❌ Kunde inte hämta XML: {e}")
    exit(1)

events = root.findall(".//event")
print(f"📥 Analyserar {len(events)} kurser från XML...")

filtered = []

for event in events:
    # 1. Hämta Grundinfo
    # I XML heter det <title>, inte <name>
    title = event.findtext("title") or event.findtext("name") or "Namnlös kurs"
    place = event.findtext("place") or ""
    instructor = event.findtext("instructorsName") or "" # Ibland ligger det under <instructor>

    # 2. Filtrera på sal direkt (effektivisering)
    place_lower = place.lower()
    if "light box" in place_lower:
        final_place = "Light Box"
    elif "black box" in place_lower:
        final_place = "Black Box"
    else:
        continue # Inte rätt sal

    # 3. Datumlogik (Detta är den kluriga delen i XML)
    # Vi måste kolla om kursen går IDAG.
    
    shows_today = False
    start_time_str = ""
    end_time_str = ""

    # Steg A: Kolla specifika datum (om det finns <dates>-lista)
    # XML struktur kan variera, vi letar brett.
    schedule = event.find("schedule")
    if schedule is not None:
        # -- Metod 1: Perioder (Veckokurser) --
        # Ofta ligger infon i <period> -> <dayOfWeek>
        periods = schedule.findall(".//period")
        for p in periods:
            dow = p.findtext("dayOfWeek")
            s_date_str = p.findtext("startDate")
            e_date_str = p.findtext("endDate")
            
            # Hämta tid
            t_start = p.findtext("startTime")
            t_end = p.findtext("endTime")

            s_date = parse_xml_date(s_date_str)
            e_date = parse_xml_date(e_date_str)

            # Matchar veckodag?
            if dow == today_dow_cogwork:
                # Matchar datumintervall?
                if s_date and e_date:
                    if s_date <= today_date <= e_date:
                        shows_today = True
                        start_time_str = t_start
                        end_time_str = t_end
                        break # Träff!
                elif s_date: # Bara startdatum (tillsvidare)
                     if today_date >= s_date:
                        shows_today = True
                        start_time_str = t_start
                        end_time_str = t_end
                        break

        # -- Metod 2: Specifika datum (Engångs eller avvikelser) --
        if not shows_today:
            # Ibland ligger det som <occasion><date>...</date></occasion>
            occasions = schedule.findall(".//occasion")
            for occ in occasions:
                occ_date_str = occ.findtext("date")
                if occ_date_str and occ_date_str.startswith(str(today_date)):
                    shows_today = True
                    start_time_str = occ.findtext("startTime")
                    end_time_str = occ.findtext("endTime")
                    break

        # -- Metod 3: Fallback på huvudnoden om schedule är platt --
        if not shows_today:
            # Vissa XML-strukturer har dayOfWeek direkt under schedule
            dow_direct = schedule.findtext("dayOfWeek")
            if dow_direct == today_dow_cogwork:
                # Kolla datumintervall på eventet
                ev_start = parse_xml_date(schedule.findtext("startDate"))
                ev_end = parse_xml_date(schedule.findtext("endDate"))
                
                in_range = True
                if ev_start and ev_end:
                    in_range = (ev_start <= today_date <= ev_end)
                
                if in_range:
                    shows_today = True
                    start_time_str = schedule.findtext("startTime")
                    end_time_str = schedule.findtext("endTime")

    if shows_today:
        # Snygga till tider (ta bort sekunder: 18:00:00 -> 18:00)
        if start_time_str: start_time_str = start_time_str[:5]
        if end_time_str: end_time_str = end_time_str[:5]

        time_display = start_time_str
        if start_time_str and end_time_str:
            time_display = f"{start_time_str}–{end_time_str}"

        filtered.append({
            "course": title,
            "time": time_display,
            "raw_time": start_time_str,
            "place": final_place,
            "teacher": instructor
        })

print(f"🟢 Hittade {len(filtered)} klasser för {today_label} i Light Box/Black Box.")

# =========================
# 4️⃣ Sortera & Skapa HTML
# =========================
filtered.sort(key=lambda x: x["raw_time"] or "23:59")

light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

def render_box(rows):
    if not rows:
        return "<p style='color:#777; font-style:italic;'>Inga klasser i denna sal idag</p>"
    html_cards = ""
    for r in rows:
        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p class="time">{html.escape(r['time'])}</p>
            <p class="teacher">{html.escape(r['teacher'])}</p>
        </div>
        """
    return html_cards

html_content = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="600">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dagens schema</title>
    <style>
        body {{
            font-family: 'Agrandir', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #ffffff;
            color: #000;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
            font-weight: 600;
            font-size: 2.5rem;
            margin-bottom: 0.2rem;
        }}
        h2.date-line {{
            text-align: center;
            color: #444;
            font-weight: 400;
            margin-top: 0.2rem;
            margin-bottom: 2rem;
            font-size: 1.3rem;
        }}
        .wrapper {{
            display: flex;
            justify-content: space-between;
            gap: 2%;
            margin-top: 1rem;
        }}
        .column {{
            width: 48%;
        }}
        .column h2 {{
            background-color: #a3c0b2;
            color: #000;
            padding: 0.8rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 1.4rem;
            text-align: center;
        }}
        .class-card {{
            background-color: #CDDCD1;
            padding: 1rem 1.2rem;
            border-radius: 1rem;
            margin-bottom: 1rem;
        }}
        .class-card h3 {{
            margin: 0;
            font-size: 1.2rem;
        }}
        .class-card p {{
            margin: 0.2rem 0;
            font-size: 1rem;
        }}
        .time {{ font-weight: bold; }}
        .teacher {{ font-style: italic; }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <h2 class="date-line">{today_label}</h2>
    <div class="wrapper">
        <div class="column">
            <h2>Light Box</h2>
            {render_box(light_box)}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_box(black_box)}
        </div>
    </div>
</body>
</html>
"""

# =========================
# 5️⃣ Spara HTML
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ index.html uppdaterad! ({today_label})")
