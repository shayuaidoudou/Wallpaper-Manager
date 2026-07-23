from pathlib import Path
import sys

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.path_config import config_dir_hint, resolve_config_from_user_selection


def test_resolve_vscode_from_user_folder(tmp_path: Path):
    user = tmp_path / "Code" / "User"
    user.mkdir(parents=True)
    settings = user / "settings.json"
    settings.write_text("{}", encoding="utf-8")

    resolved, error = resolve_config_from_user_selection(AppId.VSCODE, tmp_path / "Code")
    assert error is None
    assert resolved == settings.resolve()


def test_resolve_jetbrains_from_product_folder(tmp_path: Path):
    product = tmp_path / "IntelliJIdea2025.2"
    options = product / "options"
    options.mkdir(parents=True)
    other = options / "other.xml"
    other.write_text("<application/>", encoding="utf-8")

    resolved, error = resolve_config_from_user_selection(AppId.IDEA, product)
    assert error is None
    assert resolved == other.resolve()


def test_resolve_ghostty_from_support_folder(tmp_path: Path):
    support = tmp_path / "com.mitchellh.ghostty"
    support.mkdir()
    config = support / "config.ghostty"
    config.write_text("font-size = 14\n", encoding="utf-8")

    resolved, error = resolve_config_from_user_selection(AppId.GHOSTTY, support)
    assert error is None
    assert resolved == config.resolve()


def test_resolve_accepts_direct_file(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    resolved, error = resolve_config_from_user_selection(AppId.CURSOR, settings)
    assert error is None
    assert resolved == settings.resolve()


def test_resolve_unknown_folder_returns_error(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    resolved, error = resolve_config_from_user_selection(AppId.CURSOR, empty)
    assert resolved is None
    assert error is not None
    assert "未找到" in error


def test_windows_dir_hints(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert "%APPDATA%" in config_dir_hint(AppId.CURSOR)
    assert "ghostty" in config_dir_hint(AppId.GHOSTTY).lower()


def test_windows_program_files_maps_to_auto(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sys, "platform", "win32")
    install = tmp_path / "Program Files" / "Cursor"
    install.mkdir(parents=True)
    # Without a real APPDATA config, auto may still return a Path; ensure no hard error.
    resolved, error = resolve_config_from_user_selection(AppId.CURSOR, install)
    # Either mapped to auto path or gave a clear install-dir error.
    assert (resolved is not None and error is None) or (
        resolved is None and error is not None and "安装目录" in error
    )
