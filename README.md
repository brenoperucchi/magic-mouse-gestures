# Magic Mouse Gestures for Linux

Enable macOS-style swipe gestures on Apple Magic Mouse 2 for Linux/Wayland.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Wayland-lightgrey.svg)

## Features

- **Horizontal swipe gestures** for browser back/forward navigation
- Works with **Wayland** compositors (Hyprland, Sway, GNOME, etc.)
- Lightweight Python daemon with minimal dependencies
- Automatic device detection and reconnection
- Configurable via environment variables

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

---

## Installation

Choose **one** of the two methods below:

### Option A: Automatic Installation (Recommended)

```bash
git clone https://github.com/brenoperucchi/magic-mouse-gestures.git
cd magic-mouse-gestures
./install.sh
```

The installer will:
- Check dependencies (`python3`, `wtype`, `bluetoothctl`)
- Install the driver to `/opt/magic-mouse-gestures/`
- Install udev rules for non-root access
- Reconnect Magic Mouse to apply permissions
- Install and enable the systemd user service
- Verify everything is working

**Note:** Do NOT run with `sudo`. The script requests sudo only when needed.

### Option B: Manual Installation

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

#### 2. Install driver and udev rules

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

Disconnect and reconnect via Bluetooth to apply permissions:

```bash
bluetoothctl disconnect <MAC_ADDRESS>
bluetoothctl connect <MAC_ADDRESS>
```

#### 4. Install and enable the service

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

---

## Uninstall

```bash
cd magic-mouse-gestures
./uninstall.sh
```

This stops the service, removes all installed files, and restores default permissions.

---

## Configuration

All thresholds can be configured via environment variables (no need to edit code):

| Variable | Default | Description |
|----------|---------|-------------|
| `SWIPE_THRESHOLD` | 200 | Minimum horizontal movement (pixels) |
| `SWIPE_VERTICAL_MAX` | 150 | Maximum vertical movement (pixels) |
| `SWIPE_TIME_MAX` | 0.5 | Maximum swipe duration (seconds) |
| `SWIPE_VELOCITY_MIN` | 200 | Minimum swipe velocity (pixels/second) |
| `SCROLL_COOLDOWN` | 0.25 | Cooldown after scroll before allowing swipe (seconds) |
| `MIN_FINGERS` | 1 | Minimum fingers for swipe gesture |
| `MAX_FINGERS` | 2 | Maximum fingers (ignore if more) |
| `DEBUG` | false | Enable debug output (1, true, yes) |

### Example: Custom configuration

```bash
SWIPE_THRESHOLD=150 SWIPE_VELOCITY_MIN=150 python3 /opt/magic-mouse-gestures/magic_mouse_gestures.py
```

### Persistent configuration (systemd)

Edit the service file to add environment variables:

```bash
systemctl --user edit magic-mouse-gestures
```

Add:

```ini
[Service]
Environment="SWIPE_THRESHOLD=150"
Environment="SWIPE_VELOCITY_MIN=150"
```

Then restart:

```bash
systemctl --user restart magic-mouse-gestures
```

---

## Debugging

### Step 1: Stop the systemd service

```bash
systemctl --user stop magic-mouse-gestures
```

### Step 2: Run manually with debug enabled

```bash
DEBUG=1 python3 /opt/magic-mouse-gestures/magic_mouse_gestures.py
```

Or from the project directory:

```bash
DEBUG=1 python3 ~/Projects/magic-mouse-gestures/magic_mouse_gestures.py
```

### Step 3: Save debug output to a file

```bash
DEBUG=1 python3 /opt/magic-mouse-gestures/magic_mouse_gestures.py 2>&1 | tee ~/magic-mouse.log
```

### Step 4: Restart the service when done

```bash
systemctl --user start magic-mouse-gestures
```

### View service logs

```bash
journalctl --user -u magic-mouse-gestures -f
```

---

## Troubleshooting

### Device not found

Make sure your Magic Mouse 2 is connected via Bluetooth:

```bash
bluetoothctl devices
```

### Permission denied

Either run with `sudo` or install the udev rules (see installation).

### Gestures not working

1. Check if the service is running:
   ```bash
   systemctl --user status magic-mouse-gestures
   ```

2. View logs:
   ```bash
   journalctl --user -u magic-mouse-gestures -f
   ```

3. Run with debug to see touch data:
   ```bash
   systemctl --user stop magic-mouse-gestures
   DEBUG=1 python3 /opt/magic-mouse-gestures/magic_mouse_gestures.py
   ```

### Verify udev rules

After reconnecting the Magic Mouse, check permissions:

```bash
ls -la /dev/hidraw*
```

The Magic Mouse device should show `crw-rw-rw-` permissions.

---

## Technical Details

### HID Data Structure

The Magic Mouse 2 sends touch data in the following format:

- **Header (14 bytes):** Mouse movement and button states
- **Touch data (8 bytes per finger):**
  - Bytes 0-1: X position (12-bit)
  - Bytes 1-2: Y position (12-bit)
  - Bytes 3-4: Touch ellipse dimensions
  - Bytes 5-6: Touch ID and orientation
  - Byte 7: Touch state (1-4 = contact, 5-7 = lift)

### Coordinate Parsing

Coordinates are 12-bit values (0-4095) parsed as:

```python
x = tdata[0] | ((tdata[1] & 0x0F) << 8)
y = (tdata[2] << 4) | (tdata[1] >> 4)
```

### Why not libinput?

The Linux kernel's `hid-magicmouse` driver converts touch data into scroll events only. It doesn't expose raw multitouch data to libinput, which is why `libinput-gestures` doesn't work with Magic Mouse.

This driver bypasses that limitation by reading directly from the HID raw interface.

---

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Apple Magic Mouse 2 HID documentation from the Linux kernel source
- The Hyprland and Wayland communities
