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
MAX_CARDS_PER_COLUMN = 5

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
    "EP 1 Contemporary": {"default": {"place": "Light Box"}},
    "EP 2 Contemporary": {"default": {"place": "Black Box"}},
    "EP 3 Contemporary": {"default": {"place": "Light Box"}},
    "EP 1 & EP2 Street/Commercial": {"default": {"place": "Black Box"}},
    "EP 3 Street/Commercial": {"default": {"place": "Light Box"}},
    "AP Jazz Step 1": {"default": {"place": "Black Box"}},
    "AP Step 2 Jazz": {"default": {"place": "Black Box"}},
    "AP Step 1 Contemporary": {"default": {"place": "Black Box"}},
    "AP Step 2 Contemporary": {"default": {"place": "Black Box"}},
    "AP Street/Commercial Step 1": {"default": {"place": "Light Box"}},
    "AP Street/Commercial Step 2": {"default": {"place": "Light Box"}},
    "EP 1 Technical Skills": {"default": {"place": "Light Box"}},
    "EP 2 & EP 3 Technical Skills": {"default": {"place": "Black Box"}},
    "AP Technical Skills Step 1 & 2": {"default": {"place": "Black Box"}},
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
    "Jazz Kids 5 - 6": {"default": {"place": "Light Box"}},
    "Popstars 5-6": {"default": {"place": "Black Box"}},
    "Juniorstreet 7-9": {"default": {"place": "Light Box"}},
    "Showjazz 7-9": {"default": {"place": "Light Box"}},
    "Showjazz 8-9": {"default": {"place": "Black Box"}},
    "Balett 7-9": {"default": {"place": "Light Box"}},
    "Streetdance 8-9": {"default": {"place": "Light Box"}},
    "Streetdance 10+": {"default": {"place": "Black Box"}},
    "K-pop Kids 6-7": {"default": {"place": "Black Box"}},
    "K-pop 8-10": {"default": {"place": "Black Box"}},
    "K-pop 10+": {"default": {"place": "Black Box"}},
    "Tiktok 8-9": {"default": {"place": "Black Box"}},
    "Tiktok 10+": {"default": {"place": "Black Box"}},
    "Cheerdance 7-8": {"default": {"place": "Black Box"}},

    # ÖVRIGA KLASSER (13+ & VUXNA)
    "Balett 9+": {"default": {"place": "Black Box"}},
    "Jazz 16+": {"default": {"place": "Black Box"}},
    "Contemporary 11+": {"default": {"place": "Black Box"}},
    "Advanced Contemporary": {"default": {"place": "Light Box"}},
    "Commercial Jazz 11+": {"default": {"place": "Light Box"}},
    "Commercial Hiphop 13+": {"default": {"place": "Light Box"}},
    "Jazz & Funk": {"default": {"place": "Light Box"}},
    "Jazz/Balett 55+": {"default": {"place": "Light Box"}},
}

# Manuell override: kurs + lärare -> sal
# Används när samma kurs har flera parallella grupper med olika lärare.
PLACE_BY_TEACHER = {
    ("jazz & funk open level", "amanda"): "Black Box",
    ("jazz & funk open level", "hilda"): "Light Box",
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
            key = (event, weekday, start_time)
            if key not in teacher_map:
                teacher_map[key] = []
            if instructors and instructors not in teacher_map[key]:
                teacher_map[key].append(instructors)

        # fallback: kurs + veckodag
        if weekday:
            key = (event, weekday, None)
            if key not in teacher_map:
                teacher_map[key] = []
            if instructors and instructors not in teacher_map[key]:
                teacher_map[key].append(instructors)

        # fallback: kurs generellt
        key = (event, None, None)
        if key not in teacher_map:
            teacher_map[key] = []
        if instructors and instructors not in teacher_map[key]:
            teacher_map[key].append(instructors)

    return teacher_map

def _pick_instructor(val, occ_idx: int) -> str:
    if not val:
        return "Instruktör"
    if isinstance(val, list):
        if not val:
            return "Instruktör"
        if occ_idx is None or occ_idx < 0:
            return val[0]
        return val[min(occ_idx, len(val) - 1)]
    return str(val)

def get_teacher(course_summary: str, weekday_full: str, start_hhmm: str, teacher_map: dict, occ_idx: int = 0) -> str:
    e = norm_name(course_summary)

    t = teacher_map.get((e, weekday_full, start_hhmm))
    if t:
        return _pick_instructor(t, occ_idx)

    t = teacher_map.get((e, weekday_full, None))
    if t:
        return _pick_instructor(t, occ_idx)

    t = teacher_map.get((e, None, None))
    if t:
        return _pick_instructor(t, occ_idx)

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
def _place_from_location(location: str):
    if not location:
        return None
    loc = norm_name(location)
    if "light" in loc and "box" in loc:
        return "Light Box"
    if "black" in loc and "box" in loc:
        return "Black Box"
    return None

def get_place(course_summary: str, weekday_full: str, location=None) -> str:
    loc_place = _place_from_location(location)
    if loc_place:
        return loc_place
    summary_norm = norm_name(course_summary)
    summary_compact = re.sub(r"\s*-\s*", "-", summary_norm)
    summary_compact = re.sub(r"\s*/\s*", "/", summary_compact)
    summary_compact = re.sub(r"\s+", " ", summary_compact).strip()

    keys_sorted = sorted(PLACE_MAP.keys(), key=lambda x: len(x), reverse=True)
    for k in keys_sorted:
        k_norm = k.lower()
        k_compact = re.sub(r"\s*-\s*", "-", k_norm)
        k_compact = re.sub(r"\s*/\s*", "/", k_compact)
        k_compact = re.sub(r"\s+", " ", k_compact).strip()
        if (
            k_norm in summary_norm
            or k_norm in summary_compact
            or k_compact in summary_norm
            or k_compact in summary_compact
        ):
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
occurrence_counter = {}

for component in gcal.walk("VEVENT"):
    summary = str(component.get("summary")).replace("Kurs: ", "").strip()
    location_raw = component.get("location")
    location = str(location_raw).strip() if location_raw else ""

    dtstart = component.get("dtstart").dt
    dtend = component.get("dtend").dt

    start_local = to_stockholm(dtstart) if isinstance(dtstart, datetime) else None
    end_local = to_stockholm(dtend) if isinstance(dtend, datetime) else None
    if not start_local or not end_local:
        continue

    if start_local.date() != TARGET_DATE:
        continue

    start_hhmm = start_local.strftime("%H:%M")

    occ_key = (norm_name(summary), weekday_full, start_hhmm)
    occ_idx = occurrence_counter.get(occ_key, 0)
    occurrence_counter[occ_key] = occ_idx + 1
    teacher = get_teacher(summary, weekday_full, start_hhmm, TEACHER_MAP, occ_idx)
    place = get_place(summary, weekday_full, location)
    override_key = (norm_name(summary), norm_name(teacher))
    if override_key in PLACE_BY_TEACHER:
        place = PLACE_BY_TEACHER[override_key]

    daily_schedule.append({
        "course": summary,
        "time": f"{start_local:%H:%M}–{end_local:%H:%M}",
        "raw_time": start_hhmm,
        "place": place,
        "teacher": teacher,
        "start_dt": start_local,
        "end_dt": end_local,
  #      "is_live": (start_local <= now < end_local),
    })

daily_schedule.sort(key=lambda x: x["start_dt"])
print("Schedule generated:", len(daily_schedule), "classes")

# ==========================================
# 7) PÅGÅR NU / NÄSTA (stöd för flera samtidigt)
# ==========================================
def iso(dt: datetime) -> str:
    return dt.isoformat() if dt else ""

# Alla som pågår
ongoing_list = [c for c in daily_schedule if c["start_dt"] <= now < c["end_dt"]]

# Välj den som startade senast; vid lika start -> den som slutar först
if ongoing_list:
    latest_start = max(c["start_dt"] for c in ongoing_list)
    tied = [c for c in ongoing_list if c["start_dt"] == latest_start]
    ongoing = min(tied, key=lambda x: x["end_dt"])
else:
    ongoing = None

# Nästa klass efter "nu" (robust även om listan inte är sorterad)
future = [c for c in daily_schedule if c["start_dt"] > now]
upcoming = min(future, key=lambda x: x["start_dt"]) if future else None

# Live-highlight i listan: ALLA som pågår
for c in daily_schedule:
    c["is_live"] = False

for live in ongoing_list:
    for c in daily_schedule:
        if (c.get("start_dt") == live.get("start_dt")
            and c.get("end_dt") == live.get("end_dt")
            and c.get("course") == live.get("course")):
            c["is_live"] = True

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
              <span class="live-indicator"></span>
              <div class="time">{esc(c["time"])}</div>
              <div class="name">{esc(c["course"])}</div>
              <div class="teacher">{esc(c["teacher"])}</div>
              <div class="progress"><div class="progress-fill"></div></div>
            </div>
            """)
        cards_html = "\n".join(parts)

    return f"""
   
<div class="column">
  <h2>{esc(title)}</h2>
  <div class="cards">{cards_html}</div>
</div>

    """

# ===============================
# ONGOING / UPCOMING (PRODUCTION)
# ===============================

ongoing_list = [
    c for c in daily_schedule
    if c["start_dt"] <= now < c["end_dt"]
]

# vilken ska visas i statuskortet?
if ongoing_list:
    latest_start = max(c["start_dt"] for c in ongoing_list)
    tied = [c for c in ongoing_list if c["start_dt"] == latest_start]

    # vid samma start → den som slutar först
    ongoing = min(tied, key=lambda x: x["end_dt"])
else:
    ongoing = None


upcoming = next(
    (c for c in daily_schedule if c["start_dt"] > now),
    None
)

for c in daily_schedule:
    c["is_live"] = False

for c in ongoing_list:
    c["is_live"] = True

# Se till att splitten alltid finns innan html_out
light = [c for c in daily_schedule if c.get("place") == "Light Box"]
black = [c for c in daily_schedule if c.get("place") == "Black Box"]
other = [c for c in daily_schedule if c.get("place") not in ("Light Box", "Black Box")]



def status_card_ongoing(ongoing, upcoming) -> str:
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
              <div class="statustitle" id="ongoing-title">Välkommen! Nästa klass startar {upcoming["start_dt"]:%H:%M}</div>
              <div class="statusmeta" id="ongoing-meta">{esc(upcoming["course"])} · {esc(upcoming["place"])} · {esc(upcoming["teacher"])}</div>
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
      <div class="statuslabel">Pågår nu <span class="live-dot"></span></div>
      <div class="statustitle" id="ongoing-title">{esc(ongoing["course"])}</div>
      <div class="statusmeta" id="ongoing-meta">{esc(ongoing["time"])} · {esc(ongoing["place"])} · {esc(ongoing["teacher"])}</div>
      <div class="statusextra" id="ongoing-extra"></div>
    </div>
    """

def status_card_upcoming(upcoming) -> str:
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
      <div class="statusmeta" id="upcoming-meta">{esc(upcoming["time"])} · {esc(upcoming["place"])} · {esc(upcoming["teacher"])}</div>
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
  var MAX_CARDS_PER_COLUMN = __MAX_CARDS_PER_COLUMN__;
  var TICK_MS = 5000;
  var EMPTY_RELOAD_MS = 600000;
  var cardNodes = document.querySelectorAll(".card");
  var classes = [];
  var lastOngoingKey = null;
  var lastUpcomingKey = null;

  function parseISO(s) {
    if (!s) return null;
    var d = new Date(s);
    return isNaN(d.getTime()) ? null : d;
  }

  function getAttr(el, name) {
    return el ? (el.getAttribute(name) || "") : "";
  }

  function two(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function timeLabel(d) {
    return two(d.getHours()) + ":" + two(d.getMinutes());
  }

  function fmtMinutes(mins) {
    mins = Math.max(0, Math.floor(mins));
    if (mins < 60) return mins + " min";
    var h = Math.floor(mins / 60);
    var m = mins % 60;
    if (m === 0) return h + " h";
    return h + " h " + m + " min";
  }

  function getNow() {
    return new Date(new Date().getTime() + nowOffset);
  }

  function setText(el, txt) {
    if (el) el.textContent = txt;
  }

  function textById(id, txt) {
    setText(document.getElementById(id), txt);
  }

  function ensureChild(parent, id, className, beforeId) {
    var el = document.getElementById(id);
    var before;
    if (!el && parent) {
      el = document.createElement("div");
      el.id = id;
      el.className = className;
      before = document.getElementById(beforeId);
      parent.insertBefore(el, before || null);
    }
    return el;
  }

  function hasClass(el, name) {
    return (" " + el.className + " ").indexOf(" " + name + " ") !== -1;
  }

  function addClass(el, name) {
    if (el && !hasClass(el, name)) {
      el.className = el.className ? el.className + " " + name : name;
    }
  }

  function removeClass(el, name) {
    if (el) {
      el.className = (" " + el.className + " ").replace(" " + name + " ", " ").replace(/^\s+|\s+$/g, "");
    }
  }

  function setLiveDot(show) {
    var card = document.getElementById("status-ongoing");
    var label = card ? card.querySelector(".statuslabel") : null;
    var dot = label ? label.querySelector(".live-dot") : null;
    if (show && label && !dot) {
      dot = document.createElement("span");
      dot.className = "live-dot";
      label.appendChild(dot);
    } else if (!show && dot && dot.parentNode) {
      dot.parentNode.removeChild(dot);
    }
  }

  function keyFor(item) {
    if (!item) return "";
    return item.startMs + "|" + item.endMs + "|" + item.course + "|" + item.place + "|" + item.teacher;
  }

  function setClassData(card, item) {
    if (!card) return;
    if (!item) {
      card.removeAttribute("data-start");
      card.removeAttribute("data-end");
      card.removeAttribute("data-course");
      card.removeAttribute("data-place");
      card.removeAttribute("data-teacher");
      card.removeAttribute("data-time");
      return;
    }
    card.setAttribute("data-start", item.startISO);
    card.setAttribute("data-end", item.endISO);
    card.setAttribute("data-course", item.course);
    card.setAttribute("data-place", item.place);
    card.setAttribute("data-teacher", item.teacher);
    card.setAttribute("data-time", item.time);
  }

  function setWelcomeData(card, item) {
    if (!card) return;
    if (!item) {
      card.removeAttribute("data-up-start");
      card.removeAttribute("data-up-end");
      card.removeAttribute("data-up-course");
      card.removeAttribute("data-up-place");
      card.removeAttribute("data-up-teacher");
      card.removeAttribute("data-up-time");
      return;
    }
    card.setAttribute("data-up-start", item.startISO);
    card.setAttribute("data-up-end", item.endISO);
    card.setAttribute("data-up-course", item.course);
    card.setAttribute("data-up-place", item.place);
    card.setAttribute("data-up-teacher", item.teacher);
    card.setAttribute("data-up-time", item.time);
  }

  function compareClasses(a, b) {
    if (a.startMs !== b.startMs) return a.startMs - b.startMs;
    if (a.endMs !== b.endMs) return a.endMs - b.endMs;
    return a.index - b.index;
  }

  function collectClasses() {
    var i;
    var card;
    var start;
    var end;
    for (i = 0; i < cardNodes.length; i += 1) {
      card = cardNodes[i];
      start = parseISO(getAttr(card, "data-start"));
      end = parseISO(getAttr(card, "data-end"));
      if (start && end) {
        classes.push({
          element: card,
          index: i,
          start: start,
          end: end,
          startMs: start.getTime(),
          endMs: end.getTime(),
          startISO: getAttr(card, "data-start"),
          endISO: getAttr(card, "data-end"),
          course: getAttr(card, "data-course"),
          place: getAttr(card, "data-place"),
          teacher: getAttr(card, "data-teacher"),
          time: getAttr(card, "data-time")
        });
      }
    }
    classes.sort(compareClasses);
  }

  function getOngoing(now) {
    var nowMs = now.getTime();
    var ongoing = [];
    var i;
    for (i = 0; i < classes.length; i += 1) {
      if (classes[i].startMs <= nowMs && nowMs < classes[i].endMs) {
        ongoing.push(classes[i]);
      }
    }
    return ongoing;
  }

  function chooseOngoing(ongoing) {
    var selected = null;
    var i;
    for (i = 0; i < ongoing.length; i += 1) {
      if (!selected ||
          ongoing[i].startMs > selected.startMs ||
          (ongoing[i].startMs === selected.startMs && ongoing[i].endMs < selected.endMs)) {
        selected = ongoing[i];
      }
    }
    return selected;
  }

  function findUpcoming(now) {
    var nowMs = now.getTime();
    var i;
    for (i = 0; i < classes.length; i += 1) {
      if (classes[i].startMs > nowMs) return classes[i];
    }
    return null;
  }

  function updateOngoingStatus(now, item, upcoming) {
    var card = document.getElementById("status-ongoing");
    var meta = ensureChild(card, "ongoing-meta", "statusmeta", "ongoing-extra");
    var displayKey;
    if (!card) return;

    if (item) {
      displayKey = "ongoing|" + keyFor(item);
      if (displayKey !== lastOngoingKey) {
        card.setAttribute("data-mode", "ongoing");
        setClassData(card, item);
        setWelcomeData(card, null);
        textById("ongoing-title", item.course);
        setText(meta, item.time + " · " + item.place + " · " + item.teacher);
        setLiveDot(true);
        lastOngoingKey = displayKey;
      }
      textById("ongoing-extra", fmtMinutes((item.endMs - now.getTime()) / 60000) + " kvar");
      return;
    }

    if (upcoming) {
      displayKey = "welcome|" + keyFor(upcoming);
      if (displayKey !== lastOngoingKey) {
        card.setAttribute("data-mode", "welcome");
        setClassData(card, null);
        setWelcomeData(card, upcoming);
        textById("ongoing-title", "Välkommen! Nästa klass startar " + timeLabel(upcoming.start));
        setText(meta, upcoming.course + " · " + upcoming.place + " · " + upcoming.teacher);
        setLiveDot(false);
        lastOngoingKey = displayKey;
      }
      textById("ongoing-extra", "");
      return;
    }

    displayKey = "empty";
    if (displayKey !== lastOngoingKey) {
      card.setAttribute("data-mode", "empty");
      setClassData(card, null);
      setWelcomeData(card, null);
      textById("ongoing-title", "Välkommen! Inget mer schemalagt idag");
      setText(meta, "");
      setLiveDot(false);
      lastOngoingKey = displayKey;
    }
    textById("ongoing-extra", "");
  }

  function updateUpcomingStatus(now, item) {
    var card = document.getElementById("status-upcoming");
    var meta = ensureChild(card, "upcoming-meta", "statusmeta", "upcoming-extra");
    var displayKey;
    if (!card) return;

    if (item) {
      displayKey = "upcoming|" + keyFor(item);
      if (displayKey !== lastUpcomingKey) {
        card.setAttribute("data-mode", "upcoming");
        setClassData(card, item);
        textById("upcoming-title", item.course);
        setText(meta, item.time + " · " + item.place + " · " + item.teacher);
        lastUpcomingKey = displayKey;
      }
      textById("upcoming-extra", "Startar om " + fmtMinutes((item.startMs - now.getTime()) / 60000));
      return;
    }

    displayKey = "empty";
    if (displayKey !== lastUpcomingKey) {
      card.setAttribute("data-mode", "empty");
      setClassData(card, null);
      textById("upcoming-title", "Inget mer schemalagt idag");
      setText(meta, "");
      lastUpcomingKey = displayKey;
    }
    textById("upcoming-extra", "");
  }

  function updateLiveCards(now) {
    var nowMs = now.getTime();
    var i;
    var item;
    var fill;
    var totalMs;
    var pct;
    for (i = 0; i < classes.length; i += 1) {
      item = classes[i];
      removeClass(item.element, "live");
      removeClass(item.element, "ended");
      removeClass(item.element, "upcoming");

      fill = item.element.querySelector(".progress-fill");
      totalMs = Math.max(1, item.endMs - item.startMs);
      pct = ((nowMs - item.startMs) / totalMs) * 100;
      pct = Math.min(100, Math.max(0, pct));
      if (fill) fill.style.width = pct + "%";

      if (item.startMs <= nowMs && nowMs < item.endMs) {
        addClass(item.element, "live");
      } else if (item.endMs <= nowMs) {
        addClass(item.element, "ended");
      } else {
        removeClass(item.element, "live");
        removeClass(item.element, "ended");
      }
    }
  }

  function updateColumnWindows(now) {
    var columns = document.querySelectorAll(".column");
    var nowMs = now.getTime();
    var i;
    var j;
    var col;
    var cards;
    var total;
    var endedCount;
    var end;
    var maxStart;
    var startIdx;
    var endIdx;

    for (i = 0; i < columns.length; i += 1) {
      col = columns[i];
      cards = col.querySelectorAll(".card");
      total = cards.length;
      if (total <= MAX_CARDS_PER_COLUMN) {
        for (j = 0; j < total; j += 1) {
          cards[j].style.display = "";
        }
        continue;
      }

      endedCount = 0;
      for (j = 0; j < total; j += 1) {
        end = parseISO(getAttr(cards[j], "data-end"));
        if (end && end.getTime() <= nowMs) endedCount += 1;
        else break;
      }

      maxStart = Math.max(0, total - MAX_CARDS_PER_COLUMN);
      startIdx = Math.min(endedCount, maxStart);
      endIdx = startIdx + MAX_CARDS_PER_COLUMN;

      for (j = 0; j < total; j += 1) {
        cards[j].style.display = j >= startIdx && j < endIdx ? "" : "none";
      }
    }
  }

  function updateClock(now) {
    var el = document.getElementById("live-clock");
    if (el) el.textContent = timeLabel(now);
  }

  function tick() {
    var now = getNow();
    var ongoing = getOngoing(now);
    var selectedOngoing = chooseOngoing(ongoing);
    var upcoming = findUpcoming(now);

    if (pageDay && now.toDateString() !== pageDay) {
      location.reload();
      return;
    }

    updateOngoingStatus(now, selectedOngoing, upcoming);
    updateUpcomingStatus(now, upcoming);
    updateLiveCards(now);
    updateColumnWindows(now);
    updateClock(now);
  }

  if (cardNodes.length === 0) {
    setTimeout(function() { location.reload(); }, EMPTY_RELOAD_MS);
  }

  collectClasses();

  var generatedNow = parseISO(document.body ? getAttr(document.body, "data-schedule-now") : "");
  var nowOffset = generatedNow ? generatedNow.getTime() - new Date().getTime() : 0;
  var pageDay = classes.length > 0 ? classes[0].start.toDateString() : null;

  tick();
  setInterval(tick, TICK_MS);
  setInterval(function() { updateClock(getNow()); }, 1000);
})();
</script>
"""
js_out = js_out.replace("__MAX_CARDS_PER_COLUMN__", str(MAX_CARDS_PER_COLUMN))
schedule_now_attr = f" data-schedule-now='{esc(iso(now))}'" if SCHEDULE_NOW else ""
html_out = f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <style>
        @font-face {{
          font-family: 'Agrandir';
          src: url('https://static1.squarespace.com/static/68093bdd8e42fd6c032c5835/t/680d0c38f474794b748500db/1745685560738/Agrandir-Regular.woff2') format('woff2');
          font-weight: 400;
          font-style: normal;
          font-display: swap;
        }}
        @font-face {{
          font-family: 'Agrandir';
          src: url('https://static1.squarespace.com/static/68093bdd8e42fd6c032c5835/t/680d0c3898f175135e941828/1745685560778/Agrandir-TextBold.woff2') format('woff2');
          font-weight: 700;
          font-style: normal;
          font-display: swap;
        }}
        @font-face {{
          font-family: 'Agrandir';
          src: url('https://static1.squarespace.com/static/68093bdd8e42fd6c032c5835/t/680d0c381a4da06e7eee7440/1745685560732/Agrandir-GrandLight.woff2') format('woff2');
          font-weight: 300;
          font-style: normal;
          font-display: swap;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Agrandir', sans-serif; background: #fafafa; color: #1a1a1a; }}

        .banner {{
          background: #d4507a;
          padding: 10px 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
        }}
        .banner-logo {{ height: 48px; display: block; }}
        #live-clock {{
          position: absolute;
          right: 28px;
          font-size: 1.4rem;
          font-weight: 300;
          color: #fff;
          letter-spacing: 0.02em;
          font-variant-numeric: tabular-nums;
        }}

        .main {{ width: 100%; padding: 32px 28px 20px; }}
        h1 {{ font-size: 1.75rem; font-weight: 700; color: #1a1a1a; text-align: center; margin-bottom: 4px; letter-spacing: -0.01em; }}
        .date {{ text-align: center; color: #aaa; font-size: 0.85rem; font-weight: 400; margin-bottom: 28px; letter-spacing: 0.02em; }}

        .statuswrap {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 32px; }}
        .statuscard {{
          background: #fff;
          border-radius: 10px;
          padding: 18px 20px;
          border: 1px solid #eee;
          position: relative;
        }}
        .statuscard[data-mode="ongoing"],
        .statuscard[data-mode="welcome"] {{ border-left: 3px solid #d4507a; padding-left: 18px; }}
        .statuscard[data-mode="upcoming"],
        .statuscard[data-mode="done"] {{ border-left: 3px solid #e0e0e0; padding-left: 18px; }}

        .statuslabel {{
          font-size: 0.65rem; font-weight: 700; letter-spacing: 0.12em;
          text-transform: uppercase; color: #b0b0b0; margin-bottom: 8px;
          display: flex; align-items: center; gap: 8px;
        }}
        .live-dot {{
          width: 6px; height: 6px; background: #d4507a; border-radius: 50%;
          display: inline-block; animation: pulse 2.2s ease-in-out infinite;
        }}
        @keyframes pulse {{
          0%, 100% {{ opacity: 1; transform: scale(1); }}
          50% {{ opacity: 0.35; transform: scale(1.5); }}
        }}
        .statustitle {{ font-size: 1.15rem; font-weight: 700; color: #1a1a1a; line-height: 1.25; }}
        .statusmeta {{ font-size: 0.78rem; color: #999; margin-top: 4px; letter-spacing: 0.01em; }}
        .statusextra {{ font-size: 0.78rem; font-weight: 700; margin-top: 10px; }}
        .statuscard[data-mode="ongoing"] .statusextra,
        .statuscard[data-mode="welcome"] .statusextra {{ color: #d4507a; }}
        .statuscard[data-mode="upcoming"] .statusextra,
        .statuscard[data-mode="done"] .statusextra {{ color: #aaa; }}
        .pill {{ display: none; }}

        .wrapper {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .column {{ min-width: 0; }}
        h2 {{
          font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
          text-transform: uppercase; color: #b0b0b0;
          padding: 0 0 10px; margin: 0 0 10px;
          border-bottom: 1px solid #eee;
          background: none; border-radius: 0; text-align: left;
        }}

        .card {{
          background: #fff;
          border-radius: 10px;
          padding: 14px 16px;
          margin-bottom: 8px;
          border: 1px solid #f0f0f0;
          border-left: 3px solid #ececec;
          position: relative;
          box-shadow: none;
          transition: opacity 0.3s ease;
        }}
        .card.live {{
          border-color: rgba(212, 80, 122, 0.35);
          border-left: 3px solid #d4507a;
          background: #fef9fb;
          transform: none;
          box-shadow: none;
        }}
        .card.ended {{ opacity: 0.3; filter: none; }}
        .card .live-indicator {{
          width: 5px; height: 5px; background: #d4507a; border-radius: 50%;
          position: absolute; right: 16px; top: 16px;
          animation: pulse 2.2s ease-in-out infinite; display: none;
        }}
        .card.live .live-indicator {{ display: block; }}
        .progress {{ height: 2px; margin-top: 10px; border-radius: 2px; background: #f0f0f0; overflow: hidden; }}
        .progress-fill {{ width: 0%; height: 100%; background: #d4507a; border-radius: 2px; transition: width 0.5s linear; }}
        .card.ended .progress-fill {{ background: #ccc; }}
        .time {{ font-size: 0.78rem; color: #bbb; font-variant-numeric: tabular-nums; font-weight: 400; }}
        .name {{ font-size: 0.95rem; font-weight: 700; color: #1a1a1a; margin: 3px 0 2px; line-height: 1.25; }}
        .teacher {{ font-size: 0.7rem; color: #c0c0c0; font-style: normal; letter-spacing: 0.02em; }}

        .footer-text {{ text-align: center; color: #ccc; font-size: 0.65rem; padding: 20px 0 8px; letter-spacing: 0.03em; }}

        @media (max-width: 920px) {{
          .main {{ padding: 20px 16px 16px; }}
          .statuswrap {{ grid-template-columns: 1fr; gap: 10px; }}
          .wrapper {{ grid-template-columns: 1fr; gap: 12px; }}
          h1 {{ font-size: 1.4rem; }}
          .statustitle {{ font-size: 1rem; }}
          .name {{ font-size: 0.9rem; }}
          .time {{ font-size: 0.75rem; }}
          .banner {{ padding: 10px 16px; }}
          .banner-logo {{ height: 36px; }}
          #live-clock {{ font-size: 1.1rem; right: 16px; }}
        }}
    </style>
</head>
<body{schedule_now_attr}>
<div class="banner">
  <img class="banner-logo" src="3%20Lines/SDS%20Dancer%20Three%20Lines%20White.png" alt="Sollentuna Dans &amp; Scenskola">
  <div id="live-clock"></div>
</div>
<div class="main">
  <h1>Dagens schema</h1>
  <div class="date">{today_label}</div>

    

    {status_html}

      <div class="wrapper">
        {render_col("Light Box", light)}
        {render_col("Black Box", black)}
        {render_col("Övriga", other) if other else ""}
      </div>

  <div class="footer-text">Uppdaterad {now:%H:%M}</div>
</div>

{js_out}
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
