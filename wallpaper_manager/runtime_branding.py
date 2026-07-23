"""Ensure frozen macOS builds launch the branded embedded Flet view (Dock icon).

The embedded Flet view is what actually renders the Flutter UI (and runs the
``file_selector_macos`` plugin behind the folder/file pickers). ``flet pack``
ships it ad-hoc signed with *no* entitlements, so the picker raises
``PlatformException(ENTITLEMENT_NOT_FOUND)``. After extracting our own copy we
re-sign it with an entitlements plist that grants user-selected file access.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

BRAND_MARKER = "brand-v2"
VIEW_DIR = Path.home() / ".wallpaper-manager" / "flet-view"


def _entitlements_path() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    candidate = Path(meipass) / "assets" / "entitlements.plist"
    return candidate if candidate.is_file() else None


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
        # Signing is best-effort; a failure just leaves the picker broken,
        # it should never crash app startup.
        pass


def prepare_branded_flet_view() -> None:
    """Point FLET_VIEW_PATH at the icon-patched, entitled client inside the .app.

    ``flet pack`` embeds a branded ``flet-macos.tar.gz``, but Flet prefers an
    existing ``~/.flet/client/...`` cache (default Flet icon, no entitlements).
    For frozen apps we extract our own copy once, re-sign it, and force that path.
    """
    if sys.platform != "darwin":
        return
    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("FLET_VIEW_PATH"):
        return

    marker = VIEW_DIR / BRAND_MARKER
    app_bundle = VIEW_DIR / "Wallpaper Manager.app"
    if marker.is_file() and app_bundle.is_dir():
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

    _resign_view(app_bundle)

    marker.write_text(BRAND_MARKER + "\n", encoding="utf-8")
    os.environ["FLET_VIEW_PATH"] = str(VIEW_DIR)
