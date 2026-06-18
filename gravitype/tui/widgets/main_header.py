from typing import Optional
from rich.console import RenderableType
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static
from textual.message import Message
from gravitype.tui.widgets.figlet import generate_figlet


class SetScreen(Message):
    """Message posted to switch active screen in ContentSwitcher."""

    def __init__(self, screen_name: str) -> None:
        super().__init__()
        self.screen_name = screen_name


class NavItemBase(Widget):
    """
    Base Widget for Header NavItems
    """

    def __init__(self, text: str, screen_name: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.text = text
        self.screen_name = screen_name

    def on_click(self, event) -> None:
        print(f"NavItemBase on_click called for {self.screen_name}", flush=True)
        if self.screen_name:
            self.post_message(SetScreen(self.screen_name))

    def render(self) -> RenderableType:
        return self.text


class Banner(NavItemBase):
    """
    Text Widget to render text in a bigger font using Figlet
    """

    def render(self) -> RenderableType:
        return generate_figlet(self.text)


class NavItem(NavItemBase):
    """
    A navigation menu tab item
    """

    pass


class MainHeader(Widget):
    """
    Header which forms the top banner of the main app view
    """

    def compose(self) -> ComposeResult:
        yield Static()  # Spacer
        yield Banner("gravitype", "welcome")

        with Horizontal():
            play_item = NavItem("🕹️ play", "welcome")
            play_item.add_class("active")
            yield play_item
            yield NavItem(" settings", "settings")
            yield NavItem("󰋗 help", "help")
            yield NavItem(" about", "about")

    def set_active(self, name: str) -> None:
        for i in self.query(NavItem):
            i.set_class(i.screen_name == name, "active")
