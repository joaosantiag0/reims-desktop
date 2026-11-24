# Reims Desktop

<div align="center">
  <img src="iso-builder/customization/reims-logo.png" alt="Reims Desktop Logo" width="140" />
  <h3>A Linux Distribution and Graphical Interface for Hardware-Accelerated macOS Virtualization via Vulkan</h3>
  <p>Built on Ubuntu 24.04 LTS (Noble) with an ultra-lightweight LXQt desktop, Calamares installer, and native <a href="https://github.com/steelbrain/reims-vgpu">reims-vgpu</a> integration.</p>
  <p><strong>Independent Unofficial Community Project</strong> &bull; No connection to Apple Inc. or upstream Reims &bull; Zero Apple binaries bundled.</p>
</div>

---

> [!CAUTION]
> ### ⚖️ Legal Disclaimers & Compliance
>
> 1. **No Connection to Apple Inc. or Reims:**  
>    **Reims Desktop is an independent, community-driven open-source project.** It has **no connection, affiliation, sponsorship, or endorsement with Apple Inc. or the upstream Reims (`steelbrain/reims-vgpu`) project or authors.** macOS, OS X, Mac, and Apple are registered trademarks of Apple Inc.
>
> 2. **Zero Apple Binaries Distributed (No Apple Code Bundled):**  
>    **This repository, ISO images, and Debian packages contain NO Apple proprietary binaries, bootroms, kernels, drivers, or copyrighted software.**  
>    Reims Desktop only provides standard open-source Linux software (KVM, QEMU, LXQt, and open-source helper utilities). All macOS recovery packages or installation media must be downloaded directly by the end user from Apple's public servers in accordance with Apple's software license agreements.

---

## 🚀 Overview

**Reims Desktop** is a specialized Linux operating system designed to turn any compatible x86_64 PC or laptop (Intel/AMD CPUs with NVIDIA or AMD dedicated GPUs) into a high-performance workstation for virtualizing **macOS** with near-native hardware GPU acceleration through **Vulkan** (`/dev/udmabuf` + KVM).

The system strips away bloatware, tunes the Linux kernel and graphics stack for minimal latency, and provides a turnkey experience with a graphical installer and control center available in English, Portuguese, and Spanish.

---

## 🛠️ Project Binaries (`reims-desktop*`)

All binaries in the project are standardized under the `reims-desktop*` prefix for consistent CLI and automated script usage:

| Binary | Description | Compatibility Alias |
| :--- | :--- | :--- |
| **`reims-desktop`** | Main Qt graphical application (Reims Desktop Control Center) to configure, download, and run macOS virtual machines. | `reims-gui` |
| **`reims-desktop-ctl`** | Command-line interface for host hardware diagnostics (`doctor`), GPU allocation, and VM lifecycle control. | `reims-ctl` |
| **`reims-desktop-update`** | System updater CLI to check, download, and apply OS component updates from GitHub Releases or Git master. | `reims-update` |
| **`reims-desktop-util`** | Disk image formatting and Apple recovery installer download automation utility. | `reims-util` |

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

## 🌿 Branching Strategy

This repository maintains two primary branches:
- **`main` (Stable):** Production-ready code, official GitHub Releases (`v*`), and release ISO images.
- **`development` (Rolling/Active):** Ongoing feature development, rapid testing, and rolling updates.

---

## 🔄 Continuous Update System

**Reims Desktop** provides accessible updates for both the desktop environment/programs and the underlying Linux operating system across multiple workflows:

### 1. Via Graphical Interface (Control Center)
- Click the **"Updates"** button on the top header of Reims Desktop (`reims-desktop`).
- The application queries the GitHub Releases API in the background, displays formatted release notes, and downloads/installs the latest packages with a single click.
- An optional checkbox allows updating the base operating system (Ubuntu security patches & drivers) simultaneously.

### 2. Via Command Line (CLI - Official Releases)
```bash
# Check if a new release is available
reims-desktop-update --check

# Download and install the latest release packages (.deb)
reims-desktop-update

# Update only Ubuntu distribution packages & drivers (APT)
reims-desktop-update --system

# Perform a full update of Reims Desktop + Ubuntu OS packages
reims-desktop-update --full
```

### 3. Via Git Rolling Update (Development)
```bash
# Perform a rolling update directly from the stable main branch
reims-desktop-update --git

# Or pull and compile the cutting-edge development branch
reims-desktop-update --git --branch development
```

### 4. Via Native Ubuntu APT Repository
Reims Desktop packages are published directly to an official APT repository hosted on GitHub Pages:
```bash
# Repository is pre-configured on Reims Desktop (/etc/apt/sources.list.d/reims.list)
sudo apt update && sudo apt upgrade
```

---

## ⚡ High-Speed Hardware Sync & Direct Boot

For rapid development cycles and testing on physical machines or target laptops, see the [FAST_TRANSFER_GUIDE.md](FAST_TRANSFER_GUIDE.md):
- **Instant Memory Streaming:** Sync full code and packaging to the target host in ~2 seconds via piped SSH streams.
- **Direct Disk Remastering:** Update live installation media and kernel images directly on internal storage (`/dev/sda1` / `/mnt/installer/`) without writing to USB drives.
- **Raw High-Throughput Streams:** Transfer large ISO images at wire speed using `nc` or local HTTP streaming.

---

## 🧪 Automated Testing

This repository enforces strict code quality and automated test coverage rules (compliant with [agents.md](agents.md)):

```bash
# Run all test suites (Core & APT repo, ISO builder, Reims Desktop GUI, and Debian Packaging)
python3 -m unittest discover -s tests -p "test_*.py"
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

## 📄 License, Trademarks & Compliance

* **Open-Source Licensing:** Distributed under open-source licenses (GPL/MIT). Refer to individual component packaging control files and license headers for details.
* **No Apple Proprietary Code:** This repository, generated `.deb` packages, and ISO builds do **not** host, distribute, or bundle any Apple intellectual property, proprietary macOS binaries, firmware, or recovery files.
* **Trademarks & Affiliation:** macOS, OS X, and Apple are registered trademarks of Apple Inc. Reims Desktop is an independent open-source community effort and has no affiliation, connection, or endorsement with Apple Inc. or the upstream Reims repository.
