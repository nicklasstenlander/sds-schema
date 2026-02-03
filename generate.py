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
# 8) HTML (PRODUCTION VERSION)
#    - robust escaping
#    - data-attribut för JS uppdatering
#    - LIVE-highlight styrs av JS i realtid
# ==========================================
from datetime import datetime
import html

def iso(dt: datetime) -> str:
    # ISO8601 med offset så JS kan parsa korrekt
    return dt.isoformat()

def slug(s: str) -> str:
    # Enkelt id för DOM
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-åäö]", "", s)
    return s or "x"

def esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)

def render_col(title: str, classes: list[dict]) -> str:
    if not classes:
        cards_html = '<p class="empty">Inga lektioner</p>'
    else:
        parts = []
        for c in classes:
            # data- attribut med enkla citat => säkert även om text innehåller "
            parts.append(f"""
            <div class="card{' live' if c.get('is_live') else ''}"
                 data-start='{esc(iso(c["start_dt"]))}'
                 data-end='{esc(iso(c["end_dt"]))}'
                 data-course='{esc(c["course"])}'
                 data-place='{esc(c["place"])}'
                 data-teacher='{esc(c["teacher"])}'
                 data-time='{esc(c["time"])}'>
              <div class="time">{esc(c["time"])}</div>
              <div class="name">{esc(c["course"])}</div>
              <div class="teacher">{esc(c["teacher"])}</div>
            </div>
            """)
        cards_html = "\n".join(parts)

    return f"""
   
<div class="column">
  <h2>{esc(title)}</h2>
  <div class="cards">{cards_html}</div>
</div>

    """

# Se till att splitten alltid finns innan html_out
light = [c for c in daily_schedule if c.get("place") == "Light Box"]
black = [c for c in daily_schedule if c.get("place") == "Black Box"]
other = [c for c in daily_schedule if c.get("place") not in ("Light Box", "Black Box")]

# Ongoing / Upcoming baserat på "now" (server-time när html genereras)
ongoing = next((c for c in daily_schedule if c["start_dt"] <= now < c["end_dt"]), None)
upcoming = next((c for c in daily_schedule if c["start_dt"] > now), None)

def status_card_ongoing(ongoing: dict | None, upcoming: dict | None) -> str:
    # Om inget pågår: visa välkommen + nästa start om finns
    if not ongoing:
        if upcoming:
            return f"""
            <div class="statuscard" id="status-ongoing"
                 data-mode="welcome"
                 data-now='{esc(iso(now))}'
                 data-up-start='{esc(iso(upcoming["start_dt"]))}'
                 data-up-end='{esc(iso(upcoming["end_dt"]))}'
                 data-up-course='{esc(upcoming["course"])}'
                 data-up-place='{esc(upcoming["place"])}'
                 data-up-teacher='{esc(upcoming["teacher"])}'
                 data-up-time='{esc(upcoming["time"])}'>
              <div class="statuslabel">Pågår nu</div>
              <div class="statustitle" id="ongoing-title">
                Välkommen! Nästa klass startar {upcoming["start_dt"]:%H:%M}
              </div>
              <div class="statusmeta" id="ongoing-meta">
                {esc(upcoming["course"])} • {esc(upcoming["place"])} • {esc(upcoming["teacher"])}
              </div>
              <div class="statusextra" id="ongoing-extra"></div>
            </div>
            """
        return f"""
        <div class="statuscard" id="status-ongoing" data-mode="empty" data-now='{esc(iso(now))}'>
          <div class="statuslabel">Pågår nu</div>
          <div class="statustitle" id="ongoing-title">Välkommen! Inget mer schemalagt idag</div>
          <div class="statusextra" id="ongoing-extra"></div>
        </div>
        """

    # Om något pågår
    return f"""
    <div class="statuscard" id="status-ongoing"
         data-mode="ongoing"
         data-start='{esc(iso(ongoing["start_dt"]))}'
         data-end='{esc(iso(ongoing["end_dt"]))}'
         data-course='{esc(ongoing["course"])}'
         data-place='{esc(ongoing["place"])}'
         data-teacher='{esc(ongoing["teacher"])}'
         data-time='{esc(ongoing["time"])}'>
      <div class="statuslabel">Pågår nu <span class="pill">LIVE</span></div>
      <div class="statustitle" id="ongoing-title">{esc(ongoing["course"])}</div>
      <div class="statusmeta" id="ongoing-meta">
        {esc(ongoing["time"])} • {esc(ongoing["place"])} • {esc(ongoing["teacher"])}
      </div>
      <div class="statusextra" id="ongoing-extra"></div>
    </div>
    """

def status_card_upcoming(upcoming: dict | None) -> str:
    if not upcoming:
        return f"""
        <div class="statuscard" id="status-upcoming" data-mode="empty" data-now='{esc(iso(now))}'>
          <div class="statuslabel">Nästa</div>
          <div class="statustitle" id="upcoming-title">Inget mer schemalagt idag</div>
          <div class="statusextra" id="upcoming-extra"></div>
        </div>
        """
    return f"""
    <div class="statuscard" id="status-upcoming"
         data-mode="upcoming"
         data-start='{esc(iso(upcoming["start_dt"]))}'
         data-end='{esc(iso(upcoming["end_dt"]))}'
         data-course='{esc(upcoming["course"])}'
         data-place='{esc(upcoming["place"])}'
         data-teacher='{esc(upcoming["teacher"])}'
         data-time='{esc(upcoming["time"])}'>
      <div class="statuslabel">Nästa</div>
      <div class="statustitle" id="upcoming-title">{esc(upcoming["course"])}</div>
      <div class="statusmeta" id="upcoming-meta">
        {esc(upcoming["time"])} • {esc(upcoming["place"])} • {esc(upcoming["teacher"])}
      </div>
      <div class="statusextra" id="upcoming-extra"></div>
    </div>
    """

status_html = f"""
<div class="statuswrap">
  {status_card_ongoing(ongoing, upcoming)}
  {status_card_upcoming(upcoming)}
</div>
"""

# ------------------------------------------
# JS: uppdaterar nedräkning + LIVE-highlight
# ------------------------------------------
js_out = r"""
<script>
(function() {
  function parseISO(s) {
    if (!s) return null;
    const d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  function pad(n) { return String(n).padStart(2, "0"); }

  function fmtMinutes(mins) {
    mins = Math.max(0, Math.floor(mins));
    if (mins < 60) return mins + " min";
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (m === 0) return h + " h";
    return h + " h " + m + " min";
  }

  function setText(id, txt) {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  }

  function updateStatusCards(now) {
    const ongoing = document.getElementById("status-ongoing");
    const upcoming = document.getElementById("status-upcoming");

    if (ongoing) {
      const mode = ongoing.dataset.mode;

      if (mode === "ongoing") {
        const end = parseISO(ongoing.dataset.end);
        if (end) {
          const left = (end - now) / 60000;
          setText("ongoing-extra", fmtMinutes(left) + " kvar");
        }
      } else if (mode === "welcome") {
        const start = parseISO(ongoing.dataset.upStart);
        if (start) {
          // Ingen extra-text behövs här, men du kan lägga "Startar om X" om du vill.
          setText("ongoing-extra", "");
        }
      } else {
        setText("ongoing-extra", "");
      }
    }

    if (upcoming) {
      const mode = upcoming.dataset.mode;
      if (mode === "upcoming") {
        const start = parseISO(upcoming.dataset.start);
        if (start) {
          const until = (start - now) / 60000;
          setText("upcoming-extra", "Startar om " + fmtMinutes(until));
        }
      } else {
        setText("upcoming-extra", "");
      }
    }
  }

  function updateLiveCards(now) {
    const cards = Array.from(document.querySelectorAll(".card"));
    // Ta bort live på alla först
    cards.forEach(c => c.classList.remove("live"));

    // Hitta aktuell (först som matchar)
    for (const c of cards) {
      const start = parseISO(c.dataset.start);
      const end = parseISO(c.dataset.end);
      if (start && end && start <= now && now < end) {
        c.classList.add("live");
        break;
      }
    }
  }

  function tick() {
    const now = new Date();
    updateStatusCards(now);
    updateLiveCards(now);
  }

  // Kickstart + uppdatera varje 5:e sekund (snabb, men billig)
  tick();
  setInterval(tick, 5000);
})();
</script>
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
{js_out}
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
