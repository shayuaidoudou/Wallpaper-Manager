"""Online gallery panel — browse Nuanxin wallpapers, download on apply."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import flet as ft

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService
from wallpaper_manager.gallery.models import GalleryItem
from wallpaper_manager.gallery.nuanxin_client import NuanxinGalleryClient, build_cdn_url
from wallpaper_manager.ui import motion as m
from wallpaper_manager.ui.theme import (
    ACCENT,
    ACCENT_2,
    ERROR,
    HAIRLINE,
    MUTED,
    PANEL_BORDER,
    SUCCESS,
    TEXT,
    opa,
    shell,
)

OnToast = Callable[[str, str], Awaitable[None] | None]
OnApplied = Callable[[AppId, str, int], Awaitable[None] | None]


class GalleryPanel:
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

        self._client = NuanxinGalleryClient()
        self._categories: list[str] = []
        self._items: list[GalleryItem] = []
        self._selected_category: str | None = None
        self._busy = False
        self._load_token = 0

        self.target_text = ft.Text("", size=13, color=MUTED)
        self.dir_text = ft.Text("", size=12, color=MUTED)
        self.status_text = ft.Text("正在加载分类…", size=12, color=MUTED)
        self.search_field = ft.TextField(
            hint_text="搜索标题 / 标签",
            label_style=ft.TextStyle(color=MUTED, size=11),
            color=TEXT,
            bgcolor=opa(0.88, "#0c0916"),
            border_color=PANEL_BORDER,
            focused_border_color=ACCENT,
            border_radius=14,
            filled=True,
            cursor_color=ACCENT,
            on_change=self._on_search_change,
        )
        self.category_row = ft.Row(spacing=8, scroll=ft.ScrollMode.AUTO)
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

    async def reload(self) -> None:
        app_id = self.active_app()
        self.target_text.value = f"将应用到：{self.app_names[app_id]}"
        self.dir_text.value = f"下载目录：{self.service.gallery_download_dir()}"
        self.status_text.value = "正在加载分类…"
        self.page.update()
        try:
            cats = await self._client.list_categories()
            self._categories = [c.name for c in cats] or [
                "风景",
                "动漫",
                "游戏",
                "插画",
                "萌宠",
                "人像",
                "影视",
            ]
            self._render_categories()
            if not self._selected_category or self._selected_category not in self._categories:
                self._selected_category = self._categories[0]
            await self._load_category(self._selected_category)
        except Exception as exc:
            self.status_text.value = f"加载失败：{exc}"
            self.status_text.color = ERROR
            self.page.update()

    async def aclose(self) -> None:
        await self._client.aclose()

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
                                    "在线图库",
                                    size=28,
                                    weight=ft.FontWeight.W_800,
                                    color=TEXT,
                                ),
                                self.target_text,
                                self.dir_text,
                            ],
                            spacing=6,
                            tight=True,
                            expand=True,
                        ),
                        back,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                self.category_row,
                self.search_field,
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

    def _render_categories(self) -> None:
        chips: list[ft.Control] = []
        for name in self._categories:
            selected = name == self._selected_category
            chip = ft.Container(
                content=ft.Text(
                    name,
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=TEXT if selected else MUTED,
                ),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border_radius=999,
                bgcolor=opa(0.22, ACCENT) if selected else opa(0.35, "#141022"),
                border=ft.Border.all(1, ACCENT if selected else HAIRLINE),
                ink=False,
                data=name,
            )
            m.wire_pressable(
                chip,
                page=self.page,
                on_click=self._category_handler(name),
                hover_scale=1.03,
                press_scale=0.97,
            )
            chips.append(chip)
        self.category_row.controls = chips

    def _category_handler(self, name: str):
        async def _handler(_event: ft.ControlEvent) -> None:
            if self._busy or name == self._selected_category:
                return
            self._selected_category = name
            self._render_categories()
            self.page.update()
            await self._load_category(name)

        return _handler

    async def _load_category(self, name: str) -> None:
        self._load_token += 1
        token = self._load_token
        self.status_text.value = f"正在加载「{name}」…"
        self.status_text.color = MUTED
        self.grid.controls = []
        self.page.update()
        try:
            items = await self._client.list_wallpapers(name)
            if token != self._load_token:
                return
            self._items = items
            self._render_grid(self._filtered_items())
            self.status_text.value = f"{name} · {len(items)} 张（仅加载缩略图）"
            self.status_text.color = MUTED
        except Exception as exc:
            if token != self._load_token:
                return
            self.status_text.value = f"加载「{name}」失败：{exc}"
            self.status_text.color = ERROR
        self.page.update()

    def _filtered_items(self) -> list[GalleryItem]:
        query = (self.search_field.value or "").strip().lower()
        if not query:
            return self._items
        out: list[GalleryItem] = []
        for item in self._items:
            hay = " ".join(
                [item.display_title, item.filename, " ".join(item.tags)]
            ).lower()
            if query in hay:
                out.append(item)
        return out

    def _on_search_change(self, _event: ft.ControlEvent) -> None:
        filtered = self._filtered_items()
        self._render_grid(filtered)
        cat = self._selected_category or ""
        self.status_text.value = f"{cat} · 显示 {len(filtered)}/{len(self._items)}"
        self.page.update()

    def _render_grid(self, items: list[GalleryItem]) -> None:
        cards: list[ft.Control] = []
        for item in items[:120]:
            cards.append(self._make_card(item))
        self.grid.controls = cards

    def _make_card(self, item: GalleryItem) -> ft.Control:
        thumb = build_cdn_url(item, kind="thumbnail")
        apply_btn = ft.Container(
            content=ft.Text("设为壁纸", size=12, weight=ft.FontWeight.W_700, color=TEXT),
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
            on_click=self._apply_handler(item, apply_btn),
            hover_scale=1.03,
            press_scale=0.96,
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Image(
                            src=thumb,
                            fit=ft.BoxFit.COVER,
                            expand=True,
                            border_radius=12,
                        ),
                        expand=True,
                        border_radius=12,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        bgcolor=opa(0.4, "#120e1c"),
                    ),
                    ft.Text(
                        item.display_title,
                        size=12,
                        color=TEXT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        item.resolution or item.category,
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

    def _apply_handler(self, item: GalleryItem, button: ft.Container):
        async def _handler(_event: ft.ControlEvent) -> None:
            if self._busy:
                return
            self._busy = True
            app_id = self.active_app()
            opacity = self.opacity_for(app_id)
            original = button.content
            button.content = ft.Text("下载中…", size=12, color=MUTED, weight=ft.FontWeight.W_700)
            self.page.update()
            try:
                result = await self.service.apply_gallery_item(
                    app_id, item, opacity, client=self._client
                )
                if result.last_error:
                    await self._emit_toast(f"失败：{result.last_error}", ERROR)
                    return
                path = result.image_path or ""
                applied = self.on_applied(app_id, path, opacity)
                if isinstance(applied, Awaitable):
                    await applied
                await self._emit_toast(
                    f"已下载并应用到 {self.app_names[app_id]}",
                    SUCCESS,
                )
                back = self.on_back()
                if isinstance(back, Awaitable):
                    await back
            except Exception as exc:
                await self._emit_toast(f"失败：{exc}", ERROR)
            finally:
                button.content = original
                self._busy = False
                self.page.update()

        return _handler

    async def _emit_toast(self, message: str, color: str) -> None:
        result = self.on_toast(message, color)
        if isinstance(result, Awaitable):
            await result
