"""Midnight Glass visual tokens and decoration helpers."""

from __future__ import annotations

import flet as ft

# Core palette — deep space + cyan glass (no purple)
BG = "#07090e"
BG_MID = "#0c1219"
PANEL = "#101822"
PANEL_ELEVATED = "#15202b"
ACCENT = "#38bdf8"
ACCENT_2 = "#22d3ee"
ACCENT_DIM = "#0e7490"
TEXT = "#f1f5f9"
MUTED = "#8b9bb0"
PANEL_BORDER = "#1e2d3d"
PANEL_BORDER_LIT = "#2a4158"
ERROR = "#fb7185"
SUCCESS = "#34d399"
GLOW = "#38bdf833"


def page_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.TOP_LEFT,
        end=ft.Alignment.BOTTOM_RIGHT,
        colors=["#0a1624", BG, "#05070b"],
        stops=[0.0, 0.45, 1.0],
    )


def accent_gradient() -> ft.LinearGradient:
    return ft.LinearGradient(
        begin=ft.Alignment.CENTER_LEFT,
        end=ft.Alignment.CENTER_RIGHT,
        colors=[ACCENT_2, ACCENT, "#7dd3fc"],
    )


def glass_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=40,
            color="#00000066",
            offset=ft.Offset(0, 18),
        ),
        ft.BoxShadow(
            spread_radius=-2,
            blur_radius=28,
            color=GLOW,
            offset=ft.Offset(0, 0),
        ),
    ]


def soft_shadow() -> list[ft.BoxShadow]:
    return [
        ft.BoxShadow(
            spread_radius=0,
            blur_radius=24,
            color="#00000055",
            offset=ft.Offset(0, 12),
        )
    ]


def ambient_orb(
    *,
    size: float,
    color: str,
    top: float | None = None,
    left: float | None = None,
    right: float | None = None,
    bottom: float | None = None,
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
            radius=0.75,
            colors=[color, "#00000000"],
        ),
        animate_opacity=ft.Animation(1600, ft.AnimationCurve.EASE_IN_OUT),
        opacity=0.9,
        ignore_interactions=True,
    )
