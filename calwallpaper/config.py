"""
Configuration management for calwallpaper.
"""

import os
import re
import yaml
import subprocess

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/calwallpaper/config.yaml")
CACHE_DIR = os.path.expanduser("~/.cache/calwallpaper")
ORIGINAL_WP_FILE = os.path.join(CACHE_DIR, "original_wallpaper.txt")

DEFAULT_CONFIG = {
    "wallpaper": {
        "source": "auto",  # 'auto' to detect KDE wallpaper, or absolute path
        "blur_radius": 32,
        "card_tint": "#080c14",
        "card_opacity": 0.82,
        "border_color": "rgba(255, 255, 255, 0.14)",
    },
    "layout": {
        "position": "center",   # 'center', 'bottom', 'top'
        "width_percent": 92,     # Width as % of screen width
        "height_percent": 78,    # Height as % of screen height
        "view": "top_magnified", # "top_magnified", "week", or "month"
        "start_day": "sunday",   # Always start on Sunday
        "days_count": 7,         # 7 days (Sun - Sat)
        "time_format": "12h",    # '12h' (AM/PM) or '24h'
    },
    "timezones": {
        "primary": "America/Denver",
        "primary_label": "MDT",
        "secondary": "America/Anchorage",
        "secondary_label": "AKDT",
    },
    "grid_hours": {
        "start": 7,   # 7 AM
        "end": 21,    # 9 PM
    },
    "calendars": [
        {
            "name": "CU Boulder Things",
            "color": "#cfb87c",  # CU Boulder Gold
            "url": "",
            "enabled": True,
        },
        {
            "name": "Alaska (.edu)",
            "color": "#38bdf8",  # Alaska Sky Blue
            "url": "",
            "enabled": True,
        },
    ],
}


def is_calwallpaper_output(path):
    """Check if the path is a generated calwallpaper image."""
    if not path:
        return False
    norm = os.path.normpath(str(path))
    return "calwallpaper" in norm and ("wallpaper" in norm or ".png" in norm)


def save_original_wallpaper(path):
    """Save the path to the original un-composited wallpaper."""
    if path and not is_calwallpaper_output(path):
        os.makedirs(CACHE_DIR, exist_ok=True)
        clean = path.strip()
        if clean.startswith("file://"):
            clean = clean[7:]
        if os.path.exists(clean):
            with open(ORIGINAL_WP_FILE, "w", encoding="utf-8") as f:
                f.write(clean)


def get_saved_original_wallpaper():
    """Retrieve saved original wallpaper path if valid."""
    if os.path.exists(ORIGINAL_WP_FILE):
        try:
            with open(ORIGINAL_WP_FILE, "r", encoding="utf-8") as f:
                path = f.read().strip()
                if os.path.exists(path) and not is_calwallpaper_output(path):
                    return path
        except Exception:
            pass
    return None


def get_current_plasma_wallpaper():
    """Detect active wallpaper path directly from KDE Plasma DBus / containments."""
    # 1. Ask active Plasma desktop via DBus
    try:
        cmd = [
            "qdbus6",
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
            'var d = desktops(); if (d.length > 0) { d[0].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"]; print(d[0].readConfig("Image")); }'
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            img = res.stdout.strip()
            if img.startswith("file://"):
                img = img[7:]
            if os.path.exists(img) and not is_calwallpaper_output(img):
                save_original_wallpaper(img)
                return img
    except Exception:
        pass

    # 2. Check saved original wallpaper
    saved = get_saved_original_wallpaper()
    if saved:
        return saved

    # 3. Read desktop-appletsrc actively for active containments (e.g. 43, 85)
    config_path = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            matches = re.findall(r"\[Containments\]\[(43|85)\]\[Wallpaper\].*?\nImage\s*=\s*(.+)", content, re.IGNORECASE)
            for cid, raw_img in matches:
                img = raw_img.strip()
                if img.startswith("file://"):
                    img = img[7:]
                if os.path.exists(img) and not is_calwallpaper_output(img):
                    save_original_wallpaper(img)
                    return img
        except Exception:
            pass

    # 4. Default CachyOS wallpapers
    for candidate in [
        "/usr/share/wallpapers/cachyos-wallpapers/Liquid.png",
        "/usr/share/wallpapers/cachyos-wallpapers/north.png",
        "/usr/share/wallpapers/cachyos-wallpapers/Dimensions.png",
    ]:
        if os.path.exists(candidate):
            save_original_wallpaper(candidate)
            return candidate

    return None


def load_config():
    """Load user configuration or generate default if missing."""
    os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    if not os.path.exists(DEFAULT_CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}

        config = DEFAULT_CONFIG.copy()
        if "wallpaper" in user_config:
            config["wallpaper"].update(user_config["wallpaper"])
        if "layout" in user_config:
            config["layout"].update(user_config["layout"])
        if "timezones" in user_config:
            config["timezones"].update(user_config["timezones"])
        if "grid_hours" in user_config:
            config["grid_hours"].update(user_config["grid_hours"])
        if "calendars" in user_config:
            config["calendars"] = user_config["calendars"]
        return config
    except Exception as e:
        print(f"[calwallpaper] Error reading config: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
