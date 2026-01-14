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

__version__ = "1.2.0"

# Magic Mouse 2 identifiers
VENDOR_ID = "004c"
PRODUCT_ID = "0269"

# Touch coordinates are 12-bit (0-4095)
COORD_MAX = 4096

# Touch states - only these indicate active contact
# States 1-4 are contact, states 5-7 are lift/transitional
CONTACT_STATES = {1, 2, 3, 4}

# Reconnection settings
RECONNECT_DELAY_INITIAL = 1.0   # Initial delay before reconnect attempt
RECONNECT_DELAY_MAX = 30.0      # Maximum delay between attempts
RECONNECT_DELAY_MULTIPLIER = 2  # Exponential backoff multiplier
ERROR_THRESHOLD = 10            # Consecutive errors before reconnect


def get_env_float(name: str, default: float) -> float:
    """Get float value from environment variable."""
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def get_env_int(name: str, default: int) -> int:
    """Get int value from environment variable."""
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# Configurable thresholds via environment variables
SWIPE_THRESHOLD = get_env_int('SWIPE_THRESHOLD', 200)        # Min horizontal movement
SWIPE_VERTICAL_MAX = get_env_int('SWIPE_VERTICAL_MAX', 150)  # Max vertical movement
SWIPE_TIME_MAX = get_env_float('SWIPE_TIME_MAX', 0.5)        # Max swipe duration (seconds)
SWIPE_VELOCITY_MIN = get_env_int('SWIPE_VELOCITY_MIN', 200)  # Min horizontal velocity (px/s)
SCROLL_COOLDOWN = get_env_float('SCROLL_COOLDOWN', 0.25)     # Cooldown after scroll (seconds)
MIN_FINGERS = get_env_int('MIN_FINGERS', 1)                  # Min fingers for swipe
MAX_FINGERS = get_env_int('MAX_FINGERS', 2)                  # Max fingers (ignore >2)

DEBUG = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes')


def wrap_delta(new: int, old: int) -> int:
    """
    Calculate delta handling 12-bit coordinate wraparound.

    When touch coordinates wrap from 4095 to 0 (or vice versa),
    naive subtraction gives wrong results. This calculates the
    shortest distance accounting for wraparound.
    """
    delta = new - old
    if delta > COORD_MAX // 2:
        delta -= COORD_MAX
    elif delta < -COORD_MAX // 2:
        delta += COORD_MAX
    return delta


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
    last_scroll_time: float = 0


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
                    # Use constants for device matching
                    if VENDOR_ID in content and PRODUCT_ID in content:
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
    y = (tdata[2] << 4) | (tdata[1] >> 4)
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

    Only returns touches in active contact states (1-4).
    States 5-7 are lift/transitional and are filtered out.
    """
    if len(data) < 14:
        return []

    touches = []
    num_fingers = (len(data) - 14) // 8

    for i in range(num_fingers):
        offset = 14 + (i * 8)
        if offset + 8 <= len(data):
            touch = parse_touch(data, offset)
            # Only include active contact states, filter lift/transitional
            if touch.state in CONTACT_STATES and touch.size > 0:
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


def reset_state(state: GestureState, avg_x: int, avg_y: int, now: float, finger_count: int):
    """Reset gesture tracking state."""
    state.start_x = avg_x
    state.start_y = avg_y
    state.start_time = now
    state.finger_count = finger_count


def detect_gesture(touches: List[Touch], state: GestureState) -> Optional[str]:
    """
    Analyze touch data to detect horizontal swipe gestures.

    Features:
    - Handles 12-bit coordinate wraparound
    - Cancels tracking if vertical movement dominates (scroll detection)
    - Enforces minimum velocity to avoid slow drift false positives
    - Cooldown after scroll to prevent immediate swipe detection
    - Resets on finger count changes
    - Ignores >2 fingers (noise)
    """
    now = time.monotonic()

    # Cooldown after last gesture
    if now - state.last_gesture_time < 0.5:
        return None

    # No touches - reset state
    if not touches:
        state.start_x = None
        state.start_y = None
        state.start_time = None
        state.finger_count = 0
        return None

    num_fingers = len(touches)

    # Ignore too many fingers (usually noise/accidental touch)
    if num_fingers > MAX_FINGERS:
        if DEBUG:
            print(f"Ignoring {num_fingers} fingers (max={MAX_FINGERS})")
        return None

    # Require minimum fingers
    if num_fingers < MIN_FINGERS:
        return None

    avg_x = sum(t.x for t in touches) // num_fingers
    avg_y = sum(t.y for t in touches) // num_fingers

    # Reset if finger count changed (finger added/removed)
    if state.start_x is not None and num_fingers != state.finger_count:
        if DEBUG:
            print(f"Finger count changed: {state.finger_count} -> {num_fingers}, resetting")
        reset_state(state, avg_x, avg_y, now, num_fingers)
        return None

    # Initialize tracking on first touch
    if state.start_x is None:
        reset_state(state, avg_x, avg_y, now, num_fingers)
        return None

    # Use wrap_delta to handle 12-bit coordinate wraparound
    delta_x = wrap_delta(avg_x, state.start_x)
    delta_y = wrap_delta(avg_y, state.start_y)
    elapsed = now - state.start_time

    # Avoid division by zero
    if elapsed < 0.01:
        return None

    # Calculate velocity
    velocity_x = abs(delta_x) / elapsed

    # Scroll detection: vertical movement dominates
    if abs(delta_y) > SWIPE_VERTICAL_MAX or abs(delta_y) > abs(delta_x):
        if DEBUG:
            print(f"Scroll detected: delta_y={delta_y}, resetting")
        state.last_scroll_time = now
        reset_state(state, avg_x, avg_y, now, num_fingers)
        return None

    # Cooldown after scroll - don't allow swipe immediately after scrolling
    if now - state.last_scroll_time < SCROLL_COOLDOWN:
        return None

    # Check for horizontal swipe
    if elapsed < SWIPE_TIME_MAX and abs(delta_x) > SWIPE_THRESHOLD:
        # Verify velocity is high enough (intentional swipe, not slow drift)
        if velocity_x >= SWIPE_VELOCITY_MIN:
            # Verify horizontal is dominant
            if abs(delta_x) > abs(delta_y) * 3:
                gesture = "swipe_right" if delta_x > 0 else "swipe_left"
                if DEBUG:
                    print(f"Swipe detected: delta_x={delta_x}, velocity={velocity_x:.0f}px/s")
                state.start_x = None
                state.start_y = None
                state.start_time = None
                state.last_gesture_time = now
                return gesture

    # Reset if gesture took too long
    if elapsed > SWIPE_TIME_MAX:
        reset_state(state, avg_x, avg_y, now, num_fingers)

    return None


def print_config():
    """Print current configuration."""
    print(f"Configuration:")
    print(f"  SWIPE_THRESHOLD    = {SWIPE_THRESHOLD} px")
    print(f"  SWIPE_VERTICAL_MAX = {SWIPE_VERTICAL_MAX} px")
    print(f"  SWIPE_TIME_MAX     = {SWIPE_TIME_MAX} s")
    print(f"  SWIPE_VELOCITY_MIN = {SWIPE_VELOCITY_MIN} px/s")
    print(f"  SCROLL_COOLDOWN    = {SCROLL_COOLDOWN} s")
    print(f"  MIN_FINGERS        = {MIN_FINGERS}")
    print(f"  MAX_FINGERS        = {MAX_FINGERS}")
    print(f"  DEBUG              = {DEBUG}")
    print()


def run_device_loop(fd: int, state: GestureState) -> bool:
    """
    Main device reading loop.

    Returns True if should attempt reconnect, False to exit.
    """
    consecutive_errors = 0

    while True:
        try:
            data = os.read(fd, 64)
            consecutive_errors = 0  # Reset on successful read
        except OSError as e:
            consecutive_errors += 1
            if DEBUG:
                print(f"Read error ({consecutive_errors}): {e}")

            if consecutive_errors >= ERROR_THRESHOLD:
                print("Device disconnected, attempting reconnect...")
                return True  # Signal reconnect

            time.sleep(0.1)  # Small delay before retry
            continue

        if not data:
            consecutive_errors += 1
            if consecutive_errors >= ERROR_THRESHOLD:
                print("Device not responding, attempting reconnect...")
                return True
            time.sleep(0.1)
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


def main():
    """Main entry point with automatic reconnection."""
    print(f"Magic Mouse Gestures v{__version__}")
    print("=" * 35)

    if DEBUG:
        print_config()

    state = GestureState()
    reconnect_delay = RECONNECT_DELAY_INITIAL

    while True:
        # Find device
        hidraw = find_hidraw_device()
        if not hidraw:
            print(f"Magic Mouse not found, retrying in {reconnect_delay:.0f}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * RECONNECT_DELAY_MULTIPLIER, RECONNECT_DELAY_MAX)
            continue

        # Open device
        try:
            fd = os.open(hidraw, os.O_RDONLY)
        except PermissionError:
            print(f"Permission denied for {hidraw}", file=sys.stderr)
            print("Run with sudo or configure udev rules.")
            sys.exit(1)
        except OSError as e:
            print(f"Failed to open {hidraw}: {e}")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * RECONNECT_DELAY_MULTIPLIER, RECONNECT_DELAY_MAX)
            continue

        # Connected successfully - reset backoff
        reconnect_delay = RECONNECT_DELAY_INITIAL
        print(f"Connected: {hidraw}")
        print("Swipe horizontally for browser back/forward")
        print("Press Ctrl+C to stop\n")

        try:
            should_reconnect = run_device_loop(fd, state)
            if not should_reconnect:
                break
        except KeyboardInterrupt:
            print("\nStopped")
            break
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

        # Wait before reconnect attempt
        print(f"Reconnecting in {reconnect_delay:.0f}s...")
        time.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * RECONNECT_DELAY_MULTIPLIER, RECONNECT_DELAY_MAX)


if __name__ == "__main__":
    main()
