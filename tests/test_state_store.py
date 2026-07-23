from pathlib import Path

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.state_store import StateStore


def test_roundtrip(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.VSCODE, "/tmp/a.png", 35)
    data = store.load()
    assert data[AppId.VSCODE]["image_path"] == "/tmp/a.png"
    assert data[AppId.VSCODE]["opacity_ui"] == 35


def test_clear_app(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_app(AppId.CURSOR, "/tmp/b.png", 20)
    store.clear_app(AppId.CURSOR)
    assert AppId.CURSOR not in store.load()


def test_path_override_roundtrip(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.save_path_override(AppId.GHOSTTY, "/custom/config.ghostty")
    store.save_path_override(AppId.VSCODE, "  /custom/settings.json  ")

    overrides = store.load_path_overrides()
    assert overrides[AppId.GHOSTTY] == "/custom/config.ghostty"
    assert overrides[AppId.VSCODE] == "/custom/settings.json"

    store.save_path_override(AppId.VSCODE, None)
    overrides = store.load_path_overrides()
    assert AppId.VSCODE not in overrides
    assert AppId.GHOSTTY in overrides
