"""macOS-like motion tokens for Violet Noir.

Prefer transform/opacity only. Curves biased toward fast-out / slow-in.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import flet as ft

# Apple-ish: quick commit, soft settle
SNAP = ft.Animation(200, ft.AnimationCurve.FAST_OUT_SLOWIN)
SETTLE = ft.Animation(340, ft.AnimationCurve.EASE_OUT_CUBIC)
PANEL = ft.Animation(160, ft.AnimationCurve.EASE_OUT)
PRESS = ft.Animation(80, ft.AnimationCurve.EASE_OUT)
RELEASE = ft.Animation(280, ft.AnimationCurve.FAST_OUT_SLOWIN)
HOVER = ft.Animation(160, ft.AnimationCurve.EASE_OUT)
ENTRANCE = ft.Animation(520, ft.AnimationCurve.EASE_OUT_CUBIC)
SOFT = ft.Animation(420, ft.AnimationCurve.EASE_IN_OUT_SINE)
# UINavigationController-style page turn
TAB_OUT = ft.Animation(220, ft.AnimationCurve.EASE_IN_CUBIC)
TAB_IN = ft.Animation(300, ft.AnimationCurve.FAST_OUT_SLOWIN)
INSTANT = ft.Animation(1, ft.AnimationCurve.LINEAR)
TAB_SLIDE = 0.085  # fraction of width — enough to feel, not enough to shake

IDLE = 1.0
HOVER_SCALE = 1.02
PRESS_SCALE = 0.97
SELECTED_SCALE = 1.0


def _as_bool(data: Any) -> bool:
    if isinstance(data, bool):
        return data
    return str(data).lower() in {"true", "1", "true"}


def wire_pressable(
    control: ft.Container,
    *,
    page: ft.Page,
    on_click: Callable[[ft.ControlEvent], Any] | None = None,
    idle_scale: float = IDLE,
    hover_scale: float = HOVER_SCALE,
    press_scale: float = PRESS_SCALE,
    selected_scale: float | None = None,
    is_selected: Callable[[], bool] | None = None,
    is_enabled: Callable[[], bool] | None = None,
) -> None:
    """Hover lift + press squash on a Container (macOS button feel)."""
    state = {"hover": False, "press": False}

    control.scale = idle_scale
    control.animate_scale = HOVER

    def _base() -> float:
        if is_selected and is_selected() and selected_scale is not None:
            return selected_scale
        return idle_scale

    def _target() -> float:
        if is_enabled and not is_enabled():
            return _base()
        if state["press"]:
            return press_scale
        if state["hover"]:
            return hover_scale if not (is_selected and is_selected()) else (selected_scale or hover_scale)
        return _base()

    def _sync() -> None:
        control.scale = _target()
        page.update()

    def _on_hover(e: ft.ControlEvent) -> None:
        state["hover"] = _as_bool(e.data)
        control.animate_scale = HOVER
        _sync()

    def _on_tap_down(_e: ft.ControlEvent) -> None:
        if is_enabled and not is_enabled():
            return
        state["press"] = True
        control.animate_scale = PRESS
        _sync()

    async def _on_click(e: ft.ControlEvent) -> None:
        state["press"] = False
        control.animate_scale = RELEASE
        _sync()
        if on_click is None:
            return
        if is_enabled and not is_enabled():
            return
        result = on_click(e)
        if isinstance(result, Awaitable):
            await result

    control.on_hover = _on_hover
    control.on_tap_down = _on_tap_down
    control.on_click = _on_click


async def press_bounce(control: ft.Container, page: ft.Page, *, down: float = 0.96) -> None:
    control.animate_scale = PRESS
    control.scale = down
    page.update()
    await asyncio.sleep(0.07)
    control.animate_scale = RELEASE
    control.scale = IDLE
    page.update()


async def fade_swap(
    control: ft.Control,
    page: ft.Page,
    mutate: Callable[[], None],
    *,
    out_ms: float = 0.08,
) -> None:
    """Soft opacity crossfade around a content mutation (no lateral motion)."""
    if hasattr(control, "opacity"):
        control.opacity = 0.55  # type: ignore[attr-defined]
    page.update()
    await asyncio.sleep(out_ms)
    mutate()
    if hasattr(control, "opacity"):
        control.opacity = 1  # type: ignore[attr-defined]
    page.update()
