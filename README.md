# calwallpaper 🗓️🖼️

> **Dynamic Live Weekly Calendar Wallpaper for Linux (KDE Plasma 6 / Wayland)**

`calwallpaper` dynamically composites an aesthetic, Google Calendar-style weekly schedule with a frosted-glass card overlay directly onto your active desktop wallpaper. It aggregates multiple calendar sources (Google Calendar, Outlook, Apple iCloud, Nextcloud, and local `.ics` files), updates seamlessly in the background, and synchronizes across all virtual desktops and monitors.

---

## ✨ Features

- **Google Calendar-Style Weekly Grid:**
  - 7-day schedule with proportional hourly event blocks positioned by start time and duration.
  - Overlap resolver that tiles simultaneous meetings into sub-columns.
  - Signature Google red **"Now" indicator** (line and circle showing current time).
  - Classic blue date badge for the active day.
- **Dual Timezone Columns:**
  - Displays two timezones side-by-side in the left time gutter (e.g., `AKDT` and `MDT`) aligned with the hour grid.
- **12-Hour AM/PM Support:**
  - Clear 12-hour format for event intervals (`10:10 AM – 11:10 AM`), hour ticks (`8 AM`, `12 PM`), and header clock.
- **Sunday-to-Saturday Week Layout:**
  - Configurable to always start on Sunday, Monday, or today.
- **True Frosted Glass (Glassmorphism):**
  - Applies a Gaussian blur on the exact region of the base wallpaper behind the card, blending dark translucency with sharp vector typography.
- **Multi-Source Calendar Aggregation:**
  - Connect any number of feeds: public/private Google Calendars, Microsoft 365, iCloud, Nextcloud, and local `.ics` files.
  - Each source has its own custom label and accent color.
  - Offline cache fallback so network drops never break your wallpaper.
- **KDE Plasma 6 & Multi-Monitor Sync:**
  - Directly drives Plasma's DBus scripting engine (`org.kde.PlasmaShell`) to update all screens, virtual desktops, and containments simultaneously.
  - Uses cache-busting alternating slots to force immediate GPU texture reloading.
- **Native PyQt6 Graphical Settings UI:**
  - Adjust translucency, blur, margins, colors, timezones, and calendar feeds with a friendly GUI.
  - Integrated into the KDE Application Launcher / KRunner.
- **Zero-Resource Idle:**
  - Runs periodically via a `systemd` user timer (default: every 15 min), consuming 0% idle CPU and RAM.

---

## 🚀 Installation

### Prerequisites (Arch / CachyOS)
```bash
sudo pacman -S python python-pillow python-cairo python-pyqt6
```

### Install from Repository
```bash
git clone https://github.com/StefanoFochesatto/calwallpaper.git ~/calwallpaper
cd ~/calwallpaper
./install.sh
```

The installer:
1. Copies modules to `~/.local/share/calwallpaper/`.
2. Creates an isolated virtual environment with dependencies (`cairosvg`, `icalendar`, `recurring-ical-events`, `pyyaml`, `requests`).
3. Installs `calwallpaper` and `calwallpaper-settings` to `~/.local/bin/`.
4. Adds the desktop shortcut to your application menu.
5. Enables the `systemd` user timer for auto-updates.

---

## 🖥️ Graphical Settings UI

Launch the settings window from your application menu (search **"Calendar Wallpaper Settings"**) or run:

```bash
calwallpaper ui
# or
calwallpaper-settings
```

From the GUI you can:
- Adjust card **translucency** and **blur intensity** with live sliders.
- Fine-tune screen margins and card sizing.
- Add or remove calendar feeds and pick accent colors with a color palette.
- Change primary and secondary timezones.
- Click **"Apply & Update Wallpaper"** to see changes immediately.

---

## ⚙️ Configuration File

Configuration is stored in `~/.config/calwallpaper/config.yaml`:

```yaml
wallpaper:
  source: auto                 # 'auto' detects active KDE wallpaper, or set custom path
  blur_radius: 32              # Frosted glass blur intensity
  card_tint: '#080c14'         # Glass tint color
  card_opacity: 0.62           # Card opacity (0.20 to 1.0)
  border_color: rgba(255, 255, 255, 0.16)

layout:
  position: center             # 'center', 'top', or 'bottom'
  width_percent: 82            # Card width as % of screen width
  height_percent: 74           # Card height as % of screen height
  start_day: sunday            # 'sunday', 'monday', or 'today'
  days_count: 7                # 7 days (Sun - Sat)
  time_format: 12h             # '12h' (AM/PM) or '24h'

timezones:
  primary: America/Denver      # Right column in gutter
  primary_label: MDT
  secondary: America/Anchorage # Left column in gutter
  secondary_label: AKDT

grid_hours:
  start: 7                     # 7 AM
  end: 21                      # 9 PM

calendars:
  - name: CU Boulder Things
    color: '#cfb87c'           # CU Gold
    url: 'https://calendar.google.com/calendar/ical/.../public/basic.ics'
    enabled: true

  - name: Alaska (.edu)
    color: '#38bdf8'           # Sky Blue
    url: 'https://calendar.google.com/calendar/ical/.../public/basic.ics'
    enabled: true
```

---

## 💻 CLI Commands

```bash
# Update wallpaper immediately
calwallpaper run

# Open graphical settings window
calwallpaper ui

# Generate a preview image without setting wallpaper
calwallpaper preview

# View or edit configuration file
calwallpaper config
calwallpaper config --edit

# Check background timer status and logs
calwallpaper status

# Change auto-sync interval (e.g., every 30 minutes)
calwallpaper install-service --interval 30min

# Disable background service
calwallpaper uninstall-service
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
