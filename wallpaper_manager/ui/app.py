"""Violet Noir UI — cinematic purple glass with macOS-smooth interactions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import flet as ft

from wallpaper_manager.core.image_service import validate_image_path
from wallpaper_manager.core.models import AppId
from wallpaper_manager.core.service import WallpaperService, build_default_service
from wallpaper_manager.ui import motion as m
from wallpaper_manager.ui.settings_panel import SettingsPanel
from wallpaper_manager.ui.gallery_panel import GalleryPanel
from wallpaper_manager.ui.library_panel import LibraryPanel
from wallpaper_manager.ui.theme import (
    ACCENT,
    ACCENT_2,
    ACCENT_DIM,
    BG,
    ERROR,
    HAIRLINE,
    HAIRLINE_STRONG,
    MUTED,
    PANEL_BORDER,
    PANEL_BORDER_LIT,
    PANEL_ELEVATED,
    RADIUS_CTRL,
    RADIUS_PILL,
    SPACE_MD,
    SPACE_SM,
    SUCCESS,
    SURFACE,
    TEXT,
    TRACK,
    accent_gradient,
    ambient_phase,
    aurora_band,
    frame_aura,
    glass_chip,
    glow,
    micro_label,
    opa,
    page_gradient,
    shell,
    soft_orb,
    spark,
    title_shader,
)

APP_NAMES = {
    AppId.VSCODE: "VS Code",
    AppId.CURSOR: "Cursor",
    AppId.IDEA: "IDEA",
    AppId.PYCHARM: "PyCharm",
    AppId.GHOSTTY: "Ghostty",
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
    if app_id is AppId.GHOSTTY:
        return (
            f"已应用到 {APP_NAMES[app_id]}。"
            "多数外观项可自动重载；若未生效请完全退出 Ghostty 后重开。"
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
        self._tab_busy = False
        self._toast_token = 0
        self._last_preview_src = ""
        self._showing_settings = False
        self._showing_gallery = False
        self._showing_library = False
        self.settings_panel: SettingsPanel | None = None
        self.gallery_panel: GalleryPanel | None = None
        self.library_panel: LibraryPanel | None = None
        self.main_view: ft.Container
        self.settings_view: ft.Container
        self.gallery_view: ft.Container
        self.library_view: ft.Container
        self.settings_button: ft.Container
        self.gallery_button: ft.Container
        self.library_button: ft.Container

        self.preview_image = ft.Image(
            src="",
            fit=ft.BoxFit.COVER,
            expand=True,
            visible=False,
            fade_in_animation=380,
            opacity=1,
            scale=1.0,
            animate_opacity=m.SETTLE,
            animate_scale=m.SETTLE,
        )
        self.preview_veil = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
                colors=[
                    opa(0.0, BG),
                    opa(0.28, BG),
                    opa(0.72, "#05030c"),
                ],
            ),
            ignore_interactions=True,
        )
        self.preview_edge = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=[
                    opa(0.55, ACCENT_2),
                    opa(0.0, ACCENT),
                    opa(0.4, ACCENT_DIM),
                ],
            ),
            blend_mode=ft.BlendMode.SOFT_LIGHT,
            opacity=0.7,
            animate_opacity=ft.Animation(1800, ft.AnimationCurve.EASE_IN_OUT_SINE),
            ignore_interactions=True,
        )
        self.preview_message = ft.Text(
            "选择一张图片，预览会在这里展开",
            color=MUTED,
            size=14,
            text_align=ft.TextAlign.CENTER,
            animate_opacity=m.SNAP,
            opacity=1,
        )
        self.preview_placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.WALLPAPER_OUTLINED,
                        size=42,
                        color=PANEL_BORDER_LIT,
                    ),
                    self.preview_message,
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
            visible=True,
            ignore_interactions=True,
        )
        self.preview_backdrop = ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#1c1532", "#0b0814"],
            ),
            ignore_interactions=True,
        )
        self.preview_badge = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        width=6,
                        height=6,
                        border_radius=6,
                        bgcolor=ACCENT_2,
                        shadow=glow(0.35),
                    ),
                    ft.Text(
                        "LIVE PREVIEW",
                        size=10,
                        weight=ft.FontWeight.W_700,
                        color=TEXT,
                        style=ft.TextStyle(letter_spacing=1.2),
                    ),
                ],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border_radius=RADIUS_PILL,
            bgcolor=opa(0.72, "#0d0a16"),
            border=ft.Border.all(1, HAIRLINE),
            left=14,
            top=14,
        )
        self.opacity_chip = ft.Container(
            content=ft.Text("Opacity 25%", size=11, weight=ft.FontWeight.W_600, color=TEXT),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border_radius=RADIUS_PILL,
            bgcolor=opa(0.72, "#0d0a16"),
            border=ft.Border.all(1, HAIRLINE),
            right=14,
            bottom=14,
            scale=1,
            opacity=1,
            animate_opacity=m.SNAP,
            animate_scale=m.RELEASE,
        )
        self.preview_app_chip = ft.Container(
            content=ft.Text("VS Code", size=11, weight=ft.FontWeight.W_600, color=ACCENT_2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            border_radius=RADIUS_PILL,
            bgcolor=opa(0.72, "#0d0a16"),
            border=ft.Border.all(1, opa(0.4, ACCENT)),
            right=14,
            top=14,
        )
        self.ring_glow = ft.Container(
            expand=True,
            border_radius=20,
            border=ft.Border.all(1.5, opa(0.0, ACCENT)),
            animate=m.SETTLE,
            ignore_interactions=True,
        )
        self.path_field = ft.TextField(
            label="图片路径",
            hint_text="粘贴绝对路径，或点击浏览",
            prefix_icon=ft.Icons.LINK_ROUNDED,
            color=TEXT,
            label_style=ft.TextStyle(color=MUTED, size=11),
            hint_style=ft.TextStyle(color=opa(0.55, MUTED), size=13),
            bgcolor=TRACK,
            border_color=PANEL_BORDER,
            focused_border_color=ACCENT,
            border_radius=RADIUS_CTRL,
            filled=True,
            cursor_color=ACCENT,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=14),
            on_change=self._on_path_change,
            on_submit=self._on_path_change,
            expand=True,
        )
        self.opacity_label = ft.AnimatedSwitcher(
            content=ft.Text("25%", color=ACCENT_2, weight=ft.FontWeight.W_700, size=15),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=180,
            reverse_duration=120,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
        )
        self.opacity_slider = ft.CupertinoSlider(
            min=0,
            max=100,
            active_color=ACCENT,
            thumb_color="#ffffff",
            on_change=self._on_opacity_change,
            on_change_end=self._on_opacity_settle,
            expand=True,
        )
        self.opacity_value_chip = ft.Container(
            content=self.opacity_label,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border_radius=12,
            bgcolor=opa(0.18, ACCENT),
            border=ft.Border.all(1, opa(0.45, ACCENT)),
            alignment=ft.Alignment.CENTER,
        )
        self.opacity_slider_well = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=self.opacity_slider,
                        expand=True,
                        padding=ft.Padding.only(left=4, right=8, top=2, bottom=2),
                        alignment=ft.Alignment.CENTER_LEFT,
                    ),
                    self.opacity_value_chip,
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            border_radius=16,
            bgcolor=TRACK,
            border=ft.Border.all(1, HAIRLINE),
            shadow=[
                ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=12,
                    color=opa(0.35, "#000000"),
                    offset=ft.Offset(0, 4),
                )
            ],
        )
        self.clear_button = ft.Container(
            content=ft.Text("清除", color=MUTED, weight=ft.FontWeight.W_600, size=13),
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            border_radius=RADIUS_PILL,
            border=ft.Border.all(1, HAIRLINE),
            bgcolor=opa(0.35, "#120e1c"),
            animate_opacity=m.SNAP,
            animate_scale=m.HOVER,
            scale=1,
            ink=False,
        )
        self.apply_icon_wrap = ft.Container(
            content=ft.Icon(ft.Icons.ARROW_FORWARD_ROUNDED, size=15, color=BG),
            width=28,
            height=28,
            border_radius=28,
            bgcolor=opa(0.18, "#000000"),
            alignment=ft.Alignment.CENTER,
            animate_scale=m.RELEASE,
            scale=1,
        )
        self.apply_label = ft.Text("应用到", color=BG, weight=ft.FontWeight.W_700, size=13)
        self.apply_button = ft.Container(
            content=ft.Row(
                [self.apply_label, self.apply_icon_wrap],
                spacing=10,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(left=18, right=6, top=6, bottom=6),
            border_radius=RADIUS_PILL,
            gradient=accent_gradient(),
            shadow=glow(0.32),
            animate=ft.Animation(1800, ft.AnimationCurve.EASE_IN_OUT_SINE),
            animate_scale=m.HOVER,
            animate_opacity=m.SNAP,
            scale=1,
            ink=False,
        )
        self.apply_icon = self.apply_icon_wrap.content
        self.browse_button = ft.Container(
            content=ft.Text("浏览", color=ACCENT_2, weight=ft.FontWeight.W_700, size=13),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            border_radius=RADIUS_CTRL,
            border=ft.Border.all(1, opa(0.55, ACCENT)),
            bgcolor=opa(0.1, ACCENT),
            animate_scale=m.HOVER,
            scale=1,
            ink=False,
        )
        self.status_dot = ft.Container(
            width=8,
            height=8,
            border_radius=8,
            bgcolor=ACCENT_2,
            shadow=glow(0.5),
            animate_opacity=m.SOFT,
            opacity=1,
        )
        self.status_text = ft.Text("", size=12, color=TEXT, weight=ft.FontWeight.W_600)
        self.toast = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, size=18, color=ACCENT_2),
                    ft.Text("", color=TEXT, size=13, weight=ft.FontWeight.W_600, expand=True),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            border_radius=16,
            bgcolor=opa(0.92, PANEL_ELEVATED),
            border=ft.Border.all(1, HAIRLINE),
            shadow=glow(0.28),
            top=22,
            left=36,
            right=36,
            opacity=0,
            offset=ft.Offset(0, -0.35),
            animate_opacity=m.SETTLE,
            animate_offset=m.SETTLE,
            visible=False,
            ignore_interactions=True,
        )
        self.header_block: ft.Container
        self.tabs_block: ft.Container
        self.main_panel: ft.Container
        self.preview_shell: ft.Container
        self.root_shell: ft.Container
        self.orb_a: ft.Container
        self.orb_b: ft.Container
        self.orb_c: ft.Container
        self.aurora: ft.Container
        self.sparks: list[ft.Container] = []
        self.preview_aura: ft.Container
        self._ambient_t = 0.0
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
                    size=12,
                    weight=ft.FontWeight.W_700,
                    color=TEXT if selected else MUTED,
                ),
                ft.Row(
                    [
                        ft.Container(
                            width=5,
                            height=5,
                            border_radius=5,
                            bgcolor=ACCENT_2 if draft.installed else ERROR,
                        ),
                        ft.Text(
                            status,
                            size=9,
                            weight=ft.FontWeight.W_600,
                            color=ACCENT_2 if draft.installed else ERROR,
                        ),
                    ],
                    spacing=5,
                    tight=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=4,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        tab = ft.Container(
            content=body,
            padding=ft.Padding.symmetric(horizontal=10, vertical=10),
            border_radius=12,
            expand=True,
            alignment=ft.Alignment.CENTER,
            bgcolor=opa(0.18, "#ffffff") if selected else "#00000000",
            border=ft.Border.all(1, HAIRLINE_STRONG if selected else "#00000000"),
            shadow=glow(0.2) if selected else None,
            animate=m.SNAP,
            animate_scale=m.HOVER,
            scale=m.IDLE,
            ink=False,
        )
        m.wire_pressable(
            tab,
            page=self.page,
            on_click=self._tab_click_handler(app_id),
            idle_scale=m.IDLE,
            hover_scale=1.01,
            press_scale=0.985,
            selected_scale=m.IDLE,
            is_selected=lambda aid=app_id: aid == self.active_app,
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
            tab.bgcolor = opa(0.18, "#ffffff") if selected else "#00000000"
            tab.border = ft.Border.all(1, HAIRLINE_STRONG if selected else "#00000000")
            tab.shadow = glow(0.2) if selected else None
            tab.scale = m.IDLE
            col = tab.content
            assert isinstance(col, ft.Column)
            title, status_row = col.controls
            assert isinstance(title, ft.Text)
            assert isinstance(status_row, ft.Row)
            title.color = TEXT if selected else MUTED
            title.value = APP_NAMES[app_id]
            dot, status = status_row.controls
            assert isinstance(dot, ft.Container)
            assert isinstance(status, ft.Text)
            status.value = "已连接" if draft.installed else "未安装"
            status.color = ACCENT_2 if draft.installed else ERROR
            dot.bgcolor = ACCENT_2 if draft.installed else ERROR

    async def _select_tab(self, app_id: AppId) -> None:
        if app_id == self.active_app or self._tab_busy:
            return
        self._tab_busy = True
        old_idx = APP_ORDER.index(self.active_app)
        new_idx = APP_ORDER.index(app_id)
        # Moving right in the tab bar → old exits left, new enters from right.
        direction = 1 if new_idx > old_idx else -1
        slide = m.TAB_SLIDE * direction
        try:
            # 1) Highlight tab immediately (iOS segmented control feel).
            self.active_app = app_id
            self._refresh_tabs()
            self.page.update()

            # 2) Current panel slides out with a soft fade.
            self.main_panel.animate_opacity = m.TAB_OUT
            self.main_panel.animate_offset = m.TAB_OUT
            self.main_panel.opacity = 0
            self.main_panel.offset = ft.Offset(-slide, 0)
            self.page.update()
            await asyncio.sleep(0.22)

            # 3) Swap content, park new panel off-stage with NO animated jump.
            self._load_active_draft(animate_preview=False)
            self.main_panel.animate_opacity = m.INSTANT
            self.main_panel.animate_offset = m.INSTANT
            self.main_panel.offset = ft.Offset(slide, 0)
            self.main_panel.opacity = 0
            self.page.update()
            await asyncio.sleep(0.02)

            # 4) New panel slides in from the arrival side.
            self.main_panel.animate_opacity = m.TAB_IN
            self.main_panel.animate_offset = m.TAB_IN
            self.main_panel.opacity = 1
            self.main_panel.offset = ft.Offset(0, 0)
            self.page.update()
            await asyncio.sleep(0.3)
        finally:
            self.main_panel.animate_opacity = m.ENTRANCE
            self.main_panel.animate_offset = m.ENTRANCE
            self._tab_busy = False

    def build(self) -> ft.Control:
        installed_count = sum(d.installed for d in self.drafts.values())
        self.status_text.value = f"{installed_count}/{len(APP_ORDER)} 已连接"

        title = ft.ShaderMask(
            content=ft.Text(
                "Wallpaper Manager",
                size=32,
                weight=ft.FontWeight.W_800,
                color=ft.Colors.WHITE,
                style=ft.TextStyle(letter_spacing=-0.8, height=1.05),
            ),
            shader=title_shader(),
            blend_mode=ft.BlendMode.SRC_IN,
        )

        self.settings_button = ft.Container(
            content=ft.Icon(ft.Icons.TUNE_ROUNDED, size=17, color=ACCENT_2),
            width=38,
            height=38,
            border_radius=19,
            alignment=ft.Alignment.CENTER,
            bgcolor=SURFACE,
            border=ft.Border.all(1, HAIRLINE),
            ink=False,
        )
        self.gallery_button = ft.Container(
            content=ft.Icon(ft.Icons.PHOTO_LIBRARY_ROUNDED, size=17, color=ACCENT_2),
            width=38,
            height=38,
            border_radius=19,
            alignment=ft.Alignment.CENTER,
            bgcolor=SURFACE,
            border=ft.Border.all(1, HAIRLINE),
            ink=False,
            tooltip="在线图库",
        )
        self.library_button = ft.Container(
            content=ft.Icon(ft.Icons.FAVORITE_ROUNDED, size=17, color=ACCENT_2),
            width=38,
            height=38,
            border_radius=19,
            alignment=ft.Alignment.CENTER,
            bgcolor=SURFACE,
            border=ft.Border.all(1, HAIRLINE),
            ink=False,
            tooltip="收藏与历史",
        )

        status_chip = glass_chip(
            ft.Row(
                [self.status_dot, self.status_text],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            lit=True,
        )

        self.header_block = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                "VIOLET NOIR",
                                size=10,
                                weight=ft.FontWeight.W_700,
                                color=ACCENT_2,
                                style=ft.TextStyle(letter_spacing=3.2),
                            ),
                            title,
                            ft.Text(
                                "按应用独立管理壁纸 · 本地配置即时写入",
                                size=12,
                                color=MUTED,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    ft.Container(expand=True),
                    self.library_button,
                    self.gallery_button,
                    self.settings_button,
                    status_chip,
                ],
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            opacity=0,
            offset=ft.Offset(0, 0.035),
            animate_opacity=m.ENTRANCE,
            animate_offset=m.ENTRANCE,
        )

        self.tabs_block = ft.Container(
            content=ft.Row(
                [self._make_tab(app_id) for app_id in APP_ORDER],
                spacing=4,
            ),
            padding=5,
            border_radius=16,
            bgcolor=TRACK,
            border=ft.Border.all(1, HAIRLINE),
            opacity=0,
            offset=ft.Offset(0, 0.035),
            animate_opacity=m.ENTRANCE,
            animate_offset=m.ENTRANCE,
        )

        preview_inner = ft.Container(
            content=ft.Stack(
                [
                    self.preview_backdrop,
                    self.preview_placeholder,
                    self.preview_image,
                    self.preview_veil,
                    self.preview_edge,
                    self.preview_badge,
                    self.preview_app_chip,
                    self.opacity_chip,
                    self.ring_glow,
                ],
                fit=ft.StackFit.EXPAND,
            ),
            height=300,
            border_radius=18,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        self.preview_shell = shell(preview_inner, padding=6, radius=24)
        self.preview_shell.scale = 1
        self.preview_shell.animate_scale = m.SETTLE
        self.preview_aura = frame_aura()
        self.preview_frame = ft.Stack(
            [
                self.preview_aura,
                self.preview_shell,
            ],
        )

        action_bar = ft.Container(
            content=ft.Row(
                [self.clear_button, ft.Container(expand=True), self.apply_button],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            border_radius=18,
            bgcolor=TRACK,
            border=ft.Border.all(1, HAIRLINE),
        )

        controls = ft.Column(
            [
                micro_label("Image Source"),
                ft.Row([self.path_field, self.browse_button], spacing=SPACE_SM),
                ft.Container(height=SPACE_SM),
                micro_label("Opacity"),
                self.opacity_slider_well,
                ft.Text(
                    "0% 完全透明 · 100% 完全不透明 · 编辑器主题底色会透出",
                    size=11,
                    color=MUTED,
                ),
                ft.Container(height=SPACE_SM),
                action_bar,
            ],
            spacing=SPACE_SM,
        )

        panel_body = ft.Container(
            content=ft.Column([self.preview_frame, controls], spacing=SPACE_MD),
            padding=SPACE_MD,
        )
        self.main_panel = ft.Container(
            content=shell(panel_body, padding=7, radius=28),
            opacity=0,
            offset=ft.Offset(0, 0.04),
            animate_opacity=m.ENTRANCE,
            animate_offset=m.ENTRANCE,
        )

        self.main_view = ft.Container(
            content=ft.Column(
                [self.header_block, self.tabs_block, self.main_panel],
                spacing=18,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=ft.Padding.symmetric(horizontal=32, vertical=26),
            expand=True,
            visible=True,
            opacity=1,
            animate_opacity=m.PANEL,
        )

        self.settings_panel = SettingsPanel(
            self.page,
            self.service,
            APP_NAMES,
            APP_ORDER,
            on_back=self._show_main,
            on_paths_changed=self._reload_after_path_change,
            on_toast=self._toast_from_settings,
        )
        self.settings_view = ft.Container(
            content=self.settings_panel.control(),
            padding=ft.Padding.symmetric(horizontal=36, vertical=28),
            expand=True,
            visible=False,
            opacity=0,
            animate_opacity=m.PANEL,
        )
        self.gallery_panel = GalleryPanel(
            self.page,
            self.service,
            APP_NAMES,
            active_app=lambda: self.active_app,
            opacity_for=lambda app_id: self.drafts[app_id].opacity_ui,
            on_back=self._show_main,
            on_applied=self._on_gallery_applied,
            on_toast=self._toast_from_settings,
        )
        self.gallery_view = ft.Container(
            content=self.gallery_panel.control(),
            padding=ft.Padding.symmetric(horizontal=36, vertical=28),
            expand=True,
            visible=False,
            opacity=0,
            animate_opacity=m.PANEL,
        )
        self.library_panel = LibraryPanel(
            self.page,
            self.service,
            APP_NAMES,
            active_app=lambda: self.active_app,
            opacity_for=lambda app_id: self.drafts[app_id].opacity_ui,
            on_back=self._show_main,
            on_applied=self._on_gallery_applied,
            on_toast=self._toast_from_settings,
        )
        self.library_view = ft.Container(
            content=self.library_panel.control(),
            padding=ft.Padding.symmetric(horizontal=36, vertical=28),
            expand=True,
            visible=False,
            opacity=0,
            animate_opacity=m.PANEL,
        )

        self.aurora = aurora_band()
        self.orb_a = soft_orb(
            420, "#a855f7", 0.26, breathe_ms=5600, top=-160, right=-100
        )
        self.orb_b = soft_orb(
            320, "#e879f9", 0.16, breathe_ms=6400, bottom=-140, left=-110
        )
        self.orb_c = soft_orb(
            240, "#7c3aed", 0.14, breathe_ms=7200, top=240, left=400
        )
        self.sparks = [
            spark(3, top=100, left=200),
            spark(4, color="#ffffff", top=160, right=160),
            spark(3, bottom=180, left=280),
            spark(3, top=320, right=240),
            spark(4, color=ACCENT_2, bottom=120, right=320),
        ]

        self.root_shell = ft.Container(
            expand=True,
            gradient=page_gradient(),
            content=ft.Stack(
                [
                    self.aurora,
                    self.orb_a,
                    self.orb_b,
                    self.orb_c,
                    *self.sparks,
                    self.main_view,
                    self.settings_view,
                    self.gallery_view,
                    self.library_view,
                    self.toast,
                ],
                expand=True,
            ),
        )

        m.wire_pressable(
            self.settings_button,
            page=self.page,
            on_click=self._show_settings,
            hover_scale=1.06,
            press_scale=0.94,
        )
        m.wire_pressable(
            self.gallery_button,
            page=self.page,
            on_click=self._show_gallery,
            hover_scale=1.06,
            press_scale=0.94,
        )
        m.wire_pressable(
            self.library_button,
            page=self.page,
            on_click=self._show_library,
            hover_scale=1.06,
            press_scale=0.94,
        )
        m.wire_pressable(
            self.browse_button,
            page=self.page,
            on_click=self._on_browse,
            hover_scale=1.04,
            press_scale=0.96,
        )
        m.wire_pressable(
            self.apply_button,
            page=self.page,
            on_click=self._on_apply,
            hover_scale=1.035,
            press_scale=0.955,
            is_enabled=lambda: can_apply(self.drafts[self.active_app]),
        )
        m.wire_pressable(
            self.clear_button,
            page=self.page,
            on_click=self._on_clear,
            hover_scale=1.03,
            press_scale=0.96,
            is_enabled=lambda: self.drafts[self.active_app].installed,
        )

        self._load_active_draft(animate_preview=False)
        self._refresh_tabs()
        return self.root_shell

    async def _show_settings(self, _event: ft.ControlEvent | None = None) -> None:
        if self.settings_panel is None:
            return
        self._showing_settings = True
        self._showing_gallery = False
        self._showing_library = False
        self.settings_panel.reload()
        await self._swap_to_overlay(self.settings_view)

    async def _show_gallery(self, _event: ft.ControlEvent | None = None) -> None:
        if self.gallery_panel is None:
            return
        self._showing_gallery = True
        self._showing_settings = False
        self._showing_library = False
        await self._swap_to_overlay(self.gallery_view)
        await self.gallery_panel.reload()

    async def _show_library(self, _event: ft.ControlEvent | None = None) -> None:
        if self.library_panel is None:
            return
        self._showing_library = True
        self._showing_settings = False
        self._showing_gallery = False
        self.library_panel.reload()
        await self._swap_to_overlay(self.library_view)

    async def _swap_to_overlay(self, overlay: ft.Container) -> None:
        self.main_view.opacity = 0
        self.page.update()
        await asyncio.sleep(0.08)
        self.main_view.visible = False
        for view in (self.settings_view, self.gallery_view, self.library_view):
            view.visible = False
            view.opacity = 0
        overlay.visible = True
        overlay.opacity = 0
        self.page.update()
        await asyncio.sleep(0.016)
        overlay.opacity = 1
        self.page.update()

    async def _show_main(self, _event: ft.ControlEvent | None = None) -> None:
        self._showing_settings = False
        self._showing_gallery = False
        self._showing_library = False
        for view in (self.settings_view, self.gallery_view, self.library_view):
            view.opacity = 0
        self.page.update()
        await asyncio.sleep(0.08)
        for view in (self.settings_view, self.gallery_view, self.library_view):
            view.visible = False
        self.main_view.visible = True
        self.main_view.opacity = 0
        self.page.update()
        await asyncio.sleep(0.016)
        self.main_view.opacity = 1
        self.page.update()

    async def _on_gallery_applied(
        self, app_id: AppId, image_path: str, opacity_ui: int
    ) -> None:
        draft = self.drafts[app_id]
        draft.image_path = image_path
        draft.opacity_ui = opacity_ui
        draft.validation_error = None
        tip = self.service.extension_tip(app_id)
        if tip:
            draft.last_error = tip
        else:
            draft.last_error = None
        if app_id == self.active_app:
            self._load_active_draft(animate_preview=True)
        else:
            self.active_app = app_id
            self._refresh_tabs()
            self._load_active_draft(animate_preview=True)

    def _reload_after_path_change(self) -> None:
        states = self.service.bootstrap()
        for app_id in APP_ORDER:
            self.drafts[app_id] = self._draft_from_state(states[app_id])
        installed_count = sum(d.installed for d in self.drafts.values())
        self.status_text.value = f"{installed_count}/{len(APP_ORDER)} 已连接"
        self._refresh_tabs()
        self._load_active_draft(animate_preview=False)

    async def _toast_from_settings(self, message: str, color: str) -> None:
        await self._show_toast(message, color, ok=color != ERROR)

    async def _play_entrance(self) -> None:
        await asyncio.sleep(0.03)
        self.header_block.opacity = 1
        self.header_block.offset = ft.Offset(0, 0)
        self.page.update()
        await asyncio.sleep(0.07)
        self.tabs_block.opacity = 1
        self.tabs_block.offset = ft.Offset(0, 0)
        self.page.update()
        await asyncio.sleep(0.07)
        self.main_panel.opacity = 1
        self.main_panel.offset = ft.Offset(0, 0)
        self.preview_aura.opacity = 1
        self.preview_aura.scale = 1.02
        self.page.update()
        await asyncio.sleep(0.2)
        self.preview_aura.scale = 1.0
        self.page.update()
        if not self._motion_running:
            self._motion_running = True
            self.page.run_task(self._ambient_loop)

    async def _ambient_loop(self) -> None:
        while self._motion_running:
            self._ambient_t += 0.4
            t = self._ambient_t
            a = ambient_phase(t)
            b = ambient_phase(t + 1.3)
            c = ambient_phase(t + 2.1)

            self.orb_a.opacity = 0.55 + 0.3 * a
            self.orb_a.scale = 0.96 + 0.08 * a
            self.orb_a.rotate = ft.Rotate(t * 0.1, alignment=ft.Alignment.CENTER)

            self.orb_b.opacity = 0.4 + 0.28 * b
            self.orb_b.scale = 0.95 + 0.1 * b
            self.orb_b.rotate = ft.Rotate(-t * 0.08, alignment=ft.Alignment.CENTER)

            self.orb_c.opacity = 0.35 + 0.28 * c
            self.orb_c.scale = 0.96 + 0.08 * c
            self.orb_c.rotate = ft.Rotate(t * 0.12, alignment=ft.Alignment.CENTER)

            self.aurora.opacity = 0.5 + 0.25 * ambient_phase(t * 0.55)
            self.status_dot.opacity = 0.45 + 0.55 * ambient_phase(t * 1.1)
            self.preview_aura.opacity = 0.35 + 0.28 * ambient_phase(t * 0.85)
            self.preview_aura.scale = 0.992 + 0.014 * ambient_phase(t * 0.85)
            self.preview_edge.opacity = 0.4 + 0.3 * ambient_phase(t * 0.7)
            self.apply_button.shadow = glow(0.22 + 0.18 * ambient_phase(t * 0.9))

            for i, s in enumerate(self.sparks):
                twinkle = ambient_phase(t * 1.6 + i * 0.9)
                s.opacity = 0.2 + 0.55 * twinkle
                s.scale = 0.7 + 0.45 * twinkle

            self.page.update()
            await asyncio.sleep(1.35)

    def _on_path_change(self, event: ft.Event[ft.TextField]) -> None:
        path = event.control.value.strip()
        draft = self.drafts[self.active_app]
        draft.image_path = path or None
        if path:
            valid, error = validate_image_path(path)
            draft.validation_error = None if valid else error
        else:
            draft.validation_error = None
        self._refresh_preview(animate_image=True)
        self.page.update()

    def _on_opacity_change(self, event: ft.ControlEvent) -> None:
        draft = self.drafts[self.active_app]
        draft.opacity_ui = int(round(event.control.value or 0))
        self._refresh_preview(animate_image=False)
        self.opacity_chip.scale = 1.04
        self.page.update()

    def _on_opacity_settle(self, _event: ft.ControlEvent) -> None:
        self.opacity_chip.scale = 1.0
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
        self._refresh_preview(animate_image=True)
        self.preview_shell.scale = 1.015
        self.page.update()
        await asyncio.sleep(0.18)
        self.preview_shell.scale = 1.0
        self.page.update()

    async def _on_apply(self, _event: ft.ControlEvent) -> None:
        draft = self.drafts[self.active_app]
        if not can_apply(draft):
            return
        valid, error = validate_image_path(draft.image_path or "")
        if not valid:
            draft.validation_error = error
            self._refresh_preview(animate_image=False)
            self.page.update()
            return
        absolute_path = normalize_image_path(draft.image_path or "")
        draft.image_path = absolute_path
        self.path_field.value = absolute_path
        result = self.service.apply(self.active_app, absolute_path, draft.opacity_ui)
        if result.last_error:
            await self._show_toast(f"应用失败：{result.last_error}", ERROR, ok=False)
            return

        applied_app = self.active_app
        applied_name = APP_NAMES[applied_app]
        self.apply_icon_wrap.scale = 1.18
        self.ring_glow.border = ft.Border.all(2.2, ACCENT_2)
        self.preview_shell.scale = 1.02
        self.preview_aura.opacity = 1
        self.preview_aura.scale = 1.06
        self.apply_button.shadow = glow(0.85)
        self.apply_label.value = "已应用"
        assert isinstance(self.apply_icon, ft.Icon)
        self.apply_icon.name = ft.Icons.CHECK_ROUNDED
        self.page.update()
        await asyncio.sleep(0.18)
        self.apply_icon_wrap.scale = 1.0
        self.preview_shell.scale = 1.0
        self.preview_aura.scale = 1.0
        self.page.update()
        tip = self.service.extension_tip(applied_app)
        message = apply_success_message(applied_app)
        await self._show_toast(f"{message} {tip}" if tip else message, SUCCESS)
        await asyncio.sleep(0.45)
        self.ring_glow.border = ft.Border.all(1.5, opa(0.0, ACCENT))
        if self.active_app == applied_app:
            self.apply_label.value = f"应用到 {applied_name}"
            self.apply_icon.name = ft.Icons.ARROW_FORWARD_ROUNDED
        self.page.update()

    async def _on_clear(self, _event: ft.ControlEvent) -> None:
        result = self.service.clear(self.active_app)
        if result.last_error:
            await self._show_toast(f"清除失败：{result.last_error}", ERROR, ok=False)
            return
        self.drafts[self.active_app] = self._draft_from_state(result)
        self.preview_image.opacity = 0
        self.page.update()
        await asyncio.sleep(0.12)
        self._load_active_draft(animate_preview=False)
        self._refresh_tabs()
        self.page.update()
        await self._show_toast(f"已清除 {APP_NAMES[self.active_app]} 的壁纸设置。", SUCCESS)

    def _load_active_draft(self, *, animate_preview: bool = True) -> None:
        draft = self.drafts[self.active_app]
        self.path_field.value = draft.image_path or ""
        self.opacity_slider.value = draft.opacity_ui
        self._refresh_preview(animate_image=animate_preview)

    def _set_opacity_label(self, value: int) -> None:
        self.opacity_label.content = ft.Text(
            f"{value}%",
            color=ACCENT_2,
            weight=ft.FontWeight.W_700,
            size=15,
        )

    def _refresh_preview(self, *, animate_image: bool = False) -> None:
        draft = self.drafts[self.active_app]
        has_valid_image = bool(draft.image_path and not draft.validation_error)
        new_src = (
            normalize_image_path(draft.image_path)
            if has_valid_image and draft.image_path
            else ""
        )
        src_changed = new_src != self._last_preview_src
        self._last_preview_src = new_src

        if animate_image and src_changed and has_valid_image:
            self.preview_placeholder.visible = False
            self.page.run_task(self._crossfade_preview, new_src, draft.opacity_ui)
        else:
            self.preview_image.src = new_src
            self.preview_image.visible = has_valid_image
            self.preview_image.opacity = (
                max(0.28, draft.opacity_ui / 100) if has_valid_image else 1.0
            )
            self.preview_image.scale = 1.015 if has_valid_image else 1.0
            self.preview_placeholder.visible = not has_valid_image

        self._set_opacity_label(draft.opacity_ui)
        chip = self.opacity_chip.content
        assert isinstance(chip, ft.Text)
        chip.value = f"Opacity {draft.opacity_ui}%"
        app_chip = self.preview_app_chip.content
        assert isinstance(app_chip, ft.Text)
        app_chip.value = APP_NAMES[self.active_app]
        if draft.validation_error:
            self.preview_placeholder.visible = True
            self.preview_message.value = draft.validation_error
            self.preview_message.color = ERROR
            self.preview_message.opacity = 1
        elif not draft.image_path:
            self.preview_placeholder.visible = True
            self.preview_message.value = "选择一张图片，预览会在这里展开"
            self.preview_message.color = MUTED
            self.preview_message.opacity = 1
        else:
            self.preview_message.value = ""
            self.preview_message.opacity = 0
        self.apply_label.value = f"应用到 {APP_NAMES[self.active_app]}"
        self.apply_button.opacity = 1 if can_apply(draft) else 0.4
        self.apply_button.disabled = not can_apply(draft)
        self.clear_button.opacity = 1 if draft.installed else 0.35
        self.clear_button.disabled = not draft.installed

    async def _crossfade_preview(self, src: str, opacity_ui: int) -> None:
        self.preview_placeholder.visible = False
        self.preview_image.opacity = 0
        self.preview_image.scale = 1.04
        self.page.update()
        await asyncio.sleep(0.12)
        self.preview_image.src = src
        self.preview_image.visible = True
        self.preview_image.opacity = max(0.28, opacity_ui / 100)
        self.preview_image.scale = 1.015
        self.page.update()

    async def _show_toast(self, message: str, color: str, *, ok: bool = True) -> None:
        self._toast_token += 1
        token = self._toast_token
        row = self.toast.content
        assert isinstance(row, ft.Row)
        icon, text = row.controls
        assert isinstance(icon, ft.Icon)
        assert isinstance(text, ft.Text)
        icon.name = ft.Icons.CHECK_CIRCLE_ROUNDED if ok else ft.Icons.ERROR_ROUNDED
        icon.color = color if not ok else ACCENT_2
        text.value = message
        self.toast.visible = True
        self.toast.opacity = 0
        self.toast.offset = ft.Offset(0, -0.35)
        self.page.update()
        await asyncio.sleep(0.016)
        self.toast.opacity = 1
        self.toast.offset = ft.Offset(0, 0)
        self.page.update()
        await asyncio.sleep(3.2)
        if token != self._toast_token:
            return
        self.toast.opacity = 0
        self.toast.offset = ft.Offset(0, -0.25)
        self.page.update()
        await asyncio.sleep(0.28)
        if token == self._toast_token:
            self.toast.visible = False
            self.page.update()


def main(page: ft.Page) -> None:
    page.title = "Wallpaper Manager"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(
        color_scheme_seed=ACCENT,
        splash_color=opa(0.2, ACCENT_2),
        highlight_color=opa(0.12, ACCENT),
    )
    page.padding = 0
    page.window.width = 1080
    page.window.height = 840
    page.window.min_width = 880
    page.window.min_height = 700
    # Window / task-switcher icon (Dock icon for packaged .app comes from --icon).
    icon_path = _resolve_app_icon()
    if icon_path is not None:
        page.window.icon = str(icon_path)
    ui = WallpaperManagerUI(page, build_default_service())
    page.add(ui.build())
    page.run_task(ui._play_entrance)


def _resolve_app_icon() -> Path | None:
    root = Path(__file__).resolve().parents[2]
    for name in ("icon.png", "icon.icns", "shayu.jpg"):
        candidate = root / "assets" / name
        if candidate.is_file():
            return candidate
    return None


def run_app() -> None:
    assets = Path(__file__).resolve().parents[2] / "assets"
    ft.run(main, assets_dir=str(assets) if assets.is_dir() else "assets")
