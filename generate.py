import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import re
import os
import xml.etree.ElementTree as ET

# ==========================================
# 1) KONFIG
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")
XML_PATH = "data.xml"

# Kör TEST lokalt (valfritt):
# export SCHEDULE_TEST_MODE=1
TEST_MODE = os.getenv("SCHEDULE_TEST_MODE", "0") == "1"

# Sätt fast "nu" om du vill reproducera samma vy:
# export SCHEDULE_NOW="2026-02-02 12:00"
NOW_OVERRIDE = os.getenv("SCHEDULE_NOW")

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]


# ==========================================
# 2) HJÄLPARE: NORMALISERING
# ==========================================
def norm_spaces(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00A0", " ")  # NBSP -> space
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def norm_title(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Kurs: ", "")
    s = html.unescape(s)
    s = norm_spaces(s)
    return s.lower()

def norm_place(s: str) -> str:
    """
    Gör platsen kanonisk så filtering alltid funkar.
    """
    s = norm_spaces(s)

    # Vanliga varianter / case / extra ord
    low = s.lower()
    if "light" in low and "box" in low:
        return "Light Box"
    if "black" in low and "box" in low:
        return "Black Box"

    return s  # okänd/övrig


# ==========================================
# 3) ICAL TIDSZON
# ==========================================
def to_stockholm(dt):
    """
    MinaAktiviteter iCal kan vara UTC-taggad men redan "lokal".
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
# 4) XML: LÄS SÄKERT + LOOKUP-BYGG
# ==========================================
def load_xml_safe(xml_path: str) -> ET.Element:
    raw = open(xml_path, "r", encoding="utf-8", errors="replace").read()

    # ta bort kontrolltecken XML ogillar
    raw = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", raw)

    # fixa & som inte redan är en entitet
    raw = re.sub(
        r"&(?!(amp;|lt;|gt;|quot;|apos;|#[0-9]+;|#x[0-9A-Fa-f]+;))",
        "&amp;",
        raw,
    )

    return ET.fromstring(raw)

def _text(node) -> str:
    return norm_spaces(node.text) if node is not None and node.text else ""

def extract_instructors_from_event(event_node) -> str:
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
    """
    occ_index[(title_norm, 'YYYY-MM-DD')] = list[{start_dt, place, teacher}]
    title_defaults[title_norm] = {place, teacher}
    """
    root = load_xml_safe(xml_path)

    occ_index = {}
    title_defaults = {}

    for event in root.findall(".//event"):
        title = norm_spaces(event.findtext("title") or "")
        if not title:
            continue

        event_place = norm_place(event.findtext("place") or "")
        event_teacher = extract_instructors_from_event(event)

        t_norm = norm_title(title)

        title_defaults.setdefault(t_norm, {"place": "", "teacher": ""})
        if event_place and not title_defaults[t_norm]["place"]:
            title_defaults[t_norm]["place"] = event_place
        if event_teacher and not title_defaults[t_norm]["teacher"]:
            title_defaults[t_norm]["teacher"] = event_teacher

        for occ in event.findall(".//occasions/occasion"):
            sdt = norm_spaces(occ.findtext("startDateTime") or "")
            if not sdt:
                continue

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

            occasion_place = norm_place(occ.findtext("place") or "")
            final_place = occasion_place or event_place

            final_teacher = event_teacher

            occ_index.setdefault((t_norm, date_str), []).append(
                {"start_dt": dt_obj, "place": final_place, "teacher": final_teacher}
            )

    return occ_index, title_defaults


try:
    OCC_INDEX, TITLE_DEFAULTS = parse_xml_lookups(XML_PATH)
except Exception as e:
    print("Kunde inte läsa data.xml:", e)
    OCC_INDEX, TITLE_DEFAULTS = {}, {}

def _nearest_occ(title_norm: str, date_str: str, target_dt: datetime, minutes_window: int = 3):
    candidates = OCC_INDEX.get((title_norm, date_str), [])
    if not candidates:
        return None

    best = None
    best_diff = None
    target_naive = target_dt.replace(tzinfo=None)

    for c in candidates:
        diff_min = abs((c["start_dt"] - target_naive).total_seconds()) / 60.0
        if diff_min <= minutes_window and (best_diff is None or diff_min < best_diff):
            best = c
            best_diff = diff_min
    return best

def get_place_from_xml(course_summary: str, start_local: datetime) -> str:
    t_norm = norm_title(course_summary)
    date_str = start_local.strftime("%Y-%m-%d")

    hit = _nearest_occ(t_norm, date_str, start_local)
    if hit and hit.get("place"):
        return norm_place(hit["place"])

    d = TITLE_DEFAULTS.get(t_norm, {})
    if d.get("place"):
        return norm_place(d["place"])

    return "Övriga"

def get_teacher_from_xml(course_summary: str, start_local: datetime) -> str:
    t_norm = norm_title(course_summary)
    date_str = start_local.strftime("%Y-%m-%d")

    hit = _nearest_occ(t_norm, date_str, start_local)
    if hit and hit.get("teacher"):
        return norm_spaces(hit["teacher"]) or "Instruktör"

    d = TITLE_DEFAULTS.get(t_norm, {})
    if d.get("teacher"):
        return norm_spaces(d["teacher"]) or "Instruktör"

    return "Instruktör"


# ==========================================
# 5) NOW + DAGENS SCHEMA (ICAL)
# ==========================================
if NOW_OVERRIDE:
    now = TZ.localize(datetime.strptime(NOW_OVERRIDE, "%Y-%m-%d %H:%M"))
elif TEST_MODE:
    now = TZ.localize(datetime(2026, 2, 2, 12, 0, 0))
else:
    now = datetime.now(TZ)

TARGET_DATE = now.date()
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

daily_schedule = []

try:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(ICAL_URL, headers=headers, timeout=20)
    resp.raise_for_status()

    gcal = Calendar.from_ical(resp.content)

    for component in gcal.walk("VEVENT"):
        summary = norm_spaces(str(component.get("summary") or "")).replace("Kurs: ", "")
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
                "place": norm_place(location),
                "teacher": teacher,
                "start_dt": start_local,
                "end_dt": end_local,
                "is_live": (start_local <= now < end_local),
            }
        )

except Exception as e:
    print(f"Fel vid hämtning/parsning av iCal: {e}")

daily_schedule.sort(key=lambda x: x["raw_time"])


# ==========================================
# 6) PÅGÅR / NÄSTA
# ==========================================
ongoing = next((c for c in daily_schedule if c["start_dt"] <= now < c["end_dt"]), None)
upcoming = next((c for c in daily_schedule if c["start_dt"] > now), None)

def format_minutes(mins: int) -> str:
    mins = max(0, int(mins))
    if mins < 60:
        return f"{mins} min"
    h = mins // 60
    m = mins % 60
    return f"{h} h" if m == 0 else f"{h} h {m} min"

def minutes_until(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def minutes_left(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def status_card(label, c, empty_text):
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
# 7) HTML
# ==========================================
def render_col(title, classes):
    cards = "".join(
        f"""
        <div class="card {'live' if c.get('is_live') else ''}">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>"""
        for c in classes
    ) or '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
    return f'<div class="column"><h2>{title}</h2>{cards}</div>'

light = [c for c in daily_schedule if norm_place(c["place"]) == "Light Box"]
black = [c for c in daily_schedule if norm_place(c["place"]) == "Black Box"]
other = [c for c in daily_schedule if norm_place(c["place"]) not in ("Light Box", "Black Box")]

print(f"[debug] classes: total={len(daily_schedule)} light={len(light)} black={len(black)} other={len(other)}")

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
        Uppdaterad {now.strftime('%H:%M')}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_out)

print(f"Skapade index.html för {today_label} med {len(daily_schedule)} lektioner.")
