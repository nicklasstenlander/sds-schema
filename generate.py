import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import re
import xml.etree.ElementTree as ET

# ==========================================
# 1️⃣ KONFIGURATION
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")
XML_PATH = "data.xml"

# TEST-LÄGE: Sätt till False för live-drift
TEST_MODE = True
now = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ) if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

# För att snabbt se LIVE i preview (valfritt)
FORCE_LIVE_PREVIEW = False

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# ==========================================
# 2️⃣ NORMALISERING (för matchning)
# ==========================================
def norm_name(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Kurs: ", "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

# ==========================================
# 3️⃣ TIDSZON (behåller din "1 timme efter"-fix)
# ==========================================
def to_stockholm(dt):
    """
    MinaAktiviteter iCal verkar ibland vara UTC-taggad men redan i lokal tid.
    Vi korrigerar bort Stockholms offset (1h vinter, 2h sommar).
    """
    if not isinstance(dt, datetime):
        return None

    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    local = dt.astimezone(TZ)
    offset = local.utcoffset() or timedelta(0)
    return local - offset

# ==========================================
# 4️⃣ XML: SAL + LÄRARE (data.xml)
# ==========================================
def _text(node) -> str:
    return (node.text or "").strip() if node is not None else ""

def extract_instructors_from_event(event_node) -> str:
    """
    Tar i första hand <combinedTitle> (kort, t.ex. "Sofia"),
    annars faller tillbaka på <name>.
    """
    instructors_node = event_node.find("instructors")
    if instructors_node is None:
        return ""

    combined = _text(instructors_node.find("combinedTitle"))
    if combined:
        return combined

    names = []
    for instr in instructors_node.findall(".//instructor"):
        nm = _text(instr.find("name"))
        if nm:
            names.append(nm)

    # de-dup, behåll ordning
    seen = set()
    uniq = []
    for n in names:
        k = n.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(n)

    return ", ".join(uniq)

def parse_xml_lookups(xml_path: str):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Vi lagrar occurrences som datetime istället för HH:MM-sträng
    # occurrences[(title_norm, 'YYYY-MM-DD')] = list of dicts {start_dt, place, teacher}
    occ_index = {}
    title_defaults = {}  # title_norm -> {"place":..., "teacher":...}

    for event in root.findall(".//event"):
        title = (event.findtext("title") or "").strip()
        event_place = (event.findtext("place") or "").strip()
        event_teacher = extract_instructors_from_event(event)

        if not title:
            continue

        t_norm = norm_name(title)

        # defaults per title (om event-nivå finns)
        if t_norm not in title_defaults:
            title_defaults[t_norm] = {"place": "", "teacher": ""}
        if event_place and not title_defaults[t_norm]["place"]:
            title_defaults[t_norm]["place"] = event_place
        if event_teacher and not title_defaults[t_norm]["teacher"]:
            title_defaults[t_norm]["teacher"] = event_teacher

        # occasions
        for occ in event.findall(".//occasions/occasion"):
            sdt = (occ.findtext("startDateTime") or "").strip()
            if not sdt:
                continue

            # parse datetime (med sekunder)
            dt_obj = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt_obj = datetime.strptime(sdt, fmt)
                    break
                except ValueError:
                    pass
            if not dt_obj:
                continue

            date_str = dt_obj.strftime("%Y-%m-%d")

            occasion_place = (occ.findtext("place") or "").strip()
            occasion_teacher = event_teacher  # oftast bara på event-nivå i din xml, men vi håller öppet

            final_place = occasion_place or event_place
            final_teacher = occasion_teacher

            occ_index.setdefault((t_norm, date_str), []).append(
                {
                    "start_dt": dt_obj,
                    "place": final_place,
                    "teacher": final_teacher,
                }
            )

    return occ_index, title_defaults


# Läs in XML
try:
    OCC_INDEX, TITLE_DEFAULTS = parse_xml_lookups(XML_PATH)
except Exception as e:
    print("Kunde inte läsa data.xml:", e)
    OCC_INDEX, TITLE_DEFAULTS = {}, {}

try:
    PLACE_BY_OCC, TEACHER_BY_OCC, PLACE_BY_TITLE, TEACHER_BY_TITLE = parse_xml_lookups(XML_PATH)
except Exception as e:
    print("Kunde inte läsa data.xml:", e)
    PLACE_BY_OCC, TEACHER_BY_OCC, PLACE_BY_TITLE, TEACHER_BY_TITLE = {}, {}, {}, {}


def _nearest_occ(title_norm: str, date_str: str, target_dt: datetime, minutes_window: int = 2):
    """
    Returnerar närmaste occurrence samma dag inom +/- minutes_window minuter.
    """
    candidates = OCC_INDEX.get((title_norm, date_str), [])
    if not candidates:
        return None

    best = None
    best_diff = None
    for c in candidates:
        diff_min = abs((c["start_dt"] - target_dt.replace(tzinfo=None)).total_seconds()) / 60.0
        if diff_min <= minutes_window and (best_diff is None or diff_min < best_diff):
            best = c
            best_diff = diff_min
    return best


def get_place_from_xml(course_summary: str, start_local: datetime) -> str:
    t_norm = norm_name(course_summary)
    date_str = start_local.strftime("%Y-%m-%d")

    hit = _nearest_occ(t_norm, date_str, start_local, minutes_window=2)
    if hit and hit.get("place"):
        return hit["place"]

    d = TITLE_DEFAULTS.get(t_norm, {})
    if d.get("place"):
        return d["place"]

    return "Övriga"


def get_teacher_from_xml(course_summary: str, start_local: datetime) -> str:
    t_norm = norm_name(course_summary)
    date_str = start_local.strftime("%Y-%m-%d")

    hit = _nearest_occ(t_norm, date_str, start_local, minutes_window=2)
    if hit and hit.get("teacher"):
        return hit["teacher"]

    d = TITLE_DEFAULTS.get(t_norm, {})
    if d.get("teacher"):
        return d["teacher"]

    return "Instruktör"
# ==========================================
# 5️⃣ SCHEMA-LOGIK (iCal för dagens pass)
# ==========================================
daily_schedule = []

try:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    resp.raise_for_status()

    gcal = Calendar.from_ical(resp.content)

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

        location = get_place_from_xml(summary, start_local)
        teacher = get_teacher_from_xml(summary, start_local)

        daily_schedule.append(
            {
                "course": summary,
                "time": f"{start_local.strftime('%H:%M')}–{end_local.strftime('%H:%M')}",
                "raw_time": start_local.strftime("%H:%M"),
                "place": location,
                "teacher": teacher,
                "start_dt": start_local,
                "end_dt": end_local,
            }
        )

except Exception as e:
    print(f"Fel vid hämtning/parsning av iCal: {e}")

daily_schedule.sort(key=lambda x: x["raw_time"])


# TEST: sätt now mitt i första lektionen (om du vill)
# if TEST_MODE and daily_schedule:
 #   now = daily_schedule[0]["start_dt"] + timedelta(minutes=5)

# Sätt is_live (ALLTID efter att now är klart)
#for c in daily_schedule:
 #   c["is_live"] = (c["start_dt"] <= now < c["end_dt"])

# ==========================================
# 6️⃣ PÅGÅR NU / NÄSTA
# ==========================================
ongoing = None
upcoming = None

live_banner = ""

if ongoing:
    live_banner = f"""
    <div class="livebanner">
        🔥 JUST NU I {html.escape(ongoing['place'].upper())}<br>
        <span class="liveclass">{html.escape(ongoing['course'])}</span>
    </div>
    """

for c in daily_schedule:
    if c["start_dt"] <= now < c["end_dt"]:
        ongoing = c
        break

for c in daily_schedule:
    if c["start_dt"] > now:
        upcoming = c
        break

def minutes_until(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def minutes_left(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def format_minutes(mins: int) -> str:
    mins = max(0, int(mins))
    if mins < 60:
        return f"{mins} min"
    h = mins // 60
    m = mins % 60
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"

def status_card(label, c, empty_text):
    # Special: "Pågår nu" när inget pågår -> Välkommen + nästa starttid
    if label == "Pågår nu" and not c:
        if upcoming:
            return f"""
            <div class="statuscard">
                <div class="statuslabel">Pågår nu</div>
                <div class="statustitle">Välkommen! Nästa klass startar {html.escape(upcoming['start_dt'].strftime('%H:%M'))}</div>
                <div class="statusmeta">{html.escape(upcoming['course'])} • {html.escape(upcoming['place'])} • {html.escape(upcoming['teacher'])}</div>
            </div>
            """
        return """
        <div class="statuscard">
            <div class="statuslabel">Pågår nu</div>
            <div class="statustitle">Välkommen! Inget mer schemalagt idag</div>
        </div>
        """

    # Standard: om kortet saknar data (t.ex. Nästa när inget finns)
    if not c:
        return f"""
        <div class="statuscard">
            <div class="statuslabel">{label}</div>
            <div class="statustitle">{html.escape(empty_text)}</div>
        </div>
        """

    extra = ""
    if label == "Pågår nu":
        extra = f"{format_minutes(minutes_left(c['end_dt']))} kvar"
    elif label == "Nästa":
        extra = f"Startar om {format_minutes(minutes_until(c['start_dt']))}"

    return f"""
    <div class="statuscard">
        <div class="statuslabel">{label}{'<span class="pill">LIVE</span>' if label == 'Pågår nu' else ''}</div>
        <div class="statustitle">{html.escape(c['course'])}</div>
        <div class="statusmeta">{html.escape(c['time'])} • {html.escape(c['place'])} • {html.escape(c['teacher'])}</div>
        <div class="statusextra">{html.escape(extra)}</div>
    </div>
    """

status_html = f"""
<div class="statuswrap">
    {status_card("Pågår nu", ongoing, "Ingen lektion pågår just nu")}
    {status_card("Nästa", upcoming, "Inget mer schemalagt idag")}
</div>
"""

# ==========================================
# 7️⃣ HTML-GENERERING
# ==========================================
def render_col(title, classes):
    cards = "".join(
        [
            f"""
        <div class="card {'live' if c.get('is_live') else ''}">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>"""
            for c in classes
        ]
    ) or '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

light = [c for c in daily_schedule if c["place"] == "Light Box"]
black = [c for c in daily_schedule if c["place"] == "Black Box"]
other = [c for c in daily_schedule if c["place"] not in ("Light Box", "Black Box")]

html_out = f"""
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <style>
        body {{ font-family: sans-serif; background: #fff; margin: 0; padding: 20px; color: #333; }}
        h1 {{ text-align: center; margin: 0; font-size: 2.5rem; text-transform: uppercase; }}
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 30px; font-weight: bold; }}
        .wrapper {{ display: flex; gap: 20px; justify-content: center; align-items: flex-start; }}
        .column {{ flex: 1; min-width: 320px; }}
        h2 {{ background: #ee7a9f; color: white; padding: 15px; border-radius: 12px; text-align: center; margin-top: 0; }}
        .card {{ background: #f4d1ce; padding: 20px; border-radius: 18px; margin-bottom: 15px; border-left: 12px solid #ee7a9f; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .card.live {{
        border-left: 16px solid #ff4d6d;
        background: #ffe5ec;
        transform: scale(1.02);
        box-shadow: 0 8px 18px rgba(0,0,0,0.15); 
        }}
        .time {{ font-weight: bold; font-size: 1.3rem; }}
        .name {{ font-size: 1.4rem; font-weight: 800; margin: 5px 0; line-height: 1.1; }}
        .teacher {{ font-style: italic; color: #555; font-size: 1.1rem; }}

        .statuswrap {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; }}
        .statuscard {{ flex: 1; min-width: 320px; background: #fff7f9; border: 2px solid #ee7a9f; border-radius: 18px; padding: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); }}
        .statuslabel {{ font-weight: 900; text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.95rem; color: #ee7a9f; }}
        .statustitle {{ font-size: 1.6rem; font-weight: 900; margin: 6px 0 2px; line-height: 1.1; }}
        .statusmeta {{ font-size: 1.1rem; color: #444; }}
        .statusextra {{ margin-top: 8px; font-weight: 900; font-size: 1.05rem; color: #222; }}
        .pill {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: #ee7a9f; color: white; font-weight: 800; font-size: 0.95rem; margin-left: 8px; vertical-align: middle; }}
        .livebanner {{
        border: 2px solid #ee7a9f;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 18px;
        background: #fff7f9;
        box-shadow: 0 4px 6px rgba(0,0,0,0.06);
        font-weight: 900;
        font-size: 1.4rem;
        }}

.liverow {{
    padding: 6px 0;
}}

.livepill {{
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background: #ee7a9f;
    color: white;
    font-weight: 800;
    font-size: 0.9rem;
    margin-right: 10px;
    vertical-align: middle;
}}

.liveclass {{
    font-weight: 800;
}}
    
    </style>
</head>
<body>
    <h1>Dagens schema</h1>
    <div class="date">{today_label}</div>
    {live_banner}

    {status_html}

    <div class="wrapper">
        {render_col("Light Box", light)}
        {render_col("Black Box", black)}
        {render_col("Övriga", other) if other else ""}
    </div>

    <div style="text-align:center;color:#999;margin-top:20px;font-size:0.9rem;">
        Uppdaterad {now.strftime('%H:%M')}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
