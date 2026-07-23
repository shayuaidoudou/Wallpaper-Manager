from pathlib import Path

from wallpaper_manager.detect.paths import (
    cursor_settings_path,
    find_ghostty_config,
    find_jetbrains_other_xml,
    ghostty_config_candidates,
    vscode_settings_path,
)


def test_vscode_settings_path_macos(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    p = vscode_settings_path(tmp_path)
    assert p == tmp_path / "Library/Application Support/Code/User/settings.json"


def test_cursor_settings_path_windows(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData/Roaming"))
    p = cursor_settings_path(tmp_path)
    assert p == tmp_path / "AppData/Roaming/Cursor/User/settings.json"


def test_find_jetbrains_prefers_newest(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    root = tmp_path / "Library/Application Support/JetBrains"
    older = root / "IntelliJIdea2024.3/options"
    newer = root / "IntelliJIdea2025.2/options"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "other.xml").write_text("<app/>", encoding="utf-8")
    (newer / "other.xml").write_text("<app/>", encoding="utf-8")
    found = find_jetbrains_other_xml("IntelliJIdea", tmp_path)
    assert found == newer / "other.xml"


def test_find_jetbrains_returns_prospective_path_when_other_xml_missing(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    root = tmp_path / "Library/Application Support/JetBrains"
    (root / "IntelliJIdea2025.9").mkdir(parents=True)
    newest = root / "IntelliJIdea2025.10"
    newest.mkdir()

    found = find_jetbrains_other_xml("IntelliJIdea", tmp_path)

    assert found == newest / "options/other.xml"


def test_ghostty_prefers_macos_config_ghostty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    support = tmp_path / "Library/Application Support/com.mitchellh.ghostty"
    support.mkdir(parents=True)
    preferred = support / "config.ghostty"
    preferred.write_text("font-size = 16\n", encoding="utf-8")
    (tmp_path / ".config/ghostty").mkdir(parents=True)
    (tmp_path / ".config/ghostty/config").write_text("theme = dark\n", encoding="utf-8")

    assert find_ghostty_config(tmp_path) == preferred
    assert ghostty_config_candidates(tmp_path)[0] == preferred


def test_ghostty_falls_back_to_xdg_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("wallpaper_manager.detect.paths.sys.platform", "darwin")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    xdg = tmp_path / ".config/ghostty"
    xdg.mkdir(parents=True)
    config = xdg / "config"
    config.write_text("font-size = 14\n", encoding="utf-8")

    assert find_ghostty_config(tmp_path) == config
