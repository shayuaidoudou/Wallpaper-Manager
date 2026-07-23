"""Nuanxin (wallpaper.061129.xyz) gallery client — list metadata, download on demand."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import httpx

from wallpaper_manager.gallery.decrypt import decrypt_blob
from wallpaper_manager.gallery.models import GalleryCategory, GalleryItem

DEFAULT_SERIES = "desktop"
DATA_BASE = "https://wallpaper.061129.xyz/data"
CDN_BASE = "https://cdn.jsdelivr.net/gh/IT-NuanxinPro/nuanXinProPic"
CACHE_BUSTER = "v1.1.24"

DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "referer": "https://wallpaper.061129.xyz/desktop",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    ),
}


def build_cdn_url(item: GalleryItem, *, kind: str = "path") -> str:
    if kind == "thumbnail":
        path = item.thumbnail_path or item.path
    elif kind == "preview":
        path = item.preview_path or item.path
    else:
        path = item.path
    if not path:
        raise ValueError("wallpaper path is empty")
    return f"{CDN_BASE}@{item.cdn_tag}{path}"


class NuanxinGalleryClient:
    def __init__(
        self,
        *,
        series: str = DEFAULT_SERIES,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.series = series
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def list_categories(self) -> list[GalleryCategory]:
        payload = await self._fetch_json(f"{DATA_BASE}/{self.series}/index.json")
        items = self._parse_blob_list(payload)
        categories: list[GalleryCategory] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("category") or entry.get("name") or "").strip()
            if not name:
                continue
            count = int(entry.get("count") or entry.get("total") or 0)
            categories.append(GalleryCategory(name=name, count=count))
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[GalleryCategory] = []
        for cat in categories:
            if cat.name in seen:
                continue
            seen.add(cat.name)
            unique.append(cat)
        return unique

    async def list_wallpapers(self, category: str) -> list[GalleryItem]:
        encoded = quote(category, safe="")
        payload = await self._fetch_json(
            f"{DATA_BASE}/{self.series}/{encoded}.json"
        )
        raw_items = self._parse_blob_list(payload)
        return [
            GalleryItem.from_api(item)
            for item in raw_items
            if isinstance(item, dict)
        ]

    async def download_full(
        self,
        item: GalleryItem,
        dest_dir: Path,
        *,
        skip_if_exists: bool = True,
    ) -> Path:
        dest_dir = Path(dest_dir).expanduser()
        dest_dir.mkdir(parents=True, exist_ok=True)
        save_path = dest_dir / item.filename
        if skip_if_exists and save_path.is_file() and save_path.stat().st_size > 0:
            return save_path

        url = build_cdn_url(item, kind="path")
        response = await self._client.get(url)
        response.raise_for_status()
        save_path.write_bytes(response.content)
        return save_path

    async def _fetch_json(self, url: str) -> dict:
        response = await self._client.get(url, params={"v": CACHE_BUSTER})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("unexpected gallery payload")
        return data

    @staticmethod
    def _parse_blob_list(payload: dict) -> list:
        blob = payload.get("blob")
        if not blob:
            # Some payloads may already be plain lists under data/items
            for key in ("data", "items", "list"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return []
        decrypted = decrypt_blob(str(blob))
        parsed = json.loads(decrypted)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("items", "data", "list", "categories"):
                value = parsed.get(key)
                if isinstance(value, list):
                    return value
        raise ValueError("decrypted gallery blob is not a list")
