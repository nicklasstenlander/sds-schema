import requests
import json
import datetime

ORG = "sollentunadans"
PW = ""
BASE = "https://dans.se/api/public"

def fetch_events():
    """Hämtar alla event."""
    resp = requests.get(f"{BASE}/events/?org={ORG}&pw={PW}")
    resp.raise_for_status()
    data = resp.json()
    return data.get("events", [])

def fetch_event_details(event_key):
    """Hämtar detaljer (inklusive ev. occasions) för ett specifikt event."""
    resp = requests.get(f"{BASE}/event/?org={ORG}&pw={PW}&verbose=1&key={event_key}")
    resp.raise_for_status()
    return resp.json()

def main():
    today = datetime.date.today().isoformat()
    print(f"🔍 Startar API-debug för {ORG} ({today})")

    # --- Steg 1: Hämta alla event ---
    events = fetch_events()
    print(f"✅ {len(events)} events hittades i listan")

    sample_dump = []

    # --- Steg 2: Hämta detaljer för de första 5 eventen ---
    for i, ev in enumerate(events[:5], start=1):
        key = ev.get("key")
        name = ev.get("name", "okänd kurs")
        if not key:
            continue

        print(f"[{i}/5] Hämtar detaljer för: {name} ({key})")
        details = fetch_event_details(key)

        # Lägg till både eventets grunddata och detaljer
        sample_dump.append({
            "summary": {
                "id": ev.get("id"),
                "name": name,
                "place": ev.get("place"),
                "category": ev.get("category", {}).get("name", ""),
                "code": ev.get("code", "")
            },
            "details": details
        })

    # --- Steg 3: Spara till JSON för inspektion ---
    with open("debug_raw_sample.json", "w", encoding="utf-8") as f:
        json.dump(sample_dump, f, indent=2, ensure_ascii=False)

    print("💾 Sparade debug_raw_sample.json med 5 fullständiga event-detaljer")
    print("Körningen är klar — öppna filen i GitHub efter nästa workflow-run.")

if __name__ == "__main__":
    main()
