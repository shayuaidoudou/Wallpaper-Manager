"""Gallery domain models for the Nuanxin wallpaper source."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GalleryCategory:
    name: str
    count: int = 0


@dataclass(frozen=True)
class GalleryItem:
    id: str
    filename: str
    category: str
    display_title: str
    path: str
    thumbnail_path: str
    preview_path: str
    cdn_tag: str
    resolution: str = ""
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> GalleryItem:
        """Rebuild from to_dict() output (JSON round-trip safe)."""
        return cls(
            id=str(data.get("id") or ""),
            filename=str(data.get("filename") or "wallpaper.jpg"),
            category=str(data.get("category") or ""),
            display_title=str(data.get("display_title") or "未命名"),
            path=str(data.get("path") or ""),
            thumbnail_path=str(data.get("thumbnail_path") or data.get("path") or ""),
            preview_path=str(data.get("preview_path") or data.get("path") or ""),
            cdn_tag=str(data.get("cdn_tag") or "v1.1.9"),
            resolution=str(data.get("resolution") or ""),
            tags=tuple(str(t) for t in (data.get("tags") or [])),
        )

    @classmethod
    def from_api(cls, raw: dict) -> GalleryItem:
        tags = raw.get("tags") or raw.get("keywords") or []
        if isinstance(tags, str):
            tag_tuple = tuple(t.strip() for t in tags.split(",") if t.strip())
        else:
            tag_tuple = tuple(str(t) for t in tags)
        resolution_raw = raw.get("resolution")
        if isinstance(resolution_raw, dict):
            label = resolution_raw.get("label")
            if label:
                resolution = str(label)
            else:
                w = resolution_raw.get("width")
                h = resolution_raw.get("height")
                resolution = f"{w}x{h}" if w and h else ""
        else:
            resolution = str(resolution_raw or "")
        return cls(
            id=str(raw.get("id") or raw.get("filename") or ""),
            filename=str(raw.get("filename") or "wallpaper.jpg"),
            category=str(raw.get("category") or ""),
            display_title=str(
                raw.get("displayTitle") or raw.get("filename") or "未命名"
            ),
            path=str(raw.get("path") or ""),
            thumbnail_path=str(raw.get("thumbnailPath") or raw.get("path") or ""),
            preview_path=str(raw.get("previewPath") or raw.get("path") or ""),
            cdn_tag=str(raw.get("cdnTag") or "v1.1.9"),
            resolution=resolution,
            tags=tag_tuple,
        )
