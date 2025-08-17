from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Center, Container
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive



from .widgets import PlayArea, StatusBar, InputArea


class GravitypeApp(App):
    TITLE = "Gravitype"
    CSS_PATH = "styles/app.tcss"
    BINDINGS = [
        Binding(key="^q", action="quit", description="quit"),
        Binding(
            key="question_mark",
            action="help",
            description="Show help screen",
            key_display="?",
        ),
        # Binding(key="j", action="down", description="Scroll down", show=False),
    ]

    words = reactive(['kanak'])

    @on(InputArea.Changed)
    async def on_input_changed(self) -> None:
        input_area = self.query_one(InputArea)
        word = input_area.value
        if word and word in self.words:
            self.words.remove(word)
            input_area.clear()


    def compose(self) -> ComposeResult:
        with Container(classes="main"):    
            yield PlayArea()
            # yield Container(
            #     StatusBar(),
            #     classes="status-bar",
            # )
            yield StatusBar(classes="status-bar")
        yield Footer()


def main():
    GravitypeApp().run()


if __name__ == "__main__":
    main()
