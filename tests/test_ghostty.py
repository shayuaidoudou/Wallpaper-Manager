from pathlib import Path

from wallpaper_manager.adapters.ghostty import (
    GhosttyAdapter,
    clear_ghostty_wallpaper,
    read_ghostty_wallpaper,
    write_ghostty_wallpaper,
)
from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.opacity import ghostty_to_ui, ui_to_ghostty


SAMPLE = """# 图片配置
background-image = /old/path.jpg
background-image-opacity = 0.5
background-image-position = center
background-image-fit = cover

# 整体透明度 + 毛玻璃模糊
background-blur-radius = 20

# Split 分屏快捷键
keybind = cmd+d=new_split:right
keybind = cmd+shift+d=new_split:down

# 字体大小
font-size = 16
"""


def test_ghostty_opacity_roundtrip():
    assert ui_to_ghostty(50) == 0.5
    assert ghostty_to_ui(0.5) == 50
    assert ui_to_ghostty(100) == 1.0
    assert ghostty_to_ui(1.0) == 100


def test_write_preserves_keybinds_and_blur(tmp_path: Path):
    config = tmp_path / "config.ghostty"
    config.write_text(SAMPLE, encoding="utf-8")

    write_ghostty_wallpaper(config, "/new/wallpaper.png", 35)
    text = config.read_text(encoding="utf-8")

    assert "background-image = /new/wallpaper.png" in text
    assert "background-image-opacity = 0.35" in text
    assert "background-image-position = center" in text
    assert "background-image-fit = cover" in text
    assert "background-blur-radius = 20" in text
    assert "keybind = cmd+d=new_split:right" in text
    assert "keybind = cmd+shift+d=new_split:down" in text
    assert "font-size = 16" in text
    assert text.count("background-image =") == 1


def test_read_and_clear_roundtrip(tmp_path: Path):
    config = tmp_path / "config.ghostty"
    config.write_text(SAMPLE, encoding="utf-8")

    path, opacity = read_ghostty_wallpaper(config)
    assert path == "/old/path.jpg"
    assert opacity == 50

    clear_ghostty_wallpaper(config)
    text = config.read_text(encoding="utf-8")
    assert "background-image" not in text
    assert "background-blur-radius = 20" in text
    assert "keybind = cmd+d=new_split:right" in text
    assert read_ghostty_wallpaper(config) == (None, 20)


def test_write_creates_file_when_missing(tmp_path: Path):
    config = tmp_path / "ghostty" / "config.ghostty"
    write_ghostty_wallpaper(config, "/Users/me/pic.jpg", 50)
    text = config.read_text(encoding="utf-8")
    assert "background-image = /Users/me/pic.jpg" in text
    assert "background-image-opacity = 0.5" in text


def test_adapter_detect_and_apply(tmp_path: Path):
    config = tmp_path / "config.ghostty"
    config.write_text("font-size = 16\n", encoding="utf-8")
    adapter = GhosttyAdapter(config_path=config)

    assert adapter.app_id is AppId.GHOSTTY
    assert adapter.detect() is True
    adapter.apply("/tmp/a.png", 40)
    assert adapter.read() == ("/tmp/a.png", 40)
    adapter.clear()
    assert adapter.read() == (None, 20)
    assert "font-size = 16" in config.read_text(encoding="utf-8")
