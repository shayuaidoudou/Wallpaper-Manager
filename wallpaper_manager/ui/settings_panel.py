"""Path configuration panel — manual IDE/config file locations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService
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


class SettingsPanel:
    def __init__(
        self,
        page: ft.Page,
        service: WallpaperService,
        app_names: dict[AppId, str],
        app_order: list[AppId],
        *,
        on_back: Callable[[], Awaitable[None] | None],
        on_paths_changed: Callable[[], None],
        on_toast: OnToast,
    ) -> None:
        self.page = page
        self.service = service
        self.app_names = app_names
        self.app_order = app_order
        self.on_back = on_back
        self.on_paths_changed = on_paths_changed
        self.on_toast = on_toast
        self._fields: dict[AppId, ft.TextField] = {}
        self._status: dict[AppId, ft.Text] = {}
        self._pick_target: AppId | None = None
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)
        self.root = self._build()

    def control(self) -> ft.Control:
        return self.root

    def reload(self) -> None:
        for app_id in self.app_order:
            info = self.service.path_info(app_id)
            field = self._fields[app_id]
            field.value = info.override_path or info.auto_path or ""
            field.hint_text = info.hint
            self._status[app_id].value = self._status_text(info)
            self._status[app_id].color = SUCCESS if info.exists else ERROR
        self.page.update()

    def _status_text(self, info) -> str:
        mode = "手动" if info.using_override else "自动检测"
        state = "已找到" if info.exists else "未找到文件"
        return f"{mode} · {state} · 目标：{info.label}"

    def _build(self) -> ft.Control:
        rows: list[ft.Control] = []
        for app_id in self.app_order:
            info = self.service.path_info(app_id)
            field = ft.TextField(
                value=info.override_path or info.auto_path or "",
                hint_text=info.hint,
                color=TEXT,
                label_style=ft.TextStyle(color=MUTED, size=12),
                bgcolor=opa(0.88, "#0c0916"),
                border_color=PANEL_BORDER,
                focused_border_color=ACCENT,
                border_radius=14,
                filled=True,
                cursor_color=ACCENT,
                expand=True,
            )
            status = ft.Text(
                self._status_text(info),
                size=11,
                color=SUCCESS if info.exists else ERROR,
            )
            self._fields[app_id] = field
            self._status[app_id] = status

            browse = ft.Container(
                content=ft.Text("浏览", color=ACCENT_2, weight=ft.FontWeight.W_700),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                border_radius=14,
                border=ft.Border.all(1, ACCENT),
                bgcolor=opa(0.12, ACCENT),
                ink=False,
            )
            reset = ft.Container(
                content=ft.Text("自动", color=MUTED, weight=ft.FontWeight.W_600),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                border_radius=14,
                border=ft.Border.all(1, PANEL_BORDER),
                bgcolor=opa(0.4, "#120e1c"),
                ink=False,
            )
            save = ft.Container(
                content=ft.Text("保存", color=TEXT, weight=ft.FontWeight.W_700),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                border_radius=14,
                bgcolor=opa(0.22, ACCENT),
                border=ft.Border.all(1, ACCENT),
                ink=False,
            )
            m.wire_pressable(
                browse,
                page=self.page,
                on_click=self._browse_handler(app_id),
                hover_scale=1.02,
                press_scale=0.97,
            )
            m.wire_pressable(
                reset,
                page=self.page,
                on_click=self._reset_handler(app_id),
                hover_scale=1.02,
                press_scale=0.97,
            )
            m.wire_pressable(
                save,
                page=self.page,
                on_click=self._save_handler(app_id),
                hover_scale=1.02,
                press_scale=0.97,
            )

            rows.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                self.app_names[app_id],
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=TEXT,
                            ),
                            status,
                            ft.Row([field, browse], spacing=8),
                            ft.Row([reset, save], spacing=8),
                        ],
                        spacing=8,
                    ),
                    padding=14,
                    border_radius=16,
                    border=ft.Border.all(1, HAIRLINE),
                    bgcolor=opa(0.35, "#141022"),
                )
            )

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
                                    "路径配置",
                                    size=28,
                                    weight=ft.FontWeight.W_800,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    "填写各应用的配置文件路径。留空并点「自动」可恢复检测。",
                                    size=13,
                                    color=MUTED,
                                ),
                            ],
                            spacing=6,
                            tight=True,
                            expand=True,
                        ),
                        back,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Container(height=8),
                *rows,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        )
        return shell(
            ft.Container(content=body, padding=18),
            padding=8,
            radius=30,
        )

    def _browse_handler(self, app_id: AppId):
        async def _handler(_event: ft.ControlEvent) -> None:
            self._pick_target = app_id
            files = await self.file_picker.pick_files(
                dialog_title=f"选择 {self.app_names[app_id]} 配置文件",
                allow_multiple=False,
            )
            if not files:
                return
            self._fields[app_id].value = files[0].path
            self.page.update()

        return _handler

    def _save_handler(self, app_id: AppId):
        async def _handler(_event: ft.ControlEvent) -> None:
            raw = (self._fields[app_id].value or "").strip()
            try:
                if raw:
                    path = Path(raw).expanduser()
                    if not path.exists() and not path.parent.exists():
                        await self._emit_toast(
                            f"{self.app_names[app_id]} 路径无效：目录不存在",
                            ERROR,
                        )
                        return
                info = self.service.set_path_override(app_id, raw or None)
                self._fields[app_id].value = info.override_path or info.auto_path or ""
                self._status[app_id].value = self._status_text(info)
                self._status[app_id].color = SUCCESS if info.exists else ERROR
                self.on_paths_changed()
                self.page.update()
                await self._emit_toast(
                    f"已保存 {self.app_names[app_id]} 路径配置",
                    SUCCESS,
                )
            except Exception as exc:
                await self._emit_toast(f"保存失败：{exc}", ERROR)

        return _handler

    def _reset_handler(self, app_id: AppId):
        async def _handler(_event: ft.ControlEvent) -> None:
            info = self.service.set_path_override(app_id, None)
            self._fields[app_id].value = info.auto_path or ""
            self._status[app_id].value = self._status_text(info)
            self._status[app_id].color = SUCCESS if info.exists else ERROR
            self.on_paths_changed()
            self.page.update()
            await self._emit_toast(
                f"{self.app_names[app_id]} 已恢复自动检测",
                SUCCESS,
            )

        return _handler

    async def _emit_toast(self, message: str, color: str) -> None:
        result = self.on_toast(message, color)
        if isinstance(result, Awaitable):
            await result
