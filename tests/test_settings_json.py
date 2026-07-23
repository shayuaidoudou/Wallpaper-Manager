import json
from pathlib import Path

from wallpaper_manager.adapters.settings_json import (
    clear_background_cover,
    read_background_cover,
    write_background_cover,
)
from wallpaper_manager.adapters.vscode import VsCodeAdapter


def test_write_preserves_other_keys(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"editor.fontSize": 20}), encoding="utf-8")

    write_background_cover(settings, "/tmp/w.png", 25)

    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["editor.fontSize"] == 20
    assert data["backgroundCover.imagePath"] == "/tmp/w.png"
    assert data["backgroundCover.opacity"] == 0.2


def test_read_and_clear(tmp_path: Path):
    settings = tmp_path / "settings.json"
    write_background_cover(settings, "/tmp/w.png", 50)

    path, ui = read_background_cover(settings)
    assert path == "/tmp/w.png"
    assert ui == 50

    clear_background_cover(settings)
    path2, ui2 = read_background_cover(settings)
    assert path2 is None
    assert ui2 == 0


def test_vscode_detect(tmp_path: Path):
    settings = tmp_path / "User" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{}", encoding="utf-8")

    adapter = VsCodeAdapter(settings_path=settings)

    assert adapter.detect() is True
