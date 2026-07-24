from __future__ import annotations

from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
PREVIEW_CACHE_DIR = Path.home() / ".wallpaper-manager" / "preview-cache"
PREVIEW_MAX_EDGE = 1280
PREVIEW_JPEG_QUALITY = 82


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


def ensure_preview_image(
    path: str | Path,
    *,
    cache_dir: Path | None = None,
    max_edge: int = PREVIEW_MAX_EDGE,
) -> str:
    """Return a local path suitable for UI preview (downscaled JPEG when needed).

    The original file is never modified. Small images are returned as-is.
    """
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        return str(source)

    try:
        from PIL import Image

        with Image.open(source) as img:
            width, height = img.size
            if max(width, height) <= max_edge and source.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
            }:
                # Already small enough for the preview pane.
                if source.stat().st_size <= 2_500_000:
                    return str(source)

            root = cache_dir if cache_dir is not None else PREVIEW_CACHE_DIR
            root.mkdir(parents=True, exist_ok=True)
            stamp = int(source.stat().st_mtime_ns)
            dest = root / f"{source.stem}-{stamp}-{max_edge}.jpg"
            if dest.is_file() and dest.stat().st_size > 0:
                return str(dest)

            work = img.convert("RGB") if img.mode not in ("RGB", "L") else img.copy()
            work.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            work.save(dest, format="JPEG", quality=PREVIEW_JPEG_QUALITY, optimize=True)
            return str(dest)
    except Exception:
        return str(source)
