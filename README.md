# Magic Mouse Gestures for Linux

Enable macOS-style swipe gestures on Apple Magic Mouse 2 for Linux/Wayland.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Wayland-lightgrey.svg)

## Features

- **Horizontal swipe gestures** for browser back/forward navigation
- Works with **Wayland** compositors, using `wtype` or `ydotool` to send keys
- Lightweight Python daemon with minimal dependencies
- Automatic device detection and reconnection
- Configurable via environment variables

## Extended version

For one-finger scrolling, middle click, native Wayland pinch zoom, and GNOME
three-finger gestures, see
[`Salacfrantisek/magic-mouse-wayland-gestures`](https://github.com/Salacfrantisek/magic-mouse-wayland-gestures).
It is derived from this project, retains the MIT attribution, and is currently
tested with the Bluetooth/Lightning Magic Mouse 2 (`004C:0269`) on GNOME
Wayland.

## How It Works

The Magic Mouse 2 has a touch-sensitive surface, but Linux only exposes basic mouse functionality by default. This driver reads raw HID data directly from the device to detect touch positions and translate horizontal swipes into keyboard shortcuts.

| Gesture | Action |
|---------|--------|
| Swipe → (right) | Browser back (Alt+Left) |
| Swipe ← (left) | Browser forward (Alt+Right) |

Prefer the opposite direction? Set `SWIPE_REVERSE=1` to swap them.

## Requirements

- Linux with kernel 5.15+ (built-in Magic Mouse 2 support)
- **Wayland session** (not X11)
- Python 3.8+
- A way to send keystrokes: `wtype`, or `ydotool` (with its `ydotoold` daemon) as a fallback

### Supported Devices

| Device | Vendor:Product | Status |
|--------|----------------|--------|
| Magic Mouse 2 (Bluetooth/Lightning) | `004C:0269` | Tested (Hyprland) |
| Magic Mouse 1, Magic Mouse 2 USB-C | `05AC:030D`, `05AC:0323` | Not supported |

### Supported Desktops

Keys are sent with `wtype` when the compositor allows it, and with `ydotool`
otherwise (see [ydotool fallback](#ydotool-fallback)):

| Desktop | `wtype` | `ydotool` |
|---------|---------|-----------|
| **Hyprland** | Tested | Tested |
| **GNOME** (Wayland) | Does not work: Mutter lacks the virtual-keyboard protocol (see #1) | Reported working (see #1), not tested here |
| **Sway**, **KDE Plasma** (Wayland) | Not tested | Not tested |

`ydotool` works at the `uinput` level, below the compositor, so it should work
anywhere it can open `/dev/uinput`.

To check if you're running Wayland:

```bash
echo $XDG_SESSION_TYPE
# Should output: wayland
```

### ydotool fallback

Some compositors (notably GNOME) do not support the virtual keyboard protocol
that `wtype` relies on. In that case the driver falls back to `ydotool`, which
works at the uinput level. It needs the `ydotoold` daemon running and access to
its socket. Set `KEY_BACKEND=wtype` or `KEY_BACKEND=ydotool` to force one
backend; the default is `auto` (try `wtype`, then `ydotool`).

The command line of `ydotool` changed between 0.x (key names) and 1.x (numeric
key codes), and 0.x silently types the wrong thing when given the 1.x syntax.
The driver detects the version from the output of `ydotool help`; set
`YDOTOOL_SYNTAX=name` (0.x) or `YDOTOOL_SYNTAX=code` (1.x) to override it.

#### Setting up ydotool

1. Install it (`sudo pacman -S ydotool`, `sudo apt install ydotool` or
   `sudo dnf install ydotool`).
2. Start the daemon as your user. Arch ships a user unit:

   ```bash
   systemctl --user enable --now ydotool
   ```

   On other distributions run `ydotoold` yourself or write a user unit for it.
3. Make sure your user can open `/dev/uinput`. Either add yourself to the
   `input` group (`sudo usermod -aG input $USER`, then log in again) or grant an
   ACL: `sudo setfacl -m u:$USER:rw /dev/uinput`.

Check it end to end by running `KEY_BACKEND=ydotool DEBUG=1 python3
magic_mouse_gestures.py` and swiping: the log should show the back/forward
actions and your browser should navigate.

**Note:** X11 sessions are not supported (would require `xdotool` instead of `wtype`).

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
- Check dependencies (`python3`, `wtype` or `ydotool`, `bluetoothctl`)
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
sudo pacman -S python wtype bluez-utils   # add ydotool for GNOME
```

**Debian/Ubuntu:**
```bash
sudo apt install python3 wtype bluez   # add ydotool for GNOME
```

**Fedora:**
```bash
sudo dnf install python3 wtype bluez   # add ydotool for GNOME
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
| `SWIPE_REVERSE` | false | Swap back and forward (swipe left goes back, swipe right goes forward) |
| `KEY_BACKEND` | auto | `auto` (try `wtype`, then `ydotool`), `wtype` or `ydotool` |
| `YDOTOOL_SYNTAX` | auto | Force `name` (ydotool 0.x) or `code` (1.x) instead of detecting it |
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
DEBUG=1 python3 magic_mouse_gestures.py
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
bluetoothctl devices Connected
```

Then check that the kernel exposes it as `004C:0269`:

```bash
grep -H HID_ID /sys/class/hidraw/hidraw*/device/uevent
```

### Permission denied

Either run with `sudo` or install the udev rules (see installation).

### Gestures are detected but nothing happens

Run with `DEBUG=1` (see [Debugging](#debugging)). If swipes are logged but the
browser doesn't navigate, the key backend is failing:

- On GNOME, `wtype` prints `Compositor does not support the virtual keyboard
  protocol`. Install `ydotool` and start `ydotoold` (see
  [Setting up ydotool](#setting-up-ydotool)).
- If `ydotoold` is not running, `ydotool` fails to connect to its socket
  (`/run/user/<uid>/.ydotool_socket`). Check `systemctl --user status ydotool`.
- Force a backend with `KEY_BACKEND=wtype` or `KEY_BACKEND=ydotool` to see
  which one fails.

### Swipes type numbers instead of navigating

ydotool 0.x silently accepts the 1.x syntax and types the key codes. The
driver detects the version from `ydotool help`; if it guesses wrong, set
`YDOTOOL_SYNTAX=name` (0.x) or `YDOTOOL_SYNTAX=code` (1.x).

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

The Magic Mouse 2 sends touch data in report `0x12`:

- **Header (14 bytes):** Mouse movement and button states
- **Touch data (8 bytes per finger):**
  - Bytes 0-2: X and Y position (two 12-bit values)
  - Bytes 3-4: Touch ellipse dimensions
  - Bytes 5-6: Touch ID and orientation
  - Byte 7: Touch state (high nibble; 0 means the finger is up)

### Coordinate Parsing

Coordinates are **signed** 12-bit values, as in the kernel's `hid-magicmouse`
driver. Measured on a Magic Mouse 2, X spans roughly -700 to 1300. The driver
reads them as unsigned (0-4095):

```python
x = tdata[0] | ((tdata[1] & 0x0F) << 8)
y = (tdata[2] << 4) | (tdata[1] >> 4)
```

so a position left of the center shows up as a value near 4095. That is why
`wrap_delta()` computes movement modulo 4096: swipes still come out with the
right sign. The one case it can't cover is averaging two fingers that sit on
opposite sides of the center.

### Why not libinput?

The Linux kernel's `hid-magicmouse` driver converts touch data into scroll events only. It doesn't expose raw multitouch data to libinput, which is why `libinput-gestures` doesn't work with Magic Mouse.

This driver bypasses that limitation by reading directly from the HID raw interface.

### Kernel Module: hid_magicmouse

The `hid_magicmouse` kernel module handles **scroll functionality**. Our driver handles **swipe gestures**. Both work together.

**Check if module is loaded:**

```bash
lsmod | grep hid_magicmouse
```

**Force load the module:**

```bash
sudo modprobe hid_magicmouse
```

**View module parameters:**

```bash
modinfo hid_magicmouse
```

**Current settings:**

```bash
systool -m hid_magicmouse -av
```

### Scroll Configuration

The installer copies `modprobe/hid-magicmouse.conf` to `/etc/modprobe.d/` with optimized scroll settings:

```
options hid_magicmouse scroll_acceleration=1 scroll_speed=32 emulate_3button=0
```

| Option | Default | Description |
|--------|---------|-------------|
| `scroll_acceleration` | 1 | Enable scroll acceleration |
| `scroll_speed` | 32 | Scroll speed multiplier |
| `emulate_3button` | 0 | Emulate middle button with 3-finger click |
| `emulate_scroll_wheel` | 1 | Enable scroll wheel emulation |

**Apply changes manually:**

```bash
sudo modprobe -r hid_magicmouse && sudo modprobe hid_magicmouse
```

Then reconnect the Magic Mouse via Bluetooth.

---

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

Run the tests with `python3 -m pytest`. They cover key sending and the
`ydotool` syntax detection and need neither a mouse nor a running compositor.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Apple Magic Mouse 2 HID documentation from the Linux kernel source
- The Hyprland and Wayland communities
- [@JaapStruyk](https://github.com/JaapStruyk) for the original `ydotool` report and diff (#1), and [@sodonnel](https://github.com/sodonnel) for the `ydotool` 0.x/1.x syntax findings
