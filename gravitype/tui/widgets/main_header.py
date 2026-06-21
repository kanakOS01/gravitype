from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Static, Button

BANNER_TEXT = """\
 ██████╗ ██████╗  █████╗ ██╗   ██╗██╗████████╗██╗   ██╗██████╗ ███████╗
██╔════╝ ██╔══██╗██╔══██╗██║   ██║██║╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝
██║  ███╗██████╔╝███████║██║   ██║██║   ██║    ╚████╔╝ ██████╔╝█████╗  
██║   ██║██╔══██╗██╔══██║╚██╗ ██╔╝██║   ██║     ╚██╔╝  ██╔═══╝ ██╔══╝  
╚██████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║   ██║      ██║   ██║     ███████╗
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝     ╚══════╝"""

# BANNER_TEXT = """\
# ┏━┓┏━┓┏━┓╻ ╻╻╺┳╸╻ ╻┏━┓┏━╸
# ┃╺┓┣┳┛┣━┫┗┳┛┃ ┃ ┗┳┛┣━┛┣╸
# ┗━┛╹┗╸╹ ╹ ╹ ╹ ╹  ╹ ┗╸ ┗━╸
# """


class Banner(Static):
    """
    Text Widget to render the hardcoded GRAVITYPE banner using Unicode block text.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(BANNER_TEXT, **kwargs)


class NavItem(Button):
    """
    A navigation menu tab item using Button for maximum click compatibility and keyboard accessibility
    """

    def __init__(self, text: str, screen_name: str, **kwargs) -> None:
        super().__init__(text, **kwargs)
        self.screen_name = screen_name


class MainHeader(Widget):
    """
    Header which forms the top banner of the main app view
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            play_item = NavItem(" play", "welcome")
            play_item.add_class("active")
            yield play_item
            yield NavItem(" settings", "settings")
            yield NavItem(" help", "help")
            yield NavItem(" about", "about")

    def set_active(self, name: str) -> None:
        for i in self.query(NavItem):
            i.set_class(i.screen_name == name, "active")
