from pathlib import Path

from wallpaper_manager.core.image_service import validate_image_path


def test_missing_file():
    ok, err = validate_image_path("/no/such/file.png")
    assert ok is False
    assert err


def test_valid_png(tmp_path: Path):
    from PIL import Image

    p = tmp_path / "a.png"
    Image.new("RGB", (8, 8), color=(10, 20, 30)).save(p)
    ok, err = validate_image_path(str(p))
    assert ok is True
    assert err is None


def test_reject_txt(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_text("hi", encoding="utf-8")
    ok, err = validate_image_path(str(p))
    assert ok is False
