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
echo "Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/magic_mouse_gestures.py" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/magic_mouse_gestures.py"

# Install udev rules
echo "Installing udev rules..."
cp "$SCRIPT_DIR/udev/99-magic-mouse.rules" /etc/udev/rules.d/
udevadm control --reload-rules

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/systemd/magic-mouse-gestures.service" /etc/systemd/system/
systemctl daemon-reload

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "  1. Reconnect your Magic Mouse via Bluetooth"
echo "  2. Enable the service: sudo systemctl enable --now magic-mouse-gestures"
echo "  3. Check status: sudo systemctl status magic-mouse-gestures"
echo
