#!/usr/bin/env python3
"""Script to generate a static Debian/Ubuntu APT repository for GitHub Pages.

Usage:
  python3 scripts/generate_apt_repo.py --deb-dir dist --out-dir repo
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import io
import os
import shutil
import tarfile
from pathlib import Path
from typing import Dict, List, Tuple


def extract_control_info(deb_path: Path) -> Tuple[Dict[str, str], int, str, str]:
    """Extracts control fields, file size, SHA256 and MD5 from a .deb package."""
    content = deb_path.read_bytes()
    size = len(content)
    sha256 = hashlib.sha256(content).hexdigest()
    md5 = hashlib.md5(content).hexdigest()

    control_text = ""
    with io.BytesIO(content) as f:
        magic = f.read(8)
        if magic != b"!<arch>\n":
            raise ValueError(f"{deb_path.name} is not a valid ar archive")

        while True:
            hdr = f.read(60)
            if not hdr or len(hdr) < 60:
                break
            name = hdr[0:16].decode("ascii", errors="replace").strip().rstrip("/")
            member_size = int(hdr[48:58].decode("ascii", errors="replace").strip())
            member_data = f.read(member_size)
            if member_size % 2 != 0:
                f.read(1)

            if "control.tar" in name:
                with tarfile.open(fileobj=io.BytesIO(member_data), mode="r:*") as tar:
                    for m in tar.getmembers():
                        if m.name in ("control", "./control") or m.name.endswith("/control"):
                            f_ctrl = tar.extractfile(m)
                            if f_ctrl:
                                control_text = f_ctrl.read().decode("utf-8", errors="replace")
                                break

    fields: Dict[str, str] = {}
    current_key = ""
    for line in control_text.splitlines():
        if line.startswith(" ") or line.startswith("\t"):
            if current_key in fields:
                fields[current_key] += "\n" + line
        elif ":" in line:
            key, val = line.split(":", 1)
            current_key = key.strip()
            fields[current_key] = val.strip()

    return fields, size, sha256, md5


def generate_apt_repo(
    deb_dir: Path,
    out_dir: Path,
    suite: str = "noble",
    component: str = "main",
    origin: str = "Reims Desktop",
    label: str = "Reims Desktop",
    description: str = "Official Reims Desktop APT Repository",
) -> None:
    deb_files = sorted(deb_dir.glob("*.deb"))
    if not deb_files:
        raise FileNotFoundError(f"No .deb packages found in {deb_dir}")

    # Prepare directories
    pool_dir = out_dir / "pool" / component
    dists_dir = out_dir / "dists" / suite
    arch_amd64_dir = dists_dir / component / "binary-amd64"
    arch_all_dir = dists_dir / component / "binary-all"

    for d in [pool_dir, arch_amd64_dir, arch_all_dir]:
        d.mkdir(parents=True, exist_ok=True)

    packages_amd64: List[str] = []
    packages_all: List[str] = []

    for deb_path in deb_files:
        fields, size, sha256, md5 = extract_control_info(deb_path)
        dest_deb = pool_dir / deb_path.name
        shutil.copy2(deb_path, dest_deb)

        rel_filename = f"pool/{component}/{deb_path.name}"
        fields["Filename"] = rel_filename
        fields["Size"] = str(size)
        fields["SHA256"] = sha256
        fields["MD5sum"] = md5

        # Format package stanza
        lines = []
        for k, v in fields.items():
            lines.append(f"{k}: {v}")
        stanza = "\n".join(lines) + "\n"

        arch = fields.get("Architecture", "all")
        if arch in ("all", "amd64"):
            packages_amd64.append(stanza)
        if arch == "all":
            packages_all.append(stanza)

    # Write Packages and Packages.gz
    for target_dir, stanzas in [(arch_amd64_dir, packages_amd64), (arch_all_dir, packages_all)]:
        content = "\n".join(stanzas).encode("utf-8")
        pkg_file = target_dir / "Packages"
        pkg_file.write_bytes(content)

        gz_file = target_dir / "Packages.gz"
        with gzip.open(gz_file, "wb") as gz:
            gz.write(content)

    # Generate Release file
    release_files = [
        f"{component}/binary-amd64/Packages",
        f"{component}/binary-amd64/Packages.gz",
        f"{component}/binary-all/Packages",
        f"{component}/binary-all/Packages.gz",
    ]

    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC")

    md5_entries = []
    sha256_entries = []

    for rel_path in release_files:
        full_path = dists_dir / rel_path
        if full_path.exists():
            data = full_path.read_bytes()
            size = len(data)
            md5_entries.append(f" {hashlib.md5(data).hexdigest()} {size} {rel_path}")
            sha256_entries.append(f" {hashlib.sha256(data).hexdigest()} {size} {rel_path}")

    release_content = [
        f"Origin: {origin}",
        f"Label: {label}",
        f"Suite: {suite}",
        f"Codename: {suite}",
        f"Version: 24.04",
        f"Architectures: amd64 all",
        f"Components: {component}",
        f"Description: {description}",
        f"Date: {date_str}",
        "MD5Sum:",
        "\n".join(md5_entries),
        "SHA256:",
        "\n".join(sha256_entries),
    ]

    (dists_dir / "Release").write_text("\n".join(release_content) + "\n", encoding="utf-8")

    # Generate landing index.html
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Reims Desktop Official APT Repository</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0b0f19; color: #f1f5f9; line-height: 1.6; }}
    h1 {{ color: #38bdf8; border-bottom: 1px solid #1e293b; padding-bottom: 12px; }}
    pre {{ background: #1e293b; color: #38bdf8; padding: 14px; border-radius: 8px; overflow-x: auto; font-size: 14px; }}
    a {{ color: #38bdf8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 20px; margin-top: 24px; }}
  </style>
</head>
<body>
  <h1>📦 Reims Desktop Official APT Repository</h1>
  <p>Official software repository for <strong>Reims Desktop</strong> (Ubuntu 24.04 LTS Noble).</p>
  
  <div class="card">
    <h3>Quick Setup</h3>
    <p>Add this repository to your system:</p>
    <pre>echo "deb [trusted=yes] https://joaosantiag0.github.io/reims-desktop noble main" | sudo tee /etc/apt/sources.list.d/reims.list
sudo apt update
sudo apt install reims-core reims-gui reims-vgpu</pre>
  </div>

  <div class="card">
    <h3>Packages Included</h3>
    <ul>
      <li><strong>reims-core</strong>: System daemons, updater CLI, udev & udmabuf rules</li>
      <li><strong>reims-gui</strong>: Reims Desktop Control Center (Qt6 graphical interface)</li>
      <li><strong>reims-vgpu</strong>: Accelerated QEMU virtualization stack with Metal/Vulkan bridging</li>
    </ul>
  </div>

  <p style="margin-top: 40px; font-size: 12px; color: #64748b;">
    Reims Desktop is an independent unofficial community project.
  </p>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html_content, encoding="utf-8")
    print(f"✓ APT Repository successfully created at {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Debian APT repository for GitHub Pages")
    parser.add_argument("--deb-dir", type=Path, default=Path("dist"), help="Directory containing .deb packages")
    parser.add_argument("--out-dir", type=Path, default=Path("repo"), help="Target repository directory")
    parser.add_argument("--suite", type=str, default="noble", help="Debian/Ubuntu suite codename (default: noble)")
    parser.add_argument("--component", type=str, default="main", help="Repository component (default: main)")

    args = parser.parse_args()
    generate_apt_repo(args.deb_dir, args.out_dir, suite=args.suite, component=args.component)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
