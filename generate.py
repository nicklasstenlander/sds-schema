def main():
    today = datetime.date.today().isoformat()
    events = fetch_events()
    events_today = []

    print(f"Hämtar schema för {today}... ({len(events)} event funna)")

    debug_data = []

    for i, ev in enumerate(events, start=1):
        key = ev.get("key")
        if not key:
            continue

        print(f"[{i}/{len(events)}] Hämtar detaljer för event {key}...")

        details = fetch_event_details(key)
        if not details:
            print(f"⚠️  Inga detaljer för event {key}")
            continue

        schedule = details.get("schedule", {})
        occasions = schedule.get("occasions", [])
        print(f"  → {details.get('name','(okänd)')} har {len(occasions)} tillfällen")

        if occasions:
            debug_data.append({
                "event": details.get("name"),
                "occasions": occasions
            })

        for occ in occasions:
            if occ.get("startDateTime", "").startswith(today):
                events_today.append({
                    "name": details.get("name", "Okänd kurs"),
                    "teacher": details.get("instructorsName", ""),
                    "place": details.get("place", ""),
                    "start": occ.get("startDateTime"),
                    "end": occ.get("endDateTime")
                })

    print(f"\nTotalt {len(events_today)} lektioner för {today}.")
    print(f"Sparar {len(debug_data)} events med occasions till debug_occurrences.json\n")

    # --- Skriv debug-logg till JSON ---
    with open("debug_occurrences.json", "w", encoding="utf-8") as f:
        json.dump(debug_data, f, indent=2, ensure_ascii=False)

    # --- Skapa HTML ---
    html_output = generate_html(events_today)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_output)
