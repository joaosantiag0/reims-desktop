"""Live X11 screen capture and input forwarding for Reims Web Console.

Since upstream `reims-vgpu` (`reims-graphics-pci`) renders directly into a
Vulkan/X11 window on `DISPLAY=:0` with `-vga none -display none`, standard QEMU
VNC is unavailable. This module captures frames via `scrot` and forwards
mouse/keyboard events via `xdotool`.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_KEY_MAP: Dict[str, str] = {
    "Enter": "Return",
    "Backspace": "BackSpace",
    "Escape": "Escape",
    "Tab": "Tab",
    " ": "space",
    "ArrowUp": "Up",
    "ArrowDown": "Down",
    "ArrowLeft": "Left",
    "ArrowRight": "Right",
    "Delete": "Delete",
    "Insert": "Insert",
    "Home": "Home",
    "End": "End",
    "PageUp": "Prior",
    "PageDown": "Next",
    "Control": "Control_L",
    "Shift": "Shift_L",
    "Alt": "Alt_L",
    "Meta": "Super_L",
    "CapsLock": "Caps_Lock",
    **{f"F{i}": f"F{i}" for i in range(1, 13)},
}


def _display_env() -> Dict[str, str]:
    env = dict(os.environ)
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":0"
    if not env.get("XAUTHORITY"):
        home_xauth = Path.home() / ".Xauthority"
        if home_xauth.exists():
            env["XAUTHORITY"] = str(home_xauth)
    return env


def is_console_available(mock: bool = False) -> bool:
    if mock:
        return True
    return shutil.which("scrot") is not None


def get_screen_size(mock: bool = False) -> Tuple[int, int]:
    if mock:
        return (1920, 1080)
    xwininfo = shutil.which("xwininfo")
    if xwininfo:
        try:
            res = subprocess.run(
                [xwininfo, "-root"],
                env=_display_env(),
                capture_output=True,
                text=True,
                timeout=3,
            )
            w = re.search(r"Width:\s+(\d+)", res.stdout)
            h = re.search(r"Height:\s+(\d+)", res.stdout)
            if w and h:
                return (int(w.group(1)), int(h.group(1)))
        except Exception as e:
            logger.debug("xwininfo failed: %s", e)
    return (1920, 1080)


def capture_jpeg_frame(quality: int = 65, mock: bool = False) -> Optional[bytes]:
    if mock:
        # Minimal valid 1x1 JPEG for unit tests.
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
            b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
            b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00"
            b"\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01"
            b"\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05"
            b"\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00"
            b"\x00\x00\xff\xd9"
        )
    scrot = shutil.which("scrot")
    if not scrot:
        return None
    base_dir = "/dev/shm" if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK) else None
    with tempfile.NamedTemporaryFile(suffix=".jpg", dir=base_dir, delete=True) as tmp:
        try:
            res = subprocess.run(
                [scrot, "-q", str(quality), "-o", tmp.name],
                env=_display_env(),
                capture_output=True,
                timeout=3,
            )
            if res.returncode != 0:
                return None
            return Path(tmp.name).read_bytes()
        except Exception as e:
            logger.debug("scrot capture failed: %s", e)
            return None


def _map_key(key: str) -> Optional[str]:
    if not key:
        return None
    if key in _KEY_MAP:
        return _KEY_MAP[key]
    if len(key) == 1:
        return key
    return None


def send_input(event: Dict[str, Any], mock: bool = False) -> bool:
    if mock:
        return True
    xdotool = shutil.which("xdotool")
    if not xdotool:
        return False

    kind = str(event.get("type", ""))
    env = _display_env()

    if kind in ("mousemove", "mousedown", "mouseup", "click", "wheel"):
        w, h = get_screen_size(mock=False)
        nx = max(0.0, min(1.0, float(event.get("x", 0.5))))
        ny = max(0.0, min(1.0, float(event.get("y", 0.5))))
        px = str(int(nx * w))
        py = str(int(ny * h))
        btn = str(int(event.get("button", 1)))

        if kind == "mousemove":
            args = [xdotool, "mousemove", px, py]
        elif kind == "mousedown":
            args = [xdotool, "mousemove", "--sync", px, py, "mousedown", btn]
        elif kind == "mouseup":
            args = [xdotool, "mousemove", "--sync", px, py, "mouseup", btn]
        elif kind == "click":
            args = [xdotool, "mousemove", "--sync", px, py, "click", btn]
        else:
            delta_y = float(event.get("deltaY", 0))
            wheel_btn = "4" if delta_y < 0 else "5"
            args = [xdotool, "mousemove", "--sync", px, py, "click", wheel_btn]
        res = subprocess.run(args, env=env, capture_output=True, timeout=3)
        return res.returncode == 0

    if kind in ("keydown", "keyup", "key"):
        raw_key = str(event.get("key", ""))
        mapped = _map_key(raw_key)
        if not mapped:
            return False
        if kind in ("keydown", "keyup") and len(raw_key) == 1 and mapped == raw_key:
            # Printable characters work best with `xdotool type` on keydown to
            # respect shift/dead-keys/accents; ignore keyup for single chars.
            if kind == "keyup":
                return True
            res = subprocess.run(
                [xdotool, "type", "--clearmodifiers", "--delay", "5", "--", raw_key],
                env=env,
                capture_output=True,
                timeout=3,
            )
            return res.returncode == 0
        sub = {"keydown": "keydown", "keyup": "keyup", "key": "key"}[kind]
        res = subprocess.run([xdotool, sub, mapped], env=env, capture_output=True, timeout=3)
        return res.returncode == 0

    if kind == "text":
        text = str(event.get("text", ""))
        if not text:
            return False
        res = subprocess.run(
            [xdotool, "type", "--clearmodifiers", "--delay", "10", "--", text],
            env=env,
            capture_output=True,
            timeout=5,
        )
        return res.returncode == 0

    return False
