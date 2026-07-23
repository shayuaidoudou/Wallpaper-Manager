from pathlib import Path

from wallpaper_manager.detect.paths import (
    cursor_settings_path,
    find_jetbrains_other_xml,
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
