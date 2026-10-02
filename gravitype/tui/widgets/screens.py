from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Label, Static, Select
from gravitype.core import words
from gravitype.core.config import config
from gravitype.core.themes import family_options
from gravitype.core.session import format_percent, format_wpm
from gravitype.core.stats import format_duration, stats
from gravitype.tui.widgets.table import Table

GENERAL_KEYBINDS = [
    ("ctrl+q", "Quit App"),
    ("ctrl+l", "Toggle Light / Dark Appearance"),
    ("ctrl+s", "Navigate to Settings"),
    ("ctrl+h / ?", "Navigate to Help"),
    ("ctrl+a", "Navigate to About"),
    ("ctrl+t", "Navigate to Stats"),
    ("escape / ctrl+p", "Return to Menu/Play Setup"),
]

TYPING_KEYBINDS = [
    ("escape", "Pause / Resume Falling Game"),
    ("ctrl+g", "Exit Game (not counted in high score)"),
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
                "Gravitype is a Terminal Typing Game where words fall from the sky. "
                "Your objective is to type the words before they hit the bottom border!\n\n"
                "Thanks to the Smassh project for the color-theme ideas and implementation reference.\n\n"
                "Test your limits, avoid typos and set new high scores!",
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
            yield Table(
                f"Word Sets  ({words.words_dir()})",
                title_prefix=" \U000f0219 ",
                key_ratio=2,
                id="help-word-sets",
            )

    def on_mount(self) -> None:
        self.sync_word_sets()

    def sync_word_sets(self) -> None:
        """List the custom sets found, and any file that was not loaded.

        A file that fails to load is otherwise invisible - it just does not
        appear in the menu, with no hint as to why.
        """
        rows = [
            (name.upper(), f"{len(entries)} entries")
            for name, entries in sorted(words.custom_sets().items())
        ]
        rows += [
            (filename, f"skipped - {reason}")
            for filename, reason in sorted(words.skipped_files().items())
        ]
        if not rows:
            rows = [("none yet", "drop a .txt file in the folder above")]

        try:
            self.query_one("#help-word-sets", Table).set_rows(rows)
        except Exception:
            pass


class StatsScreen(Widget):
    """
    Lifetime play statistics, refreshed every time the tab is opened.
    """

    TITLE_PREFIX = ""

    def compose(self) -> ComposeResult:
        with Container(classes="stats-container"):
            yield Label("YOUR STATS", classes="stats-title")
            yield Table(
                "Lifetime",
                title_prefix=self.TITLE_PREFIX,
                key_ratio=2,
                id="stats-lifetime",
            )
            yield Table(
                "By Category  (level · done/started · wpm · acc · time)",
                title_prefix=self.TITLE_PREFIX,
                key_ratio=2,
                id="stats-categories",
            )

    def on_mount(self) -> None:
        self.sync_stats()

    def sync_stats(self) -> None:
        """Re-read the stats file and rebuild both tables."""
        data = stats.snapshot()

        lifetime = [
            ("Games Started", str(data["games_started"])),
            ("Games Completed", str(data["games_completed"])),
            ("Max Level Reached", str(data["max_level"])),
            # A stored best of 0.0 means "never set", not "zero words a minute".
            ("Best WPM", format_wpm(data["best_wpm"] or None)),
            ("Average WPM", format_wpm(data["avg_wpm"])),
            ("Accuracy", format_percent(data["accuracy"])),
            ("Words Typed", str(data["words_hit"])),
            ("Total Time Played", format_duration(data["total_play_seconds"])),
        ]

        # A deleted word set keeps its history in stats.json, but listing a
        # category you can no longer play is just clutter.
        playable = set(words.available_categories())

        categories = []
        for name, values in sorted(data["categories"].items()):
            if name not in playable:
                continue
            categories.append(
                (
                    name.upper(),
                    # Column meanings live in the table title, which keeps the
                    # row short enough not to wrap on a narrow terminal.
                    f"lvl {values['max_level']} \u00b7 "
                    f"{values['games_completed']}/{values['games_started']} \u00b7 "
                    f"{format_wpm(values['best_wpm'] or None)} \u00b7 "
                    f"{format_percent(values['accuracy'])} \u00b7 "
                    f"{format_duration(values['total_play_seconds'])}",
                )
            )
        if not categories:
            categories = [("\u2014", "No games played yet")]

        try:
            self.query_one("#stats-lifetime", Table).set_rows(lifetime)
            self.query_one("#stats-categories", Table).set_rows(categories)
        except Exception:
            pass


class SettingsScreen(Widget):
    """
    Settings menu containing interactive options for Theme, Sound, and Starting Lives.
    """

    def compose(self) -> ComposeResult:
        with Container(classes="settings-container"):
            yield Label("SETTINGS", classes="settings-title")

            # Appearance (dark / light). Every theme has both variants, so
            # this is independent of the theme choice below.
            with Horizontal(classes="setting-row"):
                yield Label("Appearance", classes="setting-label")
                yield Select(
                    options=[
                        ("Dark", "dark"),
                        ("Light", "light"),
                    ],
                    value=config.get("mode"),
                    allow_blank=False,
                    id="select-mode",
                )

            # Theme selection
            with Horizontal(classes="setting-row"):
                yield Label("Color Theme", classes="setting-label")
                yield Select(
                    options=family_options(),
                    value=config.get("theme"),
                    allow_blank=False,
                    id="select-theme",
                )

            # Sound selection
            with Horizontal(classes="setting-row"):
                yield Label("Sound (Bell)", classes="setting-label")
                yield Select(
                    options=[
                        ("ON", "on"),
                        ("OFF", "off"),
                    ],
                    value="on" if config.get("sound_enabled") else "off",
                    allow_blank=False,
                    id="select-sound",
                )

            # Lives selection
            with Horizontal(classes="setting-row"):
                yield Label("Starting Lives", classes="setting-label")
                yield Select(
                    options=[
                        ("3 Lives", "3"),
                        ("5 Lives", "5"),
                        ("8 Lives", "8"),
                    ],
                    value=str(config.get("starting_lives")),
                    allow_blank=False,
                    id="select-lives",
                )

    def on_mount(self) -> None:
        self.sync_settings()

    def sync_settings(self) -> None:
        mode_val = config.get("mode")
        theme_val = config.get("theme")
        sound_val = "on" if config.get("sound_enabled") else "off"
        lives_val = str(config.get("starting_lives"))

        try:
            self.query_one("#select-mode", Select).value = mode_val
            self.query_one("#select-theme", Select).value = theme_val
            self.query_one("#select-sound", Select).value = sound_val
            self.query_one("#select-lives", Select).value = lives_val
        except Exception:
            pass

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id
        value = event.value

        if value is None or value == Select.BLANK:
            return

        if select_id == "select-theme":
            config.set("theme", value)
            self.app.apply_theme()
        elif select_id == "select-mode":
            config.set("mode", value)
            self.app.apply_theme()
        elif select_id == "select-sound":
            config.set("sound_enabled", value == "on")
        elif select_id == "select-lives":
            new_lives = int(value)
            config.set("starting_lives", new_lives)
            self.app.lives = new_lives
