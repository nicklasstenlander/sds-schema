import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import json
import re
import os

# ==========================================
# 1) KONFIG
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")

TEACHER_JSON_PATH = "Data-4.json"   # <-- du sa: ta lärare härifrån

# Testa annan tid/dag (bra för "imorgon")
# Ex: SCHEDULE_NOW="2026-02-03T12:00:00+01:00" python3 generate.py
SCHEDULE_NOW = os.getenv("SCHEDULE_NOW")

def get_now():
    if SCHEDULE_NOW:
        # tillåt både med och utan timezone (utan -> antas Stockholm)
        try:
            dt = datetime.fromisoformat(SCHEDULE_NOW)
            if dt.tzinfo is None:
                return TZ.localize(dt)
            return dt.astimezone(TZ)
        except Exception:
            pass
    return datetime.now(TZ)

now = get_now()
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"
weekday_full = VECKODAGAR[now.weekday()]

# ==========================================
# 2) SAL-MAPPNING (manuell, som din fungerande)
# ==========================================
PLACE_MAP = {
    "Barndans med förälder": {
        "Måndag": {"place": "Light Box"},
        "Lördag": {"place": "Light Box"},
        "Söndag": {"place": "Light Box"},
        "default": {"place": "Light Box"}
    },

    # EDUCATION & ADVANCED PROGRAMS
    "EP 1 Jazz": {"default": {"place": "Light Box"}},
    "EP 2 Jazz": {"default": {"place": "Light Box"}},
    "EP 3 Jazz": {"default": {"place": "Light Box"}},
    "EP 1 Contemporary": {"default": {"place": "Black Box"}},
    "EP 2 Contemporary": {"default": {"place": "Black Box"}},
    "EP 3 Contemporary": {"default": {"place": "Black Box"}},
    "AP Jazz Step 1": {"default": {"place": "Black Box"}},
    "AP Step 2 Jazz": {"default": {"place": "Black Box"}},
    "AP Step 1 Contemporary": {"default": {"place": "Black Box"}},
    "AP Step 2 Contemporary": {"default": {"place": "Black Box"}},
    "Technical Skills": {"default": {"place": "Black Box"}},
    "Education Program 1": {"default": {"place": "Light Box"}},
    "Education Program 2": {"default": {"place": "Light Box"}},
    "Education Program 3": {"default": {"place": "Light Box"}},
    "Advanced Program Step 1": {"default": {"place": "Light Box"}},
    "Advanced Program Step 2": {"default": {"place": "Light Box"}},

    # TALENT & PERFORMANCE
    "Talent Program": {"default": {"place": "Light Box"}},
    "Tillval Talent Program": {"default": {"place": "Light Box"}},
    "Talent Program Jazz": {"default": {"place": "Black Box"}},
    "Talent Program Street": {"default": {"place": "Black Box"}},
    "Performance Intermediate": {"default": {"place": "Black Box"}},
    "Performance Advanced": {"default": {"place": "Light Box"}},

    # BARN & UNGDOM (7-12 år)
    "Barndans 3-4": {"default": {"place": "Black Box"}},
    "Barndans 4-5": {"default": {"place": "Light Box"}},
    "Barndans 5-6": {"default": {"place": "Black Box"}},
    "Barnbalett 5-6": {"default": {"place": "Light Box"}},
    "Jazz Kids 5-6": {"default": {"place": "Light Box"}},
    "Popstars 5-6": {"default": {"place": "Black Box"}},
    "Juniorstreet 7-9": {"default": {"place": "Light Box"}},
    "Showjazz 7-9": {"default": {"place": "Light Box"}},
    "Showjazz 8-9": {"default": {"place": "Black Box"}},
    "Balett 7-9": {"default": {"place": "Light Box"}},
    "Streetdance 8-9": {"default": {"place": "Light Box"}},
    "Streetdance 10+": {"default": {"place": "Light Box"}},
    "K-pop Kids 6-7": {"default": {"place": "Black Box"}},
    "K-pop 8-10": {"default": {"place": "Black Box"}},
    "K-pop 10+": {"default": {"place": "Black Box"}},
    "Tiktok 8-9": {"default": {"place": "Black Box"}},
    "Tiktok 10+": {"default": {"place": "Black Box"}},
    "Cheerdance 7-8": {"default": {"place": "Black Box"}},

    # ÖVRIGA KLASSER (13+ & VUXNA)
    "Balett 9+": {"default": {"place": "Black Box"}},
    "Jazz 16+": {"default": {"place": "Black Box"}},
    "Contemporary 11+": {"default": {"place": "Light Box"}},
    "Advanced Contemporary": {"default": {"place": "Black Box"}},
    "Commercial Jazz 11+": {"default": {"place": "Light Box"}},
    "Commercial Hiphop 13+": {"default": {"place": "Light Box"}},
    "Jazz & Funk": {"default": {"place": "Light Box"}},
    "Jazz/Balett 55+": {"default": {"place": "Light Box"}},
}

# ==========================================
# 3) NORMALISERING + LÄRAR-MAPPNING (Data-4.json)
# ==========================================
DOW_MAP = {
    "Mån": "Måndag",
    "Tis": "Tisdag",
    "Ons": "Onsdag",
    "Tors": "Torsdag",
    "Fre": "Fredag",
    "Lör": "Lördag",
    "Sön": "Söndag",
}

def norm_spaces(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00A0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def norm_name(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Kurs: ", "")
    s = html.unescape(s)
    s = norm_spaces(s)
    return s.lower()

def parse_teacher_map(json_path: str):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    teacher_map = {}

    for row in data.get("rows", []):
        event = norm_name(row.get("eventName", ""))
        if not event:
            continue

        weekday = DOW_MAP.get(row.get("dayOfWeek"))
        start_time = (row.get("startTime") or "").strip()  # "HH:MM"
        instructors = (row.get("instructors") or "").strip()

        if not instructors:
            continue

        # mest specifikt: kurs + veckodag + starttid
        if weekday and start_time:
            teacher_map[(event, weekday, start_time)] = instructors

        # fallback: kurs + veckodag
        if weekday:
            teacher_map.setdefault((event, weekday, None), instructors)

        # fallback: kurs generellt
        teacher_map.setdefault((event, None, None), instructors)

    return teacher_map

def get_teacher(course_summary: str, weekday_full: str, start_hhmm: str, teacher_map: dict) -> str:
    e = norm_name(course_summary)

    t = teacher_map.get((e, weekday_full, start_hhmm))
    if t:
        return t

    t = teacher_map.get((e, weekday_full, None))
    if t:
        return t

    t = teacher_map.get((e, None, None))
    if t:
        return t

    return "Instruktör"

TEACHER_MAP = parse_teacher_map(TEACHER_JSON_PATH)

# ==========================================
# 4) TIDSKONVERTERING (din fungerande “-offset” fix)
# ==========================================
def to_stockholm(dt):
    """
    MinaAktiviteter iCal verkar ibland vara UTC-taggad men redan i lokal tid.
    Vi:
      1) konverterar till Stockholm
      2) drar av Stockholms offset (1h vinter / 2h sommar)
    """
    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    local = dt.astimezone(TZ)
    offset = local.utcoffset() or timedelta(0)
    return local - offset

# ==========================================
# 5) PLATS (sal) från PLACE_MAP
# ==========================================
def get_place(course_summary: str, weekday_full: str) -> str:
    summary_norm = norm_name(course_summary)

    keys_sorted = sorted(PLACE_MAP.keys(), key=lambda x: len(x), reverse=True)
    for k in keys_sorted:
        if k.lower() in summary_norm:
            info = PLACE_MAP[k].get(weekday_full, PLACE_MAP[k].get("default"))
            return info.get("place", "Övriga")

    return "Övriga"

# ==========================================
# 6) HÄMTA DAGENS SCHEMA FRÅN iCal
# ==========================================
print("Downloading iCal...")
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(ICAL_URL, headers=headers, timeout=30)
resp.raise_for_status()
gcal = Calendar.from_ical(resp.content)

daily_schedule = []

for component in gcal.walk("VEVENT"):
    summary = str(component.get("summary")).replace("Kurs: ", "").strip()

    dtstart = component.get("dtstart").dt
    dtend = component.get("dtend").dt

    start_local = to_stockholm(dtstart) if isinstance(dtstart, datetime) else None
    end_local = to_stockholm(dtend) if isinstance(dtend, datetime) else None
    if not start_local or not end_local:
        continue

    if start_local.date() != TARGET_DATE:
        continue

    start_hhmm = start_local.strftime("%H:%M")

    location = get_place(summary, weekday_full)
    teacher = get_teacher(summary, weekday_full, start_hhmm, TEACHER_MAP)

    daily_schedule.append({
        "course": summary,
        "time": f"{start_local:%H:%M}–{end_local:%H:%M}",
        "raw_time": start_hhmm,
        "place": location,
        "teacher": teacher,
        "start_dt": start_local,
        "end_dt": end_local,
  #      "is_live": (start_local <= now < end_local),
    })

daily_schedule.sort(key=lambda x: x["start_dt"])
print("Schedule generated:", len(daily_schedule), "classes")

# ==========================================
# 7) PÅGÅR NU / NÄSTA
# ==========================================
ongoing = next(
    (c for c in daily_schedule if c.get("start_dt") and c.get("end_dt") and c["start_dt"] <= now < c["end_dt"]),
    None
)
upcoming = next(
    (c for c in daily_schedule if c.get("start_dt") and c["start_dt"] > now),
    None
)

def iso(dt) -> str:
    return dt.isoformat() if dt else ""

# Säkerställ att exakt en klass får live-highlight i listan (samma som ongoing)
for c in daily_schedule:
    c["is_live"] = False

if ongoing:
    # Matcha på start_dt + course (tillräckligt i praktiken)
    for c in daily_schedule:
        if c.get("start_dt") == ongoing.get("start_dt") and c.get("course") == ongoing.get("course"):
            c["is_live"] = True
            break

# ==========================================
# 8) HTML
# ==========================================

def iso(dt):
    """ISO-sträng för data-attribut. Klarar None."""
    if not dt:
        return ""
    # Viktigt: ha timezone-aware datetime i dt (du har TZ)
    return dt.isoformat()

def slug(s: str) -> str:
    """Gör säkra id:n för HTML."""
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-åäö]", "", s)
    return s

def render_col(title, classes):
    cards_html = "".join(
        f"""
        <div class="card {'live' if c.get('is_live') else ''}">
            <div class="time">{html.escape(c.get('time', ''))}</div>
            <div class="name">{html.escape(c.get('course', ''))}</div>
            <div class="teacher">{html.escape(c.get('teacher', ''))}</div>
        </div>
        """
        for c in (classes or [])
    )

    if not cards_html:
        cards_html = '<p class="empty">Inga lektioner</p>'

    return f"""
    <div class="column">
        <h2>{html.escape(title)}</h2>
        {cards_html}
    </div>
    """

# Se till att splitten ALLTID finns innan html_out
light = [c for c in daily_schedule if c.get("place") == "Light Box"]
black = [c for c in daily_schedule if c.get("place") == "Black Box"]
other = [c for c in daily_schedule if c.get("place") not in ("Light Box", "Black Box")]

def status_card(label, c, empty_text, show_live_pill=False):
    label_id = slug(label)

    # Special: "Pågår nu" när inget pågår -> Välkommen + nästa starttid
    if label == "Pågår nu" and not c:
        if upcoming:
            start_txt = upcoming["start_dt"].strftime("%H:%M")
            return f"""
            <div class="statuscard" id="status-ongoing"
                 data-now="{iso(now)}"
                 data-up-start="{iso(upcoming.get('start_dt'))}"
                 data-up-end="{iso(upcoming.get('end_dt'))}">
                <div class="statuslabel">Pågår nu</div>
                <div class="statustitle">Välkommen! Nästa klass startar {html.escape(start_txt)}</div>
                <div class="statusmeta">
                    {html.escape(upcoming.get('course',''))} • {html.escape(upcoming.get('place',''))} • {html.escape(upcoming.get('teacher',''))}
                </div>
                <div class="statusextra" id="ongoing-extra"></div>
            </div>
            """
        return f"""
        <div class="statuscard" id="status-ongoing" data-now="{iso(now)}">
            <div class="statuslabel">Pågår nu</div>
            <div class="statustitle">{html.escape(empty_text)}</div>
            <div class="statusextra" id="ongoing-extra"></div>
        </div>
        """

    # Om t.ex. "Nästa" saknas
    if not c:
        return f"""
        <div class="statuscard" id="status-{label_id}">
            <div class="statuslabel">{html.escape(label)}</div>
            <div class="statustitle">{html.escape(empty_text)}</div>
        </div>
        """

    live_pill = '<span class="pill">LIVE</span>' if show_live_pill else ""
    return f"""
    <div class="statuscard" id="status-{label_id}"
         data-start="{iso(c.get('start_dt'))}"
         data-end="{iso(c.get('end_dt'))}">
        <div class="statuslabel">{html.escape(label)}{live_pill}</div>
        <div class="statustitle">{html.escape(c.get('course',''))}</div>
        <div class="statusmeta">
            {html.escape(c.get('time',''))} • {html.escape(c.get('place',''))} • {html.escape(c.get('teacher',''))}
        </div>
        <div class="statusextra" id="{label_id}-extra"></div>
    </div>
    """

status_html = f"""
<div class="statuswrap">
    {status_card("Pågår nu", ongoing, "Ingen lektion pågår just nu", show_live_pill=True)}
    {status_card("Nästa", upcoming, "Inget mer schemalagt idag")}
</div>
"""
html_out = f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; color: #333; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.5rem; text-transform: uppercase; }}
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 22px; font-weight: bold; }}

        .statuswrap {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 18px; }}
        .statuscard {{
            flex: 1; min-width: 220px;
            background: #fff7f9;
            border: 2px solid #ee7a9f;
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.06);
        }}
        .statuslabel {{ font-weight: 900; text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.95rem; color: #ee7a9f; }}
        .statustitle {{ font-size: 1.6rem; font-weight: 900; margin: 6px 0 2px; line-height: 1.1; }}
        .statusmeta {{ font-size: 1.1rem; color: #444; }}
        .statusextra {{ margin-top: 8px; font-weight: 900; font-size: 1.05rem; color: #222; }}
        .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #ee7a9f; color: white; font-weight: 800; font-size: 0.95rem; margin-left: 8px; vertical-align: middle; }}

        .wrapper {{ display: flex; gap: 20px; justify-content: center; align-items: flex-start; }}
        .column {{ flex: 1; min-width: 260px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 0; }}

        .card {{
            background: #f4d1ce;
            padding: 12px;
            border-radius: 18px;
            margin-bottom: 10px;
            border-left: 12px solid #ee7a9f;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .card.live {{
            border-left: 16px solid #ff4d6d;
            background: #ffe5ec;
            transform: scale(1.02);
            box-shadow: 0 8px 18px rgba(0,0,0,0.15);
        }}
        .time {{ font-weight: bold; font-size: 1.3rem; }}
        .name {{ font-size: 1.4rem; font-weight: 800; margin: 3px 0; line-height: 1.0; }}
        .teacher {{ font-style: italic; color: #555; font-size: 1.0rem; }}
    </style>
</head>
<body>
    <h1>Dagens schema</h1>
    <div class="date">{today_label}</div>

    {status_html}

    <div class="wrapper">
        {render_col("Light Box", light)}
        {render_col("Black Box", black)}
        {render_col("Övriga", other) if other else ""}
    </div>

    <div style="text-align:center;color:#999;margin-top:20px;font-size:0.9rem;">
        Uppdaterad {now:%H:%M}
    </div>

<script>
(function() {{
  function pad(n) {{ return (n < 10 ? "0" : "") + n; }}

  function fmt(mins) {{
    mins = Math.max(0, Math.floor(mins));
    if (mins < 60) return mins + " min";
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    if (m === 0) return h + " h";
    return h + " h " + m + " min";
  }}

  function parseISO(s) {{
    if (!s) return null;
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }}

  function updateCards() {{
    var nowD = new Date(); // browserns tid -> live countdown

    // Pågår nu (om vi har data-start/data-end)
    var ongoing = document.getElementById("status-pågår-nu");
    if (!ongoing) ongoing = document.getElementById("status-pågår-nu".replace("å","a")); // safety (om id ändras)
    // Vi satte id "status-pågår-nu" via python -> men HTML id får å. Safari/Chrome klarar det oftast.
    // Fallback: använd status-ongoing
    if (!ongoing) ongoing = document.getElementById("status-ongoing");

    var next = document.getElementById("status-nästa");
    if (!next) next = document.getElementById("status-nästa".replace("ä","a"));
    if (!next) next = document.getElementById("status-next");

    // Ongoing card: antingen pågående pass (start/end) eller "välkommen" (up-start/up-end)
    if (ongoing) {{
      var s = parseISO(ongoing.getAttribute("data-start"));
      var e = parseISO(ongoing.getAttribute("data-end"));
      var upS = parseISO(ongoing.getAttribute("data-up-start"));
      var upE = parseISO(ongoing.getAttribute("data-up-end"));

      var extraEl = document.getElementById("pågår nu-extra") || document.getElementById("ongoing-extra");

      if (s && e) {{
        var left = (e - nowD) / 60000;
        if (extraEl) extraEl.textContent = fmt(left) + " kvar";
      }} else if (upS) {{
        var until = (upS - nowD) / 60000;
        if (extraEl) extraEl.textContent = ""; // vi visar inget extra på välkommen-kortet
      }}
    }}

    if (next) {{
      var ns = parseISO(next.getAttribute("data-start"));
      var extraEl2 = document.getElementById("nästa-extra") || document.getElementById("next-extra");
      if (ns && extraEl2) {{
        var until2 = (ns - nowD) / 60000;
        extraEl2.textContent = "Startar om " + fmt(until2);
      }}
    }}
  }}

  updateCards();
  setInterval(updateCards, 10000); // uppdatera var 10:e sekund
}})();
</script>

</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
