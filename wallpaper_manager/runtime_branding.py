"""Ensure frozen macOS builds launch the branded embedded Flet view (Dock icon)."""

from __future__ import annotations

import os
import shutil
import sys
import tarfile
from pathlib import Path

BRAND_MARKER = "brand-v1"
VIEW_DIR = Path.home() / ".wallpaper-manager" / "flet-view"


def prepare_branded_flet_view() -> None:
    """Point FLET_VIEW_PATH at the icon-patched client shipped inside the .app.

    ``flet pack`` embeds a branded ``flet-macos.tar.gz``, but Flet prefers an
    existing ``~/.flet/client/...`` cache (default Flet icon). For frozen apps we
    extract our own copy once and force that path.
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

    marker.write_text(BRAND_MARKER + "\n", encoding="utf-8")
    os.environ["FLET_VIEW_PATH"] = str(VIEW_DIR)
