from textual.widgets import Static
from textual.reactive import reactive

class TypedArea(Static):
    typed = reactive("")

    def render(self):
        return f"Typed: {self.typed}"
