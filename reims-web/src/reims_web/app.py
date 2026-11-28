"""FastAPI application exposing the reims-ctl core layer over HTTP.

Routes (all under /api):
- POST   /api/login               exchange admin password for a bearer token
- POST   /api/logout              revoke the current token
- GET    /api/i18n                full translation dictionary for ?lang=
- GET    /api/vms                 list VMs (upstream/desktop/mock backend)
- POST   /api/vms                 start VM creation (background task) -> task id
- POST   /api/vms/{name}/start    start a VM
- POST   /api/vms/{name}/stop     stop a VM (?force=true for hard stop)
- DELETE /api/vms/{name}          delete a VM
- GET    /api/vms/{name}/console  console availability probe (noVNC groundwork)
- GET    /api/doctor              host diagnostics (KVM/udmabuf/Vulkan/QEMU)
- GET    /api/gpus                available physical GPUs
- GET    /api/stats               one-shot host CPU/RAM sample
- WS     /api/ws/stats            live host stats stream (token via ?token=)
- GET    /api/tasks/{task_id}     creation task progress polling

The service never imports PySide6: it only touches the Qt-free core modules
(`reims_gui.core.ctl_client`, `reims_gui.core.system_stats`).
"""
from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from reims_gui.core.ctl_client import ReimsCtlClient
from reims_gui.core.models import DoctorHealth, GpuDevice, NewVmRequest, VmInfo
from reims_gui.core.system_stats import SystemStatsSampler
from reims_gui.i18n.translator import Translator

from reims_web import console as vm_console
from reims_web.auth import AuthManager, read_password_from_sources

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
STATS_INTERVAL_SECONDS = 2.0


def serialize_vm(vm: VmInfo) -> Dict[str, Any]:
    return {
        "name": vm.name,
        "status": vm.status.value,
        "cpus": vm.cpus,
        "memory_mib": vm.memory_mib,
        "memory_gib": vm.memory_gib,
        "disk_path": vm.disk_path,
        "disk_size_gb": vm.disk_size_gb,
        "graphics": vm.graphics.value,
        "gpu_name": vm.gpu_name,
        "macos_version": vm.macos_version,
        "ssh_port": vm.ssh_port,
        "pid": vm.pid,
    }


def serialize_doctor(health: DoctorHealth) -> Dict[str, Any]:
    return {
        "kvm_ok": health.kvm_ok,
        "kvm_details": health.kvm_details,
        "udmabuf_ok": health.udmabuf_ok,
        "udmabuf_details": health.udmabuf_details,
        "vulkan_ok": health.vulkan_ok,
        "vulkan_details": health.vulkan_details,
        "qemu_ok": health.qemu_ok,
        "qemu_details": health.qemu_details,
        "all_ok": health.all_ok,
    }


def serialize_gpu(gpu: GpuDevice) -> Dict[str, Any]:
    return {
        "name": gpu.name,
        "vendor_id": gpu.vendor_id,
        "device_id": gpu.device_id,
        "id_string": gpu.id_string,
        "is_default": gpu.is_default,
    }


class CreateTaskRegistry:
    """Thread-safe progress registry for background VM creation jobs."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def start(self, client: ReimsCtlClient, req: NewVmRequest) -> str:
        with self._lock:
            self._counter += 1
            task_id = f"create-{self._counter}-{req.name}"
            self._tasks[task_id] = {
                "progress": 0,
                "message": "",
                "log": [],
                "done": False,
                "ok": False,
                "vm_name": req.name,
            }

        def callback(progress: int, message: str, log_line: str) -> None:
            with self._lock:
                task = self._tasks.get(task_id)
                if task is None:
                    return
                task["progress"] = progress
                task["message"] = message
                task["log"].append(log_line)
                task["log"] = task["log"][-200:]

        def worker() -> None:
            try:
                ok = client.create_vm(req, progress_callback=callback)
            except Exception as e:  # defensive: worker must never die silently
                logger.exception("create task %s failed", task_id)
                ok = False
                with self._lock:
                    task = self._tasks.get(task_id)
                    if task:
                        task["message"] = str(e)
            with self._lock:
                task = self._tasks.get(task_id)
                if task:
                    task["done"] = True
                    task["ok"] = bool(ok)

        threading.Thread(target=worker, name=f"reims-web-{task_id}", daemon=True).start()
        return task_id

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return {
                "task_id": task_id,
                "progress": task["progress"],
                "message": task["message"],
                "log": list(task["log"]),
                "done": task["done"],
                "ok": task["ok"],
                "vm_name": task["vm_name"],
            }


def create_app(
    mock: bool = False,
    auth_manager: Optional[AuthManager] = None,
    client: Optional[ReimsCtlClient] = None,
) -> FastAPI:
    auth = auth_manager or AuthManager(read_password_from_sources())
    ctl = client or ReimsCtlClient(mock=mock)
    sampler = SystemStatsSampler()
    tasks = CreateTaskRegistry()

    app = FastAPI(title="Reims Web", version="0.1.0", docs_url=None, redoc_url=None)

    def require_auth(request: Request) -> None:
        if not auth.enabled:
            return
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.startswith("Bearer ") else ""
        if not token:
            token = request.headers.get("X-Auth-Token", "").strip()
        if not auth.validate_token(token):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.post("/api/login")
    def login(body: Dict[str, Any]) -> Dict[str, Any]:
        password = str(body.get("password", ""))
        if not auth.check_password(password):
            raise HTTPException(status_code=403, detail="invalid_password")
        return {"token": auth.create_session(), "auth_required": auth.enabled}

    @app.post("/api/logout")
    def logout(request: Request) -> Dict[str, bool]:
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.startswith("Bearer ") else ""
        auth.revoke_token(token)
        return {"ok": True}

    @app.get("/api/auth/status")
    def auth_status() -> Dict[str, bool]:
        return {"auth_required": auth.enabled}

    @app.get("/api/i18n")
    def i18n(lang: str = Query(default="", pattern=r"^[a-z]{2}(_[A-Z]{2})?$")) -> Dict[str, Any]:
        translator = Translator.get_instance()
        if lang and lang in translator._translations:
            translator.set_language(lang)
        return {
            "current": translator.current_language,
            "translations": translator._translations.get(
                translator.current_language, translator._translations.get("en_US", {})
            ),
        }

    @app.get("/api/vms", dependencies=[Depends(require_auth)])
    def list_vms() -> List[Dict[str, Any]]:
        return [serialize_vm(vm) for vm in ctl.list_vms()]

    @app.post("/api/vms", dependencies=[Depends(require_auth)])
    def create_vm(body: Dict[str, Any]) -> Dict[str, str]:
        name = str(body.get("name", "")).strip()
        if not name:
            raise HTTPException(status_code=422, detail="name_required")
        req = NewVmRequest(
            name=name,
            macos_release=str(body.get("macos_release", "tahoe")),
            cpus=int(body.get("cpus", 4)),
            memory_mib=int(body.get("memory_mib", 8192)),
            disk_size_gb=int(body.get("disk_size_gb", 64)),
            gpu=_resolve_gpu(body.get("gpu_name")),
            custom_installer_path=body.get("custom_installer_path") or None,
        )
        return {"task_id": tasks.start(ctl, req)}

    def _resolve_gpu(gpu_name: Any) -> Optional[GpuDevice]:
        if not gpu_name or str(gpu_name).lower() == "auto":
            return None
        for gpu in ctl.list_gpus():
            if gpu.name == str(gpu_name):
                return gpu
        return None

    @app.get("/api/tasks/{task_id}", dependencies=[Depends(require_auth)])
    def task_status(task_id: str) -> Dict[str, Any]:
        task = tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        return task

    @app.post("/api/vms/{name}/start", dependencies=[Depends(require_auth)])
    def start_vm(name: str) -> Dict[str, bool]:
        if not ctl.start_vm(name):
            raise HTTPException(status_code=500, detail="start_failed")
        return {"ok": True}

    @app.post("/api/vms/{name}/stop", dependencies=[Depends(require_auth)])
    def stop_vm(name: str, force: bool = False) -> Dict[str, bool]:
        if not ctl.stop_vm(name, force=force):
            raise HTTPException(status_code=500, detail="stop_failed")
        return {"ok": True}

    @app.delete("/api/vms/{name}", dependencies=[Depends(require_auth)])
    def delete_vm(name: str) -> Dict[str, bool]:
        if not ctl.delete_vm(name):
            raise HTTPException(status_code=500, detail="delete_failed")
        return {"ok": True}

    @app.get("/api/vms/{name}/console", dependencies=[Depends(require_auth)])
    def console(name: str) -> Dict[str, Any]:
        if not vm_console.is_console_available(mock=mock):
            return {"available": False, "reason": "console_display_unavailable", "name": name}
        width, height = vm_console.get_screen_size(mock=mock)
        return {
            "available": True,
            "name": name,
            "stream_url": f"/api/vms/{name}/screen.mjpeg",
            "input_url": f"/api/vms/{name}/input",
            "width": width,
            "height": height,
        }

    @app.get("/api/vms/{name}/screen.mjpeg")
    async def screen_mjpeg(name: str, request: Request, token: str = "") -> StreamingResponse:
        if auth.enabled:
            auth_header = request.headers.get("Authorization", "")
            bearer = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
            if not auth.validate_token(bearer or token):
                raise HTTPException(status_code=401, detail="unauthorized")
        if not vm_console.is_console_available(mock=mock):
            raise HTTPException(status_code=503, detail="console_display_unavailable")

        async def _frame_stream():
            while True:
                if await request.is_disconnected():
                    break
                frame = await asyncio.to_thread(vm_console.capture_jpeg_frame, 65, mock)
                if frame:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                        + frame
                        + b"\r\n"
                    )
                if mock:
                    break
                await asyncio.sleep(0.08)

        return StreamingResponse(
            _frame_stream(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.post("/api/vms/{name}/input", dependencies=[Depends(require_auth)])
    async def console_input(name: str, body: Dict[str, Any]) -> Dict[str, bool]:
        ok = await asyncio.to_thread(vm_console.send_input, body, mock)
        if not ok:
            raise HTTPException(status_code=400, detail="input_failed")
        return {"ok": True}

    @app.get("/api/doctor", dependencies=[Depends(require_auth)])
    def doctor() -> Dict[str, Any]:
        return serialize_doctor(ctl.run_doctor())

    @app.get("/api/gpus", dependencies=[Depends(require_auth)])
    def gpus() -> List[Dict[str, Any]]:
        return [serialize_gpu(gpu) for gpu in ctl.list_gpus()]

    @app.get("/api/stats", dependencies=[Depends(require_auth)])
    def stats() -> Dict[str, Any]:
        sample = sampler.sample()
        if sample is None:
            raise HTTPException(status_code=503, detail="stats_unavailable")
        return {
            "cpu_percent": sample.cpu_percent,
            "ram_percent": sample.ram_percent,
            "ram_used_gb": sample.ram_used_gb,
            "ram_total_gb": sample.ram_total_gb,
        }

    @app.websocket("/api/ws/stats")
    async def ws_stats(websocket: WebSocket, token: str = "") -> None:
        if auth.enabled and not auth.validate_token(token):
            await websocket.close(code=4401)
            return
        await websocket.accept()
        try:
            while True:
                sample = sampler.sample()
                if sample is not None:
                    await websocket.send_json(
                        {
                            "cpu_percent": sample.cpu_percent,
                            "ram_percent": sample.ram_percent,
                            "ram_used_gb": sample.ram_used_gb,
                            "ram_total_gb": sample.ram_total_gb,
                        }
                    )
                await asyncio.sleep(STATS_INTERVAL_SECONDS)
        except WebSocketDisconnect:
            logger.debug("stats websocket client disconnected")
        except Exception as e:
            logger.debug("stats websocket closed: %s", e)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    # Static SPA last, so /api/* takes precedence.
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    app.state.ctl_client = ctl
    app.state.auth_manager = auth
    app.state.tasks = tasks
    return app
