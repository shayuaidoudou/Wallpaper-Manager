"""Ensure frozen macOS builds launch the branded embedded Flet view (Dock icon).

The embedded Flet view is what actually renders the Flutter UI (and runs the
``file_selector_macos`` plugin behind the folder/file pickers). ``flet pack``
ships it ad-hoc signed with *no* entitlements, so the picker raises
``PlatformException(ENTITLEMENT_NOT_FOUND)``. After extracting our own copy we
re-sign it with an entitlements plist that grants user-selected file access.

Flet runs as a *second* process. If that process uses the same CFBundleIdentifier
(or is a full GUI app), Dock shows two identical icons. We give the view a
distinct bundle id and mark it as an agent (LSUIElement) so only the host .app
owns the Dock tile.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

# Bump when branding / Dock policy for the view changes.
BRAND_MARKER = "brand-v4"
VIEW_DIR = Path.home() / ".wallpaper-manager" / "flet-view"
VIEW_BUNDLE_ID = "store.shayuaidoudou.wallpaper-manager.flet-view"
VIEW_DISPLAY_NAME = "Wallpaper Manager UI"


def _entitlements_path() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    candidate = Path(meipass) / "assets" / "entitlements.plist"
    return candidate if candidate.is_file() else None


def _patch_view_identity(app_bundle: Path) -> None:
    """Distinct id + agent app so Dock does not show a second Wallpaper Manager."""
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
    # Hide this helper process from the Dock; the host PyInstaller .app remains.
    info["LSUIElement"] = True

    try:
        with info_path.open("wb") as fh:
            plistlib.dump(info, fh)
    except Exception:
        pass


def _resign_view(app_bundle: Path) -> None:
    """Ad-hoc re-sign the extracted view app with file-access entitlements."""
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
    """Point FLET_VIEW_PATH at the icon-patched, entitled client for frozen apps."""
    if sys.platform != "darwin":
        return
    if not getattr(sys, "frozen", False):
        return
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
