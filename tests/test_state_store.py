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
