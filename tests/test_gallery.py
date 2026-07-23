import asyncio
import json

import httpx

from wallpaper_manager.gallery.decrypt import decrypt_blob, encrypt_blob
from wallpaper_manager.gallery.models import GalleryItem
from wallpaper_manager.gallery.nuanxin_client import (
    NuanxinGalleryClient,
    build_cdn_url,
    friendly_network_error,
)


def test_friendly_network_error_forbidden():
    request = httpx.Request("GET", "https://wallpaper.061129.xyz/data/desktop/index.json")
    response = httpx.Response(403, request=request)
    exc = httpx.HTTPStatusError("403", request=request, response=response)
    msg = friendly_network_error(exc)
    assert "节点" in msg and "直连" in msg


def test_friendly_network_error_connect():
    exc = httpx.ConnectError("boom")
    msg = friendly_network_error(exc)
    assert "节点" in msg


def test_friendly_network_error_passthrough():
    assert friendly_network_error(ValueError("plain")) == "plain"


def test_encrypt_decrypt_roundtrip():
    payload = [{"id": "1", "filename": "a.jpg", "category": "风景"}]
    blob = encrypt_blob(json.dumps(payload, ensure_ascii=False))
    assert blob.startswith("v1.")
    assert json.loads(decrypt_blob(blob)) == payload


def test_parse_blob_list_from_payload():
    items = [{"id": "x", "filename": "t.png", "path": "/desktop/t.png", "cdnTag": "v1.2.0"}]
    payload = {"blob": encrypt_blob(json.dumps(items))}
    parsed = NuanxinGalleryClient._parse_blob_list(payload)
    assert parsed == items


def test_build_cdn_url_kinds():
    item = GalleryItem(
        id="1",
        filename="海.jpg",
        category="风景",
        display_title="海",
        path="/desktop/风景/海.jpg",
        thumbnail_path="/desktop/风景/thumbs/海.webp",
        preview_path="/desktop/风景/preview/海.webp",
        cdn_tag="v1.3.48",
    )
    assert build_cdn_url(item, kind="path").endswith("@v1.3.48/desktop/风景/海.jpg")
    assert "thumbs" in build_cdn_url(item, kind="thumbnail")
    assert "preview" in build_cdn_url(item, kind="preview")


def test_gallery_item_from_api():
    item = GalleryItem.from_api(
        {
            "id": "9",
            "filename": "猫.png",
            "category": "萌宠",
            "displayTitle": "橘猫",
            "path": "/a.png",
            "thumbnailPath": "/a.webp",
            "previewPath": "/a-p.webp",
            "cdnTag": "v1.1.9",
            "tags": ["cute", "cat"],
        }
    )
    assert item.display_title == "橘猫"
    assert item.tags == ("cute", "cat")


def test_download_skips_existing(tmp_path, monkeypatch):
    item = GalleryItem(
        id="1",
        filename="local.png",
        category="风景",
        display_title="local",
        path="/x.png",
        thumbnail_path="/x.webp",
        preview_path="/x.webp",
        cdn_tag="v1.1.9",
    )
    target = tmp_path / "local.png"
    target.write_bytes(b"abc")

    client = NuanxinGalleryClient()

    async def boom(*_a, **_k):
        raise AssertionError("should not hit network")

    monkeypatch.setattr(client._client, "get", boom)

    async def _run():
        path = await client.download_full(item, tmp_path)
        await client.aclose()
        return path

    assert asyncio.run(_run()) == target
