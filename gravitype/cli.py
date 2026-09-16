"""Console entry point for Gravitype."""

from gravitype.tui.app import GravitypeApp


def main() -> None:
    """Launch the Gravitype TUI."""
    GravitypeApp().run()
