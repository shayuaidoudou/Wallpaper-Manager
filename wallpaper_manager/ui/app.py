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
    MUTED,
    PANEL_BORDER,
    PANEL_BORDER_LIT,
    PANEL_ELEVATED,
    SUCCESS,
    TEXT,
    accent_gradient,
    ambient_orb,
    glass_shadow,
    page_gradient,
    soft_shadow,
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

        self.preview_image = ft.Image(
            src="",
            fit=ft.BoxFit.COVER,
            expand=True,
            visible=False,
            fade_in_animation=280,
            opacity=1,
            animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        )
        self.preview_overlay = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=["#c084fc00", "#7c3aed33", "#09060f99"],
            ),
            ignore_interactions=True,
        )
        self.preview_message = ft.Text(
            "紫霓幻境 · 选择本地壁纸开始预览",
            color=MUTED,
            size=14,
            text_align=ft.TextAlign.CENTER,
        )
        self.preview_badge = ft.Container(
            content=ft.Text("PREVIEW", size=11, weight=ft.FontWeight.W_700, color=TEXT),
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            border_radius=999,
            bgcolor="#1a0b2ecc",
            border=ft.Border.all(1, ACCENT),
            right=16,
            top=16,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(900, ft.AnimationCurve.EASE_IN_OUT),
            scale=1.0,
        )
        self.opacity_chip = ft.Container(
            content=ft.Text("25%", size=12, weight=ft.FontWeight.W_700, color=ACCENT_2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border_radius=999,
            bgcolor="#14081fcc",
            border=ft.Border.all(1, ACCENT_DIM),
            left=16,
            bottom=16,
            shadow=soft_shadow(),
            animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
        )
        self.shimmer = ft.Container(
            width=90,
            height=420,
            left=-120,
            top=-20,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.CENTER_LEFT,
                end=ft.Alignment.CENTER_RIGHT,
                colors=["#ffffff00", "#ffffff33", "#ffffff00"],
            ),
            rotate=ft.Rotate(angle=-0.35, alignment=ft.Alignment.CENTER),
            animate_position=ft.Animation(1800, ft.AnimationCurve.EASE_IN_OUT),
            ignore_interactions=True,
            opacity=0.55,
        )
        self.path_field = ft.TextField(
            label="图片路径",
            hint_text="选择或粘贴本地图片绝对路径",
            prefix_icon=ft.Icons.IMAGE_OUTLINED,
            color=TEXT,
            label_style=ft.TextStyle(color=MUTED, size=12),
            bgcolor="#140a1ecc",
            border_color=PANEL_BORDER,
            focused_border_color=ACCENT,
            border_radius=14,
            filled=True,
            on_change=self._on_path_change,
            on_submit=self._on_path_change,
            expand=True,
            cursor_color=ACCENT,
        )
        self.opacity_label = ft.Text("", color=ACCENT_2, weight=ft.FontWeight.W_700, size=15)
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
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.DELETE_OUTLINE, size=18, color=MUTED),
                    ft.Text("清除", color=MUTED, weight=ft.FontWeight.W_600),
                ],
                spacing=8,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=18, vertical=12),
            border_radius=14,
            border=ft.Border.all(1, PANEL_BORDER),
            bgcolor="#1a0f2888",
            on_click=self._on_clear,
            animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
            ink=True,
        )
        self.apply_button = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=18, color=BG),
                    ft.Text("应用到", color=BG, weight=ft.FontWeight.W_700),
                ],
                spacing=8,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=22, vertical=13),
            border_radius=16,
            gradient=accent_gradient(),
            shadow=soft_shadow(),
            on_click=self._on_apply,
            animate_scale=ft.Animation(180, ft.AnimationCurve.EASE_OUT_BACK),
            ink=True,
        )
        self.apply_label = self.apply_button.content.controls[1]  # type: ignore[attr-defined]
        self.apply_icon = self.apply_button.content.controls[0]  # type: ignore[attr-defined]
        self.status_text = ft.Text("", size=12, color=MUTED)
        self.title_glow = ft.Text(
            "Manager",
            size=44,
            weight=ft.FontWeight.W_800,
            color=TEXT,
            style=ft.TextStyle(letter_spacing=-1.2, height=1),
            animate_opacity=ft.Animation(1200, ft.AnimationCurve.EASE_IN_OUT),
            opacity=1,
        )
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)
        self.main_panel: ft.Container
        self.root_shell: ft.Container
        self.orb_a: ft.Container
        self.orb_b: ft.Container
        self.orb_c: ft.Container
        self._motion_running = False

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
        label = APP_NAMES[app_id] if draft.installed else f"{APP_NAMES[app_id]}"
        subtitle = "ONLINE" if draft.installed else "OFFLINE"
        selected = app_id == self.active_app

        body = ft.Column(
            [
                ft.Text(
                    label,
                    size=13,
                    weight=ft.FontWeight.W_700,
                    color=TEXT if selected else MUTED,
                ),
                ft.Text(
                    subtitle,
                    size=10,
                    weight=ft.FontWeight.W_600,
                    color=SUCCESS if draft.installed else ERROR,
                ),
            ],
            spacing=2,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        tab = ft.Container(
            content=body,
            padding=ft.Padding.symmetric(horizontal=18, vertical=12),
            border_radius=16,
            expand=True,
            alignment=ft.Alignment.CENTER,
            bgcolor=ft.Colors.with_opacity(0.28, ACCENT) if selected else "#140a1e99",
            border=ft.Border.all(
                1.5 if selected else 1, ACCENT_2 if selected else PANEL_BORDER
            ),
            shadow=soft_shadow() if selected else None,
            animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(220, ft.AnimationCurve.EASE_OUT_BACK),
            scale=1.0,
            on_click=self._tab_click_handler(app_id),
            ink=True,
            data=app_id,
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
            tab.bgcolor = (
                ft.Colors.with_opacity(0.28, ACCENT) if selected else "#140a1e99"
            )
            tab.border = ft.Border.all(
                1.5 if selected else 1, ACCENT_2 if selected else PANEL_BORDER
            )
            tab.shadow = soft_shadow() if selected else None
            tab.scale = 1.06 if selected else 1.0
            col = tab.content
            assert isinstance(col, ft.Column)
            title, status = col.controls
            assert isinstance(title, ft.Text)
            assert isinstance(status, ft.Text)
            title.color = TEXT if selected else MUTED
            title.value = APP_NAMES[app_id]
            status.value = "ONLINE" if draft.installed else "OFFLINE"
            status.color = SUCCESS if draft.installed else ERROR

    async def _select_tab(self, app_id: AppId) -> None:
        if app_id == self.active_app:
            return
        self.main_panel.opacity = 0.0
        self.main_panel.offset = ft.Offset(0.02, 0.04)
        self.main_panel.scale = 0.985
        self.page.update()
        await asyncio.sleep(0.1)
        self.active_app = app_id
        self._refresh_tabs()
        self._load_active_draft()
        self.main_panel.opacity = 1
        self.main_panel.offset = ft.Offset(0, 0)
        self.main_panel.scale = 1
        self.page.update()
        self.shimmer.left = -120
        self.page.update()
        await asyncio.sleep(0.02)
        self.shimmer.left = 980
        self.page.update()

    def build(self) -> ft.Control:
        installed_count = sum(draft.installed for draft in self.drafts.values())
        self.status_text.value = f"{installed_count} / {len(APP_ORDER)} editors linked"

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            "VIOLET LUXE",
                            size=12,
                            weight=ft.FontWeight.W_700,
                            color=ACCENT_2,
                            style=ft.TextStyle(letter_spacing=5),
                        ),
                        self.title_glow,
                        ft.Text(
                            "华丽紫霓 · 动效氛围壁纸中枢",
                            size=13,
                            color=MUTED,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("STATUS", size=10, weight=ft.FontWeight.W_700, color=MUTED),
                            self.status_text,
                        ],
                        spacing=4,
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    border_radius=16,
                    bgcolor="#1a0b2ecc",
                    border=ft.Border.all(1, ACCENT_DIM),
                    shadow=soft_shadow(),
                    animate_opacity=ft.Animation(900, ft.AnimationCurve.EASE_IN_OUT),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        tabs_row = ft.Container(
            content=ft.Row(
                [self._make_tab(app_id) for app_id in APP_ORDER],
                spacing=10,
            ),
            padding=8,
            border_radius=22,
            bgcolor="#12081ccc",
            border=ft.Border.all(1, PANEL_BORDER),
            shadow=soft_shadow(),
        )

        preview = ft.Container(
            content=ft.Stack(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.AUTO_AWESOME,
                                    size=46,
                                    color=ACCENT,
                                ),
                                self.preview_message,
                            ],
                            spacing=12,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        alignment=ft.Alignment.CENTER,
                        expand=True,
                        gradient=ft.LinearGradient(
                            begin=ft.Alignment.TOP_LEFT,
                            end=ft.Alignment.BOTTOM_RIGHT,
                            colors=["#221038", "#0d0716"],
                        ),
                    ),
                    self.preview_image,
                    self.preview_overlay,
                    self.shimmer,
                    self.preview_badge,
                    self.opacity_chip,
                ],
                fit=ft.StackFit.EXPAND,
            ),
            height=390,
            border_radius=24,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(1.5, ACCENT_DIM),
            shadow=glass_shadow(),
        )

        browse_button = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, size=18, color=ACCENT_2),
                    ft.Text("浏览", color=ACCENT_2, weight=ft.FontWeight.W_700),
                ],
                spacing=8,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            border_radius=14,
            border=ft.Border.all(1, ACCENT),
            bgcolor="#a855f722",
            on_click=self._on_browse,
            animate_scale=ft.Animation(140, ft.AnimationCurve.EASE_OUT_BACK),
            ink=True,
        )

        controls = ft.Column(
            [
                ft.Text("IMAGE SOURCE", size=11, weight=ft.FontWeight.W_700, color=MUTED),
                ft.Row([self.path_field, browse_button], spacing=12),
                ft.Container(height=6),
                ft.Row(
                    [
                        ft.Text(
                            "OPACITY",
                            size=11,
                            weight=ft.FontWeight.W_700,
                            color=MUTED,
                        ),
                        ft.Container(expand=True),
                        self.opacity_label,
                    ]
                ),
                self.opacity_slider,
                ft.Text(
                    "0% = 图片完全透明（显示主题底色，不是强制纯黑）",
                    color=MUTED,
                    size=12,
                ),
                ft.Container(height=4),
                ft.Row(
                    [self.clear_button, ft.Container(expand=True), self.apply_button],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
        )

        self.main_panel = ft.Container(
            content=ft.Column([preview, controls], spacing=20),
            padding=22,
            border_radius=28,
            bgcolor="#161022f2",
            border=ft.Border.all(1.5, PANEL_BORDER_LIT),
            shadow=glass_shadow(),
            opacity=1,
            offset=ft.Offset(0, 0),
            scale=1,
            animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
        )

        content = ft.Container(
            content=ft.Column(
                [header, tabs_row, self.main_panel],
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.symmetric(horizontal=36, vertical=28),
            expand=True,
        )

        self.orb_a = ambient_orb(size=360, color="#a855f755", top=-80, right=-60)
        self.orb_b = ambient_orb(size=300, color="#e879f933", bottom=-100, left=-70)
        self.orb_c = ambient_orb(size=200, color="#7c3aed44", top=200, left=460)

        self.root_shell = ft.Container(
            expand=True,
            gradient=page_gradient(),
            content=ft.Stack(
                [
                    self.orb_a,
                    self.orb_b,
                    self.orb_c,
                    content,
                ],
                expand=True,
            ),
            opacity=0,
            animate_opacity=ft.Animation(520, ft.AnimationCurve.EASE_OUT),
        )
        self._load_active_draft()
        self._refresh_tabs()
        return self.root_shell

    async def _play_entrance(self) -> None:
        await asyncio.sleep(0.04)
        self.root_shell.opacity = 1
        self.page.update()
        if not self._motion_running:
            self._motion_running = True
            self.page.run_task(self._ambient_motion_loop)

    async def _ambient_motion_loop(self) -> None:
        pulse = True
        while self._motion_running:
            self.orb_a.opacity = 0.95 if pulse else 0.45
            self.orb_a.scale = 1.08 if pulse else 0.92
            self.orb_b.opacity = 0.5 if pulse else 0.9
            self.orb_b.scale = 0.9 if pulse else 1.12
            self.orb_c.opacity = 0.85 if pulse else 0.4
            self.orb_c.scale = 1.15 if pulse else 0.88
            self.title_glow.opacity = 1.0 if pulse else 0.72
            self.preview_badge.scale = 1.05 if pulse else 0.96
            self.page.update()
            pulse = not pulse
            await asyncio.sleep(1.7)
            if pulse:
                self.shimmer.left = -120
                self.page.update()
                await asyncio.sleep(0.05)
                self.shimmer.left = 980
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

    async def _on_browse(self, _event: ft.ControlEvent) -> None:
        self.browse_button_press()
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

    def browse_button_press(self) -> None:
        # no-op hook kept for clarity; scale handled by ink/animate
        return

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
        result = self.service.apply(
            self.active_app, absolute_path, draft.opacity_ui
        )
        if result.last_error:
            self._show_snack(f"应用失败：{result.last_error}", ERROR)
            return
        applied_app = self.active_app
        applied_app_name = APP_NAMES[applied_app]
        self.apply_button.scale = 0.9
        self.apply_label.value = "已应用"
        self.apply_icon.name = ft.Icons.CHECK_CIRCLE_ROUNDED
        self.opacity_chip.scale = 1.12
        self.page.update()
        await asyncio.sleep(0.12)
        self.apply_button.scale = 1.06
        self.page.update()
        await asyncio.sleep(0.08)
        self.apply_button.scale = 1.0
        self.opacity_chip.scale = 1.0
        self.page.update()
        tip = self.service.extension_tip(applied_app)
        message = apply_success_message(applied_app)
        self._show_snack(f"{message} {tip}" if tip else message, SUCCESS)
        await asyncio.sleep(0.5)
        if self.active_app == applied_app:
            self.apply_label.value = f"应用到 {applied_app_name}"
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
            (draft.opacity_ui / 100) if has_valid_image else 1.0
        )
        self.opacity_label.value = f"{draft.opacity_ui}%"
        chip_text = self.opacity_chip.content
        assert isinstance(chip_text, ft.Text)
        chip_text.value = f"{draft.opacity_ui}%"
        self.preview_badge.opacity = 1 if has_valid_image else 0.55
        if draft.validation_error:
            self.preview_message.value = draft.validation_error
            self.preview_message.color = ERROR
        elif not draft.image_path:
            self.preview_message.value = "紫霓幻境 · 选择本地壁纸开始预览"
            self.preview_message.color = MUTED
        else:
            self.preview_message.value = ""
        self.apply_label.value = f"应用到 {APP_NAMES[self.active_app]}"
        self.apply_button.opacity = 1 if can_apply(draft) else 0.45
        self.apply_button.disabled = not can_apply(draft)
        self.clear_button.opacity = 1 if draft.installed else 0.4
        self.clear_button.disabled = not draft.installed

    def _show_snack(self, message: str, color: str) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color=TEXT),
                bgcolor=PANEL_ELEVATED,
                close_icon_color=color,
                show_close_icon=True,
                elevation=8,
            )
        )


def main(page: ft.Page) -> None:
    page.title = "Wallpaper Manager"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 1020
    page.window.height = 860
    page.window.min_width = 820
    page.window.min_height = 700
    ui = WallpaperManagerUI(page, build_default_service())
    page.add(ui.build())
    page.run_task(ui._play_entrance)


def run_app() -> None:
    ft.run(main)
