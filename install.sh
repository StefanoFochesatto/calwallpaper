#!/usr/bin/env bash
set -e

echo "=== Installing calwallpaper ==="

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/calwallpaper"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"
SYSTEMD_DIR="$HOME/.config/systemd/user"
CONFIG_DIR="$HOME/.config/calwallpaper"

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APPS_DIR" "$SYSTEMD_DIR" "$CONFIG_DIR"

# 1. Copy source files
echo "Copying package files to $INSTALL_DIR..."
cp -r "$REPO_DIR"/calwallpaper/* "$INSTALL_DIR/"

# 2. Setup Virtual Environment if not present
VENV_DIR="$INSTALL_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv --system-site-packages "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"
fi

# 3. Install CLI binaries
echo "Installing binaries to $BIN_DIR..."
cp "$REPO_DIR/bin/calwallpaper" "$BIN_DIR/"
cp "$REPO_DIR/bin/calwallpaper-settings" "$BIN_DIR/"
chmod +x "$BIN_DIR/calwallpaper" "$BIN_DIR/calwallpaper-settings"

# 4. Install Desktop Entry
echo "Installing desktop entry to $APPS_DIR..."
cp "$REPO_DIR/assets/calwallpaper-settings.desktop" "$APPS_DIR/"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

# 5. Initialize config if missing
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    echo "Creating default configuration at $CONFIG_DIR/config.yaml..."
    cp "$REPO_DIR/config.example.yaml" "$CONFIG_DIR/config.yaml"
fi

# 6. Install systemd timer
echo "Setting up background sync timer (systemd)..."
"$BIN_DIR/calwallpaper" install-service --interval 15min

echo ""
echo "✓ Installation complete!"
echo "  Run 'calwallpaper ui' or open 'Calendar Wallpaper Settings' from your application menu."
echo "  Run 'calwallpaper run' anytime to update your wallpaper."
