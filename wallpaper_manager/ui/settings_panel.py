"""Path configuration panel — pick app data folders, auto-resolve config files."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import flet as ft

from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.path_config import (
    config_dir_hint,
    data_root_guidance,
    resolve_config_from_user_selection,
)
from wallpaper_manager.core.service import WallpaperService
from wallpaper_manager.core.state_store import DEFAULT_GALLERY_DOWNLOAD_DIR
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
        self._resolved: dict[AppId, ft.Text] = {}
        self.gallery_dir_field: ft.TextField
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)
        self.root = self._build()

    def control(self) -> ft.Control:
        return self.root

    def reload(self) -> None:
        self.gallery_dir_field.value = str(self.service.gallery_download_dir())
        for app_id in self.app_order:
            info = self.service.path_info(app_id)
            field = self._fields[app_id]
            # Show resolved config file; hint tells users which folder to pick.
            field.value = info.override_path or info.auto_path or ""
            field.hint_text = config_dir_hint(app_id)
            self._status[app_id].value = self._status_text(info)
            self._status[app_id].color = SUCCESS if info.exists else ERROR
            self._resolved[app_id].value = (
                f"将写入：{info.effective_path}" if info.effective_path else "尚未解析到配置文件"
            )
        self.page.update()

    def _status_text(self, info) -> str:
        mode = "手动" if info.using_override else "自动检测"
        state = "已找到" if info.exists else "未找到文件"
        return f"{mode} · {state} · 目标文件：{info.label}"

    def _build(self) -> ft.Control:
        rows: list[ft.Control] = [self._build_gallery_dir_section()]
        for app_id in self.app_order:
            info = self.service.path_info(app_id)
            field = ft.TextField(
                value=info.override_path or info.auto_path or "",
                hint_text=config_dir_hint(app_id),
                label="数据目录或已解析的配置文件路径",
                label_style=ft.TextStyle(color=MUTED, size=11),
                color=TEXT,
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
            resolved = ft.Text(
                f"将写入：{info.effective_path}" if info.effective_path else "尚未解析到配置文件",
                size=11,
                color=MUTED,
            )
            self._fields[app_id] = field
            self._status[app_id] = status
            self._resolved[app_id] = resolved

            browse = ft.Container(
                content=ft.Text("选择目录", color=ACCENT_2, weight=ft.FontWeight.W_700),
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
                            resolved,
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
                                    data_root_guidance(),
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

    def _build_gallery_dir_section(self) -> ft.Control:
        self.gallery_dir_field = ft.TextField(
            value=str(self.service.gallery_download_dir()),
            hint_text=str(DEFAULT_GALLERY_DOWNLOAD_DIR),
            label="在线图库下载目录",
            label_style=ft.TextStyle(color=MUTED, size=11),
            color=TEXT,
            bgcolor=opa(0.88, "#0c0916"),
            border_color=PANEL_BORDER,
            focused_border_color=ACCENT,
            border_radius=14,
            filled=True,
            cursor_color=ACCENT,
            expand=True,
        )
        browse = ft.Container(
            content=ft.Text("选择目录", color=ACCENT_2, weight=ft.FontWeight.W_700),
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            border_radius=14,
            border=ft.Border.all(1, ACCENT),
            bgcolor=opa(0.12, ACCENT),
            ink=False,
        )
        reset = ft.Container(
            content=ft.Text("默认", color=MUTED, weight=ft.FontWeight.W_600),
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
            on_click=self._browse_gallery_dir,
            hover_scale=1.02,
            press_scale=0.97,
        )
        m.wire_pressable(
            reset,
            page=self.page,
            on_click=self._reset_gallery_dir,
            hover_scale=1.02,
            press_scale=0.97,
        )
        m.wire_pressable(
            save,
            page=self.page,
            on_click=self._save_gallery_dir,
            hover_scale=1.02,
            press_scale=0.97,
        )
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("壁纸下载", size=14, weight=ft.FontWeight.W_700, color=TEXT),
                    ft.Text(
                        "在线图库「设为壁纸」时原图保存到此目录",
                        size=11,
                        color=MUTED,
                    ),
                    ft.Row([self.gallery_dir_field, browse], spacing=8),
                    ft.Row([reset, save], spacing=8),
                ],
                spacing=8,
            ),
            padding=14,
            border_radius=16,
            border=ft.Border.all(1, HAIRLINE),
            bgcolor=opa(0.35, "#141022"),
        )

    async def _browse_gallery_dir(self, _event: ft.ControlEvent) -> None:
        directory = await self.file_picker.get_directory_path(
            dialog_title="选择壁纸下载目录",
        )
        if not directory:
            return
        self.gallery_dir_field.value = directory
        self.page.update()

    async def _save_gallery_dir(self, _event: ft.ControlEvent) -> None:
        raw = (self.gallery_dir_field.value or "").strip()
        try:
            path = self.service.set_gallery_download_dir(raw or None)
            self.gallery_dir_field.value = str(path)
            self.page.update()
            await self._emit_toast(f"已保存下载目录：{path}", SUCCESS)
        except Exception as exc:
            await self._emit_toast(f"保存失败：{exc}", ERROR)

    async def _reset_gallery_dir(self, _event: ft.ControlEvent) -> None:
        path = self.service.set_gallery_download_dir(None)
        self.gallery_dir_field.value = str(path)
        self.page.update()
        await self._emit_toast("已恢复默认下载目录", SUCCESS)

    def _browse_handler(self, app_id: AppId):
        async def _handler(_event: ft.ControlEvent) -> None:
            directory = await self.file_picker.get_directory_path(
                dialog_title=f"选择 {self.app_names[app_id]} 数据目录",
            )
            if not directory:
                return
            resolved, error = resolve_config_from_user_selection(app_id, directory)
            if error or resolved is None:
                await self._emit_toast(
                    f"{self.app_names[app_id]}：{error or '无法解析'}",
                    ERROR,
                )
                self._fields[app_id].value = directory
                self.page.update()
                return
            self._fields[app_id].value = str(resolved)
            self._resolved[app_id].value = f"将写入：{resolved}"
            self.page.update()
            await self._emit_toast(
                f"已从目录解析到 {self.app_names[app_id]} 配置文件",
                SUCCESS,
            )

        return _handler

    def _save_handler(self, app_id: AppId):
        async def _handler(_event: ft.ControlEvent) -> None:
            raw = (self._fields[app_id].value or "").strip()
            try:
                if not raw:
                    info = self.service.set_path_override(app_id, None)
                else:
                    info = self.service.set_path_override(app_id, raw)
                self._fields[app_id].value = info.override_path or info.auto_path or ""
                self._status[app_id].value = self._status_text(info)
                self._status[app_id].color = SUCCESS if info.exists else ERROR
                self._resolved[app_id].value = (
                    f"将写入：{info.effective_path}"
                    if info.effective_path
                    else "尚未解析到配置文件"
                )
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
            self._resolved[app_id].value = (
                f"将写入：{info.effective_path}"
                if info.effective_path
                else "尚未解析到配置文件"
            )
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
