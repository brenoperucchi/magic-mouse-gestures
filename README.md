# Magic Mouse Gestures for Linux

Enable macOS-style swipe gestures on Apple Magic Mouse 2 for Linux/Wayland.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Wayland-lightgrey.svg)

## Features

- **Horizontal swipe gestures** for browser back/forward navigation
- Works with **Wayland** compositors (Hyprland, Sway, GNOME, etc.)
- Lightweight Python daemon with minimal dependencies
- Automatic device detection via HID raw interface

## How It Works

The Magic Mouse 2 has a touch-sensitive surface, but Linux only exposes basic mouse functionality by default. This driver reads raw HID data directly from the device to detect touch positions and translate horizontal swipes into keyboard shortcuts.

| Gesture | Action |
|---------|--------|
| Swipe → (right) | Browser back (Alt+Left) |
| Swipe ← (left) | Browser forward (Alt+Right) |

## Requirements

- Linux with kernel 5.15+ (built-in Magic Mouse 2 support)
- Wayland compositor
- Python 3.8+
- `wtype` (for sending keystrokes on Wayland)

## Installation

### Quick Install (Recommended)

```bash
git clone https://github.com/brenoperucchi/magic-mouse-gestures.git
cd magic-mouse-gestures
./install.sh
```

The installer will:
- Check and install dependencies
- Install the driver and udev rules (asks for sudo password)
- Automatically reconnect your Magic Mouse to apply permissions
- Enable and start the systemd service
- Verify everything is working

**Note:** Do NOT run with `sudo`. The script will request sudo only when needed.

### Manual Installation

If you prefer to install manually:

#### 1. Install dependencies

**Arch Linux:**
```bash
sudo pacman -S python wtype bluez-utils
```

**Debian/Ubuntu:**
```bash
sudo apt install python3 wtype bluez
```

**Fedora:**
```bash
sudo dnf install python3 wtype bluez
```

#### 2. Clone and install

```bash
git clone https://github.com/brenoperucchi/magic-mouse-gestures.git
cd magic-mouse-gestures

# Install driver
sudo mkdir -p /opt/magic-mouse-gestures
sudo cp magic_mouse_gestures.py /opt/magic-mouse-gestures/
sudo chmod +x /opt/magic-mouse-gestures/magic_mouse_gestures.py

# Install udev rules
sudo cp udev/99-magic-mouse.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

#### 3. Reconnect Magic Mouse

Disconnect and reconnect via Bluetooth to apply the new permissions:

```bash
bluetoothctl disconnect <MAC_ADDRESS>
bluetoothctl connect <MAC_ADDRESS>
```

#### 4. Enable the service

```bash
mkdir -p ~/.config/systemd/user
cp systemd/magic-mouse-gestures.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now magic-mouse-gestures
```

Verify it's running:

```bash
systemctl --user status magic-mouse-gestures
```

## Manual Usage

Run directly (requires root or udev rules):

```bash
sudo python3 magic_mouse_gestures.py
```

Enable debug output:

```bash
DEBUG=1 sudo python3 magic_mouse_gestures.py
```

## Configuration

Edit the constants at the top of `magic_mouse_gestures.py`:

```python
SWIPE_THRESHOLD = 200   # Minimum horizontal movement (pixels)
SWIPE_TIME_MAX = 0.4    # Maximum swipe duration (seconds)
```

## Troubleshooting

### Device not found

Make sure your Magic Mouse 2 is connected via Bluetooth:

```bash
bluetoothctl devices
```

### Permission denied

Either run with `sudo` or install the udev rules (see installation step 3).

### Gestures not working

Check if the service is running:

```bash
systemctl --user status magic-mouse-gestures
```

View logs:

```bash
journalctl --user -u magic-mouse-gestures -f
```

### Verify udev rules are applied

After reconnecting the Magic Mouse, check the hidraw device permissions:

```bash
# Find the Magic Mouse hidraw device
ls -la /dev/hidraw*
```

The Magic Mouse device should show `crw-rw-rw-` permissions. If not, the udev rules may not have loaded correctly.

## Technical Details

### HID Data Structure

The Magic Mouse 2 sends touch data in the following format:

- **Header (14 bytes):** Mouse movement and button states
- **Touch data (8 bytes per finger):**
  - Bytes 0-2: X/Y position (12-bit each)
  - Bytes 3-4: Touch ellipse dimensions
  - Bytes 5-6: Touch ID and orientation
  - Byte 7: Touch state

### Why not libinput?

The Linux kernel's `hid-magicmouse` driver converts touch data into scroll events only. It doesn't expose the raw multitouch data to libinput, which is why gesture detection tools like `libinput-gestures` don't work with the Magic Mouse.

This driver bypasses that limitation by reading directly from the HID raw interface.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Apple Magic Mouse 2 HID documentation from the Linux kernel source
- The Hyprland and Wayland communities
