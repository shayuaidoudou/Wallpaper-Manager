from pathlib import Path

from wallpaper_manager.adapters.background_cover_dom import (
    clear_background_cover_css,
    patch_background_cover_css,
    to_vscode_file_url,
)


def test_patch_updates_opacity_and_image(tmp_path: Path):
    css = tmp_path / "css-background-cover.css"
    css.write_text(
        """
        body::before{
            opacity:0.2;
            background-image:url('vscode-file://vscode-app/old.png');
        }
        """,
        encoding="utf-8",
    )

    assert patch_background_cover_css(css, "/tmp/new.png", 0) is True
    text = css.read_text(encoding="utf-8")
    assert "opacity:0.0;" in text or "opacity:0;" in text
    assert to_vscode_file_url("/tmp/new.png") in text


def test_clear_zeros_opacity(tmp_path: Path):
    css = tmp_path / "css-background-cover.css"
    css.write_text(
        """
        body::before{
            opacity:0.35;
            background-image:url('vscode-file://vscode-app/old.png');
        }
        """,
        encoding="utf-8",
    )

    assert clear_background_cover_css(css) is True
    text = css.read_text(encoding="utf-8")
    assert "opacity:0;" in text
    assert "background-image:url('');" in text or "background-image:url();" in text
