"""Library panel — favorites & recently applied wallpapers, one-click re-apply."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path

import flet as ft

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService
from wallpaper_manager.core.state_store import library_entry_key
from wallpaper_manager.gallery.models import GalleryItem
from wallpaper_manager.gallery.nuanxin_client import (
    NuanxinGalleryClient,
    friendly_network_error,
)
from wallpaper_manager.ui import motion as m
from wallpaper_manager.ui.theme import (
    ACCENT,
    ACCENT_2,
    ERROR,
    HAIRLINE,
    MUTED,
    SUCCESS,
    TEXT,
    opa,
    shell,
)

OnToast = Callable[[str, str], Awaitable[None] | None]
OnApplied = Callable[[AppId, str, int], Awaitable[None] | None]

FAVORITE_COLOR = "#f472b6"

MODES = [("favorites", "收藏"), ("history", "最近应用")]
EMPTY_HINTS = {
    "favorites": "还没有收藏。在图库或「最近应用」里点亮 ♥ 即可收藏。",
    "history": "还没有应用记录。设置一次壁纸后会自动出现在这里。",
}


class LibraryPanel:
    def __init__(
        self,
        page: ft.Page,
        service: WallpaperService,
        app_names: dict[AppId, str],
        *,
        active_app: Callable[[], AppId],
        opacity_for: Callable[[AppId], int],
        on_back: Callable[[], Awaitable[None] | None],
        on_applied: OnApplied,
        on_toast: OnToast,
    ) -> None:
        self.page = page
        self.service = service
        self.app_names = app_names
        self.active_app = active_app
        self.opacity_for = opacity_for
        self.on_back = on_back
        self.on_applied = on_applied
        self.on_toast = on_toast

        self._mode = "favorites"
        self._entries: list[dict] = []
        self._fav_keys: set[str] = set()
        self._busy = False
        self._client: NuanxinGalleryClient | None = None

        self.target_text = ft.Text("", size=13, color=MUTED)
        self.status_text = ft.Text("", size=12, color=MUTED)
        self.mode_row = ft.Row(spacing=8)
        self.grid = ft.GridView(
            expand=True,
            runs_count=3,
            max_extent=210,
            child_aspect_ratio=0.78,
            spacing=12,
            run_spacing=12,
        )
        self.root = self._build()

    def control(self) -> ft.Control:
        return self.root

    def reload(self) -> None:
        app_id = self.active_app()
        self.target_text.value = f"将应用到：{self.app_names[app_id]}"
        self._fav_keys = self.service.favorite_keys()
        self._load_mode()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build(self) -> ft.Control:
        back = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ARROW_BACK_ROUNDED, size=16, color=ACCENT_2),
                    ft.Text("返回", color=ACCENT_2, weight=ft.FontWeight.W_700),
                ],
                spacing=6,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=999,
            border=ft.Border.all(1, ACCENT),
            bgcolor=opa(0.12, ACCENT),
            ink=False,
        )
        m.wire_pressable(
            back,
            page=self.page,
            on_click=lambda _e: self.on_back(),
            hover_scale=1.02,
            press_scale=0.97,
        )

        body = ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "收藏与历史",
                                    size=28,
                                    weight=ft.FontWeight.W_800,
                                    color=TEXT,
                                ),
                                self.target_text,
                            ],
                            spacing=6,
                            tight=True,
                            expand=True,
                        ),
                        back,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                self.mode_row,
                self.status_text,
                ft.Container(content=self.grid, expand=True),
            ],
            spacing=10,
            expand=True,
        )
        return shell(
            ft.Container(content=body, padding=18, expand=True),
            padding=8,
            radius=30,
        )

    def _render_modes(self) -> None:
        chips: list[ft.Control] = []
        for mode, label in MODES:
            selected = mode == self._mode
            chip = ft.Container(
                content=ft.Text(
                    label,
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=TEXT if selected else MUTED,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border_radius=999,
                bgcolor=opa(0.22, ACCENT) if selected else opa(0.35, "#141022"),
                border=ft.Border.all(1, ACCENT if selected else HAIRLINE),
                ink=False,
            )
            m.wire_pressable(
                chip,
                page=self.page,
                on_click=self._mode_handler(mode),
                hover_scale=1.03,
                press_scale=0.97,
            )
            chips.append(chip)
        self.mode_row.controls = chips

    def _mode_handler(self, mode: str):
        def _handler(_event: ft.ControlEvent) -> None:
            if mode == self._mode:
                return
            self._mode = mode
            self._load_mode()
            self.page.update()

        return _handler

    def _load_mode(self) -> None:
        self._render_modes()
        if self._mode == "favorites":
            self._entries = self.service.favorites()
        else:
            self._entries = self.service.history()
        self._render_grid()
        if not self._entries:
            self.status_text.value = EMPTY_HINTS[self._mode]
        else:
            label = dict(MODES)[self._mode]
            self.status_text.value = f"{label} · {len(self._entries)} 张"
        self.status_text.color = MUTED

    def _render_grid(self) -> None:
        self.grid.controls = [self._make_card(e) for e in self._entries[:120]]

    def _make_card(self, entry: dict) -> ft.Control:
        thumb_src = entry.get("thumb") or entry.get("image_path") or ""
        star_on = library_entry_key(entry) in self._fav_keys
        star = ft.Container(
            content=ft.Icon(
                ft.Icons.FAVORITE_ROUNDED if star_on else ft.Icons.FAVORITE_BORDER_ROUNDED,
                size=16,
                color=FAVORITE_COLOR if star_on else MUTED,
            ),
            width=30,
            height=30,
            border_radius=15,
            alignment=ft.Alignment.CENTER,
            bgcolor=opa(0.6, "#0d0a16"),
            border=ft.Border.all(1, HAIRLINE),
            right=6,
            top=6,
            ink=False,
        )
        m.wire_pressable(
            star,
            page=self.page,
            on_click=self._star_handler(entry, star),
            hover_scale=1.08,
            press_scale=0.92,
        )
        apply_btn = ft.Container(
            content=ft.Text("应用", size=12, weight=ft.FontWeight.W_700, color=TEXT),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            border_radius=12,
            bgcolor=opa(0.28, ACCENT),
            border=ft.Border.all(1, ACCENT),
            alignment=ft.Alignment.CENTER,
            ink=False,
        )
        m.wire_pressable(
            apply_btn,
            page=self.page,
            on_click=self._apply_handler(entry, apply_btn),
            hover_scale=1.03,
            press_scale=0.96,
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Stack(
                            [
                                ft.Image(
                                    src=thumb_src,
                                    fit=ft.BoxFit.COVER,
                                    expand=True,
                                    border_radius=12,
                                ),
                                star,
                            ],
                            fit=ft.StackFit.EXPAND,
                        ),
                        expand=True,
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        bgcolor=opa(0.4, "#120e1c"),
                    ),
                    ft.Text(
                        str(entry.get("title") or "未命名"),
                        size=12,
                        color=TEXT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        self._subtitle(entry),
                        size=11,
                        color=MUTED,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    apply_btn,
                ],
                spacing=6,
                expand=True,
            ),
            padding=10,
            border_radius=16,
            border=ft.Border.all(1, HAIRLINE),
            bgcolor=opa(0.35, "#141022"),
        )

    def _subtitle(self, entry: dict) -> str:
        parts: list[str] = []
        app_raw = entry.get("app")
        if app_raw:
            try:
                parts.append(self.app_names[AppId(app_raw)])
            except ValueError:
                pass
        applied_at = entry.get("applied_at")
        if applied_at:
            try:
                parts.append(
                    datetime.fromisoformat(str(applied_at)).strftime("%m-%d %H:%M")
                )
            except ValueError:
                pass
        if not parts:
            parts.append("在线图库" if entry.get("gallery") else "本地图片")
        return " · ".join(parts)

    def _star_handler(self, entry: dict, star: ft.Container):
        def _handler(_event: ft.ControlEvent) -> None:
            now_favorite = self.service.toggle_favorite(entry)
            key = library_entry_key(entry)
            if now_favorite:
                self._fav_keys.add(key)
            else:
                self._fav_keys.discard(key)
            if self._mode == "favorites" and not now_favorite:
                self._load_mode()
            else:
                icon = star.content
                assert isinstance(icon, ft.Icon)
                icon.name = (
                    ft.Icons.FAVORITE_ROUNDED
                    if now_favorite
                    else ft.Icons.FAVORITE_BORDER_ROUNDED
                )
                icon.color = FAVORITE_COLOR if now_favorite else MUTED
            self.page.update()

        return _handler

    def _apply_handler(self, entry: dict, button: ft.Container):
        async def _handler(_event: ft.ControlEvent) -> None:
            if self._busy:
                return
            self._busy = True
            app_id = self.active_app()
            opacity = self.opacity_for(app_id)
            original = button.content
            button.content = ft.Text(
                "应用中…", size=12, color=MUTED, weight=ft.FontWeight.W_700
            )
            self.page.update()
            try:
                result = await self._apply_entry(app_id, entry, opacity)
                if result is None:
                    await self._emit_toast(
                        "图片文件已不存在，无法重新应用。", ERROR
                    )
                    return
                if result.last_error:
                    await self._emit_toast(f"失败：{result.last_error}", ERROR)
                    return
                path = result.image_path or ""
                applied = self.on_applied(app_id, path, opacity)
                if isinstance(applied, Awaitable):
                    await applied
                await self._emit_toast(
                    f"已应用到 {self.app_names[app_id]}", SUCCESS
                )
                back = self.on_back()
                if isinstance(back, Awaitable):
                    await back
            except Exception as exc:
                await self._emit_toast(f"失败：{friendly_network_error(exc)}", ERROR)
            finally:
                button.content = original
                self._busy = False
                self.page.update()

        return _handler

    async def _apply_entry(self, app_id: AppId, entry: dict, opacity: int):
        local = entry.get("image_path")
        gallery_meta = entry.get("gallery")
        if local and Path(str(local)).is_file():
            base = {k: entry.get(k) for k in ("source", "title", "thumb", "gallery")}
            return self.service.apply(
                app_id, str(local), opacity, history_entry=base
            )
        if isinstance(gallery_meta, dict) and gallery_meta.get("path"):
            if self._client is None:
                self._client = NuanxinGalleryClient()
            item = GalleryItem.from_dict(gallery_meta)
            return await self.service.apply_gallery_item(
                app_id, item, opacity, client=self._client
            )
        return None

    async def _emit_toast(self, message: str, color: str) -> None:
        result = self.on_toast(message, color)
        if isinstance(result, Awaitable):
            await result
