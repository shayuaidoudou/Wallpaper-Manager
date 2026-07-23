from wallpaper_manager.core.models import AppId
from wallpaper_manager.ui.app import (
    APP_NAMES,
    Draft,
    apply_success_message,
    can_apply,
    normalize_image_path,
)
from wallpaper_manager.ui.theme import ACCENT, ACCENT_2, BG, MUTED, PANEL, TEXT


def test_midnight_glass_theme_constants():
    assert (BG, PANEL, ACCENT, ACCENT_2, TEXT, MUTED) == (
        "#0b0d12",
        "#141a22",
        "#38bdf8",
        "#22d3ee",
        "#eef2f7",
        "#8b95a8",
    )


def test_apply_requires_installed_app_and_valid_image():
    valid = Draft("/tmp/wallpaper.png", 35, True, None)
    invalid = Draft("/tmp/missing.png", 35, True, "文件不存在")
    uninstalled = Draft("/tmp/wallpaper.png", 35, False, None)

    assert can_apply(valid) is True
    assert can_apply(invalid) is False
    assert can_apply(uninstalled) is False


def test_success_message_has_target_specific_reload_hint():
    assert "重新加载窗口" in apply_success_message(AppId.VSCODE)
    assert "重新启动 IDE" in apply_success_message(AppId.IDEA)
    assert APP_NAMES[AppId.PYCHARM] == "PyCharm"


def test_normalize_image_path_returns_resolved_absolute_path(tmp_path, monkeypatch):
    image = tmp_path / "wallpaper.png"
    image.touch()
    monkeypatch.chdir(tmp_path)

    assert normalize_image_path("./wallpaper.png") == str(image.resolve())
