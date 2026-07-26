from pathlib import Path

from wallpaper_manager.adapters.jetbrains import JetBrainsAdapter
from wallpaper_manager.core.models import (
    AppId,
    JETBRAINS_APP_IDS,
    JETBRAINS_PRODUCT_PREFIXES,
)
from wallpaper_manager.core.path_config import CONFIG_FILE_LABELS, config_dir_hint
from wallpaper_manager.detect.paths import find_jetbrains_other_xml


def test_family_registry_covers_all_jetbrains_apps():
    assert set(JETBRAINS_APP_IDS) == {
        AppId.IDEA,
        AppId.PYCHARM,
        AppId.WEBSTORM,
        AppId.PHPSTORM,
        AppId.GOLAND,
        AppId.CLION,
        AppId.RIDER,
        AppId.DATAGRIP,
    }
    for app_id in JETBRAINS_APP_IDS:
        assert JETBRAINS_PRODUCT_PREFIXES[app_id]
        assert CONFIG_FILE_LABELS[app_id] == "other.xml"
        assert "JetBrains" in config_dir_hint(app_id)


def test_adapter_default_prefixes():
    assert JetBrainsAdapter(AppId.WEBSTORM).product_prefix == "WebStorm"
    assert JetBrainsAdapter(AppId.PHPSTORM).product_prefix == "PhpStorm"
    assert JetBrainsAdapter(AppId.GOLAND).product_prefix == "GoLand"
    assert JetBrainsAdapter(AppId.CLION).product_prefix == "CLion"
    assert JetBrainsAdapter(AppId.RIDER).product_prefix == "Rider"
    assert JetBrainsAdapter(AppId.DATAGRIP).product_prefix == "DataGrip"


def test_webstorm_apply_read_clear_roundtrip(tmp_path: Path):
    xml = tmp_path / "WebStorm2025.2" / "options" / "other.xml"
    adapter = JetBrainsAdapter(AppId.WEBSTORM, other_xml=xml)
    adapter.apply("/tmp/wall.png", 40)
    path, opacity = adapter.read()
    assert path == "/tmp/wall.png"
    assert opacity == 40
    adapter.clear()
    assert adapter.read() == (None, 0)


def test_find_newest_goland_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    root = tmp_path / "Library/Application Support/JetBrains"
    older = root / "GoLand2024.3" / "options"
    newer = root / "GoLand2025.2" / "options"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "other.xml").write_text("<application/>", encoding="utf-8")
    (newer / "other.xml").write_text("<application/>", encoding="utf-8")
    found = find_jetbrains_other_xml("GoLand", tmp_path)
    assert found == newer / "other.xml"


def test_tab_order_keeps_ghostty_last():
    order = list(AppId)
    assert order[0] is AppId.VSCODE
    assert order[-1] is AppId.GHOSTTY
    assert len(order) == 11
