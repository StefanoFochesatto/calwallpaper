"""
Google Calendar-style weekly grid SVG generator for calwallpaper.
Includes dual timezone column, 12h AM/PM format, Sunday-start week,
and proportional hourly event placement.
"""

import html
import datetime
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


def generate_weekly_svg(canvas_w, canvas_h, config, days_data, is_sample_data=False):
    """
    Generate Google Calendar-style weekly grid SVG without static frozen clock/line.
    """
    layout = config.get("layout", {})
    wallpaper_cfg = config.get("wallpaper", {})
    tz_cfg = config.get("timezones", {})
    grid_cfg = config.get("grid_hours", {})

    w_pct = layout.get("width_percent", 82) / 100.0
    h_pct = layout.get("height_percent", 74) / 100.0

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
    full_month_str = now.strftime("%B %Y")  # e.g. October 2026

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

    header_h = int(54 * scale)

    # Dual Timezone Gutter on the left
    gutter_w = int(110 * scale)
    sub_col_w = gutter_w // 2

    # Day columns
    num_days = len(days_data)
    grid_w = card_w - (pad_x * 2) - gutter_w
    col_w = grid_w // num_days

    # Day header row (Dates and Days)
    day_header_h = int(58 * scale)

    all_day_events_exist = any(any(e.get("all_day", False) for e in d["events"]) for d in days_data)
    all_day_row_h = int(32 * scale) if all_day_events_exist else 0

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

    # Card Background with rounded corners
    rx = int(22 * scale)
    svg.append(f'<rect x="0" y="0" width="{card_w}" height="{card_h}" rx="{rx}" fill="{tint}" fill-opacity="{opacity}" stroke="{border_color}" stroke-width="{max(1, int(1.5 * scale))}"/>')
    svg.append(f'<rect x="0" y="0" width="{card_w}" height="{int(card_h * 0.25)}" rx="{rx}" fill="url(#headerShine)"/>')

    # ================= TOP HEADER =================
    header_font_size = int(24 * scale)
    svg.append(f'<text x="{pad_x}" y="{pad_top + header_font_size}" font-family="{font_family}" font-size="{header_font_size}" font-weight="700" fill="#f8fafc" letter-spacing="-0.5">{escape(full_month_str)}</text>')

    # Date range subtitle
    start_d = days_data[0]["date"].strftime("%b %-d")
    end_d = days_data[-1]["date"].strftime("%b %-d, %Y")
    sub_font_size = int(13 * scale)
    svg.append(f'<text x="{pad_x}" y="{pad_top + header_font_size + int(18 * scale)}" font-family="{font_family}" font-size="{sub_font_size}" font-weight="500" fill="#94a3b8">{escape(start_d)} – {escape(end_d)} · Weekly Schedule</text>')

    # Right side: Calendar Legend Badges (prominent and clean)
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

    # Header bottom divider
    sep_y = pad_top + header_h
    svg.append(f'<line x1="{pad_x}" y1="{sep_y}" x2="{card_w - pad_x}" y2="{sep_y}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

    # ================= DUAL TIMEZONE GUTTER HEADER =================
    gutter_x = pad_x
    day_header_y = sep_y + int(6 * scale)

    # Sub-column 1 Header (Secondary: AKDT)
    tz1_center_x = gutter_x + (sub_col_w // 2)
    svg.append(f'<text x="{tz1_center_x}" y="{day_header_y + int(24 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(11 * scale)}" font-weight="700" fill="#64748b" letter-spacing="0.5">{escape(secondary_label)}</text>')
    svg.append(f'<text x="{tz1_center_x}" y="{day_header_y + int(40 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(9.5 * scale)}" font-weight="500" fill="#475569">GMT-8</text>')

    # Sub-column 2 Header (Primary: MDT)
    tz2_center_x = gutter_x + sub_col_w + (sub_col_w // 2)
    svg.append(f'<text x="{tz2_center_x}" y="{day_header_y + int(24 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(11 * scale)}" font-weight="700" fill="#38bdf8" letter-spacing="0.5">{escape(primary_label)}</text>')
    svg.append(f'<text x="{tz2_center_x}" y="{day_header_y + int(40 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(9.5 * scale)}" font-weight="500" fill="#0284c7">GMT-6</text>')

    # Gutter divider lines
    svg.append(f'<line x1="{gutter_x + sub_col_w}" y1="{day_header_y + int(10 * scale)}" x2="{gutter_x + sub_col_w}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.05)" stroke-width="1"/>')
    svg.append(f'<line x1="{gutter_x + gutter_w}" y1="{day_header_y}" x2="{gutter_x + gutter_w}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.2"/>')

    # ================= DAY HEADERS (Google Calendar Style) =================
    for i, day_info in enumerate(days_data):
        col_x = gutter_x + gutter_w + (i * col_w)
        d_obj = day_info["date"]
        is_today = day_info["is_today"]

        day_name = d_obj.strftime("%a").upper()  # SUN, MON...
        day_num = d_obj.strftime("%-d")          # 11, 12...

        center_x = col_x + (col_w // 2)

        # Day Name
        name_color = "#3b82f6" if is_today else "#94a3b8"
        svg.append(f'<text x="{center_x}" y="{day_header_y + int(18 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(12 * scale)}" font-weight="600" fill="{name_color}" letter-spacing="0.5">{escape(day_name)}</text>')

        # Date Number
        num_y = day_header_y + int(40 * scale)
        if is_today:
            circle_r = int(15 * scale)
            svg.append(f'<circle cx="{center_x}" cy="{num_y - int(4 * scale)}" r="{circle_r}" fill="#2563eb"/>')
            svg.append(f'<text x="{center_x}" y="{num_y + int(1 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(14 * scale)}" font-weight="700" fill="#ffffff">{escape(day_num)}</text>')
        else:
            svg.append(f'<text x="{center_x}" y="{num_y + int(1 * scale)}" text-anchor="middle" font-family="{font_family}" font-size="{int(15 * scale)}" font-weight="600" fill="#e2e8f0">{escape(day_num)}</text>')

        # Vertical line separating days
        if i > 0:
            svg.append(f'<line x1="{col_x}" y1="{day_header_y}" x2="{col_x}" y2="{grid_top_y + grid_h}" stroke="rgba(255, 255, 255, 0.08)" stroke-width="1"/>')

    # Horizontal divider under day headers
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

    svg.append('</g>')  # End Card Group
    svg.append('</svg>')

    return "\n".join(svg), card_x, card_y, card_w, card_h
