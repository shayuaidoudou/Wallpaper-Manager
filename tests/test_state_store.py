from pathlib import Path

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.state_store import (
    HISTORY_LIMIT,
    StateStore,
    library_entry_key,
)


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


def _entry(path: str, *, gallery_path: str | None = None, title: str = "t") -> dict:
    return {
        "source": "gallery" if gallery_path else "local",
        "title": title,
        "image_path": path or None,
        "thumb": path,
        "gallery": {"path": gallery_path} if gallery_path else None,
    }


def test_library_entry_key_prefers_gallery_identity():
    assert library_entry_key(_entry("/tmp/a.png")) == "l:/tmp/a.png"
    assert library_entry_key(_entry("/tmp/a.png", gallery_path="/g/a.jpg")) == "g:/g/a.jpg"
    # Same wallpaper favorited pre-download and applied post-download share a key.
    assert library_entry_key(_entry("", gallery_path="/g/a.jpg")) == "g:/g/a.jpg"


def test_history_dedupes_and_moves_to_front(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    store.add_history(_entry("/tmp/a.png", title="a"))
    store.add_history(_entry("/tmp/b.png", title="b"))
    store.add_history(_entry("/tmp/a.png", title="a-again"))

    history = store.load_history()
    assert [e["title"] for e in history] == ["a-again", "b"]


def test_history_is_capped(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    for i in range(HISTORY_LIMIT + 5):
        store.add_history(_entry(f"/tmp/{i}.png"))
    assert len(store.load_history()) == HISTORY_LIMIT


def test_toggle_favorite_roundtrip(tmp_path: Path):
    store = StateStore(tmp_path / "config.json")
    entry = _entry("/tmp/a.png")

    assert store.toggle_favorite(entry) is True
    assert store.favorite_keys() == {"l:/tmp/a.png"}
    assert [e["image_path"] for e in store.load_favorites()] == ["/tmp/a.png"]

    assert store.toggle_favorite(entry) is False
    assert store.load_favorites() == []
    assert store.favorite_keys() == set()
