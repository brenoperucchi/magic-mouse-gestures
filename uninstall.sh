#!/bin/bash
#
# Magic Mouse Gestures - Uninstall Script
#
# Usage: ./uninstall.sh (do NOT run with sudo)
#

set -e

INSTALL_DIR="/opt/magic-mouse-gestures"
USER_SERVICE_DIR="$HOME/.config/systemd/user"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Magic Mouse Gestures Uninstaller"
echo "================================="
echo

# Check NOT running as root
if [[ $EUID -eq 0 ]]; then
    echo -e "${RED}Error: Do not run this script with sudo${NC}"
    echo "Run it as your normal user: ./uninstall.sh"
    exit 1
fi

# Stop and disable the service
echo "Stopping service..."
if systemctl --user is-active --quiet magic-mouse-gestures 2>/dev/null; then
    systemctl --user stop magic-mouse-gestures
    echo -e "${GREEN}✓ Service stopped${NC}"
else
    echo -e "${YELLOW}! Service was not running${NC}"
fi

echo "Disabling service..."
if systemctl --user is-enabled --quiet magic-mouse-gestures 2>/dev/null; then
    systemctl --user disable magic-mouse-gestures
    echo -e "${GREEN}✓ Service disabled${NC}"
else
    echo -e "${YELLOW}! Service was not enabled${NC}"
fi

# Remove user service file
echo "Removing user service file..."
if [[ -f "$USER_SERVICE_DIR/magic-mouse-gestures.service" ]]; then
    rm "$USER_SERVICE_DIR/magic-mouse-gestures.service"
    systemctl --user daemon-reload
    echo -e "${GREEN}✓ User service file removed${NC}"
else
    echo -e "${YELLOW}! User service file not found${NC}"
fi

# Remove driver (requires sudo)
echo "Removing driver (requires sudo)..."
if [[ -d "$INSTALL_DIR" ]]; then
    sudo rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓ Driver removed${NC}"
else
    echo -e "${YELLOW}! Driver directory not found${NC}"
fi

# Remove udev rules
echo "Removing udev rules..."
if [[ -f "/etc/udev/rules.d/99-magic-mouse.rules" ]]; then
    sudo rm /etc/udev/rules.d/99-magic-mouse.rules
    sudo udevadm control --reload-rules
    echo -e "${GREEN}✓ Udev rules removed${NC}"
else
    echo -e "${YELLOW}! Udev rules not found${NC}"
fi

echo
echo "================================="
echo -e "${GREEN}Uninstall complete!${NC}"
echo
echo "Your Magic Mouse will continue to work as a normal mouse."
echo "To reinstall, run: ./install.sh"
echo
