#!/usr/bin/env python3
"""
Magic Mouse 2 Gesture Driver for Linux

Enables macOS-style swipe gestures on Apple Magic Mouse 2 for Linux/Wayland.
Reads raw HID touch data and translates horizontal swipes into browser
back/forward navigation.

Author: Breno Perucchi
License: MIT
"""

import os
import sys
import glob
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional

__version__ = "1.0.0"

# Magic Mouse 2 identifiers
VENDOR_ID = 0x004c
PRODUCT_ID = 0x0269

# Gesture detection thresholds
SWIPE_THRESHOLD = 200
SWIPE_TIME_MAX = 0.4

DEBUG = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')


@dataclass
class Touch:
    """Single touch point on the Magic Mouse surface"""
    id: int
    x: int
    y: int
    major: int
    minor: int
    size: int
    orientation: int
    state: int


@dataclass
class GestureState:
    """Tracks ongoing gesture state"""
    start_x: Optional[int] = None
    start_y: Optional[int] = None
    start_time: Optional[float] = None
    finger_count: int = 0
    last_gesture_time: float = 0


def find_hidraw_device() -> Optional[str]:
    """
    Locate the hidraw device for Magic Mouse 2.

    Searches /dev/hidraw* devices and checks their vendor/product IDs
    against known Magic Mouse 2 identifiers.
    """
    for hidraw in glob.glob('/dev/hidraw*'):
        try:
            sysfs_path = f'/sys/class/hidraw/{os.path.basename(hidraw)}/device/uevent'
            if os.path.exists(sysfs_path):
                with open(sysfs_path, 'r') as f:
                    content = f.read().lower()
                    if '004c' in content and '0269' in content:
                        return hidraw
        except (IOError, PermissionError):
            continue
    return None


def parse_touch(data: bytes, offset: int) -> Touch:
    """
    Parse 8 bytes of touch data into a Touch object.

    Magic Mouse 2 touch data format (8 bytes per finger):
    - Byte 0: X position LSB
    - Byte 1: Y MSB (4 bits) + X MSB (4 bits)
    - Byte 2: Y position LSB
    - Byte 3: Touch major axis
    - Byte 4: Touch minor axis
    - Byte 5: ID LSB (2 bits) + size (6 bits)
    - Byte 6: Orientation (6 bits) + ID MSB (2 bits)
    - Byte 7: State (4 bits) + reserved (4 bits)
    """
    tdata = data[offset:offset + 8]

    x = tdata[0] | ((tdata[1] & 0x0F) << 8)
    y = tdata[2] | ((tdata[1] & 0xF0) << 4)
    major = tdata[3]
    minor = tdata[4]
    size = tdata[5] & 0x3F
    id_lsb = (tdata[5] >> 6) & 0x03
    id_msb = tdata[6] & 0x03
    touch_id = id_lsb | (id_msb << 2)
    orientation = (tdata[6] >> 2) & 0x3F
    state = (tdata[7] >> 4) & 0x0F

    return Touch(
        id=touch_id, x=x, y=y,
        major=major, minor=minor,
        size=size, orientation=orientation,
        state=state
    )


def parse_report(data: bytes) -> List[Touch]:
    """
    Parse a complete HID report from the Magic Mouse 2.

    Report structure:
    - 14 bytes header (mouse movement data)
    - N * 8 bytes touch data (one block per detected finger)
    """
    if len(data) < 14:
        return []

    touches = []
    num_fingers = (len(data) - 14) // 8

    for i in range(num_fingers):
        offset = 14 + (i * 8)
        if offset + 8 <= len(data):
            touch = parse_touch(data, offset)
            if touch.state > 0 or touch.size > 0:
                touches.append(touch)

    return touches


def send_key(modifier: str, key: str) -> bool:
    """Send a key combination via wtype (Wayland)"""
    try:
        env = os.environ.copy()
        user = os.environ.get('SUDO_USER', os.environ.get('USER'))
        if user:
            uid = subprocess.run(
                ['id', '-u', user],
                capture_output=True, text=True
            ).stdout.strip()
            env['XDG_RUNTIME_DIR'] = f'/run/user/{uid}'
        env['WAYLAND_DISPLAY'] = os.environ.get('WAYLAND_DISPLAY', 'wayland-1')

        subprocess.run(
            ['wtype', '-M', modifier, '-k', key, '-m', modifier],
            check=True, capture_output=True, env=env
        )
        return True
    except Exception as e:
        if DEBUG:
            print(f"Key send failed: {e}", file=sys.stderr)
        return False


def detect_gesture(touches: List[Touch], state: GestureState) -> Optional[str]:
    """
    Analyze touch data to detect horizontal swipe gestures.

    Returns 'swipe_left', 'swipe_right', or None.
    """
    now = time.time()

    if now - state.last_gesture_time < 0.5:
        return None

    if not touches:
        state.start_x = None
        state.start_y = None
        state.start_time = None
        state.finger_count = 0
        return None

    avg_x = sum(t.x for t in touches) // len(touches)
    avg_y = sum(t.y for t in touches) // len(touches)

    if state.start_x is None:
        state.start_x = avg_x
        state.start_y = avg_y
        state.start_time = now
        state.finger_count = len(touches)
        return None

    delta_x = avg_x - state.start_x
    delta_y = avg_y - state.start_y
    elapsed = now - state.start_time

    if elapsed < SWIPE_TIME_MAX and abs(delta_x) > SWIPE_THRESHOLD:
        if abs(delta_x) > abs(delta_y) * 2:
            gesture = "swipe_right" if delta_x > 0 else "swipe_left"
            state.start_x = None
            state.start_y = None
            state.start_time = None
            state.last_gesture_time = now
            return gesture

    if elapsed > SWIPE_TIME_MAX:
        state.start_x = avg_x
        state.start_y = avg_y
        state.start_time = now

    return None


def main():
    """Main entry point"""
    print(f"Magic Mouse Gestures v{__version__}")
    print("=" * 35)

    hidraw = find_hidraw_device()
    if not hidraw:
        print("Error: Magic Mouse 2 not found", file=sys.stderr)
        print("\nMake sure the mouse is connected via Bluetooth.")
        sys.exit(1)

    try:
        fd = os.open(hidraw, os.O_RDONLY)
    except PermissionError:
        print(f"Error: Permission denied for {hidraw}", file=sys.stderr)
        print("Run with sudo or configure udev rules.")
        sys.exit(1)

    print(f"Connected: {hidraw}")
    print("Swipe horizontally for browser back/forward")
    print("Press Ctrl+C to stop\n")

    state = GestureState()

    try:
        while True:
            try:
                data = os.read(fd, 64)
            except OSError:
                continue

            if not data:
                continue

            touches = parse_report(data)

            if DEBUG and touches:
                for t in touches:
                    print(f"Touch: id={t.id} x={t.x} y={t.y} state={t.state}")

            gesture = detect_gesture(touches, state)

            if gesture == "swipe_left":
                if send_key('alt', 'Right'):
                    print("→ Forward")
            elif gesture == "swipe_right":
                if send_key('alt', 'Left'):
                    print("← Back")

    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
