"""Tests for the VM-mode desktop suspend feature (reims-desktop-suspend).

Covers:
- The suspend script itself: pause (SIGSTOP), kill mode, resume, idempotence,
  protected processes, and the status command.
- The reims-desktop-ctl wiring (start/create pause, stop/delete resume).
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SUSPEND_SCRIPT = REPO_ROOT / "packaging" / "templates" / "reims-core" / "usr" / "bin" / "reims-desktop-suspend"
CTL_SCRIPT = REPO_ROOT / "packaging" / "templates" / "reims-vgpu" / "usr" / "bin" / "reims-desktop-ctl"

# LXQt/desktop components the VM-mode targets by default.
DEFAULT_TARGETS = [
    "lxqt-panel", "pcmanfm-qt", "lxqt-notificationd", "lxqt-runner",
    "lxqt-globalkeys", "lxqt-globalkeysd", "lxqt-powermanagement",
    "lxqt-policykit-agent", "qlipper", "nm-tray", "lubuntu-update",
]

# Processes that must NEVER be touched (window manager/display/GUI/VM).
PROTECTED = ["Xorg", "sddm", "openbox", "kwin", "sshd", "qemu", "reims-desktop"]


def run_suspend(args: list[str], env_overrides: dict[str, str] | None = None, state_dir: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["REIMS_SUSPEND_TARGETS"] = "sleep"  # test-only target we can spawn
    if state_dir:
        env["REIMS_STATE_DIR"] = state_dir
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [str(SUSPEND_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def proc_stat(pid: int) -> str:
    """First character of ps stat/state: 'T' stopped, 'S'/'R' alive/running."""
    out = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)],
        capture_output=True, text=True,
    )
    return (out.stdout or "").strip()[:1]


class TestDesktopSuspendScript(unittest.TestCase):

    def test_script_syntax(self):
        res = subprocess.run(["bash", "-n", str(SUSPEND_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"bash -n failed: {res.stderr}")

    def test_ctl_script_syntax(self):
        res = subprocess.run(["bash", "-n", str(CTL_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"bash -n failed: {res.stderr}")

    def test_pause_stops_process_and_resume_continues_it(self):
        proc = subprocess.Popen(["sleep", "300"])
        try:
            with tempfile.TemporaryDirectory() as state_dir:
                res = run_suspend(["pause"], state_dir=state_dir)
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertIn("pausado", res.stdout)

                # Give the kernel a moment to reflect the stopped state.
                # Deadline is generous: under heavy CI/load (e.g. parallel apt
                # repo builds) the SIGSTOP delivery can lag behind.
                deadline = time.time() + 30
                while time.time() < deadline and proc_stat(proc.pid) != "T":
                    time.sleep(0.1)
                self.assertEqual(proc_stat(proc.pid), "T", "process was not SIGSTOPped")

                # status reflects the paused state
                res_status = run_suspend(["status"], state_dir=state_dir)
                self.assertIn("paused (mode=pause)", res_status.stdout)

                # pause again must be an idempotent no-op
                res_again = run_suspend(["pause"], state_dir=state_dir)
                self.assertEqual(res_again.returncode, 0)
                self.assertIn("já suspenso", res_again.stdout)

                res_resume = run_suspend(["resume"], state_dir=state_dir)
                self.assertEqual(res_resume.returncode, 0, res_resume.stderr)
                self.assertIn("restaurado", res_resume.stdout)

                deadline = time.time() + 30
                while time.time() < deadline and proc_stat(proc.pid) == "T":
                    time.sleep(0.1)
                self.assertNotEqual(proc_stat(proc.pid), "T", "process was not SIGCONTed")

                # state file cleared
                self.assertFalse((Path(state_dir) / "reims-vm-desktop.state").exists())

                # status back to running
                res_status2 = run_suspend(["status"], state_dir=state_dir)
                self.assertIn("running", res_status2.stdout)
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    def test_kill_mode_terminates_process(self):
        proc = subprocess.Popen(["sleep", "300"])
        try:
            with tempfile.TemporaryDirectory() as state_dir:
                res = run_suspend(["pause", "--kill"], state_dir=state_dir)
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertIn("kill", res.stdout)

                proc.wait(timeout=10)
                self.assertNotEqual(proc.poll(), None, "process survived kill mode")

                # state file records the killed target for the resume relaunch
                state_text = (Path(state_dir) / "reims-vm-desktop.state").read_text()
                self.assertIn('mode="kill"', state_text)
                self.assertIn('killed="sleep "', state_text)

                res_resume = run_suspend(["resume"], state_dir=state_dir)
                self.assertEqual(res_resume.returncode, 0, res_resume.stderr)
                self.assertFalse((Path(state_dir) / "reims-vm-desktop.state").exists())
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

    def test_off_mode_is_noop(self):
        with tempfile.TemporaryDirectory() as state_dir:
            res = run_suspend(["pause"], env_overrides={"REIMS_VM_MODE": "off"}, state_dir=state_dir)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("desativado", res.stdout)
            self.assertFalse((Path(state_dir) / "reims-vm-desktop.state").exists())

    def test_resume_without_state_is_noop(self):
        with tempfile.TemporaryDirectory() as state_dir:
            res = run_suspend(["resume"], state_dir=state_dir)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("Nenhum desktop suspenso", res.stdout)

    def test_default_targets_and_protected_processes(self):
        script = SUSPEND_SCRIPT.read_text()
        for target in DEFAULT_TARGETS:
            self.assertIn(target, script, f"missing default target {target}")
        # Protected processes must never appear as signals/kill targets.
        for protected in PROTECTED:
            self.assertNotIn(
                f"kill -{protected}", script,
                f"protected process {protected} must not be signalled",
            )
        self.assertNotIn('"Xorg"', script.replace("NUNCA", ""))
        # Explicit guard: the target list line must not contain protected names.
        targets_line = next(
            line for line in script.splitlines() if line.startswith("DEFAULT_TARGETS=")
        )
        for protected in PROTECTED:
            self.assertNotIn(protected, targets_line)


CRITICAL_SYSTEM_UNITS = [
    "dbus.service", "systemd-logind.service", "systemd-udevd.service",
    "systemd-resolved.service", "systemd-journald.service",
    "NetworkManager.service", "wpa_supplicant.service", "ssh.service",
    "sddm.service", "polkit.service",
]


class TestVMServicePhase(unittest.TestCase):
    """Systemd phase: stop heavy daemons on pause, restart them on resume."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tmp.name)
        self.ctl_log = self.state_dir / "systemctl.log"
        self.fake_ctl = self.state_dir / "fake-systemctl"
        self.fake_ctl.write_text(
            "#!/usr/bin/env bash\n"
            'echo "$@" >> "$FAKE_CTL_LOG"\n'
            'if [[ "$1" == "is-active" ]]; then\n'
            '  unit="${!#}"\n'
            '  for u in ${FAKE_ACTIVE_UNITS:-}; do\n'
            '    [[ "$u" == "$unit" ]] && exit 0\n'
            "  done\n"
            "  exit 3\n"
            "fi\n"
            "exit 0\n"
        )
        self.fake_ctl.chmod(0o755)
        self.ctl_log.touch()

    def tearDown(self):
        self.tmp.cleanup()

    def run_pause(self, extra_env=None):
        env = {
            "REIMS_SUSPEND_TARGETS": "sleep",
            "REIMS_STATE_DIR": str(self.state_dir),
            "REIMS_SYSTEMCTL_BIN": str(self.fake_ctl),
            "REIMS_PRIV_MOCK": "1",
            "FAKE_ACTIVE_UNITS": os.environ.pop("FAKE_ACTIVE_UNITS", ""),
            "FAKE_CTL_LOG": str(self.ctl_log),
        }
        os.environ.pop("FAKE_ACTIVE_UNITS", None)
        if extra_env:
            env.update(extra_env)
        return self._run(["pause"], env)

    def run_resume(self, extra_env=None):
        env = {
            "REIMS_SUSPEND_TARGETS": "sleep",
            "REIMS_STATE_DIR": str(self.state_dir),
            "REIMS_SYSTEMCTL_BIN": str(self.fake_ctl),
            "REIMS_PRIV_MOCK": "1",
            "FAKE_ACTIVE_UNITS": "",
            "FAKE_CTL_LOG": str(self.ctl_log),
        }
        if extra_env:
            env.update(extra_env)
        return self._run(["resume"], env)

    def _run(self, args, env):
        full_env = dict(os.environ)
        for key in ("XDG_RUNTIME_DIR",):
            full_env.pop(key, None)
        full_env.update(env)
        return subprocess.run(
            [str(SUSPEND_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=full_env,
            timeout=60,
        )

    def _ctl_calls(self):
        text = self.ctl_log.read_text() if self.ctl_log.exists() else ""
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _state(self):
        state_file = self.state_dir / "reims-vm-desktop.state"
        return state_file.read_text() if state_file.exists() else ""

    def _state_var(self, name):
        """De-quoted value of a `name="..."` line in the state file."""
        for line in self._state().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip('"')
        return ""

    def test_pause_stops_active_services_and_resume_restarts_them(self):
        res = self.run_pause({"FAKE_ACTIVE_UNITS": "snapd.socket snapd bluetooth.service"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Serviços parados", res.stdout)
        self.assertIn("snapd snapd.socket", res.stdout)

        # Only the ACTIVE units were stopped and recorded.
        self.assertIn("stop snapd.socket", " ".join(self._ctl_calls()))
        self.assertIn("stop bluetooth.service", " ".join(self._ctl_calls()))
        state = self._state()
        self.assertEqual(self._state_var("services"), "snapd snapd.socket bluetooth.service ")
        # snapd listed twice (service + socket), stopped in that order
        self.assertEqual(
            [c for c in self._ctl_calls() if c.startswith("stop snapd")],
            ["stop snapd", "stop snapd.socket"],
        )

        res_resume = self.run_resume()
        self.assertEqual(res_resume.returncode, 0, res_resume.stderr)
        self.assertIn("Serviços do sistema restaurados", res_resume.stdout)
        self.assertIn("start snapd.socket", " ".join(self._ctl_calls()))
        self.assertIn("start bluetooth.service", " ".join(self._ctl_calls()))
        self.assertNotIn("start cups.service", " ".join(self._ctl_calls()))

    def test_inactive_services_are_not_stopped_nor_recorded(self):
        res = self.run_pause({"FAKE_ACTIVE_UNITS": ""})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self._state_var("services"), "")

    def test_services_disabled_by_env(self):
        res = self.run_pause({"REIMS_VM_SERVICES": "off", "FAKE_ACTIVE_UNITS": "snapd"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("stop snapd", " ".join(self._ctl_calls()))
        self.assertEqual(self._state_var("services"), "")

    def test_services_skipped_without_privileges(self):
        res = self.run_pause({
            "REIMS_PRIV_MOCK": "0",
            "REIMS_SUDO_BIN": "/usr/bin/false",
            "FAKE_ACTIVE_UNITS": "snapd",
        })
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("fase de serviços ignorada", res.stderr)
        self.assertNotIn("stop snapd", " ".join(self._ctl_calls()))
        self.assertEqual(self._state_var("services"), "")

    def test_critical_units_never_in_default_service_list(self):
        script = SUSPEND_SCRIPT.read_text()
        services_line = next(
            line for line in script.splitlines()
            if line.startswith("DEFAULT_SYSTEM_SERVICES=")
        )
        for unit in CRITICAL_SYSTEM_UNITS:
            self.assertNotIn(unit, services_line, f"critical unit {unit} must never be stopped")

    def test_as_root_helper_rejects_unlisted_units(self):
        """--as-root is the sudoers entry point: only internal units allowed."""
        env = dict(os.environ)
        env.update({
            "REIMS_SUSPEND_TARGETS": "sleep",
            "REIMS_STATE_DIR": str(Path(self.tmp.name)),
            "REIMS_SYSTEMCTL_BIN": str(self.fake_ctl),
            "FAKE_ACTIVE_UNITS": "",
            "FAKE_CTL_LOG": str(self.ctl_log),
        })
        full_env = {k: v for k, v in os.environ.items() if k != "XDG_RUNTIME_DIR"}
        full_env.update(env)
        res = subprocess.run(
            [str(SUSPEND_SCRIPT), "--as-root", "stop", "dbus.service"],
            capture_output=True, text=True, env=full_env, timeout=60,
        )
        self.assertEqual(res.returncode, 3, res.stderr)
        self.assertIn("não autorizada", res.stderr)
        # valid unit from the internal list is dispatched to systemctl
        res_ok = subprocess.run(
            [str(SUSPEND_SCRIPT), "--as-root", "stop", "snapd"],
            capture_output=True, text=True, env=full_env, timeout=60,
        )
        self.assertEqual(res_ok.returncode, 0, res_ok.stderr)
        self.assertIn("stop snapd", self._ctl_calls_text())
        # invalid action rejected
        res_bad = subprocess.run(
            [str(SUSPEND_SCRIPT), "--as-root", "disable", "snapd"],
            capture_output=True, text=True, env=full_env, timeout=60,
        )
        self.assertEqual(res_bad.returncode, 2)

    def _ctl_calls_text(self):
        return " ".join(self._ctl_calls())

    def test_service_units_come_before_their_sockets(self):
        """Stopping X.socket first takes down X.service (Requires=) without
        recording it — verified live on snapd. X must precede X.socket."""
        script = SUSPEND_SCRIPT.read_text()
        for list_name in ("DEFAULT_SYSTEM_SERVICES=", "DEFAULT_USER_SERVICES="):
            line = next(
                l for l in script.splitlines() if l.startswith(list_name)
            )
            names = line.split("=", 1)[1].split()
            for name in names:
                if name.endswith(".socket"):
                    bare = name[:-len(".socket")]
                    if bare in names:
                        self.assertLess(
                            names.index(bare), names.index(name),
                            f"{bare} must be listed before {name} ({list_name})",
                        )

    def test_pipewire_is_not_stopped_by_default(self):
        """QEMU uses -audiodev pipewire,id=snd0; stopping PipeWire crashes VM boot."""
        script = SUSPEND_SCRIPT.read_text()
        line = next(
            l for l in script.splitlines() if l.startswith("DEFAULT_USER_SERVICES=")
        )
        for audio_unit in ("pipewire", "pipewire-pulse", "wireplumber", "pulseaudio"):
            self.assertNotIn(audio_unit, line)

    def test_user_services_phase_skipped_without_runtime_dir(self):
        res = self.run_pause({"FAKE_ACTIVE_UNITS": "snapd"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("--user", " ".join(self._ctl_calls()))

    def test_ctl_wires_suspend_on_start_and_resume_on_stop(self):
        ctl = CTL_SCRIPT.read_text()
        self.assertIn("reims-desktop-suspend", ctl)
        self.assertIn("vm_desktop_suspend", ctl)
        self.assertIn("vm_desktop_resume", ctl)
        # start path calls suspend before launching qemu
        start_idx = ctl.index("    start)")
        create_idx = ctl.index("create)")
        self.assertGreater(ctl.index("vm_desktop_suspend", start_idx), start_idx)
        self.assertGreater(ctl.index("vm_desktop_suspend", create_idx), create_idx)
        # stop and delete paths call resume
        stop_idx = ctl.index("    stop)")
        delete_idx = ctl.index("    delete)")
        self.assertGreater(ctl.index("vm_desktop_resume", stop_idx), stop_idx)
        self.assertGreater(ctl.index("vm_desktop_resume", delete_idx), delete_idx)
        # REIMS_VM_MODE passthrough documented in usage
        self.assertIn("REIMS_VM_MODE", ctl)


class TestVMWrapSoloMode(unittest.TestCase):
    """wrap: runs a command as the only app on screen (pause -> cmd -> resume)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = str(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _env(self):
        env = dict(os.environ)
        env.update({
            # Target that never matches, so the wrapped command itself is never
            # SIGSTOPped by the desktop-suspension phase.
            "REIMS_SUSPEND_TARGETS": "definitely-not-a-real-process-xyz",
            "REIMS_STATE_DIR": self.state_dir,
        })
        return env

    def _run(self, args):
        return subprocess.run(
            [str(SUSPEND_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=self._env(),
            timeout=60,
        )

    def test_wrap_pauses_runs_command_and_restores(self):
        state_file = Path(self.state_dir) / "reims-vm-desktop.state"
        # The wrapped command must see the desktop suspended while it runs.
        res = self._run([
            "wrap", "sh", "-c",
            f'test -s "{state_file}" && echo SOLO-PAUSED && echo SOLO-RUNNING',
        ])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("SOLO-PAUSED", res.stdout)
        self.assertIn("SOLO-RUNNING", res.stdout)
        # Desktop restored (state cleared) once the command exited.
        self.assertFalse(state_file.exists())
        self.assertIn("Desktop restaurado", res.stdout)

    def test_wrap_preserves_exit_code(self):
        res = self._run(["wrap", "sh", "-c", "exit 42"])
        self.assertEqual(res.returncode, 42)
        self.assertFalse((Path(self.state_dir) / "reims-vm-desktop.state").exists())

    def test_wrap_requires_command(self):
        res = self._run(["wrap"])
        self.assertEqual(res.returncode, 2)


class TestCTLStartScriptSoloMode(unittest.TestCase):
    """The bash ctl's generated start.sh: fullscreen qemu + supervisor."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        env = dict(os.environ, HOME=cls.tmp.name)
        subprocess.run(
            [str(CTL_SCRIPT), "create", "Solo-VM", "--cpus=2", "--memory-mib=4096",
             "--disk-gb=10", "--macos=tahoe"],
            capture_output=True, text=True, env=env, check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_start_sh_is_fullscreen_supervisor(self):
        start_sh = Path(self.tmp.name) / ".local/share/reims-ctl/vms/Solo-VM/start.sh"
        content = start_sh.read_text()
        self.assertIn("--full-screen", content, "QEMU must start fullscreen (solo mode)")
        self.assertIn("reims-desktop-suspend", content)
        self.assertIn('SUSPEND_BIN', content)
        # pause before qemu, supervisor wait, resume after
        self.assertIn('"${SUSPEND_BIN}" pause', content)
        self.assertIn("wait \"${QEMU_PID}\"", content)
        self.assertIn('"${SUSPEND_BIN}" resume', content)
        # pid.txt must contain the real qemu pid, not the launcher's
        self.assertIn('echo "${QEMU_PID}" > "${VM_DIR}/pid.txt"', content)

    def test_watch_pid_resumes_when_process_exits(self):
        proc = subprocess.Popen(["python3", "-c", "import time; time.sleep(1)"])
        try:
            with tempfile.TemporaryDirectory() as state_dir:
                pidfile = Path(state_dir) / "qemu.pid"
                pidfile.write_text(str(proc.pid))
                res_pause = run_suspend(["pause"], state_dir=state_dir)
                self.assertEqual(res_pause.returncode, 0)
                proc.wait(timeout=10)
                res_watch = run_suspend(["watch-pid", str(pidfile)], state_dir=state_dir)
                self.assertEqual(res_watch.returncode, 0, res_watch.stderr)
                self.assertIn("restaurado", res_watch.stdout)
                self.assertFalse((Path(state_dir) / "reims-vm-desktop.state").exists())
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
