from wallpaper_manager.core.opacity import (
    background_cover_to_ui,
    clamp_ui,
    ui_to_background_cover,
)


def test_ui_to_background_cover_maps_100_to_0_8():
    assert ui_to_background_cover(100) == 0.8


def test_ui_to_background_cover_maps_25():
    assert ui_to_background_cover(25) == 0.2


def test_background_cover_to_ui_roundtrip():
    assert background_cover_to_ui(0.2) == 25
    assert background_cover_to_ui(0.8) == 100


def test_clamp_ui():
    assert clamp_ui(-5) == 0
    assert clamp_ui(140) == 100
    assert clamp_ui(40) == 40
