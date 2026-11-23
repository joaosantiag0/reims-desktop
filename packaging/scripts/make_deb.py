#!/usr/bin/env python3
"""Builds a Debian package (.deb) from a source directory.

Uses `dpkg-deb` if available on the system, or a pure-Python fallback
implementing the Debian 'ar' + gzip format.
"""

from __future__ import annotations
import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path


def create_tar_gz_bytes(source_dir: Path, base_tar_dir: str = "./") -> bytes:
    """Creates a tar.gz archive in memory with normalized metadata."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for root, dirs, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir)
            tar_root = "." if rel_root == "." else f"./{rel_root}"

            # Add directory
            if rel_root != ".":
                ti = tarfile.TarInfo(name=tar_root)
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                ti.mtime = int(time.time())
                ti.uname = "root"
                ti.gname = "root"
                ti.uid = 0
                ti.gid = 0
                tar.addfile(ti)

            for f in sorted(files):
                file_path = Path(root) / f
                rel_file = f if rel_root == "." else f"{rel_root}/{f}"
                tar_name = f"./{rel_file}"

                with open(file_path, "rb") as fp:
                    content = fp.read()

                ti = tarfile.TarInfo(name=tar_name)
                ti.size = len(content)
                ti.mtime = int(time.time())
                ti.uname = "root"
                ti.gname = "root"
                ti.uid = 0
                ti.gid = 0

                # Check if executable
                if os.access(file_path, os.X_OK) or f.endswith((".sh", "postinst", "prerm", "postrm", "preinst")):
                    ti.mode = 0o755
                else:
                    ti.mode = 0o644

                tar.addfile(ti, io.BytesIO(content))

    return buf.getvalue()


def write_ar_member(out_fp, filename: str, data: bytes, mode: int = 0o100644):
    """Writes an ar archive member header and payload."""
    name_field = f"{filename:<16}"[:16].encode("ascii")
    mtime_field = f"{int(time.time()):<12}"[:12].encode("ascii")
    uid_field = f"{'0':<6}"[:6].encode("ascii")
    gid_field = f"{'0':<6}"[:6].encode("ascii")
    mode_field = f"{oct(mode)[2:]:<8}"[:8].encode("ascii")
    size_field = f"{len(data):<10}"[:10].encode("ascii")
    magic_end = b"`\n"

    header = name_field + mtime_field + uid_field + gid_field + mode_field + size_field + magic_end
    out_fp.write(header)
    out_fp.write(data)

    # ar requires 2-byte alignment with padding newline
    if len(data) % 2 != 0:
        out_fp.write(b"\n")


def build_deb_native(pkg_root: Path, output_deb: Path) -> Path:
    """Builds a .deb package using pure Python."""
    debian_dir = pkg_root / "DEBIAN"
    if not debian_dir.is_dir():
        raise ValueError(f"Missing DEBIAN directory in {pkg_root}")

    control_file = debian_dir / "control"
    if not control_file.is_file():
        raise ValueError(f"Missing DEBIAN/control file in {pkg_root}")

    output_deb.parent.mkdir(parents=True, exist_ok=True)

    # 1. debian-binary
    debian_binary = b"2.0\n"

    # 2. control.tar.gz
    control_tar_gz = create_tar_gz_bytes(debian_dir)

    # 3. data.tar.gz (all files except DEBIAN/)
    temp_data_dir = pkg_root / ".data_tmp"
    if temp_data_dir.exists():
        shutil.rmtree(temp_data_dir)
    temp_data_dir.mkdir(parents=True)

    try:
        for item in pkg_root.iterdir():
            if item.name in ("DEBIAN", ".data_tmp"):
                continue
            dest = temp_data_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        data_tar_gz = create_tar_gz_bytes(temp_data_dir)
    finally:
        if temp_data_dir.exists():
            shutil.rmtree(temp_data_dir)

    # Write .deb archive (ar format)
    with open(output_deb, "wb") as deb:
        deb.write(b"!<arch>\n")
        write_ar_member(deb, "debian-binary", debian_binary)
        write_ar_member(deb, "control.tar.gz", control_tar_gz)
        write_ar_member(deb, "data.tar.gz", data_tar_gz)

    return output_deb


def build_deb(pkg_root: Path, output_deb: Path, force_fallback: bool = False) -> Path:
    """Builds a .deb package using dpkg-deb if present, otherwise native fallback."""
    dpkg_deb = shutil.which("dpkg-deb")
    if dpkg_deb and not force_fallback:
        cmd = [dpkg_deb, "--build", "-Zgzip", str(pkg_root), str(output_deb)]
        subprocess.run(cmd, check=True)
        return output_deb
    return build_deb_native(pkg_root, output_deb)


def main():
    parser = argparse.ArgumentParser(description="Build Debian .deb package")
    parser.add_argument("pkg_root", type=Path, help="Package root directory containing DEBIAN/")
    parser.add_argument("output_deb", type=Path, help="Output .deb file path")
    parser.add_argument("--native", action="store_true", help="Force pure Python native packager")
    args = parser.parse_args()

    try:
        out = build_deb(args.pkg_root, args.output_deb, force_fallback=args.native)
        print(f"Successfully generated Debian package: {out}")
    except Exception as e:
        print(f"Error generating package: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
