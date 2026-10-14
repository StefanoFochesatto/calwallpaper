"""
Calendar aggregation and recurrence expansion for calwallpaper.
"""

import os
import hashlib
import datetime
import requests
import icalendar
import recurring_ical_events
from zoneinfo import ZoneInfo

CACHE_DIR = os.path.expanduser("~/.cache/calwallpaper")


def get_local_timezone():
    """Detect canonical local timezone from system."""
    try:
        if os.path.islink("/etc/localtime"):
            target = os.readlink("/etc/localtime")
            parts = target.split("zoneinfo/")
            if len(parts) > 1:
                return ZoneInfo(parts[1])
    except Exception:
        pass

    try:
        tz = datetime.datetime.now().astimezone().tzinfo
        if tz:
            return tz
    except Exception:
        pass

    return ZoneInfo("America/Denver")


LOCAL_TZ = get_local_timezone()


def format_time(dt_obj, is_12h=True):
    """Format time string (e.g. 10:10 AM or 10:10)."""
    if not isinstance(dt_obj, datetime.datetime):
        return "All Day"
    if is_12h:
        # e.g. 10:10 AM, 9:05 AM (strip leading zero from hour)
        return dt_obj.strftime("%-I:%M %p")
    return dt_obj.strftime("%H:%M")


def fetch_calendar_content(cal_entry):
    """Fetch calendar content from URL or local file, with cache fallback."""
    url = cal_entry.get("url", "").strip()
    path = cal_entry.get("path", "").strip()

    if path:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            try:
                with open(expanded_path, "rb") as f:
                    return f.read()
            except Exception as e:
                print(f"[calwallpaper] Error reading local file {path}: {e}")

    if url:
        if url.startswith("webcal://"):
            url = "https://" + url[9:]
        elif url.startswith("webcals://"):
            url = "https://" + url[10:]

        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        cache_file = os.path.join(CACHE_DIR, f"cal_{url_hash}.ics")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; calwallpaper/1.0; Linux)"
            }
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200 and resp.content:
                with open(cache_file, "wb") as f:
                    f.write(resp.content)
                return resp.content
            else:
                print(f"[calwallpaper] HTTP {resp.status_code} fetching {url}")
        except Exception as e:
            print(f"[calwallpaper] Network error fetching {url}: {e}")

        # Fallback to cache
        if os.path.exists(cache_file):
            print(f"[calwallpaper] Using cached calendar for {url}")
            with open(cache_file, "rb") as f:
                return f.read()

    return None


def get_mock_events(start_date, end_date, primary_tz, is_12h=True):
    """Generate sample events if no calendars are configured."""
    sample_items = [
        {"day_offset": 1, "start_h": 10, "start_m": 0, "dur": 60, "title": "Weekly Strategy Sync", "source": "Work", "color": "#38bdf8"},
        {"day_offset": 1, "start_h": 14, "start_m": 30, "dur": 60, "title": "Architecture Review", "source": "Work", "color": "#38bdf8"},
        {"day_offset": 2, "start_h": 10, "start_m": 0, "dur": 90, "title": "Deep Focus: Kernel & UI", "source": "Projects", "color": "#818cf8"},
        {"day_offset": 3, "start_h": 11, "start_m": 0, "dur": 60, "title": "Team Standup & Demos", "source": "Work", "color": "#38bdf8"},
        {"day_offset": 3, "start_h": 19, "start_m": 0, "dur": 90, "title": "Dinner with Friends", "source": "Personal", "color": "#34d399"},
        {"day_offset": 4, "start_h": 13, "start_m": 0, "dur": 60, "title": "Project Milestone Review", "source": "Projects", "color": "#818cf8"},
        {"day_offset": 5, "start_h": 16, "start_m": 0, "dur": 45, "title": "Weekly Retrospective", "source": "Work", "color": "#38bdf8"},
    ]

    events_by_day = {}
    curr = start_date
    while curr <= end_date:
        events_by_day[curr.strftime("%Y-%m-%d")] = []
        curr += datetime.timedelta(days=1)

    for item in sample_items:
        ev_date = start_date + datetime.timedelta(days=item["day_offset"])
        key = ev_date.strftime("%Y-%m-%d")
        if key in events_by_day:
            s_dt = datetime.datetime(ev_date.year, ev_date.month, ev_date.day, item["start_h"], item["start_m"], tzinfo=primary_tz)
            e_dt = s_dt + datetime.timedelta(minutes=item["dur"])
            s_min = item["start_h"] * 60 + item["start_m"]
            e_min = s_min + item["dur"]
            events_by_day[key].append({
                "title": item["title"],
                "start_dt": s_dt,
                "end_dt": e_dt,
                "start_time_str": format_time(s_dt, is_12h),
                "end_time_str": format_time(e_dt, is_12h),
                "start_minutes": s_min,
                "end_minutes": e_min,
                "duration_minutes": item["dur"],
                "all_day": False,
                "source": item["source"],
                "color": item["color"],
                "is_sample": True,
            })

    return events_by_day, True


def aggregate_calendars(config, start_date, end_date):
    """
    Fetch and aggregate events from all enabled calendars for [start_date, end_date].
    Returns dict mapping 'YYYY-MM-DD' to list of event dicts.
    """
    layout = config.get("layout", {})
    is_12h = layout.get("time_format", "12h").lower() == "12h"

    tz_cfg = config.get("timezones", {})
    primary_tz_name = tz_cfg.get("primary", "America/Denver")
    try:
        primary_tz = ZoneInfo(primary_tz_name)
    except Exception:
        primary_tz = LOCAL_TZ

    calendars = config.get("calendars", [])
    events_by_day = {}

    curr = start_date
    while curr <= end_date:
        events_by_day[curr.strftime("%Y-%m-%d")] = []
        curr += datetime.timedelta(days=1)

    has_active_cal = False

    for cal in calendars:
        if not cal.get("enabled", True):
            continue
        url = cal.get("url", "").strip()
        path = cal.get("path", "").strip()
        if not url and not path:
            continue

        raw_data = fetch_calendar_content(cal)
        if not raw_data:
            continue

        has_active_cal = True
        try:
            ical = icalendar.Calendar.from_ical(raw_data)
            # Expand recurring events
            expanded = recurring_ical_events.of(ical).between(start_date, end_date + datetime.timedelta(days=1))

            for ev in expanded:
                summary = str(ev.get("SUMMARY", "Event"))
                dtstart = ev.get("DTSTART")
                if not dtstart:
                    continue

                val_start = dtstart.dt
                dtend = ev.get("DTEND")
                val_end = dtend.dt if dtend else None

                all_day = False
                ev_date = None
                s_min = 0
                e_min = 0
                dur = 60
                s_dt = None
                e_dt = None

                if isinstance(val_start, datetime.datetime):
                    # Localize to primary timezone
                    if val_start.tzinfo is not None:
                        s_dt = val_start.astimezone(primary_tz)
                    else:
                        s_dt = val_start.replace(tzinfo=primary_tz)

                    ev_date = s_dt.date()
                    s_min = s_dt.hour * 60 + s_dt.minute

                    if isinstance(val_end, datetime.datetime):
                        if val_end.tzinfo is not None:
                            e_dt = val_end.astimezone(primary_tz)
                        else:
                            e_dt = val_end.replace(tzinfo=primary_tz)
                        dur = max(15, int((e_dt - s_dt).total_seconds() / 60))
                        e_min = s_min + dur
                    else:
                        e_dt = s_dt + datetime.timedelta(hours=1)
                        dur = 60
                        e_min = s_min + 60

                elif isinstance(val_start, datetime.date):
                    ev_date = val_start
                    all_day = True
                    s_min = 0
                    e_min = 1440
                    dur = 1440

                if ev_date:
                    date_key = ev_date.strftime("%Y-%m-%d")
                    if date_key in events_by_day:
                        events_by_day[date_key].append({
                            "title": summary,
                            "start_dt": s_dt,
                            "end_dt": e_dt,
                            "start_time_str": format_time(s_dt, is_12h) if not all_day else "All Day",
                            "end_time_str": format_time(e_dt, is_12h) if not all_day else "",
                            "start_minutes": s_min,
                            "end_minutes": e_min,
                            "duration_minutes": dur,
                            "all_day": all_day,
                            "source": cal.get("name", "Calendar"),
                            "color": cal.get("color", "#38bdf8"),
                            "is_sample": False,
                        })
        except Exception as e:
            print(f"[calwallpaper] Error parsing calendar '{cal.get('name')}': {e}")

    if not has_active_cal:
        return get_mock_events(start_date, end_date, primary_tz, is_12h)

    # Sort each day's events: all_day first, then by start_minutes
    for date_key in events_by_day:
        events_by_day[date_key].sort(key=lambda x: (not x["all_day"], x["start_minutes"]))

    return events_by_day, False
