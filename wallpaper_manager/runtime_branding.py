"""Ensure frozen macOS builds launch the branded embedded Flet view (Dock icon).

Architecture on macOS:
- Host process: PyInstaller ``Wallpaper Manager.app`` (Python + Flet server)
- UI process: extracted Flet/Flutter client under ``~/.wallpaper-manager/flet-view``

Both used to show up in the Dock (same name/icon → "two apps", and bouncing when
focus flips between host and UI). Policy:

- Host keeps the public path ``/Applications/Wallpaper Manager.app`` but is marked
  ``LSUIElement`` so it does not own a Dock tile.
- Flet view is the only Dock-visible app: product name ``Wallpaper Manager``,
  distinct bundle id ``...flet-view``, branded icon + entitlements for pickers.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

# Bump when Dock / branding policy for host+view changes.
BRAND_MARKER = "brand-v5"
VIEW_DIR = Path.home() / ".wallpaper-manager" / "flet-view"
VIEW_BUNDLE_ID = "store.shayuaidoudou.wallpaper-manager.flet-view"
VIEW_DISPLAY_NAME = "Wallpaper Manager"


def _entitlements_path() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    candidate = Path(meipass) / "assets" / "entitlements.plist"
    return candidate if candidate.is_file() else None


def _patch_host_as_agent() -> None:
    """Hide the PyInstaller host from the Dock (it has no real window of its own)."""
    if not getattr(sys, "frozen", False):
        return
    try:
        exe = Path(sys.executable).resolve()
        # .../Wallpaper Manager.app/Contents/MacOS/Wallpaper Manager
        app_bundle = exe.parents[1]
        if app_bundle.suffix != ".app":
            return
        info_path = app_bundle / "Contents" / "Info.plist"
        if not info_path.is_file():
            return
        with info_path.open("rb") as fh:
            info = plistlib.load(fh)
        if info.get("LSUIElement") is True:
            return
        info["LSUIElement"] = True
        with info_path.open("wb") as fh:
            plistlib.dump(info, fh)
        # Best-effort re-sign after plist edit so Gatekeeper is less noisy.
        entitlements = _entitlements_path()
        cmd = ["codesign", "--force", "--deep", "--sign", "-"]
        if entitlements is not None:
            cmd.extend(["--entitlements", str(entitlements)])
        cmd.append(str(app_bundle))
        subprocess.run(cmd, check=False, capture_output=True)
    except Exception:
        pass


def _patch_view_identity(app_bundle: Path) -> None:
    """Make the Flet client the single Dock-visible Wallpaper Manager."""
    info_path = app_bundle / "Contents" / "Info.plist"
    if not info_path.is_file():
        return
    try:
        with info_path.open("rb") as fh:
            info = plistlib.load(fh)
    except Exception:
        return

    info["CFBundleIdentifier"] = VIEW_BUNDLE_ID
    info["CFBundleName"] = VIEW_DISPLAY_NAME
    info["CFBundleDisplayName"] = VIEW_DISPLAY_NAME
    # View owns the window → must NOT be an agent.
    info["LSUIElement"] = False

    try:
        with info_path.open("wb") as fh:
            plistlib.dump(info, fh)
    except Exception:
        pass


def _resign_view(app_bundle: Path) -> None:
    entitlements = _entitlements_path()
    if entitlements is None or not app_bundle.is_dir():
        return
    try:
        subprocess.run(
            [
                "codesign",
                "--force",
                "--deep",
                "--sign",
                "-",
                "--entitlements",
                str(entitlements),
                str(app_bundle),
            ],
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


def prepare_branded_flet_view() -> None:
    """Prepare host + Flet view Dock identity, then set FLET_VIEW_PATH."""
    if sys.platform != "darwin":
        return
    if not getattr(sys, "frozen", False):
        return

    _patch_host_as_agent()

    if os.environ.get("FLET_VIEW_PATH"):
        return

    marker = VIEW_DIR / BRAND_MARKER
    app_bundle = VIEW_DIR / "Wallpaper Manager.app"
    if marker.is_file() and app_bundle.is_dir():
        _patch_view_identity(app_bundle)
        _resign_view(app_bundle)
        os.environ["FLET_VIEW_PATH"] = str(VIEW_DIR)
        return

    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    archive = Path(meipass) / "flet_desktop" / "app" / "flet-macos.tar.gz"
    if not archive.is_file():
        return

    if VIEW_DIR.exists():
        shutil.rmtree(VIEW_DIR, ignore_errors=True)
    VIEW_DIR.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(VIEW_DIR)

    _patch_view_identity(app_bundle)
    _resign_view(app_bundle)

    marker.write_text(BRAND_MARKER + "\n", encoding="utf-8")
    os.environ["FLET_VIEW_PATH"] = str(VIEW_DIR)
