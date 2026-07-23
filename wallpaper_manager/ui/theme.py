"""Violet Luxe visual tokens — glamorous purple motion chrome."""

from __future__ import annotations

import flet as ft

BG = "#09060f"
BG_MID = "#120a1c"
PANEL = "#161022"
PANEL_ELEVATED = "#1c1430"
ACCENT = "#c084fc"
ACCENT_2 = "#e879f9"
ACCENT_DIM = "#7c3aed"
TEXT = "#faf5ff"
MUTED = "#b6a4d4"
PANEL_BORDER = "#3b2758"
PANEL_BORDER_LIT = "#6d28d9"
ERROR = "#fb7185"
SUCCESS = "#d8b4fe"  # lilac, keeps palette purple (not neon green)
GLOW = "#a855f755"
GLOW_SOFT = "#c084fc33"


def page_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=["#1a0b2e", BG, "#05030a"],
        stops=[0.0, 0.48, 1.0],
    )


def accent_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=["#f0abfc", "#e879f9", "#a855f7", "#7c3aed"],
    )


def glass_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=32,
            color="#00000066",
            offset=ft.Offset(0, 14),
        ),
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=24,
            color=GLOW,
            offset=ft.Offset(0, 0),
        ),
    ]


def soft_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=18,
            color="#c084fc33",
            offset=ft.Offset(0, 8),
        ),
    ]


def selected_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=22,
            color="#e879f966",
            offset=ft.Offset(0, 0),
        ),
    ]


def ambient_orb(
    *,
    size: float,
    color: str,
    top: float | None = None,
    left: float | None = None,
    right: float | None = None,
    bottom: float | None = None,
    opacity: float = 0.55,
) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        top=top,
        left=left,
        right=right,
        bottom=bottom,
        border_radius=size,
        gradient=ft.RadialGradient(
            center=ft.Alignment.CENTER,
            radius=0.85,
            colors=[color, "#00000000"],
        ),
        animate_opacity=ft.Animation(2000, ft.AnimationCurve.EASE_IN_OUT),
        animate_scale=ft.Animation(2400, ft.AnimationCurve.EASE_IN_OUT),
        opacity=opacity,
        scale=1.0,
        ignore_interactions=True,
    )
