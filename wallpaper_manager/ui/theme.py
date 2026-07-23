"""Violet Noir — commercial ethereal glass.

Flet/Flutter translucent hex is #AARRGGBB.
Always prefer Colors.with_opacity(alpha, "#RRGGBB").
"""

from __future__ import annotations

import math

import flet as ft

BG = "#07040f"
PANEL = "#12101c"
PANEL_ELEVATED = "#1a1529"
ACCENT = "#c084fc"
ACCENT_2 = "#f0abfc"
ACCENT_DIM = "#9333ea"
TEXT = "#faf5ff"
MUTED = "#a89bbf"
PANEL_BORDER = "#2a1f42"
PANEL_BORDER_LIT = "#7c3aed"
ERROR = "#fb7185"
SUCCESS = "#e9d5ff"

SPACE_XS = 6
SPACE_SM = 10
SPACE_MD = 16
SPACE_LG = 24
RADIUS_CTRL = 14
RADIUS_PANEL = 26
RADIUS_PILL = 999


def opa(alpha: float, color: str) -> str:
    return ft.Colors.with_opacity(alpha, color)


HAIRLINE = opa(0.09, "#ffffff")
HAIRLINE_STRONG = opa(0.16, "#ffffff")
TRACK = opa(0.55, "#0a0714")
SURFACE = opa(0.72, "#141022")


def page_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment(-1, -1),
        end=ft.Alignment(1, 1),
        colors=["#2a1748", "#12091f", BG, "#03010a"],
        stops=[0.0, 0.32, 0.68, 1.0],
    )


def accent_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=["#fdf4ff", "#f0abfc", "#c084fc", "#9333ea"],
    )


def title_shader() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.CENTER_LEFT,
        end=ft.Alignment.CENTER_RIGHT,
        colors=["#ffffff", "#f5d0fe", "#e9d5ff", "#c084fc"],
    )


def panel_fill() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_CENTER,
        end=ft.Alignment.BOTTOM_CENTER,
        colors=[opa(0.96, "#1a1430"), opa(0.98, "#0c0916")],
    )


def deep_shadow() -> list[ft.BoxShadow]:
    """Commercial elevation: soft black depth + one restrained violet wash."""
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=36,
            color=opa(0.55, "#000000"),
            offset=ft.Offset(0, 18),
        ),
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=48,
            color=opa(0.16, "#7c3aed"),
            offset=ft.Offset(0, 8),
        ),
    ]


def glow(intensity: float = 0.28) -> list[ft.BoxShadow]:
    intensity = max(0.0, min(0.85, intensity))
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color=opa(intensity * 0.9, "#e879f9"),
            offset=ft.Offset(0, 0),
        ),
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=40,
            color=opa(intensity * 0.45, "#7c3aed"),
            offset=ft.Offset(0, 0),
        ),
    ]


def shell(child: ft.Control, *, padding: float = 7, radius: float = RADIUS_PANEL) -> ft.Container:
    """Double-bezel hardware frame — machined glass plate."""
    return ft.Container(
        content=ft.Container(
            content=child,
            border_radius=radius - 5,
            gradient=panel_fill(),
            border=ft.Border.all(1, HAIRLINE),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shadow=deep_shadow(),
        ),
        padding=padding,
        border_radius=radius,
        bgcolor=opa(0.28, "#1c1432"),
        border=ft.Border.all(1, HAIRLINE_STRONG),
    )


def micro_label(text: str) -> ft.Text:
    return ft.Text(
        text.upper(),
        size=10,
        weight=ft.FontWeight.W_700,
        color=MUTED,
        style=ft.TextStyle(letter_spacing=1.6),
    )


def glass_chip(child: ft.Control, *, lit: bool = False) -> ft.Container:
    return ft.Container(
        content=child,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        border_radius=RADIUS_PILL,
        bgcolor=SURFACE,
        border=ft.Border.all(1, opa(0.45, ACCENT) if lit else HAIRLINE),
        shadow=glow(0.18) if lit else None,
    )


def soft_orb(
    size: float,
    color: str,
    alpha: float = 0.22,
    *,
    breathe_ms: int = 5200,
    **pos,
) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        border_radius=size,
        gradient=ft.RadialGradient(
            center=ft.Alignment.CENTER,
            radius=0.92,
            colors=[opa(alpha, color), opa(alpha * 0.25, color), "#00000000"],
            stops=[0.0, 0.5, 1.0],
        ),
        scale=1,
        opacity=1,
        rotate=ft.Rotate(0, alignment=ft.Alignment.CENTER),
        animate_scale=ft.Animation(breathe_ms, ft.AnimationCurve.EASE_IN_OUT_SINE),
        animate_opacity=ft.Animation(breathe_ms, ft.AnimationCurve.EASE_IN_OUT_SINE),
        animate_rotation=ft.Animation(
            max(14000, breathe_ms * 3), ft.AnimationCurve.LINEAR
        ),
        ignore_interactions=True,
        **pos,
    )


def spark(size: float = 3, *, color: str = ACCENT_2, **pos) -> ft.Container:
    return ft.Container(
        width=size,
        height=size,
        border_radius=size,
        bgcolor=opa(0.75, color),
        shadow=[
            ft.BoxShadow(
                spread_radius=0,
                blur_radius=10,
                color=opa(0.45, color),
                offset=ft.Offset(0, 0),
            )
        ],
        animate_opacity=ft.Animation(2200, ft.AnimationCurve.EASE_IN_OUT_SINE),
        animate_scale=ft.Animation(2400, ft.AnimationCurve.EASE_IN_OUT_SINE),
        opacity=0.55,
        scale=1,
        ignore_interactions=True,
        **pos,
    )


def aurora_band() -> ft.Container:
    return ft.Container(
        top=0,
        left=0,
        right=0,
        height=140,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_CENTER,
            end=ft.Alignment.BOTTOM_CENTER,
            colors=[
                opa(0.32, "#5b21b6"),
                opa(0.12, "#7c3aed"),
                "#00000000",
            ],
            stops=[0.0, 0.45, 1.0],
        ),
        opacity=0.7,
        animate_opacity=ft.Animation(5600, ft.AnimationCurve.EASE_IN_OUT_SINE),
        ignore_interactions=True,
    )


def frame_aura() -> ft.Container:
    return ft.Container(
        expand=True,
        border_radius=30,
        border=ft.Border.all(1, opa(0.22, ACCENT)),
        shadow=glow(0.22),
        opacity=0.55,
        animate_opacity=ft.Animation(2800, ft.AnimationCurve.EASE_IN_OUT_SINE),
        animate_scale=ft.Animation(3200, ft.AnimationCurve.EASE_IN_OUT_SINE),
        scale=1,
        ignore_interactions=True,
    )


def ambient_phase(t: float) -> float:
    return 0.5 + 0.5 * math.sin(t)


def hairline_rule() -> ft.Container:
    return ft.Container(
        height=1,
        expand=True,
        bgcolor=HAIRLINE,
        margin=ft.Margin.symmetric(vertical=2),
    )
