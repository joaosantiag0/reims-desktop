"""Integration tests for the Reims Web FastAPI application (mock ctl backend).

Skipped gracefully when fastapi/httpx are not installed, so the shared test
suites keep passing on any environment (per agents.md).
"""
from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False

from reims_gui.core.ctl_client import ReimsCtlClient
from reims_web.app import create_app
from reims_web.auth import AuthManager


@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed")
class TestWebApiWithAuth(unittest.TestCase):
    """API surface exercised through the mock ctl (no KVM/Vulkan needed)."""

    def setUp(self):
        self.auth = AuthManager("s3cret")
        self.client = ReimsCtlClient(mock=True)
        self.app = create_app(mock=True, auth_manager=self.auth, client=self.client)
        self.tc = TestClient(self.app)
        res = self.tc.post("/api/login", json={"password": "s3cret"})
        assert res.status_code == 200, res.text
        self.headers = {"Authorization": f"Bearer {res.json()['token']}"}

    # ------------------------------------------------------------ auth
    def test_login_rejects_wrong_password(self):
        res = self.tc.post("/api/login", json={"password": "nope"})
        self.assertEqual(res.status_code, 403)

    def test_protected_routes_require_token(self):
        for path in ("/api/vms", "/api/doctor", "/api/gpus", "/api/stats"):
            res = self.tc.get(path)
            self.assertEqual(res.status_code, 401, path)

    def test_logout_revokes_token(self):
        token = self.tc.post("/api/login", json={"password": "s3cret"}).json()["token"]
        self.tc.post("/api/logout", headers={"Authorization": f"Bearer {token}"})
        res = self.tc.get("/api/vms", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 401)

    # ------------------------------------------------------------ vms
    def test_list_vms_returns_mock_fleet(self):
        res = self.tc.get("/api/vms", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        vms = res.json()
        self.assertEqual(len(vms), 2)
        self.assertEqual({v["name"] for v in vms}, {"macOS-Tahoe-Dev", "macOS-Sequoia-Test"})
        statuses = {v["name"]: v["status"] for v in vms}
        self.assertEqual(statuses["macOS-Tahoe-Dev"], "running")
        self.assertEqual(statuses["macOS-Sequoia-Test"], "stopped")
        for vm in vms:
            for field in ("name", "status", "cpus", "memory_mib", "memory_gib", "gpu_name", "macos_version"):
                self.assertIn(field, vm)

    def test_start_and_stop_vm(self):
        res = self.tc.post("/api/vms/macOS-Sequoia-Test/start", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        res = self.tc.post("/api/vms/macOS-Sequoia-Test/stop", headers=self.headers)
        self.assertEqual(res.status_code, 200)

    def test_start_unknown_vm_fails(self):
        res = self.tc.post("/api/vms/nope/start", headers=self.headers)
        self.assertEqual(res.status_code, 500)

    def test_delete_vm(self):
        res = self.tc.delete("/api/vms/macOS-Sequoia-Test", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        names = [v["name"] for v in self.tc.get("/api/vms", headers=self.headers).json()]
        self.assertNotIn("macOS-Sequoia-Test", names)

    def test_create_vm_task_flow(self):
        body = {
            "name": "WebCreated",
            "macos_release": "sequoia",
            "cpus": 4,
            "memory_mib": 8192,
            "disk_size_gb": 64,
        }
        res = self.tc.post("/api/vms", headers=self.headers, json=body)
        self.assertEqual(res.status_code, 200)
        task_id = res.json()["task_id"]
        # Mock creation is quick: poll until the worker thread finishes.
        import time

        task = None
        for _ in range(50):
            task = self.tc.get(f"/api/tasks/{task_id}", headers=self.headers).json()
            if task["done"]:
                break
            time.sleep(0.05)
        self.assertTrue(task["done"])
        self.assertTrue(task["ok"])
        self.assertGreaterEqual(task["progress"], 100)
        names = [v["name"] for v in self.tc.get("/api/vms", headers=self.headers).json()]
        self.assertIn("WebCreated", names)

    def test_create_vm_requires_name(self):
        res = self.tc.post("/api/vms", headers=self.headers, json={})
        self.assertEqual(res.status_code, 422)

    def test_unknown_task_404(self):
        res = self.tc.get("/api/tasks/create-999-x", headers=self.headers)
        self.assertEqual(res.status_code, 404)

    def test_console_probe_reports_stream_and_input(self):
        res = self.tc.get("/api/vms/macOS-Tahoe-Dev/console", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["available"])
        self.assertEqual(data["stream_url"], "/api/vms/macOS-Tahoe-Dev/screen.mjpeg")
        self.assertEqual(data["input_url"], "/api/vms/macOS-Tahoe-Dev/input")

    def test_console_stream_and_input_endpoints(self):
        token = self.headers["Authorization"].split(" ", 1)[1]
        res_stream = self.tc.get(f"/api/vms/macOS-Tahoe-Dev/screen.mjpeg?token={token}")
        self.assertEqual(res_stream.status_code, 200)
        self.assertIn("multipart/x-mixed-replace", res_stream.headers["content-type"])
        self.assertIn(b"--frame", res_stream.content)

        res_input = self.tc.post(
            "/api/vms/macOS-Tahoe-Dev/input",
            headers=self.headers,
            json={"type": "click", "x": 0.5, "y": 0.5, "button": 1},
        )
        self.assertEqual(res_input.status_code, 200)
        self.assertTrue(res_input.json()["ok"])

    # ------------------------------------------------------------ host info
    def test_doctor_endpoint(self):
        res = self.tc.get("/api/doctor", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for field in ("kvm_ok", "udmabuf_ok", "vulkan_ok", "qemu_ok", "all_ok"):
            self.assertIn(field, data)
        self.assertTrue(data["all_ok"])

    def test_gpus_endpoint(self):
        res = self.tc.get("/api/gpus", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        gpus = res.json()
        self.assertEqual(len(gpus), 2)
        self.assertIn("id_string", gpus[0])

    def test_stats_endpoint(self):
        res = self.tc.get("/api/stats", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for field in ("cpu_percent", "ram_percent", "ram_used_gb", "ram_total_gb"):
            self.assertIn(field, data)
        self.assertGreaterEqual(data["cpu_percent"], 0.0)

    def test_i18n_endpoint_switches_language(self):
        res = self.tc.get("/api/i18n", params={"lang": "en_US"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["current"], "en_US")
        self.assertEqual(data["translations"]["app.title"], "Reims Desktop")

    def test_i18n_rejects_bad_lang(self):
        res = self.tc.get("/api/i18n", params={"lang": "../etc"})
        self.assertEqual(res.status_code, 422)


@unittest.skipUnless(HAS_FASTAPI, "fastapi/httpx not installed")
class TestWebApiOpenMode(unittest.TestCase):
    """Without a configured password the API is open (local/dev usage)."""

    def setUp(self):
        self.app = create_app(
            mock=True, auth_manager=AuthManager(None), client=ReimsCtlClient(mock=True)
        )
        self.tc = TestClient(self.app)

    def test_open_mode_allows_access_without_token(self):
        res = self.tc.get("/api/vms")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 1)

    def test_auth_status_reports_open(self):
        res = self.tc.get("/api/auth/status")
        self.assertFalse(res.json()["auth_required"])

    def test_static_index_served_at_root(self):
        res = self.tc.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Reims", res.text)


if __name__ == "__main__":
    unittest.main()
