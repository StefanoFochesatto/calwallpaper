"""
CLI interface and systemd service management for calwallpaper.
"""

import os
import sys
import argparse
import subprocess
import shutil

from .config import DEFAULT_CONFIG_PATH, load_config
from .compositor import render_composite

SERVICE_DIR = os.path.expanduser("~/.config/systemd/user")
SERVICE_FILE = os.path.join(SERVICE_DIR, "calwallpaper.service")
TIMER_FILE = os.path.join(SERVICE_DIR, "calwallpaper.timer")
BIN_PATH = os.path.expanduser("~/.local/bin/calwallpaper")


def apply_wallpaper_plasma(image_path):
    """
    Apply wallpaper synchronously to ALL virtual desktops, screens, and containments in KDE Plasma 6.
    """
    abs_path = os.path.abspath(image_path)
    file_uri = "file://" + abs_path
    success = False

    dbus_script = f"""
    var allDesktops = desktops();
    for (var i = 0; i < allDesktops.length; i++) {{
        var d = allDesktops[i];
        d.wallpaperPlugin = "org.kde.image";
        d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
        d.writeConfig("Image", "{file_uri}");
    }}
    print("Updated " + allDesktops.length + " desktops");
    """
    try:
        cmd = [
            "qdbus6",
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
            dbus_script
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        if res.returncode == 0:
            print(f"[calwallpaper] Synced wallpaper across all KDE desktops via DBus: {res.stdout.strip()}")
            success = True
    except Exception as e:
        print(f"[calwallpaper] Note on DBus apply: {e}")

    try:
        cmd2 = ["plasma-apply-wallpaperimage", abs_path]
        subprocess.run(cmd2, capture_output=True, text=True, check=True)
        print("[calwallpaper] Verified via plasma-apply-wallpaperimage.")
        success = True
    except Exception:
        pass

    return success


def cmd_run(args):
    """Render calendar wallpaper and apply it to desktop."""
    print("[calwallpaper] Fetching calendars and rendering weekly wallpaper...")
    out_path = render_composite()
    if not args.no_apply:
        apply_wallpaper_plasma(out_path)


def cmd_preview(args):
    """Generate wallpaper without applying it."""
    print("[calwallpaper] Generating preview wallpaper...")
    out_path = render_composite()
    print(f"[calwallpaper] Preview ready at: {out_path}")
    if shutil.which("xdg-open") and not args.quiet:
        subprocess.Popen(["xdg-open", out_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cmd_config(args):
    """Show or open configuration file."""
    load_config()
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "nano"
    if args.edit:
        if shutil.which(editor):
            subprocess.run([editor, DEFAULT_CONFIG_PATH])
        else:
            subprocess.run(["xdg-open", DEFAULT_CONFIG_PATH])
    else:
        print(f"Config file path: {DEFAULT_CONFIG_PATH}")
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            print("-" * 50)
            print(f.read().strip())
            print("-" * 50)
        print("Tip: Run 'calwallpaper config --edit' to edit in your default editor.")
        print("Or run 'calwallpaper ui' to open the graphical Settings app.")


def cmd_ui(args):
    """Launch the graphical PyQt6 settings window."""
    try:
        from .gui import launch_gui
        launch_gui()
    except Exception as e:
        print(f"Error launching Settings GUI: {e}")
        sys.exit(1)


def cmd_install_service(args):
    """Install and enable systemd user service and timer."""
    os.makedirs(SERVICE_DIR, exist_ok=True)
    interval = args.interval or "15min"

    service_content = f"""[Unit]
Description=Dynamic Weekly Calendar Wallpaper Updater
After=graphical-session.target

[Service]
Type=oneshot
ExecStart={BIN_PATH} run
Environment=PATH={os.environ.get('PATH', '/usr/bin')}
Environment=DISPLAY={os.environ.get('DISPLAY', ':0')}
Environment=WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', 'wayland-0')}
Environment=XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')}

[Install]
WantedBy=graphical-session.target
"""

    timer_content = f"""[Unit]
Description=Dynamic Weekly Calendar Wallpaper Timer
PartOf=calwallpaper.service

[Timer]
OnBootSec=1min
OnUnitActiveSec={interval}
Persistent=true

[Install]
WantedBy=timers.target
"""

    with open(SERVICE_FILE, "w") as f:
        f.write(service_content)

    with open(TIMER_FILE, "w") as f:
        f.write(timer_content)

    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "--user", "enable", "--now", "calwallpaper.timer"], check=True)
        print(f"✓ Systemd timer installed and enabled (runs every {interval}).")
        print("  Check status anytime with: calwallpaper status")
    except Exception as e:
        print(f"Error enabling systemd timer: {e}")


def cmd_uninstall_service(args):
    """Disable and remove systemd user timer."""
    try:
        subprocess.run(["systemctl", "--user", "disable", "--now", "calwallpaper.timer"], check=False)
        if os.path.exists(TIMER_FILE):
            os.remove(TIMER_FILE)
        if os.path.exists(SERVICE_FILE):
            os.remove(SERVICE_FILE)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        print("✓ Systemd service and timer disabled and removed.")
    except Exception as e:
        print(f"Error removing systemd service: {e}")


def cmd_status(args):
    """Check status of systemd timer and recent runs."""
    try:
        subprocess.run(["systemctl", "--user", "status", "calwallpaper.timer"])
        print("\nLast execution log:")
        subprocess.run(["journalctl", "--user", "-u", "calwallpaper.service", "-n", "10", "--no-pager"])
    except Exception as e:
        print(f"Error checking status: {e}")


def main():
    parser = argparse.ArgumentParser(description="Dynamic Calendar Wallpaper for KDE Plasma & Linux")
    subparsers = parser.add_subparsers(dest="command")

    # run / update
    run_parser = subparsers.add_parser("run", aliases=["update"], help="Fetch calendars, render, and apply wallpaper")
    run_parser.add_argument("--no-apply", action="store_true", help="Do not apply to desktop, only render")
    run_parser.set_defaults(func=cmd_run)

    # ui / gui / settings
    ui_parser = subparsers.add_parser("ui", aliases=["gui", "settings"], help="Open graphical settings window")
    ui_parser.set_defaults(func=cmd_ui)

    # preview
    prev_parser = subparsers.add_parser("preview", help="Render and open preview")
    prev_parser.add_argument("-q", "--quiet", action="store_true", help="Do not open image viewer")
    prev_parser.set_defaults(func=cmd_preview)

    # config
    cfg_parser = subparsers.add_parser("config", help="View or edit configuration")
    cfg_parser.add_argument("-e", "--edit", action="store_true", help="Open in default editor")
    cfg_parser.set_defaults(func=cmd_config)

    # install-service
    inst_parser = subparsers.add_parser("install-service", help="Install and start systemd background timer")
    inst_parser.add_argument("--interval", default="15min", help="Update interval (e.g. 15min, 30min, 1h)")
    inst_parser.set_defaults(func=cmd_install_service)

    # uninstall-service
    uninst_parser = subparsers.add_parser("uninstall-service", help="Disable and remove background timer")
    uninst_parser.set_defaults(func=cmd_uninstall_service)

    # status
    status_parser = subparsers.add_parser("status", help="Check systemd timer status")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        cmd_run(argparse.Namespace(no_apply=False))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
