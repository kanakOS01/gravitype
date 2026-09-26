"""Oversized digits for the headline figures on the results screen.

Three rows of box-drawing characters, in the same spirit as the banner in
``main_header.py``. Anything without a glyph falls back to a blank cell, so a
stray character degrades to a gap rather than an exception.
"""

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget

GLYPH_HEIGHT = 3

_GLYPHS = {
    "0": ("┌─┐", "│ │", "└─┘"),
    "1": ("  ╷", "  │", "  ╵"),
    "2": ("┌─┐", "┌─┘", "└─┘"),
    "3": ("┌─┐", " ─┤", "└─┘"),
    "4": ("╷ ╷", "└─┤", "  ╵"),
    "5": ("┌─┐", "└─┐", "└─┘"),
    "6": ("┌─┐", "├─┐", "└─┘"),
    "7": ("┌─┐", "  │", "  ╵"),
    "8": ("┌─┐", "├─┤", "└─┘"),
    "9": ("┌─┐", "└─┤", "└─┘"),
    "%": ("╶╮╱", " ╱ ", "╱╰╴"),
    ".": ("   ", "   ", " ╵ "),
    "—": ("   ", "───", "   "),
}

_BLANK = ("   ", "   ", "   ")


class BigNumber(Widget):
    """Renders a short string as three-row block digits."""

    COMPONENT_CLASSES = {"bignumber--label", "bignumber--value"}

    DEFAULT_CSS = """
    BigNumber {
        height: auto;
    }
    """

    def __init__(self, label: str = "", value: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.value = value

    def update(self, label: str = None, value: str = None) -> None:
        """Change the label and/or value, then redraw."""
        if label is not None:
            self.label = label
        if value is not None:
            self.value = value
        self.refresh()

    def render(self) -> RenderableType:
        label_style = self.get_component_rich_style("bignumber--label")
        value_style = self.get_component_rich_style("bignumber--value")

        out = Text()
        if self.label:
            out.append(f"{self.label}\n", label_style)

        for row in range(GLYPH_HEIGHT):
            glyphs = (_GLYPHS.get(char, _BLANK)[row] for char in self.value)
            out.append(" ".join(glyphs), value_style)
            if row < GLYPH_HEIGHT - 1:
                out.append("\n")

        return out
