"""Unit tests for ReimsCtlClient and core models."""

import unittest
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


if __name__ == "__main__":
    unittest.main()
