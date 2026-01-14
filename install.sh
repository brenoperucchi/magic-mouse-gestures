#!/bin/bash
#
# Magic Mouse Gestures - Installation Script
#

set -e

INSTALL_DIR="/opt/magic-mouse-gestures"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Magic Mouse Gestures Installer"
echo "=============================="
echo

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo "~$ACTUAL_USER")

# Check dependencies
echo "Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required"
    exit 1
fi

if ! command -v wtype &> /dev/null; then
    echo "Error: wtype is required (for Wayland key simulation)"
    exit 1
fi

echo "Dependencies OK"
echo

# Install files
echo "Installing driver to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/magic_mouse_gestures.py" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/magic_mouse_gestures.py"

# Install udev rules
echo "Installing udev rules..."
cp "$SCRIPT_DIR/udev/99-magic-mouse.rules" /etc/udev/rules.d/
udevadm control --reload-rules

# Install systemd user service
echo "Installing systemd user service for $ACTUAL_USER..."
USER_SERVICE_DIR="$ACTUAL_HOME/.config/systemd/user"
mkdir -p "$USER_SERVICE_DIR"
cp "$SCRIPT_DIR/systemd/magic-mouse-gestures.service" "$USER_SERVICE_DIR/"
chown -R "$ACTUAL_USER:$ACTUAL_USER" "$USER_SERVICE_DIR"

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "  1. Reconnect your Magic Mouse via Bluetooth"
echo "  2. Enable the service (run as your user, not root):"
echo "     systemctl --user daemon-reload"
echo "     systemctl --user enable --now magic-mouse-gestures"
echo "  3. Check status:"
echo "     systemctl --user status magic-mouse-gestures"
echo
