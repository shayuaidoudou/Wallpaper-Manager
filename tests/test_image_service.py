from pathlib import Path

from wallpaper_manager.core.image_service import validate_image_path


def test_missing_file():
    ok, err = validate_image_path("/no/such/file.png")
    assert ok is False
    assert err == "文件不存在"


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
    assert err == "不支持的图片格式"


def test_reject_corrupt_png(tmp_path: Path):
    p = tmp_path / "bad.png"
    p.write_bytes(b"not-a-valid-png")
    ok, err = validate_image_path(str(p))
    assert ok is False
    assert err == "无法读取图片"


def test_ensure_preview_image_downscales_large_photo(tmp_path: Path):
    from PIL import Image

    from wallpaper_manager.core.image_service import ensure_preview_image

    source = tmp_path / "huge.png"
    Image.new("RGB", (4000, 2500), color=(20, 40, 60)).save(source)
    cache = tmp_path / "cache"

    preview = Path(ensure_preview_image(source, cache_dir=cache, max_edge=800))
    assert preview.is_file()
    assert preview != source.resolve()
    with Image.open(preview) as img:
        assert max(img.size) <= 800

    # Second call reuses the cached file.
    again = Path(ensure_preview_image(source, cache_dir=cache, max_edge=800))
    assert again == preview
