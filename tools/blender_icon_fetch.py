#!/usr/bin/env python3
"""Fetch Blender official icons and convert to PNGs (stored in ui/gpu/icons)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import requests

# Settings
REPO_RAW_BASE = "https://projects.blender.org/blender/blender/raw/branch/main/release/datafiles/icons_svg"
ICONS_LIST_URL = "https://projects.blender.org/api/v1/repos/blender/blender/contents/release/datafiles/icons_svg"
PNG_SIZE = 16  # Blender default icon size (ICON_DEFAULT_HEIGHT)


def get_icon_list() -> list[str]:
    """Get icon list from the repo API."""
    response = requests.get(ICONS_LIST_URL, timeout=30)
    response.raise_for_status()
    return [f["name"] for f in response.json() if f["name"].endswith(".svg")]


def download_svg(icon_name: str, dest_dir: Path) -> Path | None:
    """Download an SVG file."""
    url = f"{REPO_RAW_BASE}/{icon_name}"
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        return None
    svg_path = dest_dir / icon_name
    svg_path.write_bytes(response.content)
    return svg_path


def _resolve_inkscape(explicit_path: Path | None) -> str | None:
    """Find an Inkscape executable path."""
    if explicit_path:
        if explicit_path.exists():
            return str(explicit_path)
        return None

    env_path = os.environ.get("INKSCAPE_PATH") or os.environ.get("INKSCAPE")
    if env_path and Path(env_path).exists():
        return env_path

    which_path = shutil.which("inkscape")
    if which_path:
        return which_path

    candidates = [
        r"C:\Program Files\Inkscape\bin\inkscape.exe",
        r"C:\Program Files\Inkscape\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe",
        r"C:\Program Files (x86)\Inkscape\inkscape.exe",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate

    return None


def convert_to_png(svg_path: Path, png_path: Path, size: int, inkscape_path: str) -> None:
    """Convert SVG to PNG using Inkscape."""
    subprocess.run(
        [
            inkscape_path,
            str(svg_path),
            "--export-type=png",
            f"--export-filename={png_path}",
        # Only width is specified to preserve aspect ratio.
        f"--export-width={size}",
            "--export-background-opacity=0",
        ],
        check=False,
        capture_output=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Blender icons -> PNG")
    parser.add_argument(
        "--local-svg-dir",
        type=Path,
        default=None,
        help="Use a local icons_svg directory (e.g. Blender_source/.../icons_svg).",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=PNG_SIZE,
        help="Output PNG width in pixels (height auto).",
    )
    parser.add_argument(
        "--inkscape",
        type=Path,
        default=None,
        help="Path to inkscape executable (optional).",
    )
    args = parser.parse_args()

    # Output: ui/gpu/icons (separate from PreviewHelper)
    addon_root = Path(__file__).resolve().parents[1]
    output_dir = addon_root / "ui" / "gpu" / "icons"
    svg_dir = output_dir / "_svg"
    png_dir = output_dir

    svg_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    inkscape_path = _resolve_inkscape(args.inkscape)
    if not inkscape_path:
        raise RuntimeError(
            "Inkscape not found. Install it or pass --inkscape PATH "
            "(or set INKSCAPE_PATH)."
        )

    if args.local_svg_dir:
        icons = sorted([p.name for p in args.local_svg_dir.glob("*.svg")])
    else:
        icons = get_icon_list()

    print(f"Found {len(icons)} icons")

    for icon_name in icons:
        print(f"Processing: {icon_name}")
        if args.local_svg_dir:
            svg_path = args.local_svg_dir / icon_name
            if not svg_path.exists():
                continue
        else:
            svg_path = download_svg(icon_name, svg_dir)
            if svg_path is None:
                continue

        png_name = icon_name.replace(".svg", ".png")
        convert_to_png(svg_path, png_dir / png_name, args.size, inkscape_path)

    print(f"Done! Icons saved to {output_dir}")


if __name__ == "__main__":
    main()
