from pathlib import Path

from wallpaper_manager.adapters.ghostty import GhosttyAdapter
from wallpaper_manager.adapters.vscode import VsCodeAdapter
from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService
from wallpaper_manager.core.state_store import StateStore


def test_service_applies_path_override_to_adapter(tmp_path: Path):
    settings = tmp_path / "Code" / "User" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}", encoding="utf-8")

    store = StateStore(tmp_path / "wm.json")
    adapter = VsCodeAdapter()
    service = WallpaperService([adapter], store=store)

    # Without override, adapter uses OS default (may or may not exist).
    info = service.set_path_override(AppId.VSCODE, str(settings))
    assert info.using_override is True
    assert info.exists is True
    assert adapter.settings_path == settings.resolve()
    assert adapter.detect() is True

    cleared = service.set_path_override(AppId.VSCODE, None)
    assert cleared.using_override is False
    assert adapter._path_override is None


def test_ghostty_override_reads_custom_config(tmp_path: Path):
    config = tmp_path / "my-ghostty.conf"
    config.write_text(
        "background-image = /pic.png\nbackground-image-opacity = 0.4\n",
        encoding="utf-8",
    )
    store = StateStore(tmp_path / "wm.json")
    adapter = GhosttyAdapter()
    service = WallpaperService([adapter], store=store)
    service.set_path_override(AppId.GHOSTTY, str(config))

    assert adapter.read() == ("/pic.png", 40)
    assert service.path_info(AppId.GHOSTTY).effective_path == str(config.resolve())


def test_overrides_persist_across_service_rebuild(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    store = StateStore(tmp_path / "wm.json")
    store.save_path_override(AppId.VSCODE, str(settings))

    adapter = VsCodeAdapter()
    WallpaperService([adapter], store=store)
    assert adapter.settings_path == settings.resolve()
