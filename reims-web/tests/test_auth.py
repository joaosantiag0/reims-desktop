"""Unit tests for the Reims Web authentication manager."""
from __future__ import annotations

import unittest

from reims_web.auth import AuthManager, read_password_from_sources


class TestAuthManager(unittest.TestCase):

    def test_open_mode_when_no_password(self):
        auth = AuthManager(None)
        self.assertFalse(auth.enabled)
        # Open mode accepts any token/password.
        self.assertTrue(auth.check_password(""))
        self.assertTrue(auth.validate_token("anything"))

    def test_password_check(self):
        auth = AuthManager("s3cret")
        self.assertTrue(auth.check_password("s3cret"))
        self.assertFalse(auth.check_password("wrong"))
        self.assertFalse(auth.check_password(""))

    def test_session_roundtrip(self):
        auth = AuthManager("pw")
        token = auth.create_session()
        self.assertTrue(auth.validate_token(token))
        auth.revoke_token(token)
        self.assertFalse(auth.validate_token(token))

    def test_token_expiry(self):
        auth = AuthManager("pw", token_ttl_seconds=-1)
        token = auth.create_session()
        self.assertFalse(auth.validate_token(token))

    def test_random_password_rejected_when_enabled(self):
        auth = AuthManager("pw")
        self.assertFalse(auth.validate_token("forged-token"))


class TestPasswordSources(unittest.TestCase):

    def test_env_variable(self):
        import os

        os.environ["REIMS_WEB_PASSWORD"] = "from-env"
        try:
            self.assertEqual(read_password_from_sources(), "from-env")
        finally:
            del os.environ["REIMS_WEB_PASSWORD"]

    def test_missing_sources_open_mode(self):
        import os

        os.environ.pop("REIMS_WEB_PASSWORD", None)
        os.environ.pop("REIMS_WEB_PASSWORD_FILE", None)
        self.assertIsNone(read_password_from_sources())


if __name__ == "__main__":
    unittest.main()
