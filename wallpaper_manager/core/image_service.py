from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def validate_image_path(path: str) -> tuple[bool, str | None]:
    resolved = Path(path).expanduser().resolve()

    if not resolved.is_file():
        return False, "文件不存在"

    if not is_supported_image(resolved):
        return False, "不支持的图片格式"

    try:
        from PIL import Image

        with Image.open(resolved) as img:
            img.load()
    except Exception:
        return False, "无法读取图片"

    return True, None
