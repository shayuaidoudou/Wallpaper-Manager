from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import flet as ft

from wallpaper_manager.core.image_service import validate_image_path
from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService, build_default_service
from wallpaper_manager.ui.theme import (
    ACCENT,
    ACCENT_2,
    BG,
    ERROR,
    MUTED,
    PANEL,
    PANEL_BORDER,
    SUCCESS,
    TEXT,
)

APP_NAMES = {
    AppId.VSCODE: "VS Code",
    AppId.CURSOR: "Cursor",
    AppId.IDEA: "IDEA",
    AppId.PYCHARM: "PyCharm",
}
APP_ORDER = list(AppId)
IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "gif", "bmp"]


@dataclass
class Draft:
    image_path: str | None
    opacity_ui: int
    installed: bool
    validation_error: str | None = None


def can_apply(draft: Draft) -> bool:
    return bool(
        draft.installed and draft.image_path and draft.validation_error is None
    )


def normalize_image_path(image_path: str) -> str:
    return str(Path(image_path).expanduser().resolve())


def apply_success_message(app_id: AppId) -> str:
    if app_id in (AppId.VSCODE, AppId.CURSOR):
        return f"已应用到 {APP_NAMES[app_id]}。请重新加载窗口以查看效果。"
    return f"已应用到 {APP_NAMES[app_id]}。如未立即生效，请重新启动 IDE。"


class WallpaperManagerUI:
    def __init__(self, page: ft.Page, service: WallpaperService) -> None:
        self.page = page
        self.service = service
        states = service.bootstrap()
        self.drafts = {
            app_id: self._draft_from_state(states[app_id]) for app_id in APP_ORDER
        }
        self.active_app = APP_ORDER[0]

        self.preview_image = ft.Image(
            src="",
            fit=ft.BoxFit.COVER,
            expand=True,
            visible=False,
            fade_in_animation=220,
        )
        self.preview_overlay = ft.Container(
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.8, "#000000"),
            ignore_interactions=True,
            animate=180,
        )
        self.preview_message = ft.Text(
            "选择一张本地图片开始预览",
            color=MUTED,
            size=15,
            text_align=ft.TextAlign.CENTER,
        )
        self.path_field = ft.TextField(
            label="图片路径",
            hint_text="选择或粘贴本地图片路径",
            prefix_icon=ft.Icons.IMAGE_OUTLINED,
            color=TEXT,
            bgcolor=ft.Colors.with_opacity(0.55, PANEL),
            border_color=PANEL_BORDER,
            focused_border_color=ACCENT,
            border_radius=12,
            on_change=self._on_path_change,
            on_submit=self._on_path_change,
            expand=True,
        )
        self.opacity_label = ft.Text("", color=ACCENT_2, weight=ft.FontWeight.W_600)
        self.opacity_slider = ft.Slider(
            min=0,
            max=100,
            divisions=100,
            active_color=ACCENT,
            inactive_color=PANEL_BORDER,
            thumb_color=ACCENT_2,
            on_change=self._on_opacity_change,
            expand=True,
        )
        self.clear_button = ft.OutlinedButton(
            content="清除",
            icon=ft.Icons.DELETE_OUTLINE,
            style=ft.ButtonStyle(color=MUTED, side=ft.BorderSide(1, PANEL_BORDER)),
            on_click=self._on_clear,
        )
        self.apply_button = ft.FilledButton(
            content="",
            icon=ft.Icons.CHECK,
            bgcolor=ACCENT,
            color=BG,
            animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
            on_click=self._on_apply,
        )
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)

    @staticmethod
    def _draft_from_state(state: object) -> Draft:
        image_path = getattr(state, "image_path")
        error = None
        if image_path:
            valid, error = validate_image_path(image_path)
            if valid:
                error = None
        return Draft(
            image_path=image_path,
            opacity_ui=int(getattr(state, "opacity_ui")),
            installed=bool(getattr(state, "installed")),
            validation_error=error,
        )

    def build(self) -> ft.Control:
        installed_count = sum(draft.installed for draft in self.drafts.values())
        tabs = [
            ft.Tab(
                label=(
                    APP_NAMES[app_id]
                    if self.drafts[app_id].installed
                    else f"{APP_NAMES[app_id]} · 未安装"
                )
            )
            for app_id in APP_ORDER
        ]
        tabs_control = ft.Tabs(
            content=ft.TabBar(
                tabs=tabs,
                indicator_color=ACCENT,
                label_color=TEXT,
                unselected_label_color=MUTED,
                divider_color=PANEL_BORDER,
            ),
            length=len(tabs),
            selected_index=0,
            animation_duration=180,
            on_change=self._on_tab_change,
        )
        preview = ft.Container(
            content=ft.Stack(
                controls=[
                    ft.Container(
                        content=ft.Icon(
                            ft.Icons.LANDSCAPE_OUTLINED, size=54, color=PANEL_BORDER
                        ),
                        alignment=ft.Alignment.CENTER,
                        expand=True,
                    ),
                    self.preview_image,
                    self.preview_overlay,
                    ft.Container(
                        content=self.preview_message,
                        alignment=ft.Alignment.CENTER,
                        padding=24,
                        expand=True,
                    ),
                ],
                fit=ft.StackFit.EXPAND,
            ),
            height=360,
            bgcolor="#0f141c",
            border=ft.Border.all(1, PANEL_BORDER),
            border_radius=18,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        browse_button = ft.OutlinedButton(
            content="浏览…",
            icon=ft.Icons.FOLDER_OPEN_OUTLINED,
            style=ft.ButtonStyle(color=ACCENT, side=ft.BorderSide(1, ACCENT)),
            on_click=self._on_browse,
        )
        self.main_panel = ft.Container(
            content=ft.Column(
                controls=[
                    preview,
                    ft.Text("图片来源", size=12, color=MUTED),
                    ft.Row([self.path_field, browse_button], spacing=12),
                    ft.Row(
                        [
                            ft.Text("不透明度", color=TEXT, weight=ft.FontWeight.W_500),
                            self.opacity_slider,
                            self.opacity_label,
                        ],
                        spacing=12,
                    ),
                    ft.Row(
                        [self.clear_button, self.apply_button],
                        alignment=ft.MainAxisAlignment.END,
                        spacing=12,
                    ),
                ],
                spacing=16,
            ),
            padding=22,
            bgcolor=ft.Colors.with_opacity(0.88, PANEL),
            border=ft.Border.all(1, PANEL_BORDER),
            border_radius=20,
            opacity=1,
            animate_opacity=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
        )
        root = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Wallpaper Manager",
                        size=28,
                        weight=ft.FontWeight.W_700,
                        color=TEXT,
                    ),
                    ft.Text(f"检测到 {installed_count} 个软件", size=13, color=MUTED),
                    tabs_control,
                    self.main_panel,
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.symmetric(horizontal=32, vertical=24),
            expand=True,
            gradient=ft.RadialGradient(
                center=ft.Alignment.TOP_RIGHT,
                radius=1.25,
                colors=["#102636", BG],
            ),
        )
        self._load_active_draft()
        return root

    async def _on_tab_change(self, event: ft.Event[ft.Tabs]) -> None:
        self.main_panel.opacity = 0.72
        self.page.update()
        await asyncio.sleep(0.07)
        self.active_app = APP_ORDER[event.control.selected_index]
        self._load_active_draft()
        self.main_panel.opacity = 1
        self.page.update()

    def _on_path_change(self, event: ft.Event[ft.TextField]) -> None:
        path = event.control.value.strip()
        draft = self.drafts[self.active_app]
        draft.image_path = path or None
        if path:
            valid, error = validate_image_path(path)
            draft.validation_error = None if valid else error
        else:
            draft.validation_error = None
        self._refresh_preview()
        self.page.update()

    def _on_opacity_change(self, event: ft.Event[ft.Slider]) -> None:
        draft = self.drafts[self.active_app]
        draft.opacity_ui = int(round(event.control.value or 0))
        self._refresh_preview()
        self.page.update()

    async def _on_browse(self, _event: ft.Event[ft.OutlinedButton]) -> None:
        files = await self.file_picker.pick_files(
            dialog_title="选择壁纸",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=IMAGE_EXTENSIONS,
            allow_multiple=False,
        )
        if not files:
            return
        self.path_field.value = files[0].path
        draft = self.drafts[self.active_app]
        draft.image_path = files[0].path
        valid, error = validate_image_path(files[0].path)
        draft.validation_error = None if valid else error
        self._refresh_preview()
        self.page.update()

    async def _on_apply(self, _event: ft.Event[ft.FilledButton]) -> None:
        draft = self.drafts[self.active_app]
        if not can_apply(draft):
            return
        valid, error = validate_image_path(draft.image_path or "")
        if not valid:
            draft.validation_error = error
            self._refresh_preview()
            self.page.update()
            return
        absolute_path = normalize_image_path(draft.image_path or "")
        draft.image_path = absolute_path
        self.path_field.value = absolute_path
        result = self.service.apply(
            self.active_app, absolute_path, draft.opacity_ui
        )
        if result.last_error:
            self._show_snack(f"应用失败：{result.last_error}", ERROR)
            return
        applied_app = self.active_app
        applied_app_name = APP_NAMES[applied_app]
        self.apply_button.scale = 0.96
        self.apply_button.content = "已应用"
        self.apply_button.icon = ft.Icons.CHECK_CIRCLE
        self.page.update()
        await asyncio.sleep(0.09)
        self.apply_button.scale = 1
        self.page.update()
        tip = self.service.extension_tip(applied_app)
        message = apply_success_message(applied_app)
        self._show_snack(f"{message} {tip}" if tip else message, SUCCESS)
        await asyncio.sleep(0.45)
        if self.active_app == applied_app:
            self.apply_button.content = f"应用到 {applied_app_name}"
            self.apply_button.icon = ft.Icons.CHECK
            self.page.update()

    def _on_clear(self, _event: ft.Event[ft.OutlinedButton]) -> None:
        result = self.service.clear(self.active_app)
        if result.last_error:
            self._show_snack(f"清除失败：{result.last_error}", ERROR)
            return
        self.drafts[self.active_app] = self._draft_from_state(result)
        self._load_active_draft()
        self.page.update()
        self._show_snack(f"已清除 {APP_NAMES[self.active_app]} 的壁纸设置。", SUCCESS)

    def _load_active_draft(self) -> None:
        draft = self.drafts[self.active_app]
        self.path_field.value = draft.image_path or ""
        self.opacity_slider.value = draft.opacity_ui
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        draft = self.drafts[self.active_app]
        has_valid_image = bool(draft.image_path and not draft.validation_error)
        self.preview_image.src = (
            normalize_image_path(draft.image_path)
            if has_valid_image and draft.image_path
            else ""
        )
        self.preview_image.visible = has_valid_image
        self.preview_overlay.bgcolor = ft.Colors.with_opacity(
            1 - draft.opacity_ui / 100, "#000000"
        )
        self.opacity_label.value = f"{draft.opacity_ui}%"
        if draft.validation_error:
            self.preview_message.value = draft.validation_error
            self.preview_message.color = ERROR
        elif not draft.image_path:
            self.preview_message.value = "选择一张本地图片开始预览"
            self.preview_message.color = MUTED
        else:
            self.preview_message.value = ""
        self.apply_button.content = f"应用到 {APP_NAMES[self.active_app]}"
        self.apply_button.disabled = not can_apply(draft)
        self.clear_button.disabled = not draft.installed

    def _show_snack(self, message: str, color: str) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=TEXT),
                bgcolor=PANEL,
                close_icon_color=color,
                show_close_icon=True,
            )
        )


def main(page: ft.Page) -> None:
    page.title = "Wallpaper Manager"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 960
    page.window.height = 780
    page.window.min_width = 760
    page.window.min_height = 640
    page.add(WallpaperManagerUI(page, build_default_service()).build())


def run_app() -> None:
    ft.run(main)
