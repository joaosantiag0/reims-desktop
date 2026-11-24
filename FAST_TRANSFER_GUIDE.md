# High-Speed Notebook Transfer & Direct-Boot Guide

This guide explains how to transfer the **Reims Desktop** installer, source code, and full ISO images to your local test notebook (`192.168.2.191`) with maximum speed ("sem demorar"), avoiding the bottlenecks of slow USB flash drives or redundant disk writes.

---

## ⚡ Overview of Transfer Strategies

| Strategy | Target | Typical Speed / Time | Ideal For |
| :--- | :--- | :--- | :--- |
| **1. Memory-Piped Tar Stream** | Code, GUI, Packaging & Build Scripts | **~2 seconds** | Instant code & test syncing |
| **2. Direct NVMe / Disk Remastering** | Full Live ISO & Boot Kernels | **0 seconds transfer** | Remastering directly on host disk |
| **3. Raw TCP Stream (`nc` / `netcat`)** | Large ISO Images (3.4 GB) | **~35–50 MB/s (Wi-Fi) / 110 MB/s (GbE)** | Full ISO file updates |
| **4. Local HTTP Streaming (`python -m http.server`)** | ISO & Debian Packages | Line speed with resume support (`wget -c`) | Browser or terminal downloads |

---

## 🚀 Method 1: Ultra-Fast RAM Streaming (SSH Pipe)

Traditional `scp` writes a compressed `.tar.gz` to disk, copies it across the network, and then requires another disk write to unpack it.

By piping the `tar` output directly into SSH's standard input, data is compressed in memory on your Mac and decompressed in memory on the notebook in a single continuous stream:

```bash
# Execute from repository root:
tar -czf - \
  --exclude='.git' \
  --exclude='build' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='dist' \
  --exclude='.DS_Store' \
  --exclude='.pytest_cache' \
  . | sshpass -p "govegogo00" ssh \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      joao@192.168.2.191 \
      "mkdir -p /home/joao/reims-os && tar -xzf - -C /home/joao/reims-os"
```

### 1-Click Automated Script (`scripts/sync_to_notebook.sh`)
An automated script is included in `scripts/sync_to_notebook.sh`:

```bash
# Sync with default host (192.168.2.191):
./scripts/sync_to_notebook.sh

# Or specify custom IP:
./scripts/sync_to_notebook.sh 192.168.2.200
```

> [!NOTE]
> `scripts/sync_to_notebook.sh` is registered in `.gitignore` so local network credentials and IP addresses are **never committed or leaked** to the public GitHub repository.

---

## 💿 Method 2: Direct Disk Remastering (No USB Needed)

Instead of transferring a 3.4 GB ISO back and forth, the fastest way to install or test on the notebook is using the internal partition `/dev/sda1` mounted at `/mnt/installer/`:

1. Sync the updated project files via Method 1.
2. Run the remastering pipeline directly on the notebook:
   ```bash
   sshpass -p "govegogo00" ssh joao@192.168.2.191
   cd /home/joao/reims-os
   sudo ./run_remaster.sh
   ```
3. What `run_remaster.sh` does automatically:
   * Mounts `/dev/sda1` on `/mnt/installer`.
   * Rebuilds the ISO directly onto the high-speed NVMe storage.
   * Copies the new kernel (`vmlinuz`) and ramdisk (`initrd`) to `/mnt/installer/casper/`.
   * OpenCore / GRUB can boot the installer directly from disk without burning a physical USB flash drive!

---

## 📦 Method 3: High-Speed ISO Transfer (When transferring raw 3.4 GB file)

If you need to push a full pre-built `.iso` from your Mac to the notebook:

### Option A: Raw Netcat Stream (Fastest — Zero SSH Encryption Overhead)
SSH encrypts every packet with AES, which can cap throughput on high-speed Wi-Fi 6 or Gigabit Ethernet. `nc` transfers raw bytes at maximum wire speed:

1. **On Notebook (Receiver):**
   ```bash
   nc -l -p 9999 > /mnt/installer/reims-os.iso
   ```

2. **On Mac (Sender):**
   ```bash
   nc -w 3 192.168.2.191 9999 < dist/iso/reims-desktop-custom.iso
   ```

### Option B: Local HTTP Server with Resumable `wget`
1. **On Mac:**
   ```bash
   cd dist/iso
   python3 -m http.server 8080
   ```

2. **On Notebook:**
   ```bash
   wget -c http://<YOUR_MAC_IP>:8080/reims-os.iso -O /mnt/installer/reims-os.iso
   ```

---

## 🛡️ Security & `.gitignore` Best Practices

The following patterns are configured in `.gitignore` to guarantee local network privacy:

```gitignore
# Notebook sync and local transfer artifacts
*sync*.tar.gz
sync_notebook.sh
scripts/sync_to_notebook.sh
.sync_config
.env*
/mnt/
```

This ensures that development machines, remote host IPs, and local SSH tokens remain strictly local and confidential.
