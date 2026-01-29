import requests
from icalendar import Calendar
from datetime import datetime, date
import pytz
import html
import sys

# =========================
# 1️⃣ Konfiguration
# =========================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical" 
TZ = pytz.timezone("Europe/Stockholm")
now = datetime.now(TZ)
TARGET_DATE = now.date() 

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# --- FULLSTÄNDIG SALMAPPNING (Samtliga 77 klasser från filen) ---
LOCATION_MAP = {
    "Talent Program": "Light Box",
    "Performance Intermediate": "Black Box",
    "Education Program 1 (EP Y1)": "Light Box",
    "Advanced Program Step 2 (AP2)": "Light Box",
    "Education Program 2 (EP Y2)": "Light Box",
    "Tillval Talent Program - Technical Skills": "Light Box",
    "Education Program 3 (EP Y3)": "Light Box",
    "Advanced Program Step 1 (AP1)": "Black Box",
    "K-pop 10-13 år N1-N2": "Black Box",
    "K-pop 13+ år N1-N2": "Black Box",
    "K-pop 14+ år N3-N4": "Black Box",
    "Contemporary N4-A": "Black Box",
    "Modern Dans 10-12 år N1": "Light Box",
    "Modern Dans 13+ år N1-N2": "Light Box",
    "Contemporary N2-N3": "Light Box",
    "Barndans 4-5 år": "Teatern",
    "Förberedande Balett 6-8 år": "Teatern",
    "Jazz 9-11 år N1": "Light Box",
    "Showjazz 12+ år N1": "Light Box",
    "Commercial 13+ år N2": "Light Box",
    "Commercial 15+ år N3-N4": "Light Box",
    "Hiphop/Street 7-8 år N1": "Teatern",
    "Hiphop/Street 9-11 år N1": "Light Box",
    "Hiphop/Street 12+ år N1": "Light Box",
    "Streetdance 13+ år N2": "Black Box",
    "Streetdance 15+ år N3-N4": "Black Box",
    "Streetdance 10-12 år N1-N2": "Black Box",
    "Tiktok 10+ år N1-N2": "Black Box",
    "Commercial Hiphop 13+": "Black Box",
    "Hiphop/Street 13+ år N2-N3": "Light Box",
    "Jazz & Funk Open level": "Black Box",
    "Dance Camp vecka 9 (9-13 år)": "Light Box",
    "Barndans med förälder 1-3 år": "Light Box",
    "Barndans 4-5 år": "Light Box",
    "Förberedande Balett 6-8 år": "Light Box",
    "Jazz 9-11 år N1-N2": "Light Box",
    "Showjazz 12+ år N2": "Light Box",
    "Jazz N3-N4": "Light Box",
    "Femme 16+ år N2-N3": "Light Box",
    "Commercial Intermediate/Advanced": "Black Box",
    "Heels Open level": "Light Box",
    "AP Street/Commercial Step 2": "Black Box",
    "Balett 9-11 år N1": "Light Box",
    "Balett 12+ år N1-N2": "Light Box",
    "Balett N3-N4": "Light Box",
    "Popstars 5-6 år": "Black Box",
    "Popstars 7-8 år": "Black Box",
    "Popstars 9-11 år": "Black Box",
    "Musikal 7-9 år": "Black Box",
    "Musikal 10-12 år": "Black Box",
    "Musikal 13+ år": "Black Box",
    "Streetdance 7-9 år N1": "Black Box",
    "Streetdance 10-12 år N1": "Black Box",
    "Jazz & Commercial 9-11 år N1": "Light Box",
    "Jazz & Commercial 12+ år N1": "Light Box",
    "Lyrisk Jazz 13+ år N2": "Light Box",
    "Showkids 4-5 år": "Teatern",
    "Showkids 6-7 år": "Teatern",
    "Hiphop 8-10 år N1": "Teatern",
    "Hiphop 11-13 år N1-N2": "Teatern",
    "Dancehall Open level": "Black Box",
    "Afrobeat Open level": "Black Box",
    "Breakdance 7-9 år N1": "Light Box",
    "Breakdance 10-13 år N1-N2": "Light Box",
    "Akrobatik 7-9 år N1": "Light Box",
    "Akrobatik 10-13 år N1-N2": "Light Box",
    "Floorwork Open level": "Black Box",
    "Improvisation & Kontaktplastik": "Black Box",
    "Vuxenbalett Nybörjare": "Light Box",
    "Vuxenjazz Fortsättning": "Light Box",
    "Vuxen Streetdance Nybörjare": "Black Box",
    "Slowflow Vuxna": "Black Box",
    "K-pop 6-7 år N1-N2": "Black Box",
    "K-pop 8-11 år N1-N2": "Black Box",
    "Modern Jazz 14+ år N3": "Light Box",
    "Jazz Technical Skills": "Light Box",
    "Kreativ Dans 4-6 år": "Light Box"
}

# --- FULLSTÄNDIG INSTRUKTÖRMAPPNING ---
INSTRUCTOR_MAP = {
    "Talent Program": "Sofia, Hilda",
    "Performance Intermediate": "Sofia",
    "Education Program 1 (EP Y1)": "Madeleine, Sofia, Amanda",
    "Advanced Program Step 2 (AP2)": "Amanda, Madeleine, Sofia, Jennifer & Bella",
    "Education Program 2 (EP Y2)": "Madeleine, Sofia",
    "Tillval Talent Program - Technical Skills": "Sofia",
    "Education Program 3 (EP Y3)": "Madeleine, Sofia",
    "Advanced Program Step 1 (AP1)": "Sofia, Amanda, Jennifer & Bella",
    "K-pop 10-13 år N1-N2": "Elsa",
    "K-pop 13+ år N1-N2": "Elsa",
    "K-pop 14+ år N3-N4": "Elsa",
    "Contemporary N4-A": "Amanda",
    "Modern Dans 10-12 år N1": "Amanda",
    "Modern Dans 13+ år N1-N2": "Amanda",
    "Contemporary N2-N3": "Amanda",
    "Barndans 4-5 år": "Hilda / Madde",
    "Förberedande Balett 6-8 år": "Hilda / Madde",
    "Jazz 9-11 år N1": "Hilda",
    "Showjazz 12+ år N1": "Hilda",
    "Commercial 13+ år N2": "Hilda",
    "Commercial 15+ år N3-N4": "Hilda",
    "Hiphop/Street 7-8 år N1": "Hilda",
    "Hiphop/Street 9-11 år N1": "Hilda",
    "Hiphop/Street 12+ år N1": "Hilda",
    "Streetdance 13+ år N2": "Lova",
    "Streetdance 15+ år N3-N4": "Lova",
    "Streetdance 10-12 år N1-N2": "Lova",
    "Tiktok 10+ år N1-N2": "Lova / Elsa",
    "Commercial Hiphop 13+": "Jennifer",
    "Hiphop/Street 13+ år N2-N3": "Jennifer",
    "Jazz & Funk Open level": "Jennifer",
    "Barndans med förälder 1-3 år": "Madde",
    "Jazz 9-11 år N1-N2": "Madde",
    "Showjazz 12+ år N2": "Madde",
    "Jazz N3-N4": "Madde",
    "Femme 16+ år N2-N3": "Jennifer",
    "Commercial Intermediate/Advanced": "Jennifer & Bella",
    "Heels Open level": "Jennifer",
    "AP Street/Commercial Step 2": "Jennifer & Bella",
    "K-pop 6-7 år N1-N2": "Elsa",
    "K-pop 8-11 år N1-N2": "Elsa",
    "Modern Jazz 14+ år N3": "Sofia",
    "Jazz Technical Skills": "Sofia"
}

# =========================
# 2️⃣ Hämta & Analysera iCal
# =========================
try:
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; InfoScreen/1.0)'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    gcal = Calendar.from_ical(resp.content)
except Exception as e:
    print(f"❌ Fel vid hämtning: {e}")
    sys.exit(1)

daily_schedule = []
for component in gcal.walk():
    if component.name == "VEVENT":
        summary = str(component.get('summary'))
        clean_name = summary.replace("Kurs: ", "").strip()
        start_dt = component.get('dtstart').dt
        end_dt = component.get('dtend').dt
        event_date = start_dt.date() if isinstance(start_dt, datetime) else start_dt
        
        if event_date == TARGET_DATE and isinstance(start_dt, datetime):
            location = LOCATION_MAP.get(clean_name, "Andra")
            instructor = INSTRUCTOR_MAP.get(clean_name, "Instruktör okänd")
            start_time_str = start_dt.strftime('%H:%M')
            end_time_str = end_dt.strftime('%H:%M')
            
            daily_schedule.append({
                'course': clean_name,
                'time': f"{start_time_str}–{end_time_str}",
                'raw_time': start_time_str,
                'place': location,
                'teacher': instructor
            })

# =========================
# 3️⃣ Sortera & Förbered Kolumner
# =========================
daily_schedule.sort(key=lambda x: x["raw_time"])

light_box = [f for f in daily_schedule if f["place"] == "Light Box"]
black_box = [f for f in daily_schedule if f["place"] == "Black Box"]
other_rooms = [f for f in daily_schedule if f["place"] not in ["Light Box", "Black Box"]]

# Kolla om "Andra lokaler" ska visas
show_others = len(other_rooms) > 0

def render_box(rows):
    html_cards = ""
    for r in rows:
        loc_tag = f"<p class='loc-tag'>{r['place']}</p>" if r['place'] not in ["Light Box", "Black Box"] else ""
        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p class="time">{html.escape(r['time'])}</p>
            <p class="teacher">{html.escape(r['teacher'])}</p>
            {loc_tag}
        </div>
        """
    return html_cards

# --- HTML-STRUKTUR ---
other_column_html = f"""
<div class="column">
    <h2>Andra lokaler</h2>
    {render_box(other_rooms)}
</div>
""" if show_others else ""

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
            font-family: 'Agrandir', sans-serif;
            background-color: #ffffff;
            margin: 0;
            padding: 2rem;
        }}
        h1 {{ text-align: center; font-size: 2.5rem; margin-bottom: 0.2rem; }}
        h2.date-line {{ text-align: center; color: #444; font-weight: 400; margin-bottom: 2rem; font-size: 1.3rem; }}
        
        /* Flexbox-wrapper som fördelar ut kolumnerna jämnt */
        .wrapper {{ 
            display: flex; 
            justify-content: center; 
            gap: 1.5rem; 
        }}
        
        .column {{ 
            flex: 1; /* Gör att kolumnerna tar upp lika mycket plats */
            min-width: 300px;
        }}
        
        .column h2 {{
            background-color: #ee7a9f; 
            padding: 1rem;
            border-radius: 0.5rem;
            text-align: center;
            font-size: 1.4rem;
        }}
        
        .class-card {{
            background-color: #f4d1ce; 
            padding: 1rem 1.2rem;
            border-radius: 1rem;
            margin-bottom: 1rem;
        }}
        
        .class-card h3 {{ margin: 0; font-size: 1.2rem; }}
        .time {{ font-weight: bold; margin: 0.3rem 0; }}
        .teacher {{ font-style: italic; margin: 0; }}
        .loc-tag {{ 
            display: inline-block; background: #fff; padding: 2px 8px; 
            border-radius: 4px; font-size: 0.8rem; margin-top: 8px; font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>Dagens Schema</h1>
    <h2 class="date-line">{today_label}</h2>
    <div class="wrapper">
        <div class="column">
            <h2>Light Box</h2>
            {render_box(light_box) or "<p style='color:#777;'>Inga klasser idag</p>"}
        </div>
        <div class="column">
            <h2>Black Box</h2>
            {render_box(black_box) or "<p style='color:#777;'>Inga klasser idag</p>"}
        </div>
        {other_column_html}
    </div>
</body>
</html>
"""

# =========================
# 4️⃣ Spara filen
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ index.html genererad. 'Andra lokaler' visas: {'JA' if show_others else 'NEJ (dold)'}")
