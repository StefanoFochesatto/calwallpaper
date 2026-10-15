"""
Compositor: blurs wallpaper under the card, rasterizes SVG, and blends them into the final wallpaper.
Supports:
1. Top-Magnified View: Original weekly time blocks layout on top row with dual timezones,
   with squeezed lookahead preview weeks directly below.
2. Weekly View: Google Calendar-style time grid with dual timezone gutter.
3. Monthly View: Standalone full month grid with daily event cards.
"""

import os
import io
import glob
import datetime
import calendar
import cairosvg
from PIL import Image, ImageFilter, ImageDraw

from .config import load_config, get_current_plasma_wallpaper, CACHE_DIR
from .fetcher import aggregate_calendars
from .designer import generate_weekly_svg, generate_monthly_svg, generate_top_magnified_svg

SLOT_FILE = os.path.join(CACHE_DIR, "current_slot.txt")


def cleanup_old_cache_images():
    """Ensure no stale or orphaned images accumulate in the cache directory."""
    allowed = {"wallpaper_a.png", "wallpaper_b.png"}
    for img_path in glob.glob(os.path.join(CACHE_DIR, "*.png")):
        base = os.path.basename(img_path)
        if base not in allowed:
            try:
                os.remove(img_path)
            except Exception:
                pass


def get_next_output_path():
    """Alternate strictly between wallpaper_a.png and wallpaper_b.png."""
    cleanup_old_cache_images()

    slot = "a"
    if os.path.exists(SLOT_FILE):
        try:
            with open(SLOT_FILE, "r") as f:
                last_slot = f.read().strip()
                slot = "b" if last_slot == "a" else "a"
        except Exception:
            slot = "a"

    with open(SLOT_FILE, "w") as f:
        f.write(slot)

    return os.path.join(CACHE_DIR, f"wallpaper_{slot}.png")


def compute_date_range(config):
    """Compute start and end date based on layout configuration (weekly)."""
    layout = config.get("layout", {})
    start_mode = layout.get("start_day", "sunday").lower()
    days_count = layout.get("days_count", 7)

    today = datetime.date.today()

    if start_mode == "sunday":
        idx = (today.weekday() + 1) % 7
        start_date = today - datetime.timedelta(days=idx)
    elif start_mode == "monday":
        start_date = today - datetime.timedelta(days=today.weekday())
    else:  # "today"
        start_date = today

    end_date = start_date + datetime.timedelta(days=days_count - 1)
    return start_date, end_date, today


def create_fallback_wallpaper(width=3840, height=2400):
    """Generate a sleek, dark modern gradient background if no wallpaper is found."""
    img = Image.new("RGB", (width, height), "#080c14")
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / float(height)
        r = int(12 * (1 - ratio) + 6 * ratio)
        g = int(16 * (1 - ratio) + 10 * ratio)
        b = int(28 * (1 - ratio) + 18 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def load_base_image(config):
    """Load user's wallpaper or detect it automatically."""
    wp_cfg = config.get("wallpaper", {})
    source = wp_cfg.get("source", "auto")

    base_path = None
    if source != "auto" and os.path.exists(os.path.expanduser(source)):
        base_path = os.path.expanduser(source)
    else:
        detected = get_current_plasma_wallpaper()
        if detected and os.path.exists(detected):
            base_path = detected

    if base_path:
        try:
            print(f"[calwallpaper] Loading base wallpaper: {base_path}")
            return Image.open(base_path).convert("RGBA"), base_path
        except Exception as e:
            print(f"[calwallpaper] Error loading {base_path}: {e}")

    print("[calwallpaper] No base wallpaper found. Using modern dark canvas.")
    return create_fallback_wallpaper().convert("RGBA"), "fallback"


def render_composite(config=None):
    """
    Main pipeline:
    1. Loads base wallpaper
    2. Determines view mode (top_magnified vs week vs month)
    3. Fetches calendar events for view range
    4. Builds SVG & renders to PNG
    5. Applies frosted-glass blur behind card
    6. Composites and saves output to next alternating slot
    """
    if config is None:
        config = load_config()

    base_img, source_path = load_base_image(config)
    canvas_w, canvas_h = base_img.size

    layout = config.get("layout", {})
    view_mode = layout.get("view", "top_magnified").lower()

    if view_mode in ("top_magnified", "magnified", "focus", "fisheye"):
        today = datetime.date.today()
        start_mode = layout.get("start_day", "sunday").lower()

        # Sunday of current week (or Monday if configured)
        if start_mode == "monday":
            start_curr_week = today - datetime.timedelta(days=today.weekday())
        else:  # Sunday
            idx = (today.weekday() + 1) % 7
            start_curr_week = today - datetime.timedelta(days=idx)

        active_week_days = [start_curr_week + datetime.timedelta(days=d) for d in range(7)]

        # 2 upcoming preview weeks below: Week +1 and Week +2
        preview_weeks = []
        for offset in [1, 2]:
            w_start = start_curr_week + datetime.timedelta(weeks=offset)
            w_days = [w_start + datetime.timedelta(days=d) for d in range(7)]
            preview_weeks.append(w_days)

        start_date = active_week_days[0]
        end_date = preview_weeks[-1][-1]

        events_by_day, is_sample = aggregate_calendars(config, start_date, end_date)

        svg_str, card_x, card_y, card_w, card_h = generate_top_magnified_svg(
            canvas_w, canvas_h, config, active_week_days, preview_weeks, events_by_day, is_sample_data=is_sample
        )

    elif view_mode == "month":
        today = datetime.date.today()
        start_mode = layout.get("start_day", "sunday").lower()
        first_weekday = 6 if start_mode == "sunday" else 0
        cal = calendar.Calendar(firstweekday=first_weekday)
        month_weeks = cal.monthdatescalendar(today.year, today.month)
        start_date = month_weeks[0][0]
        end_date = month_weeks[-1][-1]

        events_by_day, is_sample = aggregate_calendars(config, start_date, end_date)

        svg_str, card_x, card_y, card_w, card_h = generate_monthly_svg(
            canvas_w, canvas_h, config, month_weeks, events_by_day, is_sample_data=is_sample
        )
    else:  # "week"
        start_date, end_date, today = compute_date_range(config)
        events_by_day, is_sample = aggregate_calendars(config, start_date, end_date)

        days_data = []
        curr = start_date
        while curr <= end_date:
            key = curr.strftime("%Y-%m-%d")
            days_data.append({
                "date": curr,
                "date_str": key,
                "is_today": (curr == today),
                "events": events_by_day.get(key, [])
            })
            curr += datetime.timedelta(days=1)

        svg_str, card_x, card_y, card_w, card_h = generate_weekly_svg(
            canvas_w, canvas_h, config, days_data, is_sample_data=is_sample
        )

    # Rasterize SVG using cairosvg
    png_bytes = cairosvg.svg2png(
        bytestring=svg_str.encode("utf-8"),
        parent_width=canvas_w,
        parent_height=canvas_h,
        output_width=canvas_w,
        output_height=canvas_h,
    )
    svg_layer = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # Frosted glass blur behind card
    blur_radius = config.get("wallpaper", {}).get("blur_radius", 32)
    if blur_radius > 0:
        scaled_radius = int(blur_radius * (canvas_w / 1920.0))
        scaled_radius = max(8, min(scaled_radius, 60))

        pad = scaled_radius * 2
        crop_x1 = max(0, card_x - pad)
        crop_y1 = max(0, card_y - pad)
        crop_x2 = min(canvas_w, card_x + card_w + pad)
        crop_y2 = min(canvas_h, card_y + card_h + pad)

        cropped = base_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        blurred_crop = cropped.filter(ImageFilter.GaussianBlur(radius=scaled_radius))

        inner_x1 = card_x - crop_x1
        inner_y1 = card_y - crop_y1
        card_blur = blurred_crop.crop((inner_x1, inner_y1, inner_x1 + card_w, inner_y1 + card_h))

        scale = canvas_w / 1920.0
        rx = int(22 * scale)
        mask = Image.new("L", (card_w, card_h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), (card_w, card_h)], radius=rx, fill=255)

        base_img.paste(card_blur, (card_x, card_y), mask=mask)

    final_img = Image.alpha_composite(base_img, svg_layer)

    os.makedirs(CACHE_DIR, exist_ok=True)
    out_path = get_next_output_path()
    rgb_output = final_img.convert("RGB")
    rgb_output.save(out_path, "PNG", optimize=False)
    print(f"[calwallpaper] Generated wallpaper saved to: {out_path}")

    return out_path
