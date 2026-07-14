from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import DataTable, Label, Static, Select
from gravitype.core.config import config, generate_theme_file
from gravitype.core.storage import storage
from gravitype.tui.widgets.table import Table

GENERAL_KEYBINDS = [
    ("ctrl+q", "Quit App"),
    ("ctrl+t", "Navigate to Stats"),
    ("ctrl+s", "Navigate to Settings"),
    ("ctrl+h / ?", "Navigate to Help"),
    ("ctrl+a", "Navigate to About"),
    ("escape / ctrl+p", "Return to Menu/Play Setup"),
]

TYPING_KEYBINDS = [
    ("escape", "Pause / Resume Falling Game"),
    ("ctrl+q", "Exit to Main Menu"),
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


class StatsScreen(Widget):
    """
    Stats screen showing aggregate history and recent completed games.
    """

    def compose(self) -> ComposeResult:
        with Container(classes="stats-container"):
            yield Label("STATS", classes="stats-title")
            yield Label("", id="stats-summary", classes="stats-summary")
            yield Label("", id="stats-categories", classes="stats-categories")
            yield DataTable(id="recent-games-table")

    def on_mount(self) -> None:
        table = self.query_one("#recent-games-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Ended", "Cat", "Score", "Level", "Words", "Misses", "Time")
        self.refresh_stats()

    def refresh_stats(self) -> None:
        stats = storage.get_stats()
        summary = (
            f"Games {stats['games_played']}  |  "
            f"High {stats['high_score']:05d}  |  "
            f"Avg {stats['average_score']:05d}  |  "
            f"Best Lvl {stats['best_level']}  |  "
            f"Words {stats['total_words_cleared']}  |  "
            f"Misses {stats['total_misses']}"
        )
        self.query_one("#stats-summary", Label).update(summary)

        category_parts = []
        for category in ("tech", "general", "mixed"):
            bucket = stats["by_category"].get(category, {})
            category_parts.append(
                f"{category.upper()}: {bucket.get('games', 0)} games, "
                f"best {bucket.get('high_score', 0):05d}"
            )
        self.query_one("#stats-categories", Label).update("  |  ".join(category_parts))

        table = self.query_one("#recent-games-table", DataTable)
        table.clear()
        for game in stats["recent_games"]:
            table.add_row(
                self._short_time(str(game.get("ended_at", ""))),
                str(game.get("category", "")).upper(),
                f"{int(game.get('score', 0) or 0):05d}",
                str(game.get("level_reached", 0)),
                str(game.get("words_cleared", 0)),
                str(game.get("words_missed", 0)),
                self._format_duration(int(game.get("duration_seconds", 0) or 0)),
            )

    def _short_time(self, value: str) -> str:
        if "T" not in value:
            return value[:16]
        date_part, time_part = value.split("T", 1)
        return f"{date_part} {time_part[:5]}"

    def _format_duration(self, seconds: int) -> str:
        minutes, remaining = divmod(max(0, seconds), 60)
        return f"{minutes}:{remaining:02d}"


class SettingsScreen(Widget):
    """
    Settings menu containing interactive options for Theme, Sound, and Starting Lives.
    """

    def compose(self) -> ComposeResult:
        with Container(classes="settings-container"):
            yield Label("SETTINGS", classes="settings-title")

            # Theme selection
            with Horizontal(classes="setting-row"):
                yield Label("Color Theme", classes="setting-label")
                yield Select(
                    options=[
                        ("Dracula", "dracula"),
                        ("Nord", "nord"),
                        ("Tokyo Night", "tokyonight"),
                        ("Gruvbox", "gruvbox_dark"),
                        ("Catppuccin", "catppuccin"),
                        ("Cyberspace", "cyberspace"),
                        ("80s Dark", "80s_after_dark"),
                    ],
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
        theme_val = config.get("theme")
        sound_val = "on" if config.get("sound_enabled") else "off"
        lives_val = str(config.get("starting_lives"))

        try:
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
            generate_theme_file(value)
        elif select_id == "select-sound":
            config.set("sound_enabled", value == "on")
        elif select_id == "select-lives":
            new_lives = int(value)
            config.set("starting_lives", new_lives)
            self.app.lives = new_lives
