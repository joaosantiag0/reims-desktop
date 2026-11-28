"""Persistent user preferences for Reims Desktop Control.

Small JSON file under the user's XDG config directory that remembers things
across sessions, such as the last VM that was started and whether the user
wants it reopened automatically at boot.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Policy for opening the last VM at startup:
#   "ask"    -> show a prompt each boot (default)
#   "always" -> start it automatically, without asking
#   "never"  -> user chose not to be asked again
POLICY_ASK = "ask"
POLICY_ALWAYS = "always"
POLICY_NEVER = "never"
VALID_POLICIES = frozenset({POLICY_ASK, POLICY_ALWAYS, POLICY_NEVER})

KEY_LAST_VM = "last_vm"
KEY_LAST_VM_POLICY = "last_vm_policy"


def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "reims-desktop"


def config_file() -> Path:
    return config_dir() / "prefs.json"


def load_prefs() -> Dict[str, Any]:
    """Load preferences from disk, returning {} on any error."""
    path = config_file()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning(f"Prefs file is not an object: {path}")
            return {}
        # Sanitize the policy value so unknown strings never reach callers.
        policy = data.get(KEY_LAST_VM_POLICY)
        if policy is not None and policy not in VALID_POLICIES:
            logger.warning(f"Ignoring invalid last_vm_policy: {policy!r}")
            data[KEY_LAST_VM_POLICY] = POLICY_ASK
        return data
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning(f"Could not read prefs file {path}: {e}")
        return {}


def save_prefs(prefs_map: Dict[str, Any]) -> bool:
    """Persist preferences to disk. Returns True on success."""
    path = config_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(prefs_map, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        return True
    except Exception as e:
        logger.warning(f"Could not write prefs file {path}: {e}")
        return False


def _update(key: str, value: Any) -> None:
    prefs_map = load_prefs()
    prefs_map[key] = value
    save_prefs(prefs_map)


def set_last_vm(name: str) -> None:
    """Record the VM most recently started (best-effort, never raises)."""
    try:
        _update(KEY_LAST_VM, str(name))
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"Could not record last VM: {e}")


def get_last_vm() -> Optional[str]:
    return load_prefs().get(KEY_LAST_VM)


def set_last_vm_policy(policy: str) -> None:
    if policy not in VALID_POLICIES:
        logger.warning(f"Refusing to store invalid last_vm_policy: {policy!r}")
        return
    _update(KEY_LAST_VM_POLICY, policy)


def get_last_vm_policy() -> str:
    return load_prefs().get(KEY_LAST_VM_POLICY, POLICY_ASK)
