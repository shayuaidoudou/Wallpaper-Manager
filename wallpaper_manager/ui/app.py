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
    ACCENT_DIM,
    BG,
    ERROR,
    HAIRLINE,
    MUTED,
    PANEL,
    PANEL_BORDER,
    PANEL_BORDER_LIT,
    PANEL_ELEVATED,
    SUCCESS,
    TEXT,
    accent_gradient,
    elev_shadow,
    glow_shadow,
    page_gradient,
    panel_gradient,
    soft_orb,
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
        return (
            f"已应用到 {APP_NAMES[app_id]}。"
            "请完全退出后再打开，或命令面板执行 Developer: Reload Window。"
        )
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
        self._tab_buttons: dict[AppId, ft.Container] = {}
        self._motion_running = False

        self.preview_image = ft.Image(
            src="",
            fit=ft.BoxFit.COVER,
            expand=True,
            visible=False,
            fade_in_animation=360,
            opacity=1,
            animate_opacity=ft.Animation(240, ft.AnimationCurve.EASE_OUT),
        )
        self.preview_veil = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=[
                    ft.Colors.with_opacity(0.0, BG),
                    ft.Colors.with_opacity(0.4, BG),
                    ft.Colors.with_opacity(0.8, BG),
                ],
            ),
            ignore_interactions=True,
        )
        self.preview_message = ft.Text(
            "选择一张图片，预览会在这里展开",
            color=MUTED,
            size=14,
            text_align=ft.TextAlign.CENTER,
        )
        self.preview_badge = ft.Container(
            content=ft.Text("预览", size=11, weight=ft.FontWeight.W_600, color=TEXT),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=999,
            bgcolor=ft.Colors.with_opacity(0.82, "#1a1328"),
            border=ft.Border.all(1, HAIRLINE),
            right=14,
            top=14,
        )
        self.opacity_chip = ft.Container(
            content=ft.Text("应用 25%", size=11, weight=ft.FontWeight.W_700, color=ACCENT_2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            border_radius=999,
            bgcolor=ft.Colors.with_opacity(0.82, "#1a1328"),
            border=ft.Border.all(1, ACCENT_DIM),
            left=14,
            bottom=14,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        self.ring_glow = ft.Container(
            expand=True,
            border_radius=22,
            border=ft.Border.all(1.5, ft.Colors.with_opacity(0.0, ACCENT)),
            animate=ft.Animation(420, ft.AnimationCurve.EASE_OUT),
            ignore_interactions=True,
        )
        self.path_field = ft.TextField(
            label="图片路径",
            hint_text="粘贴路径，或点右侧浏览",
            prefix_icon=ft.Icons.IMAGE_OUTLINED,
            color=TEXT,
            label_style=ft.TextStyle(color=MUTED, size=12),
            bgcolor=ft.Colors.with_opacity(0.85, "#100c1a"),
            border_color=PANEL_BORDER,
            focused_border_color=ACCENT,
            border_radius=14,
            filled=True,
            cursor_color=ACCENT,
            on_change=self._on_path_change,
            on_submit=self._on_path_change,
            expand=True,
        )
        self.opacity_label = ft.Text("25%", color=ACCENT_2, weight=ft.FontWeight.W_700, size=14)
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
        self.clear_button = ft.Container(
            content=ft.Text("清除", color=MUTED, weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=20, vertical=13),
            border_radius=14,
            border=ft.Border.all(1, PANEL_BORDER),
            bgcolor="#120e1c",
            on_click=self._on_clear,
            animate_opacity=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
            ink=False,
        )
        self.apply_button = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=17, color=BG),
                    ft.Text("应用到", color=BG, weight=ft.FontWeight.W_700, size=14),
                ],
                spacing=8,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=22, vertical=13),
            border_radius=14,
            gradient=accent_gradient(),
            shadow=glow_shadow(),
            on_click=self._on_apply,
            animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            ink=False,
        )
        self.apply_label = self.apply_button.content.controls[1]  # type: ignore[index]
        self.apply_icon = self.apply_button.content.controls[0]  # type: ignore[index]
        self.status_dot = ft.Container(
            width=8,
            height=8,
            border_radius=8,
            bgcolor=ACCENT_2,
            animate_opacity=ft.Animation(1400, ft.AnimationCurve.EASE_IN_OUT),
            opacity=1,
        )
        self.status_text = ft.Text("", size=12, color=TEXT, weight=ft.FontWeight.W_600)
        self.header_block: ft.Container
        self.tabs_block: ft.Container
        self.main_panel: ft.Container
        self.root_shell: ft.Container
        self.orb_a: ft.Container
        self.orb_b: ft.Container
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

    def _make_tab(self, app_id: AppId) -> ft.Container:
        draft = self.drafts[app_id]
        selected = app_id == self.active_app
        status = "已连接" if draft.installed else "未安装"
        body = ft.Column(
            [
                ft.Text(
                    APP_NAMES[app_id],
                    size=13,
                    weight=ft.FontWeight.W_700,
                    color=TEXT if selected else MUTED,
                ),
                ft.Text(
                    status,
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color=ACCENT_2 if draft.installed else ERROR,
                ),
            ],
            spacing=3,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        tab = ft.Container(
            content=body,
            padding=ft.Padding.symmetric(horizontal=14, vertical=11),
            border_radius=14,
            expand=True,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.2, ACCENT) if selected else "#00000000",
            border=ft.Border.all(1, ACCENT if selected else "#00000000"),
            shadow=glow_shadow() if selected else None,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            scale=1.0,
            on_click=self._tab_click_handler(app_id),
            ink=False,
        )
        self._tab_buttons[app_id] = tab
        return tab

    def _tab_click_handler(self, app_id: AppId):
        async def _handler(_event: ft.ControlEvent) -> None:
            await self._select_tab(app_id)

        return _handler

    def _refresh_tabs(self) -> None:
        for app_id, tab in self._tab_buttons.items():
            draft = self.drafts[app_id]
            selected = app_id == self.active_app
            tab.bgcolor = ft.Colors.with_opacity(0.2, ACCENT) if selected else "#00000000"
            tab.border = ft.Border.all(1, ACCENT if selected else "#00000000")
            tab.shadow = glow_shadow() if selected else None
            tab.scale = 1.02 if selected else 1.0
            col = tab.content
            assert isinstance(col, ft.Column)
            title, status = col.controls
            assert isinstance(title, ft.Text)
            assert isinstance(status, ft.Text)
            title.color = TEXT if selected else MUTED
            title.value = APP_NAMES[app_id]
            status.value = "已连接" if draft.installed else "未安装"
            status.color = ACCENT_2 if draft.installed else ERROR

    async def _select_tab(self, app_id: AppId) -> None:
        if app_id == self.active_app:
            return
        self.main_panel.opacity = 0
        self.main_panel.offset = ft.Offset(0, 0.025)
        self.page.update()
        await asyncio.sleep(0.12)
        self.active_app = app_id
        self._refresh_tabs()
        self._load_active_draft()
        self.main_panel.opacity = 1
        self.main_panel.offset = ft.Offset(0, 0)
        self.page.update()

    def build(self) -> ft.Control:
        installed_count = sum(d.installed for d in self.drafts.values())
        self.status_text.value = f"{installed_count}/{len(APP_ORDER)} 已连接"

        self.header_block = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                "VIOLET NOIR",
                                size=11,
                                weight=ft.FontWeight.W_700,
                                color=ACCENT_2,
                                style=ft.TextStyle(letter_spacing=3.5),
                            ),
                            ft.Text(
                                "Wallpaper Manager",
                                size=34,
                                weight=ft.FontWeight.W_800,
                                color=TEXT,
                                style=ft.TextStyle(letter_spacing=-0.8, height=1.05),
                            ),
                            ft.Text(
                                "为每个 IDE 单独设定氛围壁纸",
                                size=13,
                                color=MUTED,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Row(
                            [self.status_dot, self.status_text],
                            spacing=8,
                            tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                        border_radius=999,
                        bgcolor="#1a1328",
                        border=ft.Border.all(1, PANEL_BORDER_LIT),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            opacity=0,
            offset=ft.Offset(0, 0.04),
            animate_opacity=ft.Animation(420, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(420, ft.AnimationCurve.EASE_OUT),
        )

        self.tabs_block = ft.Container(
            content=ft.Row(
                [self._make_tab(app_id) for app_id in APP_ORDER],
                spacing=6,
            ),
            padding=6,
            border_radius=18,
            bgcolor="#0f0b18",
            border=ft.Border.all(1, PANEL_BORDER),
            opacity=0,
            offset=ft.Offset(0, 0.04),
            animate_opacity=ft.Animation(420, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(420, ft.AnimationCurve.EASE_OUT),
        )

        preview = ft.Container(
            content=ft.Stack(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(ft.Icons.WALLPAPER_OUTLINED, size=40, color=PANEL_BORDER_LIT),
                                self.preview_message,
                            ],
                            spacing=10,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.Alignment.CENTER,
                        expand=True,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_LEFT,
                            end=ft.Alignment.BOTTOM_RIGHT,
                            colors=["#1b1430", "#0d0a16"],
                        ),
                    ),
                    self.preview_image,
                    self.preview_veil,
                    self.preview_badge,
                    self.opacity_chip,
                    self.ring_glow,
                ],
                fit=ft.StackFit.EXPAND,
            ),
            height=268,
            border_radius=22,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(1, PANEL_BORDER_LIT),
            shadow=elev_shadow(),
        )

        browse_button = ft.Container(
            content=ft.Text("浏览", color=ACCENT_2, weight=ft.FontWeight.W_700),
            padding=ft.Padding.symmetric(horizontal=18, vertical=14),
            border_radius=14,
            border=ft.Border.all(1, ACCENT),
            bgcolor=ft.Colors.with_opacity(0.12, ACCENT),
            on_click=self._on_browse,
            animate_scale=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
            ink=False,
        )

        controls = ft.Column(
            [
                ft.Text("图片来源", size=12, weight=ft.FontWeight.W_600, color=MUTED),
                ft.Row([self.path_field, browse_button], spacing=10),
                ft.Container(height=4),
                ft.Row(
                    [
                        ft.Text("透明度", size=12, weight=ft.FontWeight.W_600, color=MUTED),
                        ft.Container(expand=True),
                        self.opacity_label,
                    ]
                ),
                self.opacity_slider,
                ft.Text(
                    "0% 表示图片完全透明，编辑器显示主题底色",
                    size=11,
                    color=MUTED,
                ),
                ft.Container(height=2),
                ft.Row(
                    [self.clear_button, ft.Container(expand=True), self.apply_button],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=8,
        )

        self.main_panel = ft.Container(
            content=ft.Column([preview, controls], spacing=18),
            padding=20,
            border_radius=24,
            gradient=panel_gradient(),
            border=ft.Border.all(1, HAIRLINE),
            shadow=elev_shadow(),
            opacity=0,
            offset=ft.Offset(0, 0.05),
            animate_opacity=ft.Animation(460, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(460, ft.AnimationCurve.EASE_OUT),
        )

        content = ft.Container(
            content=ft.Column(
                [self.header_block, self.tabs_block, self.main_panel],
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.symmetric(horizontal=34, vertical=26),
            expand=True,
        )

        self.orb_a = soft_orb(340, "#a855f7", opacity=0.22, top=-120, right=-80)
        self.orb_b = soft_orb(280, "#e879f9", opacity=0.14, bottom=-120, left=-90)

        self.root_shell = ft.Container(
            expand=True,
            gradient=page_gradient(),
            content=ft.Stack([self.orb_a, self.orb_b, content], expand=True),
        )
        self._load_active_draft()
        self._refresh_tabs()
        return self.root_shell

    async def _play_entrance(self) -> None:
        await asyncio.sleep(0.05)
        self.header_block.opacity = 1
        self.header_block.offset = ft.Offset(0, 0)
        self.page.update()
        await asyncio.sleep(0.08)
        self.tabs_block.opacity = 1
        self.tabs_block.offset = ft.Offset(0, 0)
        self.page.update()
        await asyncio.sleep(0.08)
        self.main_panel.opacity = 1
        self.main_panel.offset = ft.Offset(0, 0)
        self.page.update()
        if not self._motion_running:
            self._motion_running = True
            self.page.run_task(self._ambient_loop)

    async def _ambient_loop(self) -> None:
        bright = True
        while self._motion_running:
            self.orb_a.opacity = 0.62 if bright else 0.34
            self.orb_a.scale = 1.04 if bright else 0.96
            self.orb_b.opacity = 0.28 if bright else 0.5
            self.orb_b.scale = 0.96 if bright else 1.05
            self.status_dot.opacity = 1.0 if bright else 0.35
            self.page.update()
            bright = not bright
            await asyncio.sleep(2.6)

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

    async def _on_browse(self, _event: ft.ControlEvent) -> None:
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

    async def _on_apply(self, _event: ft.ControlEvent) -> None:
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
        result = self.service.apply(self.active_app, absolute_path, draft.opacity_ui)
        if result.last_error:
            self._show_snack(f"应用失败：{result.last_error}", ERROR)
            return

        applied_app = self.active_app
        applied_name = APP_NAMES[applied_app]
        self.apply_button.scale = 0.96
        self.ring_glow.border = ft.Border.all(1.5, ACCENT_2)
        self.apply_label.value = "已应用"
        self.apply_icon.name = ft.Icons.CHECK_ROUNDED
        self.page.update()
        await asyncio.sleep(0.14)
        self.apply_button.scale = 1.0
        self.page.update()
        tip = self.service.extension_tip(applied_app)
        message = apply_success_message(applied_app)
        self._show_snack(f"{message} {tip}" if tip else message, SUCCESS)
        await asyncio.sleep(0.55)
        self.ring_glow.border = ft.Border.all(1.5, ft.Colors.with_opacity(0.0, ACCENT))
        if self.active_app == applied_app:
            self.apply_label.value = f"应用到 {applied_name}"
            self.apply_icon.name = ft.Icons.AUTO_AWESOME
        self.page.update()

    def _on_clear(self, _event: ft.ControlEvent) -> None:
        result = self.service.clear(self.active_app)
        if result.last_error:
            self._show_snack(f"清除失败：{result.last_error}", ERROR)
            return
        self.drafts[self.active_app] = self._draft_from_state(result)
        self._load_active_draft()
        self._refresh_tabs()
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
        self.preview_image.opacity = (
            max(0.28, draft.opacity_ui / 100) if has_valid_image else 1.0
        )
        self.opacity_label.value = f"{draft.opacity_ui}%"
        chip = self.opacity_chip.content
        assert isinstance(chip, ft.Text)
        chip.value = f"应用 {draft.opacity_ui}%"
        if draft.validation_error:
            self.preview_message.value = draft.validation_error
            self.preview_message.color = ERROR
        elif not draft.image_path:
            self.preview_message.value = "选择一张图片，预览会在这里展开"
            self.preview_message.color = MUTED
        else:
            self.preview_message.value = ""
        self.apply_label.value = f"应用到 {APP_NAMES[self.active_app]}"
        self.apply_button.opacity = 1 if can_apply(draft) else 0.4
        self.apply_button.disabled = not can_apply(draft)
        self.clear_button.opacity = 1 if draft.installed else 0.35
        self.clear_button.disabled = not draft.installed

    def _show_snack(self, message: str, color: str) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=TEXT),
                bgcolor=PANEL_ELEVATED,
                close_icon_color=color,
                show_close_icon=True,
                elevation=6,
            )
        )


def main(page: ft.Page) -> None:
    page.title = "Wallpaper Manager"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        color_scheme_seed=ACCENT,
        splash_color=ft.Colors.with_opacity(0.2, ACCENT_2),
        highlight_color=ft.Colors.with_opacity(0.12, ACCENT),
    )
    page.padding = 0
    page.window.width = 1000
    page.window.height = 820
    page.window.min_width = 800
    page.window.min_height = 680
    ui = WallpaperManagerUI(page, build_default_service())
    page.add(ui.build())
    page.run_task(ui._play_entrance)


def run_app() -> None:
    ft.run(main)
