"""Packaging tests for the reims-web .deb template and build script."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = REPO_ROOT / "packaging" / "templates" / "reims-web"


class TestReimsWebTemplate(unittest.TestCase):

    def test_control_fields(self):
        control = (TEMPLATE_DIR / "DEBIAN" / "control").read_text(encoding="utf-8")
        self.assertTrue(control.startswith("Package: reims-web"))
        self.assertIn("Depends:", control)
        self.assertIn("python3-fastapi", control)
        self.assertIn("reims-core", control)
        # Legal compliance disclaimer is mandatory in package descriptions.
        self.assertIn("no affiliation with", control)

    def test_postinst_is_strict_and_generates_password(self):
        postinst = TEMPLATE_DIR / "DEBIAN" / "postinst"
        text = postinst.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", text)
        self.assertIn("web-password", text)
        self.assertIn("chmod 600", text)

    def test_launcher_is_strict(self):
        launcher = TEMPLATE_DIR / "usr" / "bin" / "reims-web"
        text = launcher.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env bash"))
        self.assertIn("set -euo pipefail", text)
        self.assertIn("python3 -m reims_web", text)

    def test_systemd_unit_present_and_binds_8006(self):
        unit = TEMPLATE_DIR / "lib" / "systemd" / "system" / "reims-web.service"
        text = unit.read_text(encoding="utf-8")
        self.assertIn("[Install]", text)
        self.assertIn("--port 8006", text)
        self.assertIn("WantedBy=multi-user.target", text)

    def test_build_script_exists_and_is_strict(self):
        script = REPO_ROOT / "packaging" / "scripts" / "build_web_deb.sh"
        self.assertTrue(script.exists())
        self.assertTrue(script.stat().st_mode & 0o111, "build script must be executable")
        text = script.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("build_web_deb.sh", (REPO_ROOT / "packaging" / "scripts" / "build_all.sh").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
