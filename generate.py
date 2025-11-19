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

# --- HÅRDKODAD SALMAPPNING ---
# Kurser som saknas här fallbacker till "Light Box".
# Använd värdet "EXCLUDE" för kurser som ska ignoreras helt (t.ex. Teatern).
LOCATION_MAP = {
    # Onsdag 19/11
    "Jazz Kids 5 - 6": "Light Box", 
    "Commercial Hiphop 13+": "Black Box", 
    "AP Step 2 Jazz": "Light Box", 
    "AP Street/Commercial Step 1 & 2": "Black Box", 
    "AT Contemporary": "Light Box", 
    "AT Commercial/Street": "Black Box", 
    "AP Jazz Step 1": "Light Box", 

    # Torsdag 20/11
    "Jazz/Balett 60+": "Light Box",      
    "Juniorstreet 7 - 8": "Black Box",   
    "Talent Program Street": "Black Box",
    "EP 1 Contemporary": "Light Box",    
    "Advanced Contemporary": "Light Box",
    "Streetdance 10+": "Black Box",      
    "Contemporary 12+": "Light Box",     
    "Jazz & Funk Open level": "Black Box",
    
    # Fredag 21/11
    "EP 1 & EP2 Street/Commercial": "Black Box", 
    "EP 3 Contemporary": "Light Box",            
    "EP 2 Contemporary": "Black Box",            
    "EP 3 Street/Commercial": "Light Box",       

    # Lördag 22/11
    "Tiktok 10+": "Black Box",            
    "Barndans 3-4": "Light Box",          
    "Barndans 5-6": "Light Box",          
    "Showjazz 10+": "Light Box",          
    "Danskalas": "Black Box",             

    # Söndag 23/11
    "Barndans 4-5": "Light Box",          
    "Barnbalett 5-6 år": "Light Box",     
    "Jazz Kids 7 - 9": "Light Box",       
    "Från första steg till full passion": "EXCLUDE", # Kursen i Teatern, exkluderas

    # Måndag 24/11
    "AP Step 2 Contemporary": "Black Box",        
    "AP Technical Skills Step 1 & 2": "Black Box",
    "AP Contemporary Step 1": "Black Box",       
    "EP 2 Jazz": "Light Box",                    
    "EP 3 Jazz": "Light Box",                    

    # Tisdag 25/11
    "EP 1 & EP 2 & EP 3 Technical Skills & Renertoar": "Black Box", 
    "EP 1 Technical Skills": "Light Box", 
    "EP 1 Jazz": "Light Box",             
    "Jazz 16+": "Black Box",              
    "Talent Program Jazz": "Light Box",   
}

# --- HÅRDKODAD INSTRUKTÖRMAPPNING ---
INSTRUCTOR_MAP = {
    # Onsdag 19/11 (Baserat på tidigare angivelser)
    "Jazz Kids 5 - 6": "Madeleine",
    "Commercial Hiphop 13+": "Jennifer",
    "AP Step 2 Jazz": "Amanda",
    "AP Street/Commercial Step 1 & 2": "Isabella & Jennifer",
    "AT Contemporary": "Sofia & Amanda", 
    "AT Commercial/Street": "Isabella & Jennifer",
    "AP Jazz Step 1": "Amanda & Madeleine",

    # Övriga kurser från Schema.pdf (Platshållare, fyll i vid behov)
    "Jazz/Balett 60+": "Instruktör saknas",
    "Juniorstreet 7 - 8": "Instruktör saknas",
    "Talent Program Street": "Instruktör saknas", 
    "EP 1 Contemporary": "Instruktör saknas",
    "Advanced Contemporary": "Instruktör saknas",
    "Streetdance 10+": "Instruktör saknas",
    "Contemporary 12+": "Instruktör saknas",
    "Jazz & Funk Open level": "Instruktör saknas",
    
    "EP 1 & EP2 Street/Commercial": "Instruktör saknas",
    "EP 3 Contemporary": "Instruktör saknas",
    "EP 2 Contemporary": "Instruktör saknas",
    "EP 3 Street/Commercial": "Instruktör saknas",

    "Tiktok 10+": "Instruktör saknas",
    "Barndans 3-4": "Instruktör saknas",
    "Barndans 5-6": "Instruktör saknas",
    "Showjazz 10+": "Instruktör saknas",
    "Danskalas": "Instruktör saknas",

    "Barndans 4-5": "Instruktör saknas",
    "Barnbalett 5-6 år": "Instruktör saknas",
    "Jazz Kids 7 - 9": "Instruktör saknas",
    "Från första steg till full passion": "Instruktör saknas", # Behövs för att hålla strukturen

    "AP Step 2 Contemporary": "Instruktör saknas",
    "AP Technical Skills Step 1 & 2": "Instruktör saknas",
    "AP Contemporary Step 1": "Instruktör saknas",
    "EP 2 Jazz": "Instruktör saknas",
    "EP 3 Jazz": "Instruktör saknas",

    "EP 1 & EP 2 & EP 3 Technical Skills & Renertoar": "Instruktör saknas", 
    "EP 1 Technical Skills": "Instruktör saknas",
    "EP 1 Jazz": "Instruktör saknas",
    "Jazz 16+": "Instruktör saknas",
    "Talent Program Jazz": "Instruktör saknas",
}
# =========================
# 2️⃣ Hämta & Analysera iCal-data
# =========================
print(f"⏳ Hämtar iCal-schema för {today_label}...")
try:
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; InfoScreen/1.0)'}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    gcal = Calendar.from_ical(resp.content)
except Exception as e:
    print(f"❌ Kunde inte hämta eller tolka iCal-flödet: {e}")
    # Skapa felmeddelande i HTML-filen
    with open("index.html", "w", encoding="utf-8") as f:
         f.write(f"<h1>FEL: KAN INTE HÄMTA SCHEMA! ({datetime.now(TZ).strftime('%H:%M')})</h1>")
    sys.exit(1)

daily_schedule = []

for component in gcal.walk():
    if component.name == "VEVENT":
        summary = str(component.get('summary'))
        
        start_dt = component.get('dtstart').dt
        end_dt = component.get('dtend').dt
        
        # 1. Filtrera på dagens datum
        event_date = start_dt.date() if isinstance(start_dt, datetime) else start_dt
        
        if event_date == TARGET_DATE and isinstance(start_dt, datetime):
            
            # 2. Hämta Sal och Instruktör från mappningarna
            # NYTT: Om kursen saknas i LOCATION_MAP, tilldela "Light Box" som standard (fallback).
            location = LOCATION_MAP.get(summary, "Light Box") 
            instructor = INSTRUCTOR_MAP.get(summary, "Instruktör okänd")
            
            # 3. Filtrera bort kurser som uttryckligen ska exkluderas (t.ex. Teatern)
            if location == "EXCLUDE":
                continue 
                
            start_time_str = start_dt.strftime('%H:%M')
            end_time_str = end_dt.strftime('%H:%M')
            
            daily_schedule.append({
                'course': summary,
                'time': f"{start_time_str}–{end_time_str}",
                'raw_time': start_time_str,
                'place': location,
                'teacher': instructor
            })
            
print(f"🟢 Hittade {len(daily_schedule)} klasser för {today_label}.")

# =========================
# 3️⃣ Sortera & Skapa HTML
# =========================
filtered = daily_schedule
filtered.sort(key=lambda x: x["raw_time"] or "23:59")

light_box = [f for f in filtered if f["place"] == "Light Box"]
black_box = [f for f in filtered if f["place"] == "Black Box"]

def render_box(rows):
    if not rows:
        return "<p style='color:#777; font-style:italic;'>Inga klasser i denna sal idag</p>"
    html_cards = ""
    for r in rows:
        teacher_display = html.escape(r['teacher']) if r['teacher'] and r['teacher'] != "!!! SAKNAR INSTRUKTÖR !!!" else "Instruktör okänd"

        html_cards += f"""
        <div class="class-card">
            <h3>{html.escape(r['course'])}</h3>
            <p class="time">{html.escape(r['time'])}</p>
            <p class="teacher">{teacher_display}</p>
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
            /* Färg: #ee7a9f (Primär färg) */
            background-color: #ee7a9f; 
            color: #000;
            padding: 0.8rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 1.4rem;
            text-align: center;
        }}
        .class-card {{
            /* Färg: #f4d1ce (Sekundär färg) */
            background-color: #f4d1ce; 
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
# 4️⃣ Spara HTML
# =========================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ index.html uppdaterad! ({today_label})")
