#!/usr/bin/env python3
"""
Reims Desktop - Logo & Brand Asset Processor
Converts white-background master logos into high-quality transparent RGBA icons
and dark/black background variants with anti-aliasing de-matting.
"""

from __future__ import annotations

import argparse
from collections import deque
import os
from pathlib import Path
import subprocess
import sys
from PIL import Image


def remove_white_background(
    img: Image.Image,
    threshold: int = 220,
    max_white: int = 252,
    bg_color: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """
    Flood-fills from the outer image borders to locate the background,
    removes the white canvas, and performs de-matting on anti-aliased edges.
    
    If bg_color is None, returns RGBA with transparent background (alpha=0).
    If bg_color is (R, G, B, A), composites the de-matted icon over bg_color.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    pixels = rgba.load()

    # Fast BFS queue starting from the perimeter
    visited: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()

    for x in range(w):
        for y in (0, h - 1):
            visited.add((x, y))
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if (x, y) not in visited:
                visited.add((x, y))
                q.append((x, y))

    while q:
        cx, cy = q.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                r, g, b, _ = pixels[nx, ny]
                if r > threshold and g > threshold and b > threshold:
                    visited.add((nx, ny))
                    q.append((nx, ny))

    out_img = rgba.copy()
    out_pix = out_img.load()

    for (x, y) in visited:
        r, g, b, _ = pixels[x, y]
        whiteness = min(r, g, b)
        if whiteness >= max_white:
            out_pix[x, y] = (0, 0, 0, 0)
        else:
            # Linear alpha interpolation in transition zone
            alpha = int(255 * (1.0 - (whiteness - threshold) / (max_white - threshold)))
            a_float = max(0.01, alpha / 255.0)
            # Mathematical de-matting: true_color = (observed - 255 * (1 - alpha)) / alpha
            true_r = max(0, min(255, int((r - 255 * (1 - a_float)) / a_float)))
            true_g = max(0, min(255, int((g - 255 * (1 - a_float)) / a_float)))
            true_b = max(0, min(255, int((b - 255 * (1 - a_float)) / a_float)))
            out_pix[x, y] = (true_r, true_g, true_b, alpha)

    if bg_color is not None:
        bg = Image.new("RGBA", (w, h), bg_color)
        bg.paste(out_img, (0, 0), out_img)
        return bg

    return out_img


def generate_icns(source_png: Image.Image, output_icns: Path) -> bool:
    """Generates macOS .icns using iconutil if available."""
    if sys.platform != "darwin":
        return False
    try:
        iconset_dir = output_icns.parent / f"{output_icns.stem}.iconset"
        iconset_dir.mkdir(parents=True, exist_ok=True)

        sizes = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png"),
        ]

        for sz, fname in sizes:
            resized = source_png.resize((sz, sz), Image.Resampling.LANCZOS)
            resized.save(iconset_dir / fname, "PNG")

        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_icns)],
            check=True,
            capture_output=True,
        )

        # Cleanup iconset folder
        for f in iconset_dir.glob("*.png"):
            f.unlink()
        iconset_dir.rmdir()
        return True
    except Exception as e:
        print(f"Aviso: Não foi possível gerar .icns com iconutil: {e}", file=sys.stderr)
        return False


def process_all_brand_assets(
    repo_root: Path,
    bg_mode: str = "transparent",
) -> None:
    """
    Processes the master logo and updates all derived icon sizes across the repository.
    Modes:
      - 'transparent': Alpha=0 background (Recommended OS standard)
      - 'black': Pure black (#000000) background
      - 'plymouth': Dark slate (#121418) Plymouth splash background
    """
    master_logo_path = repo_root / "assets" / "logo.png"
    if not master_logo_path.exists():
        raise FileNotFoundError(f"Master logo não encontrado em {master_logo_path}")

    print(f"Carregando {master_logo_path}...")
    master = Image.open(master_logo_path)

    bg_color = None
    if bg_mode == "black":
        bg_color = (0, 0, 0, 255)
    elif bg_mode == "plymouth":
        bg_color = (18, 20, 24, 255)

    print(f"Processando remoção de fundo branco (modo: {bg_mode})...")
    processed_master = remove_white_background(master, bg_color=bg_color)

    # 1. Update assets/logo.png
    processed_master.save(master_logo_path, "PNG")
    print(f"  [OK] Atualizado {master_logo_path} ({processed_master.size[0]}x{processed_master.size[1]})")

    # 2. Update iso-builder/customization/reims-logo.png (1024x1024)
    iso_logo_path = repo_root / "iso-builder" / "customization" / "reims-logo.png"
    iso_logo = processed_master.resize((1024, 1024), Image.Resampling.LANCZOS)
    iso_logo.save(iso_logo_path, "PNG")
    print(f"  [OK] Atualizado {iso_logo_path} (1024x1024)")

    # 3. Update iso-builder/customization/reims.icns
    icns_path = repo_root / "iso-builder" / "customization" / "reims.icns"
    if generate_icns(processed_master, icns_path):
        print(f"  [OK] Atualizado {icns_path} (macOS ICNS)")

    # 4. Update reims-gui/src/reims_gui/assets/reims-logo.png (512x512)
    gui_logo_path = repo_root / "reims-gui" / "src" / "reims_gui" / "assets" / "reims-logo.png"
    gui_logo = processed_master.resize((512, 512), Image.Resampling.LANCZOS)
    gui_logo.save(gui_logo_path, "PNG")
    print(f"  [OK] Atualizado {gui_logo_path} (512x512)")

    # 5. Update packaging pixmaps (512x512)
    pixmaps_dir = repo_root / "packaging" / "templates" / "reims-gui" / "usr" / "share" / "pixmaps"
    pixmaps_dir.mkdir(parents=True, exist_ok=True)
    for name in ("reims-desktop.png", "reims-logo.png", "reims-gui.png"):
        p = pixmaps_dir / name
        gui_logo.save(p, "PNG")
        print(f"  [OK] Atualizado {p}")

    # 6. Update packaging hicolor icon sizes
    hicolor_base = repo_root / "packaging" / "templates" / "reims-gui" / "usr" / "share" / "icons" / "hicolor"
    icon_sizes = (16, 32, 48, 64, 128, 256, 512)
    for sz in icon_sizes:
        sz_dir = hicolor_base / f"{sz}x{sz}" / "apps"
        sz_dir.mkdir(parents=True, exist_ok=True)
        sz_img = processed_master.resize((sz, sz), Image.Resampling.LANCZOS)
        for name in ("reims-desktop.png", "reims-gui.png"):
            p = sz_dir / name
            sz_img.save(p, "PNG")
        print(f"  [OK] Atualizado {hicolor_base.name}/{sz}x{sz}/apps/")

    print("Todos os assets de marca foram processados e atualizados com sucesso!")


def main() -> int:
    parser = argparse.ArgumentParser(description="Processa logos e assets de marca do Reims Desktop")
    parser.add_argument(
        "--mode",
        choices=["transparent", "black", "plymouth"],
        default="transparent",
        help="Modo de fundo: transparent (RGBA padrão), black (#000000), ou plymouth (#121418)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    process_all_brand_assets(repo_root, bg_mode=args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
