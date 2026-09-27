from typing import List, Tuple
from rich.console import RenderableType
from rich.table import box
from rich.text import Text
from textual.widget import Widget


class Table(Widget):
    """
    Table widget to show keybindings or other structured data.
    """

    COMPONENT_CLASSES = {"--header", "--key", "--action"}

    #: Prepended to the title. Overridable so the same table can front
    #: something other than a keybind list.
    DEFAULT_TITLE_PREFIX = " 󰌌 Keybinds for "

    def __init__(
        self,
        title: str,
        keys: List[Tuple[str, str]] = None,
        title_prefix: str = None,
        key_ratio: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.keys = keys if keys is not None else []
        self.title_prefix = (
            self.DEFAULT_TITLE_PREFIX if title_prefix is None else title_prefix
        )
        # Width of the left column relative to the right one. Stat names are
        # longer than keybinds, so they need more room before wrapping.
        self.key_ratio = key_ratio

    def set_rows(self, keys: List[Tuple[str, str]]) -> None:
        """Swap the table contents in place and redraw."""
        self.keys = list(keys)
        self.refresh()

    def render(self) -> RenderableType:
        from rich.table import Table as RichTable

        table_header = self.get_component_rich_style("--header")
        table_key = self.get_component_rich_style("--key")
        table_action = self.get_component_rich_style("--action")

        table = RichTable(
            expand=True,
            show_header=False,
            padding=(0, 0),
            box=box.SIMPLE,
            title=Text(
                f"{self.title_prefix}{self.title}",
                style=table_header,
                justify="left",
            ),
        )
        table.add_column(Text("Key"), style=table_key, ratio=self.key_ratio)
        table.add_column("", width=5)
        table.add_column(Text("Action"), style=table_action, ratio=4)

        for key, description in self.keys:
            table.add_row(key, "", description)

        return table
