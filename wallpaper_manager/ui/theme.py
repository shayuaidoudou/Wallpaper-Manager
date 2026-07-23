"""Violet Noir — refined purple glass theme.

Note: Flet/Flutter 8-digit hex is #AARRGGBB (NOT #RRGGBBAA).
Prefer Colors.with_opacity() for translucent colors.
"""

from __future__ import annotations

import flet as ft

BG = "#0a0612"
PANEL = "#14101f"
PANEL_ELEVATED = "#1a1528"
ACCENT = "#c084fc"
ACCENT_2 = "#f0abfc"
ACCENT_DIM = "#9333ea"
TEXT = "#faf5ff"
MUTED = "#a89bbf"
PANEL_BORDER = "#2e2148"
PANEL_BORDER_LIT = "#7c3aed"
ERROR = "#fb7185"
SUCCESS = "#e9d5ff"
HAIRLINE = ft.Colors.with_opacity(0.08, "#ffffff")


def page_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment(-1, -1),
        end=ft.Alignment(1, 1),
        colors=["#1c1030", BG, "#07040c"],
        stops=[0.0, 0.55, 1.0],
    )


def accent_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=["#f5d0fe", "#e879f9", "#a855f7"],
    )


def panel_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=[
            ft.Colors.with_opacity(0.94, "#1c1630"),
            ft.Colors.with_opacity(0.97, "#120e1c"),
        ],
    )


def elev_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=28,
            color=ft.Colors.with_opacity(0.45, "#000000"),
            offset=ft.Offset(0, 16),
        ),
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color=ft.Colors.with_opacity(0.14, "#a855f7"),
            offset=ft.Offset(0, 0),
        ),
    ]


def glow_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=18,
            color=ft.Colors.with_opacity(0.35, "#e879f9"),
            offset=ft.Offset(0, 0),
        ),
    ]


def soft_orb(size: float, color: str, opacity: float = 0.35, **pos) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        border_radius=size,
        gradient=ft.RadialGradient(
            center=ft.Alignment.CENTER,
            radius=0.9,
            colors=[ft.Colors.with_opacity(opacity, color), "#00000000"],
        ),
        opacity=1,
        scale=1,
        animate_opacity=ft.Animation(3200, ft.AnimationCurve.EASE_IN_OUT),
        animate_scale=ft.Animation(3800, ft.AnimationCurve.EASE_IN_OUT),
        ignore_interactions=True,
        **pos,
    )
