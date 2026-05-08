#!/usr/bin/env python3
"""
screenshot_html.py — capture a PNG snapshot of a local HTML report.

Used by the obs-hub analyze skill to produce a thumbnail of the
auto-generated HTML report, which is then displayed in chat as a
clickable preview linking to the full file.

Usage:
  screenshot_html.py --html=<path-to-html> --out=<path-to-png> \
                     [--width=1280] [--height=900] [--full-page]

Defaults:
  --width   1280
  --height  900   (visible viewport — captures only the top of the page)
  --full-page  capture entire page instead of just the viewport

Strategy:
  1. Headless Chrome (preferred) — produces faithful, modern-CSS output.
     Looks for `google-chrome`, `chromium`, then macOS app bundles.
  2. macOS qlmanage fallback — works without Chrome but no JS execution,
     so charts won't render. Only used as last resort.

Exits 0 on success and prints the absolute path of the PNG written.
Exits non-zero with a clear error if no engine is available.
"""

from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


CHROME_CANDIDATES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if "/" in c:
            if Path(c).exists():
                return c
        else:
            p = shutil.which(c)
            if p:
                return p
    return None


def shoot_with_chrome(chrome: str, html: Path, out: Path, width: int,
                      height: int, full_page: bool) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    file_url = f"file://{html.resolve()}"

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--virtual-time-budget=3000",  # let Chart.js / marked.js settle
        f"--window-size={width},{height}",
        f"--screenshot={out.resolve()}",
    ]
    if full_page:
        # Newer Chrome respects --full-page-screenshot in headless=new
        cmd.append("--full-page-screenshot")
    cmd.append(file_url)

    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if res.returncode != 0 or not out.exists():
        raise RuntimeError(
            f"Chrome screenshot failed (rc={res.returncode})\n"
            f"stdout: {res.stdout[:400]}\n"
            f"stderr: {res.stderr[:400]}"
        )


def shoot_with_qlmanage(html: Path, out: Path, width: int, height: int) -> None:
    """macOS Quick Look fallback — no JS, no charts, but works zero-deps."""
    if not Path("/usr/bin/qlmanage").exists():
        raise RuntimeError("qlmanage not available (not on macOS?)")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = out.parent / "_qltmp"
    tmp_dir.mkdir(exist_ok=True)
    cmd = [
        "/usr/bin/qlmanage", "-t",
        "-s", str(width),
        "-o", str(tmp_dir),
        str(html.resolve()),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    produced = tmp_dir / f"{html.name}.png"
    if res.returncode != 0 or not produced.exists():
        raise RuntimeError(
            f"qlmanage failed (rc={res.returncode}): {res.stderr[:300]}"
        )
    produced.replace(out)
    try:
        tmp_dir.rmdir()
    except OSError:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, help="Input HTML path")
    ap.add_argument("--out", required=True, help="Output PNG path")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--full-page", action="store_true",
                    help="Capture the entire page (default: viewport only)")
    ap.add_argument("--engine", choices=("auto", "chrome", "qlmanage"),
                    default="auto")
    args = ap.parse_args()

    html = Path(args.html)
    out = Path(args.out)
    if not html.exists():
        print(f"❌ HTML not found: {html}", file=sys.stderr)
        return 2

    engine = args.engine
    chrome = find_chrome() if engine in ("auto", "chrome") else None

    try:
        if engine == "qlmanage" or (engine == "auto" and not chrome):
            print("⚠️  Using qlmanage fallback (no JS / no charts). "
                  "Install Chrome for accurate snapshots.", file=sys.stderr)
            shoot_with_qlmanage(html, out, args.width, args.height)
        else:
            if not chrome:
                print("❌ No Chrome / Chromium / Edge found on PATH or in "
                      "/Applications. Install one or pass --engine=qlmanage.",
                      file=sys.stderr)
                return 3
            shoot_with_chrome(chrome, html, out, args.width, args.height,
                              args.full_page)
    except Exception as e:
        print(f"❌ Screenshot failed: {e}", file=sys.stderr)
        return 4

    size_kb = out.stat().st_size / 1024
    print(f"✅ Wrote {out.resolve()} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
