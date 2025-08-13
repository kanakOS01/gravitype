from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

from gravitype.widgets import PlayArea, StatusBar, TypedArea


class GravitypeApp(App):
    TITLE = "Gravitype"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield PlayArea()
        yield StatusBar()
        yield TypedArea()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )


if __name__ == '__main__':
    gravitype_app = GravitypeApp()
    gravitype_app.run()