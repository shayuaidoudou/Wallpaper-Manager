from pathlib import Path
from unittest.mock import MagicMock

import pytest

from wallpaper_manager.adapters.desktop import (
    DesktopAdapter,
    _applescript_quote,
    apply_macos_desktop_wallpaper,
    apply_windows_desktop_wallpaper,
    clear_macos_desktop_wallpaper,
    clear_windows_desktop_wallpaper,
    read_macos_desktop_wallpaper,
    read_windows_desktop_wallpaper,
)
from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.path_config import (
    CONFIG_FILE_LABELS,
    auto_config_path,
    config_dir_hint,
    resolve_config_from_user_selection,
)
from wallpaper_manager.core.service import WallpaperService
from wallpaper_manager.core.state_store import StateStore


def test_applescript_quote_escapes_special_chars():
    assert _applescript_quote(r'C:\a"b') == r'C:\\a\"b'


def test_desktop_adapter_identity_and_detect(monkeypatch):
    adapter = DesktopAdapter()
    assert adapter.app_id is AppId.DESKTOP
    assert adapter.extension_installed() is True

    monkeypatch.setattr("wallpaper_manager.adapters.desktop.sys.platform", "darwin")
    assert adapter.detect() is True
    monkeypatch.setattr("wallpaper_manager.adapters.desktop.sys.platform", "win32")
    assert adapter.detect() is True
    monkeypatch.setattr("wallpaper_manager.adapters.desktop.sys.platform", "linux")
    assert adapter.detect() is False


def test_read_macos_desktop_wallpaper(monkeypatch):
    monkeypatch.setattr(
        "wallpaper_manager.adapters.desktop._run_osascript",
        lambda *lines: "/tmp/wall.png",
    )
    assert read_macos_desktop_wallpaper() == "/tmp/wall.png"

    monkeypatch.setattr(
        "wallpaper_manager.adapters.desktop._run_osascript",
        lambda *lines: "missing value",
    )
    assert read_macos_desktop_wallpaper() is None


def test_apply_macos_desktop_wallpaper_invokes_osascript(monkeypatch, tmp_path: Path):
    image = tmp_path / "desk.png"
    image.write_bytes(b"png")
    calls: list[tuple[str, ...]] = []

    def fake_run(*lines: str) -> str:
        calls.append(lines)
        return ""

    monkeypatch.setattr("wallpaper_manager.adapters.desktop._run_osascript", fake_run)
    apply_macos_desktop_wallpaper(str(image))
    assert calls
    joined = "\n".join(calls[0])
    assert str(image.resolve()) in joined
    assert "System Events" in joined
    assert "set picture of d" in joined


def test_clear_macos_is_noop():
    clear_macos_desktop_wallpaper()


def test_read_windows_desktop_wallpaper(monkeypatch):
    class FakeKey:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_open_key(*args, **kwargs):
        return FakeKey()

    def fake_query(key, name):
        assert name == "WallPaper"
        return (r"C:\Users\me\wall.jpg", 1)

    fake_winreg = MagicMock()
    fake_winreg.OpenKey = fake_open_key
    fake_winreg.QueryValueEx = fake_query
    fake_winreg.HKEY_CURRENT_USER = object()
    monkeypatch.setitem(__import__("sys").modules, "winreg", fake_winreg)

    assert read_windows_desktop_wallpaper() == r"C:\Users\me\wall.jpg"


def test_apply_and_clear_windows_desktop_wallpaper(monkeypatch, tmp_path: Path):
    image = tmp_path / "desk.png"
    image.write_bytes(b"png")
    calls: list[tuple] = []

    class FakeUser32:
        def SystemParametersInfoW(self, action, param, path, flags):
            calls.append((action, param, path, flags))
            return 1

    fake_ctypes = MagicMock()
    fake_ctypes.windll.user32 = FakeUser32()
    monkeypatch.setitem(__import__("sys").modules, "ctypes", fake_ctypes)

    apply_windows_desktop_wallpaper(str(image))
    clear_windows_desktop_wallpaper()
    assert calls[0][0] == 20
    assert calls[0][2] == str(image.resolve())
    assert calls[1][2] == ""


def test_desktop_adapter_apply_read_clear_macos(monkeypatch, tmp_path: Path):
    image = tmp_path / "a.png"
    image.write_bytes(b"x")
    applied: list[str] = []

    monkeypatch.setattr("wallpaper_manager.adapters.desktop.sys.platform", "darwin")
    monkeypatch.setattr(
        "wallpaper_manager.adapters.desktop.apply_macos_desktop_wallpaper",
        lambda path: applied.append(path),
    )
    monkeypatch.setattr(
        "wallpaper_manager.adapters.desktop.read_macos_desktop_wallpaper",
        lambda: str(image),
    )
    monkeypatch.setattr(
        "wallpaper_manager.adapters.desktop.clear_macos_desktop_wallpaper",
        lambda: None,
    )

    adapter = DesktopAdapter()
    adapter.apply(str(image), 55)
    path, opacity = adapter.read()
    adapter.clear()
    assert applied == [str(image)]
    assert path == str(image)
    assert opacity == 20


def test_desktop_adapter_rejects_missing_image(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("wallpaper_manager.adapters.desktop.sys.platform", "darwin")
    adapter = DesktopAdapter()
    with pytest.raises(FileNotFoundError):
        adapter.apply(str(tmp_path / "missing.png"), 20)


def test_desktop_path_config_has_no_config_file():
    assert "系统桌面" in CONFIG_FILE_LABELS[AppId.DESKTOP]
    assert auto_config_path(AppId.DESKTOP) is None
    assert "无需" in config_dir_hint(AppId.DESKTOP) or "系统" in config_dir_hint(
        AppId.DESKTOP
    )
    resolved, error = resolve_config_from_user_selection(AppId.DESKTOP, "/tmp")
    assert resolved is None
    assert error is not None
    assert "系统桌面" in error


def test_service_precheck_and_apply_desktop_without_config_path(
    monkeypatch, tmp_path: Path
):
    from PIL import Image

    image = tmp_path / "wall.png"
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(image)

    applied: list[tuple[str, int]] = []

    class StubDesktop:
        app_id = AppId.DESKTOP

        def detect(self) -> bool:
            return True

        def read(self) -> tuple[str | None, int]:
            if applied:
                return applied[-1][0], 20
            return None, 20

        def apply(self, image_path: str, opacity_ui: int) -> None:
            applied.append((image_path, opacity_ui))

        def clear(self) -> None:
            applied.clear()

        def extension_installed(self) -> bool:
            return True

    service = WallpaperService(
        [StubDesktop()], store=StateStore(tmp_path / "config.json")
    )
    check = service.precheck(AppId.DESKTOP, str(image))
    assert check.ok is True
    assert check.warning and "透明度" in check.warning

    state = service.apply(AppId.DESKTOP, str(image), 40)
    assert state.last_error is None
    assert state.verify_warning is None or "透明度" in (state.verify_warning or "")
    assert applied and applied[0][0] == str(image)
