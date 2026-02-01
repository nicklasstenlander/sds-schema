import requests
from icalendar import Calendar
from datetime import datetime, timedelta
import pytz
import html
import re

# ==========================================
# 1) KONFIG
# ==========================================
ICAL_URL = "https://minaaktiviteter.se/sollentunadans/ical"
TZ = pytz.timezone("Europe/Stockholm")

TEST_MODE = True  # sätt True om du vill låsa datum/tid vid test
TEST_NOW = datetime(2026, 2, 2, 12, 0, 0, tzinfo=TZ)

FORCE_LIVE_PREVIEW = True  # om True: tvingar "LIVE" på första lektionen för att se highlight

now = TEST_NOW if TEST_MODE else datetime.now(TZ)
TARGET_DATE = now.date()

VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MÅNADER = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
today_label = f"{VECKODAGAR[now.weekday()]} {now.day} {MÅNADER[now.month - 1]} {now.year}"

# ==========================================
# 2) NORMALISERING / HJÄLPARE
# ==========================================
def norm_spaces(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00A0", " ")  # NBSP -> space
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def norm_title(s: str) -> str:
    """Normaliserar kursnamn så vi matchar stabilt."""
    if not s:
        return ""
    s = s.replace("Kurs: ", "")
    s = html.unescape(s)
    s = norm_spaces(s)
    return s.lower()

def norm_place(s: str) -> str:
    """Gör platsen kanonisk så filtering alltid funkar."""
    s = norm_spaces(s)
    low = s.lower()
    if "light" in low and "box" in low:
        return "Light Box"
    if "black" in low and "box" in low:
        return "Black Box"
    return s if s else "Övriga"

def format_minutes(mins: int) -> str:
    mins = max(0, int(mins))
    if mins < 60:
        return f"{mins} min"
    h = mins // 60
    m = mins % 60
    if m == 0:
        return f"{h} h"
    return f"{h} h {m} min"

def minutes_until(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

def minutes_left(dt: datetime) -> int:
    return max(0, int((dt - now).total_seconds() // 60))

# ==========================================
# 3) iCal-tidsfix (din beprövade “UTC men egentligen lokal”)
# ==========================================
def to_stockholm(dt_obj):
    """
    MinaAktiviteter iCal verkar ibland vara UTC-taggad men redan i lokal tid.
    Vi gör:
      1) konvertera till Stockholm
      2) dra bort Stockholms aktuella offset (1h/2h) för att neutralisera fel-taggning
    """
    if not isinstance(dt_obj, datetime):
        return None

    if dt_obj.tzinfo is None:
        dt_obj = pytz.utc.localize(dt_obj)

    local = dt_obj.astimezone(TZ)
    offset = local.utcoffset() or timedelta(0)
    return local - offset

# ==========================================
# 4) "HÅRDKODADE" SALAR + LÄRARE
#    (Auto-utdragna från din data.xml tidigare idag)
#    Nyckel: "kursnorm|Veckodag|HH:MM"
#    Fallback: per kursnorm
# ==========================================
PLACE_BY_OCC = {
    # ... (kortad kommentar) ...
    # Format: "kursnamn i lowercase|Måndag|17:00": "Light Box/Black Box/Övriga"
    'advanced contemporary|Torsdag|18:30': 'Black Box',
    'ap jazz step 1|Måndag|20:15': 'Black Box',
    'ap step 1 contemporary|Onsdag|19:45': 'Black Box',
    'ap step 2 contemporary|Onsdag|18:15': 'Black Box',
    'ap step 2 jazz|Måndag|17:15': 'Black Box',
    'ap street/commercial step 1|Onsdag|18:15': 'Light Box',
    'ap street/commercial step 2|Onsdag|19:45': 'Light Box',
    'ap technical skills step 1|Måndag|18:30': 'Black Box',
    'ap technical skills step 2|Måndag|19:30': 'Black Box',
    'balett 7-9|Onsdag|17:15': 'Light Box',
    'balett 9+|Onsdag|19:15': 'Light Box',
    'barnbalett 5-6|Tisdag|17:00': 'Black Box',
    'barndans 3-4|Söndag|09:30': 'Black Box',
    'barndans 4-5|Lördag|09:30': 'Light Box',
    'barndans 5-6|Söndag|10:30': 'Black Box',
    'barndans med förälder|Lördag|10:30': 'Light Box',
    'barndans med förälder|Söndag|11:30': 'Light Box',
    'cheerdance 7-8|Söndag|13:30': 'Black Box',
    'commercial hiphop 13+|Onsdag|20:15': 'Light Box',
    'commercial jazz 11+|Torsdag|19:30': 'Light Box',
    'contemporary 11+|Tisdag|19:30': 'Light Box',
    'education program 1|Måndag|17:00': 'Light Box',
    'education program 2|Torsdag|17:00': 'Light Box',
    'education program 3|Tisdag|17:00': 'Light Box',
    'ep 1 contemporary|Tisdag|18:00': 'Black Box',
    'ep 1 jazz|Torsdag|18:00': 'Light Box',
    'ep 2 contemporary|Tisdag|19:30': 'Black Box',
    'ep 2 jazz|Torsdag|19:30': 'Light Box',
    'ep 3 contemporary|Tisdag|20:30': 'Black Box',
    'ep 3 jazz|Torsdag|20:30': 'Light Box',
    'jazz & funk|Tisdag|20:30': 'Light Box',
    'jazz 16+|Torsdag|20:30': 'Black Box',
    'jazz/balett 55+|Tisdag|11:00': 'Light Box',
    'jazz kids 5-6|Söndag|12:30': 'Light Box',
    'juniorstreet 7-9|Torsdag|17:00': 'Light Box',
    'k-pop 10+|Torsdag|18:00': 'Black Box',
    'k-pop 8-10|Torsdag|17:00': 'Black Box',
    'k-pop kids 6-7|Torsdag|16:00': 'Black Box',
    'performance advanced|Onsdag|17:15': 'Light Box',
    'performance intermediate|Onsdag|18:15': 'Black Box',
    'popstars 5-6|Söndag|11:30': 'Black Box',
    'showjazz 7-9|Tisdag|18:00': 'Light Box',
    'showjazz 8-9|Tisdag|17:00': 'Black Box',
    'streetdance 10+|Tisdag|19:30': 'Light Box',
    'streetdance 8-9|Tisdag|18:30': 'Light Box',
    'talent program|Måndag|17:00': 'Light Box',
    'talent program jazz|Måndag|18:30': 'Black Box',
    'talent program street|Måndag|19:30': 'Black Box',
    'technical skills|Måndag|18:30': 'Black Box',
    'tiktok 10+|Söndag|15:30': 'Black Box',
    'tiktok 8-9|Söndag|14:30': 'Black Box',
    'tillval talent program|Måndag|20:30': 'Light Box',
}

TEACHER_BY_OCC = {
    'advanced contemporary|Torsdag|18:30': 'Amanda',
    'ap jazz step 1|Måndag|20:15': 'Madde',
    'ap step 1 contemporary|Onsdag|19:45': 'Amanda, Sofia',
    'ap step 2 contemporary|Onsdag|18:15': 'Sofia',
    'ap step 2 jazz|Måndag|17:15': 'Amanda',
    'ap street/commercial step 1|Onsdag|18:15': 'Isabella, Jennifer',
    'ap street/commercial step 2|Onsdag|19:45': 'Isabella, Jennifer',
    'ap technical skills step 1|Måndag|18:30': 'Amanda',
    'ap technical skills step 2|Måndag|19:30': 'Amanda',
    'balett 7-9|Onsdag|17:15': 'Linnea',
    'balett 9+|Onsdag|19:15': 'Linnea',
    'barnbalett 5-6|Tisdag|17:00': 'Linnea',
    'barndans 3-4|Söndag|09:30': 'Maja',
    'barndans 4-5|Lördag|09:30': 'Maja',
    'barndans 5-6|Söndag|10:30': 'Maja',
    'barndans med förälder|Lördag|10:30': 'Maja',
    'barndans med förälder|Söndag|11:30': 'Maja',
    'cheerdance 7-8|Söndag|13:30': 'Amanda',
    'commercial hiphop 13+|Onsdag|20:15': 'Sofia',
    'commercial jazz 11+|Torsdag|19:30': 'Amanda',
    'contemporary 11+|Tisdag|19:30': 'Sofia',
    'education program 1|Måndag|17:00': 'Amanda',
    'education program 2|Torsdag|17:00': 'Amanda',
    'education program 3|Tisdag|17:00': 'Amanda',
    'ep 1 contemporary|Tisdag|18:00': 'Sofia',
    'ep 1 jazz|Torsdag|18:00': 'Amanda',
    'ep 2 contemporary|Tisdag|19:30': 'Sofia',
    'ep 2 jazz|Torsdag|19:30': 'Amanda',
    'ep 3 contemporary|Tisdag|20:30': 'Sofia',
    'ep 3 jazz|Torsdag|20:30': 'Amanda',
    'jazz & funk|Tisdag|20:30': 'Amanda',
    'jazz 16+|Torsdag|20:30': 'Amanda',
    'jazz/balett 55+|Tisdag|11:00': 'Linnea',
    'jazz kids 5-6|Söndag|12:30': 'Amanda',
    'juniorstreet 7-9|Torsdag|17:00': 'Sofia',
    'k-pop 10+|Torsdag|18:00': 'Sofia',
    'k-pop 8-10|Torsdag|17:00': 'Sofia',
    'k-pop kids 6-7|Torsdag|16:00': 'Sofia',
    'performance advanced|Onsdag|17:15': 'Amanda',
    'performance intermediate|Onsdag|18:15': 'Amanda',
    'popstars 5-6|Söndag|11:30': 'Amanda',
    'showjazz 7-9|Tisdag|18:00': 'Amanda',
    'showjazz 8-9|Tisdag|17:00': 'Amanda',
    'streetdance 10+|Tisdag|19:30': 'Sofia',
    'streetdance 8-9|Tisdag|18:30': 'Sofia',
    'talent program|Måndag|17:00': 'Amanda',
    'talent program jazz|Måndag|18:30': 'Amanda',
    'talent program street|Måndag|19:30': 'Sofia',
    'technical skills|Måndag|18:30': 'Amanda',
    'tiktok 10+|Söndag|15:30': 'Sofia',
    'tiktok 8-9|Söndag|14:30': 'Sofia',
    'tillval talent program|Måndag|20:30': 'Amanda',
}

# Fallback om (kurs|dag|tid) inte matchar
PLACE_BY_TITLE = {
    'advanced contemporary': 'Black Box',
    'ap jazz step 1': 'Black Box',
    'ap step 1 contemporary': 'Black Box',
    'ap step 2 contemporary': 'Black Box',
    'ap step 2 jazz': 'Black Box',
    'ap street/commercial step 1': 'Light Box',
    'ap street/commercial step 2': 'Light Box',
    'ap technical skills step 1': 'Black Box',
    'ap technical skills step 2': 'Black Box',
    'balett 7-9': 'Light Box',
    'balett 9+': 'Light Box',
    'barnbalett 5-6': 'Black Box',
    'barndans 3-4': 'Black Box',
    'barndans 4-5': 'Light Box',
    'barndans 5-6': 'Black Box',
    'barndans med förälder': 'Light Box',
    'cheerdance 7-8': 'Black Box',
    'commercial hiphop 13+': 'Light Box',
    'commercial jazz 11+': 'Light Box',
    'contemporary 11+': 'Light Box',
    'education program 1': 'Light Box',
    'education program 2': 'Light Box',
    'education program 3': 'Light Box',
    'ep 1 contemporary': 'Black Box',
    'ep 1 jazz': 'Light Box',
    'ep 2 contemporary': 'Black Box',
    'ep 2 jazz': 'Light Box',
    'ep 3 contemporary': 'Black Box',
    'ep 3 jazz': 'Light Box',
    'jazz & funk': 'Light Box',
    'jazz 16+': 'Black Box',
    'jazz/balett 55+': 'Light Box',
    'jazz kids 5-6': 'Light Box',
    'juniorstreet 7-9': 'Light Box',
    'k-pop 10+': 'Black Box',
    'k-pop 8-10': 'Black Box',
    'k-pop kids 6-7': 'Black Box',
    'performance advanced': 'Light Box',
    'performance intermediate': 'Black Box',
    'popstars 5-6': 'Black Box',
    'showjazz 7-9': 'Light Box',
    'showjazz 8-9': 'Black Box',
    'streetdance 10+': 'Light Box',
    'streetdance 8-9': 'Light Box',
    'talent program': 'Light Box',
    'talent program jazz': 'Black Box',
    'talent program street': 'Black Box',
    'technical skills': 'Black Box',
    'tiktok 10+': 'Black Box',
    'tiktok 8-9': 'Black Box',
    'tillval talent program': 'Light Box',
}

TEACHER_BY_TITLE = {
    'advanced contemporary': 'Amanda',
    'ap jazz step 1': 'Madde',
    'ap step 1 contemporary': 'Amanda, Sofia',
    'ap step 2 contemporary': 'Sofia',
    'ap step 2 jazz': 'Amanda',
    'ap street/commercial step 1': 'Isabella, Jennifer',
    'ap street/commercial step 2': 'Isabella, Jennifer',
    'ap technical skills step 1': 'Amanda',
    'ap technical skills step 2': 'Amanda',
    'balett 7-9': 'Linnea',
    'balett 9+': 'Linnea',
    'barnbalett 5-6': 'Linnea',
    'barndans 3-4': 'Maja',
    'barndans 4-5': 'Maja',
    'barndans 5-6': 'Maja',
    'barndans med förälder': 'Maja',
    'cheerdance 7-8': 'Amanda',
    'commercial hiphop 13+': 'Sofia',
    'commercial jazz 11+': 'Amanda',
    'contemporary 11+': 'Sofia',
    'education program 1': 'Amanda',
    'education program 2': 'Amanda',
    'education program 3': 'Amanda',
    'ep 1 contemporary': 'Sofia',
    'ep 1 jazz': 'Amanda',
    'ep 2 contemporary': 'Sofia',
    'ep 2 jazz': 'Amanda',
    'ep 3 contemporary': 'Sofia',
    'ep 3 jazz': 'Amanda',
    'jazz & funk': 'Amanda',
    'jazz 16+': 'Amanda',
    'jazz/balett 55+': 'Linnea',
    'jazz kids 5-6': 'Amanda',
    'juniorstreet 7-9': 'Sofia',
    'k-pop 10+': 'Sofia',
    'k-pop 8-10': 'Sofia',
    'k-pop kids 6-7': 'Sofia',
    'performance advanced': 'Amanda',
    'performance intermediate': 'Amanda',
    'popstars 5-6': 'Amanda',
    'showjazz 7-9': 'Amanda',
    'showjazz 8-9': 'Amanda',
    'streetdance 10+': 'Sofia',
    'streetdance 8-9': 'Sofia',
    'talent program': 'Amanda',
    'talent program jazz': 'Amanda',
    'talent program street': 'Sofia',
    'technical skills': 'Amanda',
    'tiktok 10+': 'Sofia',
    'tiktok 8-9': 'Sofia',
    'tillval talent program': 'Amanda',
}

def get_place(course_summary: str, start_local: datetime) -> str:
    t = norm_title(course_summary)
    weekday = VECKODAGAR[start_local.weekday()]
    hhmm = start_local.strftime("%H:%M")
    key = f"{t}|{weekday}|{hhmm}"
    p = PLACE_BY_OCC.get(key)
    if p:
        return norm_place(p)
    p = PLACE_BY_TITLE.get(t)
    if p:
        return norm_place(p)
    return "Övriga"

def get_teacher(course_summary: str, start_local: datetime) -> str:
    t = norm_title(course_summary)
    weekday = VECKODAGAR[start_local.weekday()]
    hhmm = start_local.strftime("%H:%M")
    key = f"{t}|{weekday}|{hhmm}"
    x = TEACHER_BY_OCC.get(key)
    if x:
        return x
    x = TEACHER_BY_TITLE.get(t)
    if x:
        return x
    return "Instruktör"

# ==========================================
# 5) HÄMTA DAGENS PASS FRÅN iCal
# ==========================================
print("Downloading iCal...")
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(ICAL_URL, headers=headers, timeout=60)
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

    place = get_place(summary, start_local)
    teacher = get_teacher(summary, start_local)

    daily_schedule.append({
        "course": summary,
        "time": f"{start_local:%H:%M}–{end_local:%H:%M}",
        "place": place,
        "teacher": teacher,
        "start_dt": start_local,
        "end_dt": end_local,
        "is_live": (start_local <= now < end_local),
    })

daily_schedule.sort(key=lambda x: x["start_dt"])

# Force live-preview om du vill se highlight visuellt
if FORCE_LIVE_PREVIEW and daily_schedule:
    daily_schedule[0]["is_live"] = True

print("Schedule generated:", len(daily_schedule), "classes")

# ==========================================
# 6) PÅGÅR NU / NÄSTA
#    + Banner om flera pågår samtidigt (t.ex. i båda salar)
# ==========================================
ongoing_list = [c for c in daily_schedule if c["is_live"]]
ongoing = ongoing_list[0] if ongoing_list else None

upcoming = None
for c in daily_schedule:
    if c["start_dt"] > now:
        upcoming = c
        break

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

live_banner = ""
if ongoing_list:
    rows = ""
    for c in ongoing_list:
        rows += f"""
        <div class="liverow">
            <span class="livepill">LIVE</span>
            <strong>{html.escape(c['place'])}</strong>: {html.escape(c['course'])}
        </div>
        """
    live_banner = f"""
    <div class="livebanner">
        🔥 JUST NU
        {rows}
    </div>
    """

# ==========================================
# 7) HTML
# ==========================================
def render_col(title, classes):
    cards = "".join([
        f"""
        <div class="card {'live' if c.get('is_live') else ''}">
            <div class="time">{c['time']}</div>
            <div class="name">{html.escape(c['course'])}</div>
            <div class="teacher">{html.escape(c['teacher'])}</div>
        </div>"""
        for c in classes
    ]) or '<p style="text-align:center; color:#999; margin-top:40px;">Inga lektioner</p>'
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
        .date {{ text-align: center; color: #ee7a9f; font-size: 1.5rem; margin-bottom: 20px; font-weight: bold; }}

        .statuswrap {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 16px; }}
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
            margin: 0 auto 16px;
            background: #fff7f9;
            box-shadow: 0 4px 6px rgba(0,0,0,0.06);
            font-weight: 900;
            font-size: 1.2rem;
            max-width: 1100px;
        }}
        .liverow {{ padding: 6px 0; font-weight: 700; }}
        .livepill {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #ee7a9f;
            color: white;
            font-weight: 900;
            font-size: 0.85rem;
            margin-right: 10px;
            vertical-align: middle;
        }}

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
