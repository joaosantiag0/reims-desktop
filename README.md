# Reims Desktop

<div align="center">
  <img src="iso-builder/customization/reims-logo.png" alt="Reims Desktop Logo" width="140" />
  <h3>A Linux Distribution and Graphical Interface for Hardware-Accelerated macOS Virtualization via Vulkan</h3>
  <p>Built on Ubuntu 24.04 LTS (Noble) with an ultra-lightweight LXQt desktop, Calamares installer, and native <a href="https://github.com/steelbrain/reims-vgpu">reims-vgpu</a> integration.</p>
</div>

---

## 🚀 Overview

**Reims Desktop** is a specialized Linux operating system designed to turn any compatible x86_64 PC or laptop (Intel/AMD CPUs with NVIDIA or AMD dedicated GPUs) into a high-performance workstation for virtualizing **macOS** with near-native hardware GPU acceleration through **Vulkan** (`/dev/udmabuf` + KVM).

The system strips away bloatware, tunes the Linux kernel and graphics stack for minimal latency, and provides a turnkey experience with a graphical installer and control center available in English, Portuguese, and Spanish.

---

## 🛠️ Official Binaries (`reims-desktop*`)

All binaries in the project are standardized under the `reims-desktop*` prefix for consistent CLI and automated script usage:

| Binary | Description | Compatibility Alias |
| :--- | :--- | :--- |
| **`reims-desktop`** | Main Qt graphical application (Reims Desktop Control Center) to configure, download, and run macOS virtual machines. | `reims-gui` |
| **`reims-desktop-ctl`** | Command-line interface for host hardware diagnostics (`doctor`), GPU allocation, and VM lifecycle control. | `reims-ctl` |
| **`reims-desktop-update`** | System updater CLI to check, download, and apply OS component updates from GitHub Releases or Git master. | `reims-update` |
| **`reims-desktop-util`** | Disk image formatting and official Apple installer download automation utility. | `reims-util` |

---

## 📦 Repository Structure

```text
reims-desktop/
├── reims-gui/          # Qt6/PySide6 Graphical Interface (Reims Desktop) with i18n
├── packaging/          # Debian packaging automation (.deb files)
│   ├── templates/      # Base deb structures for reims-core, reims-gui, and reims-vgpu
│   └── scripts/        # Build scripts to compile and package all .deb artifacts
├── iso-builder/        # Live CD ISO remastering and build pipeline
│   ├── config/         # Calamares installer config, essential packages list, autostart
│   ├── customization/  # Plymouth dark themes, wallpapers, touchpad rules, welcome prompts
│   └── scripts/        # ISO build scripts (build_iso.sh, remaster_iso.sh)
└── .github/workflows/  # CI/CD: Automated test verification and GitHub Releases publishing
```

---

## 🔄 Continuous Update System

**Reims Desktop** includes an integrated update mechanism connected to this public GitHub repository:

### 1. Via Graphical Interface
- Click the **"Updates"** button on the top header of Reims Desktop.
- The application queries the GitHub Releases API in the background, displays formatted release notes, and downloads/installs the latest packages with a single click.

### 2. Via Command Line
```bash
# Check if a new release is available
reims-desktop-update --check

# Download and install the latest official release packages
reims-desktop-update

# Or perform a rolling update directly from the main Git branch
reims-desktop-update --git
```

---

## 🧪 Automated Testing

This repository enforces strict code quality and automated test coverage rules (compliant with [agents.md](agents.md)):

```bash
# Run all test suites (ISO builder, Reims Desktop GUI, and Debian Packaging)
python3 -m unittest discover -s iso-builder/tests -p "test_*.py"
PYTHONPATH=reims-gui/src python3 -m unittest discover -s reims-gui/tests -p "test_*.py"
python3 -m unittest discover -s packaging/tests -p "test_*.py"
```

---

## 💻 Local GUI Development

To run the Reims Desktop interface locally:

```bash
cd reims-gui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Launch application (with mock mode support for systems without KVM/Vulkan)
python3 -m reims_gui.main --mock
```

---

## 📄 License

Distributed under open-source licenses. Refer to individual component packaging control files and license headers for details.
