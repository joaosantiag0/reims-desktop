"""Session/token authentication for the Reims Web service.

Designed like Proxmox's cookie tickets, but minimal: a single administrator
password (sourced from the environment or a root-owned file) is exchanged for
an opaque, expiring bearer token kept in memory by the service. When no
password is configured the service runs in open mode (local/dev usage only).
"""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_TTL_SECONDS = 24 * 60 * 60


def read_password_from_sources(
    env_var: str = "REIMS_WEB_PASSWORD",
    file_env_var: str = "REIMS_WEB_PASSWORD_FILE",
) -> Optional[str]:
    """Resolve the admin password from the environment or a password file.

    Returns ``None`` when nothing is configured (open mode).
    """
    password = os.environ.get(env_var, "").strip()
    if password:
        return password
    file_path = os.environ.get(file_env_var, "").strip()
    if file_path:
        try:
            password = Path(file_path).read_text(encoding="utf-8").strip()
            if password:
                return password
        except OSError as e:
            logger.warning("Could not read password file %s: %s", file_path, e)
    return None


class AuthManager:
    """In-memory bearer token store guarded by a lock."""

    def __init__(
        self,
        password: Optional[str],
        token_ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
    ):
        self.password = password
        self.token_ttl_seconds = token_ttl_seconds
        self._sessions: Dict[str, float] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.password is not None

    def check_password(self, password: str) -> bool:
        if not self.enabled:
            return True
        return bool(password) and secrets.compare_digest(password, self.password or "")

    def create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = time.monotonic() + self.token_ttl_seconds
            self._prune_locked()
        return token

    def validate_token(self, token: str) -> bool:
        if not self.enabled:
            return True
        if not token:
            return False
        with self._lock:
            expires = self._sessions.get(token)
            if expires is None:
                return False
            if time.monotonic() > expires:
                del self._sessions[token]
                return False
        return True

    def revoke_token(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def _prune_locked(self) -> None:
        now = time.monotonic()
        expired = [tok for tok, exp in self._sessions.items() if now > exp]
        for tok in expired:
            del self._sessions[tok]
