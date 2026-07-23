def clamp_ui(opacity_ui: int) -> int:
    return max(0, min(100, int(opacity_ui)))


def ui_to_background_cover(opacity_ui: int) -> float:
    return round(clamp_ui(opacity_ui) / 100 * 0.8, 4)


def background_cover_to_ui(opacity: float) -> int:
    if opacity <= 0:
        return 0
    return clamp_ui(round(float(opacity) / 0.8 * 100))
