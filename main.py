"""Desktop entry point for packaging (`flet pack` / `flet build`)."""

from wallpaper_manager.runtime_branding import prepare_branded_flet_view

prepare_branded_flet_view()

from wallpaper_manager.ui.app import run_app

if __name__ == "__main__":
    run_app()
