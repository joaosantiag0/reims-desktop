# Reims Desktop Control Center (`reims-desktop`)

Native Qt graphical user interface for managing macOS virtual machines with hardware-accelerated graphics via [reims-vgpu](https://github.com/steelbrain/reims-vgpu) and the `reims-desktop-ctl` utility.

Engineered for **Reims Desktop** (Ubuntu 24.04 LTS / LXQt base), but compatible with any modern Linux distribution supporting KVM and Vulkan.

> [!NOTE]
> **Unofficial Community Project:**  
> This application is an independent, unofficial open-source utility and is not affiliated with, sponsored by, or endorsed by Apple Inc. or upstream authors.

---

## Features

* **Virtual Machine Manager:** Real-time visual status monitoring (Running, Stopped, Error), vCPUs, RAM, and assigned vGPU.
* **New VM Wizard:**
  * macOS release selector (macOS 26 Tahoe, macOS 15 Sequoia, macOS 14 Sonoma).
  * Fine-grained resource allocation for vCPUs, RAM, and disk storage with intuitive sliders.
  * Physical GPU selection for Vulkan acceleration.
  * Direct downloads of Apple recovery installers via `reims-desktop-util`.
* **Host Health Diagnostics (Doctor Panel):**
  * Live verification of KVM availability (`/dev/kvm`), `/dev/udmabuf` kernel module, Vulkan drivers (NVIDIA/AMD/Intel), and compatible QEMU binary.
* **Quick Actions:**
  * Start VM (launches dedicated window with Vulkan acceleration).
  * Terminal view (`reims-desktop-ctl view`).
  * Graceful shutdown (ACPI) or force stop.
  * Machine configuration adjustments (`reims-desktop-ctl set`).
* **Internationalization (i18n):**
  * Full native support for **English (en_US)**, **Portuguese (pt_BR)**, and **Spanish (es_ES)**, with automatic system language detection and dynamic switching in the header.
* **Mock / Demo Mode:**
  * Allows UI execution, development, and unit testing on systems without KVM or Vulkan hardware (`reims-desktop --mock`).

---

## Installation & Running

### Requirements
* Python >= 3.10
* `PySide6` (Qt 6)
* `reims-desktop-ctl` and `qemu-reims-vgpu` installed on host (or pass `--mock` flag).

### Virtual Environment Setup

```bash
cd reims-gui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run application
python3 -m reims_gui.main

# Run in mock mode (simulated host for UI testing)
python3 -m reims_gui.main --mock
```

---

## Source Tree Structure

```text
reims-gui/
├── src/reims_gui/
│   ├── main.py              # Application entry point
│   ├── core/
│   │   ├── models.py        # Core data models (VmInfo, GpuDevice, DoctorHealth)
│   │   ├── ctl_client.py    # Async client wrapper for reims-desktop-ctl (+ Mock mode)
│   │   └── updater.py       # GitHub Releases & Git updater engine
│   ├── i18n/
│   │   ├── translator.py    # Translation manager with dynamic language switching
│   │   └── locales/         # Translation dictionaries (pt_BR, en_US, es_ES)
│   └── ui/
│       ├── main_window.py   # Main window
│       ├── theme.py         # Modern Qt6 dark theme stylesheet
│       ├── widgets/         # UI components: vm_card, doctor_bar, header
│       └── dialogs/         # New VM wizard and update dialog
└── tests/                   # Automated unit tests for client, updater, and i18n
```
