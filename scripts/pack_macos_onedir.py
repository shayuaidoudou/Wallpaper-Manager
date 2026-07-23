"""Onedir variant of ``flet pack`` for macOS.

``flet pack`` hardcodes PyInstaller's ``--onefile`` mode on macOS, but onefile
.app bundles break TCC: macOS forgets folder-access grants and re-prompts on
every launch (PyInstaller deprecated the combination for the same reason).
This driver reuses flet's packaging hooks verbatim and simply builds in
onedir mode. Usage: ``python scripts/pack_macos_onedir.py <version>``.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import flet_cli.__pyinstaller.config as hook_config
import PyInstaller.__main__
from flet_cli.__pyinstaller.macos_utils import (
    assemble_app_bundle,
    unpack_app_bundle,
    update_flet_view_icon,
    update_flet_view_version_info,
)
from flet_cli.__pyinstaller.utils import copy_flet_bin

APP_NAME = "Wallpaper Manager"
BUNDLE_ID = "store.shayuaidoudou.wallpaper-manager"
COPYRIGHT = "Copyright (c) 2026 shayuaidoudou"

HIDDEN_IMPORTS = [
    "PIL",
    "httpx",
    "wallpaper_manager",
    "wallpaper_manager.ui.app",
    "wallpaper_manager.ui.gallery_panel",
    "wallpaper_manager.runtime_branding",
    "wallpaper_manager.gallery",
    "wallpaper_manager.adapters.vscode",
    "wallpaper_manager.adapters.cursor",
    "wallpaper_manager.adapters.jetbrains",
    "wallpaper_manager.adapters.ghostty",
]


def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("macOS only")
    version = sys.argv[1] if len(sys.argv) > 1 else "0.0.0"
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)

    icon = next(
        (
            str(root / c)
            for c in ("assets/icon.icns", "assets/icon.png")
            if (root / c).is_file()
        ),
        None,
    )

    pyi_args = [
        "main.py",
        "--noconfirm",
        "--noconsole",
        "--name",
        APP_NAME,
        "--distpath",
        "dist",
        "--osx-bundle-identifier",
        BUNDLE_ID,
        "--add-data",
        "assets/entitlements.plist:assets",
    ]
    if icon:
        pyi_args.extend(["--icon", icon])
    for mod in HIDDEN_IMPORTS:
        pyi_args.extend(["--hidden-import", mod])
    # NB: no --onefile here — onedir is PyInstaller's default.

    # Copy the Flet client and patch its icon/plist, same as `flet pack`.
    hook_config.temp_bin_dir = copy_flet_bin()
    if hook_config.temp_bin_dir is None:
        raise SystemExit("copy_flet_bin() failed")

    fletd = os.path.join(hook_config.temp_bin_dir, "fletd")
    if os.path.exists(fletd):
        os.remove(fletd)

    tar_path = os.path.join(hook_config.temp_bin_dir, "flet-macos.tar.gz")
    app_path = None
    if os.path.exists(tar_path):
        app_path = unpack_app_bundle(tar_path)
    else:
        for entry in os.listdir(hook_config.temp_bin_dir):
            if entry.endswith(".app"):
                app_path = os.path.join(hook_config.temp_bin_dir, entry)
                break
    if not app_path:
        raise SystemExit(f"Flet.app not found in {hook_config.temp_bin_dir}")

    if icon:
        update_flet_view_icon(app_path, icon)
    app_path = update_flet_view_version_info(
        app_path=app_path,
        bundle_id=BUNDLE_ID,
        product_name=APP_NAME,
        product_version=version,
        copyright=COPYRIGHT,
    )
    assemble_app_bundle(app_path, tar_path)

    # Keep only the tar.gz so PyInstaller doesn't process loose binaries.
    for entry in os.listdir(hook_config.temp_bin_dir):
        entry_path = os.path.join(hook_config.temp_bin_dir, entry)
        if entry_path == tar_path:
            continue
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path, ignore_errors=True)
        else:
            os.remove(entry_path)

    print("Running PyInstaller (onedir):", pyi_args)
    PyInstaller.__main__.run(pyi_args)

    shutil.rmtree(hook_config.temp_bin_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
