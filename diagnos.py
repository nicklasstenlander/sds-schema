import requests
import json
from datetime import datetime

# Inställningar
ORG = "sollentunadans"
URL = f"https://dans.se/api/public/events/?org={ORG}"

print(f"--- DIAGNOS STARTAR ---")
print(f"Hämtar data från: {URL}")

try:
    resp = requests.get(URL)
    data = resp.json()
    events = data.get("events", [])
except Exception as e:
    print(f"CRASH: Kunde inte hämta data. Fel: {e}")
    events = []

print(f"Antal event hittade totalt: {len(events)}")

if len(events) == 0:
    print("VARNING: API:et returnerade inga event alls. Kontrollera ORG-namnet.")
else:
    # 1. Lista alla unika platsnamn (Place)
    all_places = set()
    for e in events:
        place_name = e.get("place")
        # Om place är None, sätt en text så vi ser det
        if place_name is None:
            place_name = "[SAKNAS I DATA]"
        all_places.add(place_name)
    
    print("\n--- HITTADE PLATSER (SALAR) ---")
    for p in all_places:
        print(f"'{p}'")

    # 2. Kolla datum för dagens datum
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"\n--- DATUM-KOLL (Letar efter {today_str}) ---")
    
    hits_today = 0
    for i, e in enumerate(events):
        # Kolla bara de 5 första för att inte dränka loggen
        if i > 5: break 
        
        name = e.get("name")
        sched = e.get("schedule", {})
        dates = sched.get("dates", [])
        
        if dates and isinstance(dates, list):
            if today_str in dates:
                print(f"✅ HITTADE MATCH: '{name}' går idag enligt datumlistan!")
                hits_today += 1
            else:
                # Visa första och sista datumet i listan för att se formatet
                print(f"❌ '{name}' går inte idag. (Datum i listan: {dates[:1]} ... {dates[-1:]})")
        else:
             print(f"⚠️ '{name}' saknar 'dates'-lista. Måste använda start/slut-datum.")

    # 3. Dumpa ett helt event så vi ser strukturen
    print("\n--- EXEMPEL PÅ ETT EVENT (RAW JSON) ---")
    if events:
        print(json.dumps(events[0], indent=2))

print("\n--- DIAGNOS KLAR ---")
