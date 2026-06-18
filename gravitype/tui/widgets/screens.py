from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Label, Static
from gravitype.core.config import config, generate_theme_file
from gravitype.tui.widgets.table import Table

GENERAL_KEYBINDS = [
    ("ctrl+q", "Quit Game"),
    ("ctrl+s", "Navigate to Settings"),
    ("ctrl+h / ?", "Navigate to Help"),
    ("ctrl+a", "Navigate to About"),
    ("escape / ctrl+p", "Return to Menu/Play Setup"),
]

TYPING_KEYBINDS = [
    ("escape", "Pause / Resume Falling Game"),
    ("ctrl+w / ctrl+backspace", "Clear current input word"),
]


class AboutScreen(Widget):
    """
    About Screen to display project credits and links.
    """

    def compose(self) -> ComposeResult:
        with Container(classes="about-container"):
            yield Label("ABOUT GRAVITYPE", classes="about-title")
            yield Static(
                "Gravitype is a Neon Terminal Typing Game where words fall from the sky. "
                "Your objective is to type the words before they hit the bottom border!\n\n"
                "Inspired by the smassh typing client, this game features dynamic "
                "color themes, persistent high-scores, statistics, and a sleek keyboard layout.\n\n"
                "Test your limits, avoid typographical errors, and set new high scores!",
                classes="about-text",
            )
            yield Label(
                "[@click=app.open_github]Star Gravitype on GitHub[/]",
                classes="about-link",
            )
            yield Label("Made with ❤️ for typing enthusiasts", classes="about-outro")


class HelpScreen(Widget):
    """
    Help Screen showing game rules and keyboard shortcuts.
    """

    def compose(self) -> ComposeResult:
        with Container(classes="help-container"):
            yield Label("HOW TO PLAY & KEYBINDS", classes="help-title")
            yield Table("General Navigation", GENERAL_KEYBINDS)
            yield Table("Active Gameplay", TYPING_KEYBINDS)


class SettingsScreen(Widget):
    """
    Settings menu containing interactive options for Theme, Sound, and Starting Lives.
    """

    def compose(self) -> ComposeResult:
        with Container(classes="settings-container"):
            yield Label("SETTINGS", classes="settings-title")

            # Theme selection
            yield Label("Color Theme", classes="setting-label")
            with Horizontal(classes="setting-row"):
                yield Button("Dracula", id="theme-dracula", classes="setting-btn")
                yield Button("Nord", id="theme-nord", classes="setting-btn")
                yield Button(
                    "Tokyo Night", id="theme-tokyonight", classes="setting-btn"
                )

            with Horizontal(classes="setting-row"):
                yield Button("Gruvbox", id="theme-gruvbox_dark", classes="setting-btn")
                yield Button("Catppuccin", id="theme-catppuccin", classes="setting-btn")
                yield Button("Cyberspace", id="theme-cyberspace", classes="setting-btn")
                yield Button(
                    "80s Dark", id="theme-80s_after_dark", classes="setting-btn"
                )

            # Sound selection
            yield Label("Sound Feedback (Bell)", classes="setting-label")
            with Horizontal(classes="setting-row"):
                yield Button("ON", id="sound-on", classes="setting-btn")
                yield Button("OFF", id="sound-off", classes="setting-btn")

            # Lives selection
            yield Label("Starting Lives", classes="setting-label")
            with Horizontal(classes="setting-row"):
                yield Button("3 Lives", id="lives-3", classes="setting-btn")
                yield Button("5 Lives", id="lives-5", classes="setting-btn")
                yield Button("8 Lives", id="lives-8", classes="setting-btn")

    def on_mount(self) -> None:
        self.sync_settings()

    def sync_settings(self) -> None:
        # 1. Sync theme buttons
        active_theme = config.get("theme")
        for btn in self.query(".setting-btn"):
            if btn.id.startswith("theme-"):
                theme_id = btn.id.replace("theme-", "")
                btn.set_class(theme_id == active_theme, "active")

        # 2. Sync sound buttons
        sound_enabled = config.get("sound_enabled")
        self.query_one("#sound-on").set_class(sound_enabled, "active")
        self.query_one("#sound-off").set_class(not sound_enabled, "active")

        # 3. Sync lives buttons
        starting_lives = config.get("starting_lives")
        self.query_one("#lives-3").set_class(starting_lives == 3, "active")
        self.query_one("#lives-5").set_class(starting_lives == 5, "active")
        self.query_one("#lives-8").set_class(starting_lives == 8, "active")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id.startswith("theme-"):
            new_theme = button_id.replace("theme-", "")
            config.set("theme", new_theme)
            generate_theme_file(new_theme)
        elif button_id == "sound-on":
            config.set("sound_enabled", True)
        elif button_id == "sound-off":
            config.set("sound_enabled", False)
        elif button_id.startswith("lives-"):
            new_lives = int(button_id.replace("lives-", ""))
            config.set("starting_lives", new_lives)
            self.app.lives = new_lives

        self.sync_settings()
