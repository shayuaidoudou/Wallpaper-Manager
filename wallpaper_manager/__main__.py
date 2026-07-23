def main() -> None:
    from wallpaper_manager.runtime_branding import prepare_branded_flet_view

    prepare_branded_flet_view()
    from wallpaper_manager.ui.app import run_app

    run_app()


if __name__ == "__main__":
    main()
