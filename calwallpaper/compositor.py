"""
Compositor: blurs wallpaper under the card, rasterizes SVG, and blends them into the final wallpaper.
Alternates between output slots to force KDE Plasma texture cache invalidation.
"""

import os
import io
import datetime
import cairosvg
from PIL import Image, ImageFilter, ImageDraw

from .config import load_config, get_current_plasma_wallpaper, CACHE_DIR
from .fetcher import aggregate_calendars
from .designer import generate_weekly_svg

SLOT_FILE = os.path.join(CACHE_DIR, "current_slot.txt")


def get_next_output_path():
    """Alternate between wallpaper_a.png and wallpaper_b.png to bypass KDE image caching."""
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
    """Compute start and end date based on layout configuration."""
    layout = config.get("layout", {})
    start_mode = layout.get("start_day", "sunday").lower()
    days_count = layout.get("days_count", 7)

    today = datetime.date.today()

    if start_mode == "sunday":
        # Python weekday(): Mon=0 ... Sun=6
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
    2. Fetches calendar events
    3. Builds SVG & renders to PNG
    4. Applies frosted-glass blur behind card
    5. Composites and saves output
    """
    if config is None:
        config = load_config()

    base_img, source_path = load_base_image(config)
    canvas_w, canvas_h = base_img.size

    start_date, end_date, today = compute_date_range(config)

    # 1. Fetch & parse events
    events_by_day, is_sample = aggregate_calendars(config, start_date, end_date)

    # 2. Prepare day info objects
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

    # 3. Generate SVG
    svg_str, card_x, card_y, card_w, card_h = generate_weekly_svg(
        canvas_w, canvas_h, config, days_data, is_sample_data=is_sample
    )

    # 4. Rasterize SVG using cairosvg
    png_bytes = cairosvg.svg2png(
        bytestring=svg_str.encode("utf-8"),
        parent_width=canvas_w,
        parent_height=canvas_h,
        output_width=canvas_w,
        output_height=canvas_h,
    )
    svg_layer = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # 5. Frosted glass effect: blur wallpaper region behind the card
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

    # 6. Composite the rendered SVG layer over the base
    final_img = Image.alpha_composite(base_img, svg_layer)

    # 7. Convert to RGB and save to next alternating slot
    os.makedirs(CACHE_DIR, exist_ok=True)
    out_path = get_next_output_path()
    rgb_output = final_img.convert("RGB")
    rgb_output.save(out_path, "PNG", optimize=False)
    print(f"[calwallpaper] Generated wallpaper saved to: {out_path}")

    return out_path
