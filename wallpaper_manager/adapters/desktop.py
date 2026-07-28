"""System desktop wallpaper adapter for macOS and Windows."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from wallpaper_manager.core.models import AppId

DEFAULT_OPACITY_UI = 20


def _applescript_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _run_osascript(*lines: str) -> str:
    script = "\n".join(lines)
    completed = subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(detail or "osascript failed")
    return (completed.stdout or "").strip()


def read_macos_desktop_wallpaper() -> str | None:
    raw = _run_osascript(
        'tell application "System Events" to get picture of current desktop'
    )
    if not raw or raw.lower() in {"missing value", "null"}:
        return None
    path = Path(raw).expanduser()
    return str(path) if str(path) else None


def apply_macos_desktop_wallpaper(image_path: str) -> None:
    path = str(Path(image_path).expanduser().resolve())
    quoted = _applescript_quote(path)
    _run_osascript(
        'tell application "System Events"',
        "  repeat with d in desktops",
        f'    set picture of d to "{quoted}"',
        "  end repeat",
        "end tell",
    )


def clear_macos_desktop_wallpaper() -> None:
    # macOS has no stable public API to remove a wallpaper without replacing it.
    # Local app state is still cleared by WallpaperService.
    return


def read_windows_desktop_wallpaper() -> str | None:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
        value, _ = winreg.QueryValueEx(key, "WallPaper")
    raw = str(value or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return str(path) if str(path) else None


def apply_windows_desktop_wallpaper(image_path: str) -> None:
    import ctypes

    path = str(Path(image_path).expanduser().resolve())
    spi_setdeskwallpaper = 20
    spif_updateinifile = 0x01
    spif_sendchange = 0x02
    flags = spif_updateinifile | spif_sendchange
    ok = ctypes.windll.user32.SystemParametersInfoW(
        spi_setdeskwallpaper, 0, path, flags
    )
    if not ok:
        raise RuntimeError("SystemParametersInfoW failed while setting wallpaper")


def clear_windows_desktop_wallpaper() -> None:
    import ctypes

    spi_setdeskwallpaper = 20
    spif_updateinifile = 0x01
    spif_sendchange = 0x02
    flags = spif_updateinifile | spif_sendchange
    # Empty string clears the wallpaper image on Windows.
    ok = ctypes.windll.user32.SystemParametersInfoW(
        spi_setdeskwallpaper, 0, "", flags
    )
    if not ok:
        raise RuntimeError("SystemParametersInfoW failed while clearing wallpaper")


class DesktopAdapter:
    """Apply an image as the OS desktop wallpaper.

    Opacity is part of the shared adapter protocol but is ignored by the OS.
    """

    app_id = AppId.DESKTOP

    def detect(self) -> bool:
        return sys.platform in {"darwin", "win32"}

    def read(self) -> tuple[str | None, int]:
        if sys.platform == "darwin":
            return read_macos_desktop_wallpaper(), DEFAULT_OPACITY_UI
        if sys.platform == "win32":
            return read_windows_desktop_wallpaper(), DEFAULT_OPACITY_UI
        return None, DEFAULT_OPACITY_UI

    def apply(self, image_path: str, opacity_ui: int) -> None:
        del opacity_ui  # System desktop wallpaper has no opacity control.
        path = Path(image_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")
        if sys.platform == "darwin":
            apply_macos_desktop_wallpaper(str(path))
            return
        if sys.platform == "win32":
            apply_windows_desktop_wallpaper(str(path))
            return
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    def clear(self) -> None:
        if sys.platform == "darwin":
            clear_macos_desktop_wallpaper()
            return
        if sys.platform == "win32":
            clear_windows_desktop_wallpaper()
            return
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    def extension_installed(self) -> bool:
        return True
