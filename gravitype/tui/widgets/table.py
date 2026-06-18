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

    def __init__(
        self, title: str, keys: List[Tuple[str, str]] = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.keys = keys if keys is not None else []

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
                f" 󰌌 Keybinds for {self.title}",
                style=table_header,
                justify="left",
            ),
        )
        table.add_column(Text("Key"), style=table_key, ratio=1)
        table.add_column("", width=5)
        table.add_column(Text("Action"), style=table_action, ratio=4)

        for key, description in self.keys:
            table.add_row(key, "", description)

        return table
