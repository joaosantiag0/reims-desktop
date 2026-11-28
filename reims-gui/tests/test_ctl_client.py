"""Unit tests for ReimsCtlClient and core models."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from reims_gui.core import ctl_client
from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.core.models import (
    DoctorHealth,
    GpuDevice,
    GraphicsType,
    NewVmRequest,
    VmStatus,
)


class TestReimsCtlClient(unittest.TestCase):

    def test_client_mock_initial_state(self):
        client = ReimsCtlClient(mock=True)
        self.assertTrue(client.is_available())

        vms = client.list_vms()
        self.assertGreaterEqual(len(vms), 2)
        self.assertEqual(vms[0].name, "macOS-Tahoe-Dev")
        self.assertEqual(vms[0].status, VmStatus.RUNNING)
        self.assertEqual(vms[0].graphics, GraphicsType.REIMS_VGPU)

        gpus = client.list_gpus()
        self.assertGreaterEqual(len(gpus), 1)
        self.assertTrue(any("NVIDIA" in g.name for g in gpus))

    def test_client_mock_start_stop(self):
        client = ReimsCtlClient(mock=True)

        # Stop running VM
        stopped = client.stop_vm("macOS-Tahoe-Dev")
        self.assertTrue(stopped)
        vms = client.list_vms()
        vm = next(v for v in vms if v.name == "macOS-Tahoe-Dev")
        self.assertEqual(vm.status, VmStatus.STOPPED)

        # Start VM
        started = client.start_vm("macOS-Tahoe-Dev")
        self.assertTrue(started)
        vms = client.list_vms()
        vm = next(v for v in vms if v.name == "macOS-Tahoe-Dev")
        self.assertEqual(vm.status, VmStatus.RUNNING)

    def test_client_mock_create_delete(self):
        client = ReimsCtlClient(mock=True)

        req = NewVmRequest(
            name="macOS-New-VM",
            macos_release="tahoe",
            cpus=4,
            memory_mib=8192,
            disk_size_gb=64,
            gpu=GpuDevice(name="Test GPU", vendor_id=0x10DE, device_id=0x1234),
        )

        created = client.create_vm(req)
        self.assertTrue(created)

        vms = client.list_vms()
        self.assertTrue(any(v.name == "macOS-New-VM" for v in vms))

        deleted = client.delete_vm("macOS-New-VM")
        self.assertTrue(deleted)

        vms_after = client.list_vms()
        self.assertFalse(any(v.name == "macOS-New-VM" for v in vms_after))

    def test_doctor_health_eval(self):
        health = DoctorHealth(kvm_ok=True, udmabuf_ok=True, vulkan_ok=True, qemu_ok=True)
        self.assertTrue(health.evaluate())

        health.kvm_ok = False
        self.assertFalse(health.evaluate())


class TestUpstreamBackend(unittest.TestCase):
    """Parsers and command mapping for the upstream Rust reims-ctl."""

    def test_detect_backend_by_help_marker(self):
        from reims_gui.core import ctl_client
        import unittest.mock as mock

        with mock.patch.object(ctl_client.subprocess, "run") as run:
            run.return_value = mock.Mock(
                stdout="reims-ctl\n\nCreate, boot and manage macOS VMs on QEMU with reims-vgpu",
                stderr="",
            )
            self.assertEqual(ctl_client.detect_ctl_backend("/fake/reims-ctl"), "upstream")

            run.return_value = mock.Mock(stdout="reims-desktop-ctl (Reims Desktop build 0.1.0)", stderr="")
            self.assertEqual(ctl_client.detect_ctl_backend("/fake/reims-ctl"), "desktop")

    def test_parse_upstream_doctor(self):
        output = "\n".join(
            [
                "ok  host: x86_64 Linux, runs x86_64 VMs",
                "ok  files: settings in ~/.config, VMs in ~/.local/share/reims-ctl",
                "ok  qemu: ~/.local/share/reims-ctl/qemu/current/bin/qemu-system-x86_64 (QEMU 9.0)",
                "ok  /dev/kvm: usable",
                "FAIL /dev/udmabuf: not openable",
                "ok  vulkan: NVIDIA GeForce RTX 3060 (discrete, nvidia_icd.json)",
            ]
        )
        checks, details = ctl_client.parse_upstream_doctor(output)
        self.assertTrue(checks["kvm"])
        self.assertFalse(checks["udmabuf"])
        self.assertTrue(checks["vulkan"])
        self.assertTrue(checks["qemu"])
        self.assertEqual(details["kvm"], "usable")
        self.assertEqual(details["udmabuf"], "not openable")

    def test_parse_upstream_gpus(self):
        output = "\n".join(
            [
                "By default a VM gets the only GPU, or, of several, a discrete GPU before an integrated one.",
                " 1. NVIDIA GeForce RTX 3060  [10de:2520]  /usr/share/vulkan/icd.d/nvidia_icd.json",
                " 2. AMD Radeon 780M (RADV)  [1002:15bf]  /usr/share/vulkan/icd.d/radeon_icd.json",
                "Give a VM one with: reims-ctl set NAME --gpu NUMBER",
            ]
        )
        gpus = ctl_client.parse_upstream_gpus(output)
        self.assertEqual(len(gpus), 2)
        self.assertEqual(gpus[0].name, "NVIDIA GeForce RTX 3060")
        self.assertEqual(gpus[0].vendor_id, 0x10DE)
        self.assertEqual(gpus[0].device_id, 0x2520)
        self.assertTrue(gpus[0].is_default)
        self.assertFalse(gpus[1].is_default)
        self.assertEqual(gpus[1].device_id, 0x15BF)

    def test_parse_desktop_gpus(self):
        gpus = ctl_client.parse_desktop_gpus("[10de:2520] NVIDIA GeForce RTX 3060 Mobile")
        self.assertEqual(len(gpus), 1)
        self.assertEqual(gpus[0].name, "NVIDIA GeForce RTX 3060 Mobile")
        self.assertEqual(gpus[0].vendor_id, 0x10DE)

    def test_parse_upstream_show_and_list(self):
        show = "\n".join(
            [
                "Tahoe",
                "  state         running (pid 4242)",
                "  cpus          6",
                "  memory        16G",
                "  directory     ~/.local/share/reims-ctl/vms/Tahoe",
                "  disk          disk.qcow2 (qcow2, virtio)",
                "  graphics      reims-vgpu",
                "  gpu           automatic: the only GPU, or a discrete one before an integrated one",
            ]
        )
        fields = ctl_client.parse_upstream_show(show)
        self.assertEqual(fields["cpus"], "6")
        self.assertEqual(fields["memory"], "16G")
        self.assertEqual(fields["disk"], "disk.qcow2 (qcow2, virtio)")

        info = ctl_client.vm_info_from_upstream(
            {"name": "Tahoe", "dir": "/home/u/.local/share/reims-ctl/vms/Tahoe", "state": "running", "pid": 4242},
            fields,
        )
        self.assertEqual(info.name, "Tahoe")
        self.assertEqual(info.status, VmStatus.RUNNING)
        self.assertEqual(info.cpus, 6)
        self.assertEqual(info.memory_mib, 16384)
        self.assertTrue(info.disk_path.endswith("disk.qcow2"))
        self.assertEqual(info.gpu_name, "Auto")
        self.assertEqual(info.pid, 4242)

    def test_parse_mib(self):
        self.assertEqual(ctl_client._parse_mib("16G"), 16384)
        self.assertEqual(ctl_client._parse_mib("512M"), 512)
        self.assertEqual(ctl_client._parse_mib("8192"), 8192)
        self.assertIsNone(ctl_client._parse_mib("bogus"))

    def test_build_upstream_create_cmd(self):
        req = NewVmRequest(
            name="Tahoe",
            macos_release="tahoe",
            cpus=6,
            memory_mib=16384,
            disk_size_gb=128,
        )
        cmd = ctl_client.build_upstream_create_cmd("/usr/bin/reims-ctl", req)
        self.assertEqual(
            cmd,
            [
                "/usr/bin/reims-ctl",
                "create",
                "Tahoe",
                "--cpus",
                "6",
                "--memory",
                "16G",
                "--disk-size",
                "128G",
                "--macos",
                "tahoe",
            ],
        )

        req_installer = NewVmRequest(
            name="Sequoia",
            macos_release="sequoia",
            cpus=4,
            memory_mib=8192,
            disk_size_gb=100,
            custom_installer_path="/home/u/Install macOS Sequoia.iso",
        )
        cmd2 = ctl_client.build_upstream_create_cmd("/usr/bin/reims-ctl", req_installer)
        self.assertIn("--installer", cmd2)
        self.assertIn("/home/u/Install macOS Sequoia.iso", cmd2)
        self.assertIn("--macos", cmd)  # online flow kept --macos

    def test_client_backend_attribute(self):
        client = ReimsCtlClient(mock=True)
        self.assertEqual(client.backend, "mock")


class TestVMDesktopSuspendIntegration(unittest.TestCase):
    """VM-mode helpers: suspend/resume the LXQt desktop around VM lifecycle."""

    def setUp(self):
        # Fake reims-desktop-suspend that records invocations.
        self.tmp = tempfile.TemporaryDirectory()
        fake = Path(self.tmp.name) / "fake-suspend"
        fake.write_text(
            "#!/usr/bin/env bash\n"
            "echo \"$@\" >> \"${REIMS_FAKE_LOG}\"\n"
        )
        fake.chmod(0o755)
        self.fake_bin = str(fake)
        self.log_file = Path(self.tmp.name) / "calls.log"
        os.environ["REIMS_SUSPEND_BIN"] = self.fake_bin
        os.environ["REIMS_FAKE_LOG"] = str(self.log_file)

    def tearDown(self):
        os.environ.pop("REIMS_SUSPEND_BIN", None)
        os.environ.pop("REIMS_FAKE_LOG", None)
        self.tmp.cleanup()

    def _calls(self):
        text = self.log_file.read_text() if self.log_file.exists() else ""
        return [line.strip() for line in text.splitlines() if line.strip()]

    def test_find_suspend_binary_prefers_env(self):
        self.assertEqual(ctl_client.find_suspend_binary(), self.fake_bin)

    def test_find_suspend_binary_absent(self):
        os.environ["REIMS_SUSPEND_BIN"] = "/nonexistent/reims-desktop-suspend"
        with mock.patch.object(
            ctl_client, "_SUSPEND_BINARY_CANDIDATES", ("/definitely/not/installed",)
        ):
            self.assertIsNone(ctl_client.find_suspend_binary())

    def test_suspend_and_resume_call_helper(self):
        ctl_client.suspend_desktop_for_vm()
        ctl_client.resume_desktop_after_vm()
        calls = self._calls()
        self.assertEqual(calls, ["pause", "resume"])

    def test_helpers_survive_missing_binary(self):
        os.environ["REIMS_SUSPEND_BIN"] = "/nonexistent/reims-desktop-suspend"
        with mock.patch.object(
            ctl_client, "_SUSPEND_BINARY_CANDIDATES", ("/definitely/not/installed",)
        ):
            # Must not raise when the helper binary is not installed.
            ctl_client.suspend_desktop_for_vm()
            ctl_client.resume_desktop_after_vm()

    def _make_client(self) -> ReimsCtlClient:
        # An existing file is required (mock falls back otherwise); backend
        # detection fails on it and lands on the "desktop" path.
        fake_ctl = Path(self.tmp.name) / "fake-ctl"
        fake_ctl.write_text("#!/bin/sh\nexit 0\n")
        fake_ctl.chmod(0o755)
        self.fake_ctl = str(fake_ctl)
        return ReimsCtlClient(mock=False, binary_path=str(fake_ctl))

    @staticmethod
    def _subcommands(invoked):
        """Extract the suspend/ctl subcommands (last argv element) per call,
        skipping backend-detection --help calls."""
        return [call[-1] for call in invoked if call[-1] != "--help"]

    def test_start_vm_real_backend_suspends_desktop(self):
        with mock.patch.object(ctl_client.subprocess, "run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=0, stdout="", stderr="")
            self.assertTrue(self._make_client().start_vm("Some-VM"))
            invoked = [c.args[0] for c in run_mock.call_args_list if c.args]
            self.assertIn("pause", self._subcommands(invoked))

    def test_stop_vm_real_backend_resumes_desktop(self):
        with mock.patch.object(ctl_client.subprocess, "run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=0, stdout="", stderr="")
            self.assertTrue(self._make_client().stop_vm("Some-VM"))
            invoked = [c.args[0] for c in run_mock.call_args_list if c.args]
            self.assertIn("resume", self._subcommands(invoked))

    def test_start_vm_failure_resumes_desktop(self):
        with mock.patch.object(ctl_client.subprocess, "run") as run_mock:
            # pause succeeds; the ctl start call fails
            run_mock.side_effect = [
                mock.Mock(returncode=0, stdout="", stderr=""),
                subprocess.CalledProcessError(1, ["start"]),
            ]
            client = self._make_client()
            self.assertFalse(client.start_vm("Some-VM"))
            invoked = [c.args[0] for c in run_mock.call_args_list if c.args]
            subcommands = self._subcommands(invoked)
            self.assertEqual(subcommands[0], "pause")
            self.assertEqual(subcommands[-1], "resume")

    def test_start_vm_upstream_wraps_with_suspend(self):
        """Solo mode: upstream start daemonizes QEMU, then watch-pid restores
        the desktop when the QEMU process exits."""
        with mock.patch.object(ctl_client, "detect_ctl_backend", return_value="upstream"), \
             mock.patch.object(ctl_client.subprocess, "Popen") as popen_mock:
            popen_mock.return_value = mock.Mock(wait=mock.Mock(return_value=0))
            client = self._make_client()
            self.assertTrue(client.start_vm("Some-VM"))
        self.assertGreaterEqual(popen_mock.call_count, 2)
        start_call, watch_call = popen_mock.call_args_list[-2:]
        self.assertEqual(start_call.args[0], [client.binary_path, "start", "Some-VM"])
        self.assertTrue(start_call.kwargs.get("start_new_session"))
        watch_cmd = watch_call.args[0]
        self.assertEqual(watch_cmd[0], self.fake_bin)
        self.assertEqual(watch_cmd[1], "watch-pid")
        self.assertTrue(watch_cmd[2].endswith("Some-VM/qemu.pid"))
        self.assertTrue(watch_call.kwargs.get("start_new_session"))


if __name__ == "__main__":
    unittest.main()
