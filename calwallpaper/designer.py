"""
SVG visual generator for calwallpaper.
Renders Google Calendar-style Weekly Grid as the main view, with a sleek
mini month calendar sidebar on the left and dual timezone columns.
"""

import html
import datetime
import calendar
from zoneinfo import ZoneInfo


def escape(text):
    """Escape XML special characters."""
    return html.escape(str(text), quote=True)


def truncate(text, max_chars=22):
    """Truncate text with ellipsis if too long."""
    text = str(text).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def format_hour_12h(hour_24):
    """Format hour in 12h format (e.g. 7 AM, 12 PM, 2 PM)."""
    h = hour_24 % 24
    if h == 0:
        return "12 AM"
    elif h < 12:
        return f"{h} AM"
    elif h == 12:
        return "12 PM"
    else:
        return f"{h - 12} PM"


def assign_event_slots(events):
    """
    Assign sub-column slots for overlapping events in a single day.
    Adds 'slot_idx' and 'num_slots' to each event dictionary.
    """
    if not events:
        return []

    timed_events = [e for e in events if not e.get("all_day", False)]
    if not timed_events:
        return timed_events

    clusters = []
    curr_cluster = []
    curr_end = -1

    for ev in sorted(timed_events, key=lambda x: (x["start_minutes"], -x["duration_minutes"])):
        if not curr_cluster:
            curr_cluster.append(ev)
            curr_end = ev["end_minutes"]
        else:
            if ev["start_minutes"] < curr_end:
                curr_cluster.append(ev)
                curr_end = max(curr_end, ev["end_minutes"])
            else:
                clusters.append(curr_cluster)
                curr_cluster = [ev]
                curr_end = ev["end_minutes"]
    if curr_cluster:
        clusters.append(curr_cluster)

    results = []
    for cluster in clusters:
        slots = []
        for ev in cluster:
            placed = False
            for s_idx, end_t in enumerate(slots):
                if ev["start_minutes"] >= end_t:
                    slots[s_idx] = ev["end_minutes"]
                    ev["slot_idx"] = s_idx
                    placed = True
                    break
            if not placed:
                ev["slot_idx"] = len(slots)
                slots.append(ev["end_minutes"])

        num_slots = max(1, len(slots))
        for ev in cluster:
            ev["num_slots"] = num_slots
            results.append(ev)

    return results


# =========================================================================
# 1. MAIN VIEW: WEEKLY GRID WITH SIDEBAR MINI-MONTH CALENDAR
# =========================================================================

def generate_weekly_svg(canvas_w, canvas_h, config, days_data, is_sample_data=False):
    """
    Generate Google Calendar-style layout:
    - Left sidebar: Mini Month Calendar + Active Calendars Legend
    - Main area: 7-day Weekly Grid with Dual Timezones & Proportional Events
    """
    layout = config.get("layout", {})
    wallpaper_cfg = config.get("wallpaper", {})
    tz_cfg = config.get("timezones", {})
    grid_cfg = config.get("grid_hours", {})

    w_pct = layout.get("width_percent", 84) / 100.0
    h_pct = layout.get("height_percent", 76) / 100.0

    card_w = int(canvas_w * w_pct)
    card_h = int(canvas_h * h_pct)

    card_x = (canvas_w - card_w) // 2
    card_y = (canvas_h - card_h) // 2

    scale = canvas_w / 1920.0
    scale = max(0.8, min(scale, 2.2))

    tint = wallpaper_cfg.get("card_tint", "#080c14")
    opacity = wallpaper_cfg.get("card_opacity", 0.62)
    border_color = wallpaper_cfg.get("border_color", "rgba(255, 255, 255, 0.16)")

    font_family = "system-ui, -apple-system, 'Cantarell', 'DejaVu Sans', sans-serif"

    # Timezones
    primary_tz_name = tz_cfg.get("primary", "America/Denver")
    primary_label = tz_cfg.get("primary_label", "MDT")
    secondary_tz_name = tz_cfg.get("secondary", "America/Anchorage")
    secondary_label = tz_cfg.get("secondary_label", "AKDT")

    try:
        primary_tz = ZoneInfo(primary_tz_name)
    except Exception:
        primary_tz = ZoneInfo("America/Denver")

    try:
        secondary_tz = ZoneInfo(secondary_tz_name)
    except Exception:
        secondary_tz = ZoneInfo("America/Anchorage")

    now = datetime.datetime.now(primary_tz)
    today = now.date()
    full_month_str = now.strftime("%B %Y")

    # Determine Grid Hours
    grid_start_h = grid_cfg.get("start", 7)
    grid_end_h = grid_cfg.get("end", 21)

    for day in days_data:
        for ev in day["events"]:
            if not ev.get("all_day", False):
                s_h = ev["start_minutes"] // 60
                e_h = (ev["end_minutes"] + 59) // 60
                grid_start_h = min(grid_start_h, s_h)
                grid_end_h = max(grid_end_h, e_h)

    total_hours = grid_end_h - grid_start_h
    total_grid_minutes = total_hours * 60

    # Layout measurements
    pad_x = int(24 * scale)
    pad_top = int(20 * scale)
    pad_bottom = int(20 * scale)

    header_h = int(50 * scale)

    # SIDEBAR: Left column containing mini month calendar
    sidebar_w = int(220 * scale)
    sidebar_gap = int(22 * scale)

    # MAIN AREA: Weekly Grid
    main_area_x = pad_x + sidebar_w + sidebar_gap
    main_area_w = card_w - pad_x - main_area_x

    # Dual Timezone Gutter in Main Area
    gutter_w = int(104 * scale)
    sub_col_w = gutter_w // 2

    # Day columns
    num_days = len(days_data)
    weekly_grid_w = main_area_w - gutter_w
    col_w = weekly_grid_w // num_days

    day_header_h = int(56 * scale)

    all_day_events_exist = any(any(e.get("all_day", False) for e in d["events"]) for d in days_data)
    all_day_row_h = int(30 * scale) if all_day_events_exist else 0

    grid_top_y = pad_top + header_h + day_header_h + all_day_row_h
    grid_h = card_h - grid_top_y - pad_bottom
    hour_h = grid_h / float(total_hours)

    svg = []
    svg.append(f'<svg width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" xmlns="http://www.w3.org/2000/svg">')
    svg.append('<defs>')
    svg.append("""
      <filter id="cardGlow" x="-5%" y="-5%" width="110%" height="110%">
        <feDropShadow dx="0" dy="10" stdDeviation="20" flood-color="#000000" flood-opacity="0.5"/>
      </filter>
      <linearGradient id="headerShine" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.06"/>
        <stop offset="100%" stop-color="#ffffff" stop-opacity="0.00"/>
      </linearGradient>
    """)
    svg.append('</defs>')

    svg.append(f'<g transform="translate({card_x}, {card_y})" filter="url(#cardGlow)">')

    # Card background
    rx = int(22 * scale)
    svg.append(f'<rect x="0" y="0" width="{card_w}" height="{card_h}" rx="{rx}" fill="{tint}" fill-opacity="{opacity}" stroke="{border_color}" stroke-width="{max(1, int(1.5 * scale))}"/>')
    svg.append(f'<rect x="0" y="0" width="{card_w}" height="{int(card_h * 0.22)}" rx="{rx}" fill="url(#headerShine)"/>')

    # ================= TOP HEADER OVER MAIN AREA =================
    header_font_size = int(24 * scale)
    svg.append(f'<text x="{main_area_x}" y="{pad_top + header_font_size}" font-family="{font_family}" font-size="{header_font_size}" font-weight="700" fill="#f8fafc" letter-spacing="-0.5">{escape(full_month_str)}</text>')

    start_d = days_data[0]["date"].strftime("%b %-d")
    end_d = days_data[-1]["date"].strftime("%b %-d, %Y")
    sub_font_size = int(13 * scale)
    svg.append(f'<text x="{main_area_x}" y="{pad_top + header_font_size + int(18 * scale)}" font-family="{font_family}" font-size="{sub_font_size}" font-weight="500" fill="#94a3b8">{escape(start_d)} – {escape(end_d)} · Weekly Schedule</text>')

    # Total events count on right
    total_week_events = sum(len(d["events"]) for d in days_data)
    svg.append(f'<text x="{card_w - pad_x}" y="{pad_top + header_font_size}" text-anchor="end" font-family="{font_family}" font-size="{int(14 * scale)}" font-weight="600" fill="#38bdf8">{total_week_events} Events This Week</text>')

    # Top divider line
    sep_y = pad_top + header_h
    svg.append(f'<line x1="{pad_x}" y1="{sep_y}" x2="{card_w - pad_x}" y2="{sep_y}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

    # ================= LEFT SIDEBAR =================
    sidebar_x = pad_x
    sidebar_content_y = sep_y + int(12 * scale)

    # 1. Mini Month Calendar
    mini_cal = calendar.Calendar(firstweekday=6)  # Sunday start
    month_weeks = mini_cal.monthdatescalendar(today.year, today.month)

    # Mini Month Title
    mini_title_font = int(14 * scale)
    svg.append(f'<text x="{sidebar_x + int(4 * scale)}" y="{sidebar_content_y + mini_title_font}" font-family="{font_family}" font-size="{mini_title_font}" font-weight="700" fill="#f1f5f9">{escape(full_month_str)}</text>')

    # Day Initials Row (S M T W T F S)
    mini_cell_w = sidebar_w // 7
    mini_day_initials_y = sidebar_content_y + mini_title_font + int(18 * scale)
    day_letters = ["S", "M", "T", "W", "T", "F", "S"]
    for di, dl in enumerate(day_letters):
        dl_x = sidebar_x + (di * mini_cell_w) + (mini_cell_w // 2)
        svg.append(f'<text x="{dl_x}" y="{mini_day_initials_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="600" fill="#64748b">{dl}</text>')

    # Mini Month Date Rows
    mini_dates_start_y = mini_day_initials_y + int(8 * scale)
    mini_row_h = int(23 * scale)

    week_start_date = days_data[0]["date"]
    week_end_date = days_data[-1]["date"]

    for r_i, w_dates in enumerate(month_weeks):
        r_y = mini_dates_start_y + (r_i * mini_row_h)

        # Highlight active week in mini calendar
        is_active_week = any(week_start_date <= d <= week_end_date for d in w_dates)
        if is_active_week:
            pill_rx = int(11 * scale)
            svg.append(f'<rect x="{sidebar_x}" y="{r_y + int(2 * scale)}" width="{sidebar_w}" height="{mini_row_h - int(2 * scale)}" rx="{pill_rx}" fill="rgba(37, 99, 235, 0.16)"/>')

        for c_i, d_obj in enumerate(w_dates):
            cell_center_x = sidebar_x + (c_i * mini_cell_w) + (mini_cell_w // 2)
            d_num = str(d_obj.day)
            is_d_today = (d_obj == today)
            is_cur_month = (d_obj.month == today.month)

            num_center_y = r_y + int(15 * scale)

            if is_d_today:
                # Blue circle for today in mini calendar
                dot_r = int(9 * scale)
                svg.append(f'<circle cx="{cell_center_x}" cy="{num_center_y - int(3 * scale)}" r="{dot_r}" fill="#2563eb"/>')
                svg.append(f'<text x="{cell_center_x}" y="{num_center_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="700" fill="#ffffff">{d_num}</text>')
            elif is_cur_month:
                font_wt = "600" if is_active_week else "500"
                fill_col = "#e2e8f0" if is_active_week else "#94a3b8"
                svg.append(f'<text x="{cell_center_x}" y="{num_center_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="{font_wt}" fill="{fill_col}">{d_num}</text>')
            else:
                # Grayed out day from adjacent month
                svg.append(f'<text x="{cell_center_x}" y="{num_center_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(10 * scale)}" font-weight="500" fill="#475569">{d_num}</text>')

    # 2. Divider below mini calendar
    sidebar_sep_y = mini_dates_start_y + (len(month_weeks) * mini_row_h) + int(16 * scale)
    svg.append(f'<line x1="{sidebar_x}" y1="{sidebar_sep_y}" x2="{sidebar_x + sidebar_w}" y2="{sidebar_sep_y}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

    # 3. Active Calendars List in Sidebar
    cal_section_y = sidebar_sep_y + int(18 * scale)
    svg.append(f'<text x="{sidebar_x + int(4 * scale)}" y="{cal_section_y}" font-family="{font_family}" font-size="{int(11 * scale)}" font-weight="700" fill="#64748b" letter-spacing="1">MY CALENDARS</text>')

    active_cals = [c for c in config.get("calendars", []) if c.get("enabled", True) and (c.get("url") or c.get("path"))]
    cal_item_start_y = cal_section_y + int(16 * scale)
    item_gap = int(28 * scale)

    for ci, cal in enumerate(active_cals):
        ci_y = cal_item_start_y + (ci * item_gap)
        c_name = cal.get("name", "Calendar")
        c_color = cal.get("color", "#38bdf8")

        # Count events for this calendar this week
        c_count = sum(1 for d in days_data for e in d["events"] if e.get("source") == c_name)

        # Color dot / checkbox
        dot_cx = sidebar_x + int(10 * scale)
        dot_cy = ci_y - int(4 * scale)
        svg.append(f'<circle cx="{dot_cx}" cy="{dot_cy}" r="{int(5 * scale)}" fill="{c_color}"/>')

        # Calendar name
        svg.append(f'<text x="{sidebar_x + int(22 * scale)}" y="{ci_y}" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="600" fill="#e2e8f0">{escape(truncate(c_name, 18))}</text>')

        # Event count badge
        count_text = f"{c_count} events" if c_count != 1 else "1 event"
        svg.append(f'<text x="{sidebar_x + int(22 * scale)}" y="{ci_y + int(14 * scale)}" font-family="{font_family}" font-size="{int(10 * scale)}" font-weight="500" fill="#64748b">{count_text}</text>')

    # Vertical Divider separating sidebar from main weekly grid
    vert_div_x = pad_x + sidebar_w + (sidebar_gap // 2)
    svg.append(f'<line x1="{vert_div_x}" y1="{sep_y}" x2="{vert_div_x}" y2="{card_h - pad_bottom}" stroke="rgba(255, 255, 255, 0.10)" stroke-width="1"/>')

    # ================= DUAL TIMEZONE GUTTER =================
    gutter_x = main_area_x
    day_header_y = sep_y + int(6 * scale)

    # Secondary Timezone (AKDT)
    tz1_center_x = gutter_x + (sub_col_w // 2)
    svg.append(f'<text x="{tz1_center_x}" y="{day_header_y + int(24 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(11 * scale)}" font-weight="700" fill="#64748b" letter-spacing="0.5">{escape(secondary_label)}</text>')
    svg.append(f'<text x="{tz1_center_x}" y="{day_header_y + int(40 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(9.5 * scale)}" font-weight="500" fill="#475569">GMT-8</text>')

    # Primary Timezone (MDT)
    tz2_center_x = gutter_x + sub_col_w + (sub_col_w // 2)
    svg.append(f'<text x="{tz2_center_x}" y="{day_header_y + int(24 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(11 * scale)}" font-weight="700" fill="#38bdf8" letter-spacing="0.5">{escape(primary_label)}</text>')
    svg.append(f'<text x="{tz2_center_x}" y="{day_header_y + int(40 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(9.5 * scale)}" font-weight="500" fill="#0284c7">GMT-6</text>')

    svg.append(f'<line x1="{gutter_x + sub_col_w}" y1="{day_header_y + int(10 * scale)}" x2="{gutter_x + sub_col_w}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.05)" stroke-width="1"/>')
    svg.append(f'<line x1="{gutter_x + gutter_w}" y1="{day_header_y}" x2="{gutter_x + gutter_w}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>')

    # ================= 7 DAY HEADERS (Google Calendar Style) =================
    for i, day_info in enumerate(days_data):
        col_x = gutter_x + gutter_w + (i * col_w)
        d_obj = day_info["date"]
        is_today = day_info["is_today"]

        day_name = d_obj.strftime("%a").upper()
        day_num = d_obj.strftime("%-d")

        center_x = col_x + (col_w // 2)
        name_color = "#3b82f6" if is_today else "#94a3b8"
        svg.append(f'<text x="{center_x}" y="{day_header_y + int(18 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="600" fill="{name_color}" letter-spacing="0.5">{escape(day_name)}</text>')

        num_y = day_header_y + int(40 * scale)
        if is_today:
            circle_r = int(15 * scale)
            svg.append(f'<circle cx="{center_x}" cy="{num_y - int(4 * scale)}" r="{circle_r}" fill="#2563eb"/>')
            svg.append(f'<text x="{center_x}" y="{num_y + int(1 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(14 * scale)}" font-weight="700" fill="#ffffff">{escape(day_num)}</text>')
        else:
            svg.append(f'<text x="{center_x}" y="{num_y + int(1 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(15 * scale)}" font-weight="600" fill="#e2e8f0">{escape(day_num)}</text>')

        if i > 0:
            svg.append(f'<line x1="{col_x}" y1="{day_header_y}" x2="{col_x}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

    svg.append(f'<line x1="{gutter_x}" y1="{grid_top_y}" x2="{card_w - pad_x}" y2="{grid_top_y}" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>')

    # ================= ALL-DAY EVENTS ROW =================
    if all_day_events_exist:
        for i, day_info in enumerate(days_data):
            col_x = gutter_x + gutter_w + (i * col_w)
            all_day_evs = [e for e in day_info["events"] if e.get("all_day", False)]
            for k, ev in enumerate(all_day_evs[:1]):
                color = ev.get("color", "#38bdf8")
                b_w = col_w - int(8 * scale)
                b_x = col_x + int(4 * scale)
                b_y = grid_top_y - all_day_row_h + int(4 * scale)
                b_h = all_day_row_h - int(8 * scale)
                svg.append(f'<rect x="{b_x}" y="{b_y}" width="{b_w}" height="{b_h}" rx="{int(4 * scale)}" fill="{color}" fill-opacity="0.85"/>')
                svg.append(f'<text x="{b_x + int(6 * scale)}" y="{b_y + int(16 * scale)}" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="600" fill="#ffffff">{escape(truncate(ev.get("title", ""), int(col_w / (9 * scale))))}</text>')

    # ================= HOURLY GRID & TIME GUTTER =================
    today_ref = datetime.date.today()

    for h_idx in range(total_hours + 1):
        hour_24 = grid_start_h + h_idx
        y_pos = grid_top_y + (h_idx * hour_h)

        line_color = "rgba(255, 255, 255, 0.08)" if h_idx > 0 else "rgba(255, 255, 255, 0.12)"
        svg.append(f'<line x1="{gutter_x}" y1="{y_pos}" x2="{card_w - pad_x}" y2="{y_pos}" stroke="{line_color}" stroke-width="1"/>')

        if h_idx < total_hours:
            dt_primary = datetime.datetime(today_ref.year, today_ref.month, today_ref.day, hour_24 % 24, 0, tzinfo=primary_tz)
            dt_secondary = dt_primary.astimezone(secondary_tz)

            time_str_primary = format_hour_12h(dt_primary.hour)
            time_str_secondary = format_hour_12h(dt_secondary.hour)

            text_y = y_pos + int(14 * scale)

            svg.append(f'<text x="{tz1_center_x}" y="{text_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="500" fill="#64748b">{escape(time_str_secondary)}</text>')
            svg.append(f'<text x="{tz2_center_x}" y="{text_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(11 * scale)}" font-weight="600" fill="#94a3b8">{escape(time_str_primary)}</text>')

    # ================= TIMED EVENTS RENDERING =================
    min_grid_m = grid_start_h * 60
    max_grid_m = grid_end_h * 60

    for i, day_info in enumerate(days_data):
        col_x = gutter_x + gutter_w + (i * col_w)
        timed_events = [e for e in day_info["events"] if not e.get("all_day", False)]

        slotted_events = assign_event_slots(timed_events)

        for ev in slotted_events:
            s_m = ev["start_minutes"]
            e_m = ev["end_minutes"]

            if e_m <= min_grid_m or s_m >= max_grid_m:
                continue

            clamp_start = max(min_grid_m, s_m)
            clamp_end = min(max_grid_m, e_m)

            top_offset = ((clamp_start - min_grid_m) / float(total_grid_minutes)) * grid_h
            event_dur_m = clamp_end - clamp_start
            event_h = max(int(22 * scale), (event_dur_m / float(total_grid_minutes)) * grid_h - int(2 * scale))

            slot_idx = ev.get("slot_idx", 0)
            num_slots = ev.get("num_slots", 1)

            slot_w = (col_w - int(8 * scale)) / float(num_slots)
            ev_x = col_x + int(4 * scale) + (slot_idx * slot_w)
            ev_y = grid_top_y + top_offset
            ev_w = slot_w - int(3 * scale)

            color = ev.get("color", "#38bdf8")
            title = ev.get("title", "Event")
            time_label = f"{ev.get('start_time_str', '')} – {ev.get('end_time_str', '')}"

            card_rx = int(5 * scale)
            svg.append(f'<rect x="{ev_x}" y="{ev_y}" width="{ev_w}" height="{event_h}" rx="{card_rx}" fill="{color}" fill-opacity="0.78" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1"/>')
            svg.append(f'<path d="M {ev_x} {ev_y + card_rx} A {card_rx} {card_rx} 0 0 1 {ev_x + card_rx} {ev_y} L {ev_x + int(4 * scale)} {ev_y} L {ev_x + int(4 * scale)} {ev_y + event_h} L {ev_x + card_rx} {ev_y + event_h} A {card_rx} {card_rx} 0 0 1 {ev_x} {ev_y + event_h - card_rx} Z" fill="#ffffff" fill-opacity="0.6"/>')

            text_pad_x = ev_x + int(8 * scale)
            max_char_len = max(6, int(ev_w / (7.5 * scale)))

            if event_h >= int(40 * scale):
                svg.append(f'<text x="{text_pad_x}" y="{ev_y + int(14 * scale)}" font-family="{font_family}" font-size="{int(11.5 * scale)}" font-weight="700" fill="#ffffff">{escape(truncate(title, max_char_len))}</text>')
                svg.append(f'<text x="{text_pad_x}" y="{ev_y + int(28 * scale)}" font-family="{font_family}" font-size="{int(9.5 * scale)}" font-weight="500" fill="rgba(255, 255, 255, 0.85)">{escape(time_label)}</text>')
            else:
                svg.append(f'<text x="{text_pad_x}" y="{ev_y + int(15 * scale)}" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="700" fill="#ffffff">{escape(truncate(title, max_char_len))}</text>')

    svg.append('</g>')
    svg.append('</svg>')

    return "\n".join(svg), card_x, card_y, card_w, card_h


# =========================================================================
# 2. STANDALONE MONTHLY CALENDAR VIEW (FULL MONTH)
# =========================================================================

def generate_monthly_svg(canvas_w, canvas_h, config, month_weeks, events_by_day, is_sample_data=False):
    """Generate standalone full monthly calendar grid SVG."""
    layout = config.get("layout", {})
    wallpaper_cfg = config.get("wallpaper", {})

    w_pct = layout.get("width_percent", 84) / 100.0
    h_pct = layout.get("height_percent", 78) / 100.0

    card_w = int(canvas_w * w_pct)
    card_h = int(canvas_h * h_pct)

    card_x = (canvas_w - card_w) // 2
    card_y = (canvas_h - card_h) // 2

    scale = canvas_w / 1920.0
    scale = max(0.8, min(scale, 2.2))

    tint = wallpaper_cfg.get("card_tint", "#080c14")
    opacity = wallpaper_cfg.get("card_opacity", 0.62)
    border_color = wallpaper_cfg.get("border_color", "rgba(255, 255, 255, 0.16)")

    font_family = "system-ui, -apple-system, 'Cantarell', 'DejaVu Sans', sans-serif"

    today = datetime.date.today()
    target_month = today.month

    month_title = today.strftime("%B %Y")

    pad_x = int(24 * scale)
    pad_top = int(20 * scale)
    pad_bottom = int(20 * scale)

    header_h = int(54 * scale)
    day_header_h = int(32 * scale)

    num_weeks = len(month_weeks)
    num_cols = 7

    grid_w = card_w - (pad_x * 2)
    grid_top_y = pad_top + header_h + day_header_h
    grid_h = card_h - grid_top_y - pad_bottom

    col_w = grid_w // num_cols
    row_h = grid_h / float(num_weeks)

    svg = []
    svg.append(f'<svg width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}" xmlns="http://www.w3.org/2000/svg">')
    svg.append('<defs>')
    svg.append("""
      <filter id="cardGlow" x="-5%" y="-5%" width="110%" height="110%">
        <feDropShadow dx="0" dy="10" stdDeviation="20" flood-color="#000000" flood-opacity="0.5"/>
      </filter>
      <linearGradient id="headerShine" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.06"/>
        <stop offset="100%" stop-color="#ffffff" stop-opacity="0.00"/>
      </linearGradient>
    """)
    svg.append('</defs>')

    svg.append(f'<g transform="translate({card_x}, {card_y})" filter="url(#cardGlow)">')

    rx = int(22 * scale)
    svg.append(f'<rect x="0" y="0" width="{card_w}" height="{card_h}" rx="{rx}" fill="{tint}" fill-opacity="{opacity}" stroke="{border_color}" stroke-width="{max(1, int(1.5 * scale))}"/>')
    svg.append(f'<rect x="0" y="0" width="{card_w}" height="{int(card_h * 0.22)}" rx="{rx}" fill="url(#headerShine)"/>')

    header_font_size = int(25 * scale)
    svg.append(f'<text x="{pad_x}" y="{pad_top + header_font_size}" font-family="{font_family}" font-size="{header_font_size}" font-weight="700" fill="#f8fafc" letter-spacing="-0.5">{escape(month_title)}</text>')

    total_events = sum(len(evs) for evs in events_by_day.values())
    sub_font_size = int(13 * scale)
    svg.append(f'<text x="{pad_x}" y="{pad_top + header_font_size + int(18 * scale)}" font-family="{font_family}" font-size="{sub_font_size}" font-weight="500" fill="#94a3b8">{total_events} Events · Monthly Calendar</text>')

    active_cals = [c for c in config.get("calendars", []) if c.get("enabled", True) and (c.get("url") or c.get("path"))]
    legend_y = pad_top + header_font_size
    cur_legend_x = card_w - pad_x
    for cal in reversed(active_cals):
        name = truncate(cal.get("name", "Cal"), 20)
        col = cal.get("color", "#38bdf8")
        approx_w = int(len(name) * 8 * scale) + int(26 * scale)
        cur_legend_x -= approx_w
        svg.append(f'<circle cx="{cur_legend_x + int(6 * scale)}" cy="{legend_y - int(6 * scale)}" r="{int(5 * scale)}" fill="{col}"/>')
        svg.append(f'<text x="{cur_legend_x + int(16 * scale)}" y="{legend_y - int(2 * scale)}" font-family="{font_family}" font-size="{int(12.5 * scale)}" fill="#e2e8f0" font-weight="600">{escape(name)}</text>')
        cur_legend_x -= int(12 * scale)

    sep_y = pad_top + header_h
    svg.append(f'<line x1="{pad_x}" y1="{sep_y}" x2="{card_w - pad_x}" y2="{sep_y}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

    start_mode = layout.get("start_day", "sunday").lower()
    if start_mode == "monday":
        day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    else:
        day_names = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]

    day_header_y = sep_y + int(4 * scale)
    for c_idx, d_name in enumerate(day_names):
        c_x = pad_x + (c_idx * col_w)
        center_x = c_x + (col_w // 2)
        svg.append(f'<text x="{center_x}" y="{day_header_y + int(18 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="600" fill="#94a3b8" letter-spacing="0.5">{escape(d_name)}</text>')

    svg.append(f'<line x1="{pad_x}" y1="{grid_top_y}" x2="{card_w - pad_x}" y2="{grid_top_y}" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>')

    for r_idx, week in enumerate(month_weeks):
        cell_y = grid_top_y + (r_idx * row_h)

        if r_idx > 0:
            svg.append(f'<line x1="{pad_x}" y1="{cell_y}" x2="{card_w - pad_x}" y2="{cell_y}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

        for c_idx, d_obj in enumerate(week):
            cell_x = pad_x + (c_idx * col_w)
            is_today = (d_obj == today)
            is_in_month = (d_obj.month == target_month)

            if c_idx > 0 and r_idx == 0:
                svg.append(f'<line x1="{cell_x}" y1="{grid_top_y}" x2="{cell_x}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

            if is_today:
                svg.append(f'<rect x="{cell_x + 1}" y="{cell_y + 1}" width="{col_w - 2}" height="{int(row_h) - 2}" fill="rgba(37, 99, 235, 0.09)"/>')

            date_num_str = str(d_obj.day)
            num_center_x = cell_x + (col_w // 2)
            num_y = cell_y + int(20 * scale)

            if is_today:
                circle_r = int(12 * scale)
                svg.append(f'<circle cx="{num_center_x}" cy="{num_y - int(4 * scale)}" r="{circle_r}" fill="#2563eb"/>')
                svg.append(f'<text x="{num_center_x}" y="{num_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="700" fill="#ffffff">{escape(date_num_str)}</text>')
            elif is_in_month:
                svg.append(f'<text x="{num_center_x}" y="{num_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="600" fill="#e2e8f0">{escape(date_num_str)}</text>')
            else:
                svg.append(f'<text x="{num_center_x}" y="{num_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="500" fill="#475569">{escape(date_num_str)}</text>')

            date_key = d_obj.strftime("%Y-%m-%d")
            cell_events = events_by_day.get(date_key, [])

            chip_h = int(22 * scale)
            chip_gap = int(4 * scale)
            chips_start_y = cell_y + int(30 * scale)

            avail_h = row_h - int(34 * scale)
            max_chips_fit = max(1, int(avail_h // (chip_h + chip_gap)))

            rendered_chips = cell_events[:max_chips_fit]
            overflow = len(cell_events) - max_chips_fit

            for ev_i, ev in enumerate(rendered_chips):
                ey = chips_start_y + (ev_i * (chip_h + chip_gap))
                ew = col_w - int(10 * scale)
                ex = cell_x + int(5 * scale)
                erx = int(4 * scale)

                color = ev.get("color", "#38bdf8")
                title = ev.get("title", "Event")
                time_str = ev.get("start_time_str", "")

                if time_str and time_str != "All Day":
                    chip_text = f"{time_str} {title}"
                else:
                    chip_text = title

                max_chars = max(8, int(ew / (7.2 * scale)))
                display_text = truncate(chip_text, max_chars)

                svg.append(f'<rect x="{ex}" y="{ey}" width="{ew}" height="{chip_h}" rx="{erx}" fill="{color}" fill-opacity="0.80"/>')
                svg.append(f'<rect x="{ex}" y="{ey}" width="{int(3 * scale)}" height="{chip_h}" rx="{int(1.5 * scale)}" fill="#ffffff" fill-opacity="0.6"/>')
                svg.append(f'<text x="{ex + int(6 * scale)}" y="{ey + int(15 * scale)}" font-family="{font_family}" font-size="{int(10.5 * scale)}" font-weight="600" fill="#ffffff">{escape(display_text)}</text>')

            if overflow > 0:
                more_y = chips_start_y + (max_chips_fit * (chip_h + chip_gap)) + int(11 * scale)
                svg.append(f'<text x="{num_center_x}" y="{more_y}" text-anchor="middle" font-family="{font_family}" font-size="{int(10 * scale)}" font-weight="600" fill="#94a3b8">+{overflow} more</text>')

    svg.append('</g>')
    svg.append('</svg>')

    return "\n".join(svg), card_x, card_y, card_w, card_h
