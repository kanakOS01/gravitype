import time

from textual import on
from textual.app import App
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Label, Input, ContentSwitcher, Footer
from textual.containers import Container, Horizontal
from textual.reactive import reactive

from gravitype.core.config import config, generate_theme_file
from gravitype.core.session import RunSession, format_percent, format_wpm
from gravitype.core.stats import format_duration, stats
from gravitype.tui.widgets.header import HeaderWidget
from gravitype.tui.widgets.game_board import GameBoard
from gravitype.tui.widgets.bignum import BigNumber
from gravitype.tui.widgets.chart import BrailleChart
from gravitype.tui.widgets.main_header import MainHeader, NavItem, Banner
from gravitype.tui.widgets.screens import (
    AboutScreen,
    HelpScreen,
    SettingsScreen,
    StatsScreen,
)

#: Points required per level.
POINTS_PER_LEVEL = 150

#: Reaching this level wins the game. It is where
#: ``GameBoard.get_ticks_for_level`` stops changing - past here the game is not
#: getting harder, only counting higher, so there is nothing left to play for.
#: ``test_win_level_sits_at_the_difficulty_plateau`` keeps the two in step.
WIN_LEVEL = 27


# --- Welcome/Start Menu Screen Widget ---
class WelcomeScreen(Widget):
    """The initial welcome screen for category selection and game start."""

    def compose(self):
        with Container(id="menu-container"):
            yield Banner(classes="title")

            yield Label("Select Category:")
            with Horizontal(id="category-container"):
                yield Button("Tech", id="cat-tech", classes="category-btn active")
                yield Button("General", id="cat-general", classes="category-btn")

            yield Label("", id="high-score-label", classes="label-info")
            with Horizontal(classes="action-row"):
                yield Button("START GAME", id="btn-start", classes="action-btn")

    def on_mount(self) -> None:
        # Sync initial state
        self.app.category = "tech"
        self.update_high_score()

    def update_high_score(self) -> None:
        label = self.query_one("#high-score-label")
        label.update(f"High Score: {self.app.high_score:05d}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id.startswith("cat-"):
            for btn in self.query(".category-btn"):
                btn.remove_class("active")
            event.button.add_class("active")
            self.app.category = button_id.replace("cat-", "")
        elif button_id == "btn-start":
            self.app.start_new_game()


# --- Game Over Screen ---
class GameOverScreen(Screen):
    """Shown when a run ends, whether it was won or lost.

    The layout is the same either way - the run's figures are what you want to
    see in both cases - so a win only changes the title and the frame colour.
    """

    #: Columns in the secondary stats row, as (heading, value) callables.
    SUMMARY_FIELDS = (
        ("score", lambda app: f"{app.score:05d}"),
        ("level", lambda app: str(app.level)),
        ("words hit", lambda app: str(app.session.words_hit)),
        ("time", lambda app: format_duration(app.run_seconds)),
        ("category", lambda app: app.category.upper()),
    )

    def compose(self):
        session = self.app.session
        won = self.app.is_win

        container = Container(id="game-over-container")
        if won:
            container.add_class("won")

        with container:
            yield Label(
                "YOU WIN" if won else "GAME OVER",
                classes="win-title" if won else "game-over-title",
            )

            with Horizontal(classes="result-body"):
                with Container(classes="result-metrics"):
                    yield BigNumber("wpm", format_wpm(session.wpm), id="result-wpm")
                    yield BigNumber(
                        "acc",
                        format_percent(session.accuracy, suffix=""),
                        id="result-acc",
                    )
                yield BrailleChart(
                    session.wpm_series,
                    session.error_series,
                    x_label=self._chart_label(session),
                    empty_message="no words typed this run",
                    id="result-chart",
                )

            with Horizontal(classes="result-row"):
                for heading, value in self.SUMMARY_FIELDS:
                    with Container(classes="result-field"):
                        yield Label(heading, classes="result-field-label")
                        yield Label(value(self.app), classes="result-field-value")

            if self.app.is_new_high_score:
                yield Label("★ NEW HIGH SCORE! ★", classes="new-high-badge")
            else:
                yield Label(
                    f"High Score: {max(self.app.score, self.app.high_score):05d}",
                    classes="label-info",
                )

            with Horizontal(classes="action-row"):
                yield Button("PLAY AGAIN", id="btn-retry", classes="action-btn")
                yield Button("MAIN MENU", id="btn-menu", classes="action-btn")
                yield Button("QUIT GAME", id="btn-quit", classes="danger-btn")

    async def on_screen_resume(self) -> None:
        """Rebuild for the run that just ended.

        This screen is registered in ``SCREENS``, so Textual caches the
        instance and ``compose`` runs only once. Every figure here is read at
        compose time, so without recomposing the second and every later run
        would show the first one's score, WPM and chart - and, now that a run
        can be won, a lost run could still read YOU WIN.
        """
        await self.recompose()

    @staticmethod
    def _chart_label(session) -> str:
        """Caption the x-axis, which counts words rather than seconds."""
        count = session.words_hit
        if count < 2:
            return "word 1" if count else ""
        return f"word 1{' ' * 40}word {count}"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "btn-retry":
            self.app.start_new_game()
        elif button_id == "btn-menu":
            self.app.show_menu()
        elif button_id == "btn-quit":
            self.app.exit()


# --- Active Game Play Screen ---
class GameScreen(Screen):
    """The active game screen containing the falling board, input field and header."""

    BINDINGS = [
        ("escape", "toggle_pause", "Pause/Resume Game"),
        ("ctrl+g", "exit_to_menu", "Exit Game"),
    ]

    def compose(self):
        yield HeaderWidget()
        yield GameBoard()
        with Container(id="input-container"):
            yield Label("  ", id="keyboard-icon")
            yield Input(placeholder="Type the words as they appear...", id="word-input")
        yield Footer()

    def on_mount(self) -> None:
        self.reset_game_state()

    def on_screen_resume(self) -> None:
        self.reset_game_state()

    #: Last value seen in the input box, used to tell a typed character from
    #: a backspace. Backspaces count towards neither accuracy total.
    _previous_input = ""

    def reset_game_state(self) -> None:
        self._previous_input = ""
        self.query_one("#word-input").value = ""
        self.query_one("#word-input").focus()
        self.query_one(GameBoard).clear_board()
        self.sync_game_state()

    def sync_game_state(self) -> None:
        header = self.query_one(HeaderWidget)
        board = self.query_one(GameBoard)

        header.score = self.app.score
        header.level = self.app.level
        header.category = self.app.category
        header.lives = self.app.lives
        header.max_lives = config.get("starting_lives", 3)

        board.level = self.app.level
        board.category = self.app.category

    def on_input_changed(self, event: Input.Changed) -> None:
        typed = event.value.strip()
        previous, self._previous_input = self._previous_input, typed

        if not typed:
            event.input.remove_class("typo")
            return

        board = self.query_one(GameBoard)
        session = self.app.session

        # A burst is timed from the keystroke that first put something in the
        # box to the one that completes the word.
        if not previous:
            session.start_word()

        score_gained = board.check_match(typed)
        input_container = self.query_one("#input-container")

        # check_match only matches on an exact equality, so a hit means the
        # word typed *is* `typed` - no need for the board to hand it back.
        # A valid prefix is what the game already uses to decide on the red
        # flash below; it doubles as the per-keystroke accuracy signal.
        has_valid_prefix = score_gained > 0 or any(
            w.text.startswith(typed) for w in board.active_words
        )
        if len(typed) > len(previous):
            session.record_keystroke(has_valid_prefix)

        if score_gained > 0:
            session.record_hit(typed)
            self.app.score += score_gained
            # Clamped as well as checked: one long phrase can jump several
            # levels at once, and the results screen should read 27, not 29.
            self.app.level = min(WIN_LEVEL, 1 + (self.app.score // POINTS_PER_LEVEL))

            self.sync_game_state()

            if self.app.level >= WIN_LEVEL:
                self.app.end_game(won=True)
                return

            # Reset the input box immediately (will trigger a new Changed event with empty string)
            event.input.value = ""
            event.input.remove_class("typo")

            input_container.add_class("flash-hit")
            self.set_timer(0.15, lambda: input_container.remove_class("flash-hit"))
        elif not has_valid_prefix:
            event.input.add_class("typo")
        else:
            event.input.remove_class("typo")

    def on_game_board_word_missed(self, event: GameBoard.WordMissed) -> None:
        if self.app.lives <= 0:
            return
        self.app.lives -= 1
        self.sync_game_state()

        input_container = self.query_one("#input-container")
        input_container.add_class("flash-miss")
        self.set_timer(0.15, lambda: input_container.remove_class("flash-miss"))

        if config.get("sound_enabled"):
            self.app.bell()

        if self.app.lives <= 0:
            self.app.end_game()

    def action_toggle_pause(self) -> None:
        board = self.query_one(GameBoard)
        board.is_paused = not board.is_paused
        # Paused seconds are not play time, so stop the clock while we wait.
        self.app.set_run_paused(board.is_paused)

        input_widget = self.query_one("#word-input")
        if board.is_paused:
            input_widget.disabled = True
            input_widget.placeholder = "PAUSED - ESC to Resume | Ctrl+G to Exit"
            input_widget.value = ""
        else:
            input_widget.disabled = False
            input_widget.placeholder = "Type the words as they appear..."
            input_widget.focus()

    def action_exit_to_menu(self) -> None:
        self.app.show_menu()


# --- Main Screen with Header and Switcher ---
class MainScreen(Screen):
    """The base navigation container screen with a top header and switcher."""

    BINDINGS = [
        ("ctrl+q", "quit_app", "Quit"),
        ("ctrl+s", "switch_settings", "Settings"),
        ("ctrl+h", "switch_help", "Help"),
        ("ctrl+a", "switch_about", "About"),
        ("ctrl+t", "switch_stats", "Stats"),
        ("escape", "switch_play", "Play"),
        ("ctrl+p", "switch_play", "Play"),
    ]

    def compose(self):
        yield MainHeader()
        yield ContentSwitcher(
            WelcomeScreen(id="welcome"),
            StatsScreen(id="stats"),
            SettingsScreen(id="settings"),
            HelpScreen(id="help"),
            AboutScreen(id="about"),
            initial="welcome",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.switch_to_screen("welcome")

    def action_quit_app(self) -> None:
        self.app.exit()

    def action_switch_settings(self) -> None:
        self.switch_to_screen("settings")

    def action_switch_help(self) -> None:
        self.switch_to_screen("help")

    def action_switch_about(self) -> None:
        self.switch_to_screen("about")

    def action_switch_stats(self) -> None:
        self.switch_to_screen("stats")

    def action_switch_play(self) -> None:
        self.switch_to_screen("welcome")

    def switch_to_screen(self, screen_name: str) -> None:
        switcher = self.query_one(ContentSwitcher)
        switcher.current = screen_name
        self.query_one(MainHeader).set_active(screen_name)
        if screen_name == "welcome":
            welcome_screen = self.query_one(WelcomeScreen)
            welcome_screen.update_high_score()
        elif screen_name == "stats":
            # Re-read from disk so a run that just ended is reflected.
            self.query_one(StatsScreen).sync_stats()

    @on(Button.Pressed)
    def handle_nav_button(self, event: Button.Pressed) -> None:
        if isinstance(event.button, NavItem):
            print(
                f"MainScreen handle_nav_button called: {event.button.screen_name}",
                flush=True,
            )
            self.switch_to_screen(event.button.screen_name)


# --- Main Gravitype Application ---
class GravitypeApp(App):
    """Main Textual App orchestrating user state, menus, and file state."""

    ENABLE_COMMAND_PALETTE = False

    SCREENS = {
        "main": MainScreen,
        "game": GameScreen,
        "game_over": GameOverScreen,
    }

    score = reactive(0)
    level = reactive(1)
    lives = reactive(3)
    category = reactive("tech")
    high_score = reactive(0)
    is_new_high_score = False
    #: True when the last run ended by reaching WIN_LEVEL rather than by
    #: running out of lives.
    is_win = False

    def __init__(self, *args, **kwargs) -> None:
        # Per-run bookkeeping for the stats page. Plain attributes, not
        # reactives - nothing renders them mid-game.
        self._run_started_at = None
        self._run_active_seconds = 0.0
        self._run_recorded = True
        #: Typing measurements for the run in progress.
        self.session = RunSession()
        # Compile the active theme to a writable location, then hand the
        # generated file to Textual as this app's stylesheet.
        css_path = generate_theme_file(config.get("theme"))
        super().__init__(*args, **kwargs, css_path=css_path, watch_css=True)

    def on_mount(self) -> None:
        self.high_score = config.get("high_score", 0)
        self.lives = config.get("starting_lives", 3)
        self.push_screen("main")

    @property
    def run_seconds(self) -> float:
        """Active seconds in the current run, including any in-flight stretch.

        By the time the results screen composes, ``_finish_run`` has already
        banked the elapsed time, so this reads the final figure.
        """
        pending = 0.0
        if self._run_started_at is not None:
            pending = time.monotonic() - self._run_started_at
        return self._run_active_seconds + pending

    def set_run_paused(self, paused: bool) -> None:
        """Stop or restart the play clock around a pause."""
        if self._run_recorded:
            return
        if paused:
            self._bank_elapsed()
        elif self._run_started_at is None:
            self._run_started_at = time.monotonic()

    def _bank_elapsed(self) -> None:
        """Fold any in-flight elapsed time into the run total."""
        if self._run_started_at is not None:
            self._run_active_seconds += time.monotonic() - self._run_started_at
            self._run_started_at = None

    def _finish_run(self, completed: bool) -> None:
        """Record the current run, once.

        Several paths end a run - game over, ctrl+g, PLAY AGAIN, quitting the
        app - so this is idempotent and they can all call it freely.
        """
        if self._run_recorded:
            return
        self._run_recorded = True
        self._bank_elapsed()
        stats.record_game_finished(
            self.category,
            self.level,
            self._run_active_seconds,
            completed,
            self.session,
        )

    def show_menu(self) -> None:
        # Leaving the board mid-run counts as started but not completed.
        self._finish_run(completed=False)
        self.switch_screen("main")

    def start_new_game(self) -> None:
        # Close out a run still in progress (PLAY AGAIN takes this path).
        self._finish_run(completed=False)

        self.score = 0
        self.level = 1
        self.lives = config.get("starting_lives", 3)

        self._run_active_seconds = 0.0
        self._run_started_at = time.monotonic()
        self._run_recorded = False
        self.is_win = False
        self.session.reset()
        stats.record_game_started(self.category)

        self.switch_screen("game")
        try:
            self.get_screen("game").reset_game_state()
        except Exception:
            pass

    def end_game(self, won: bool = False) -> None:
        """Finish the run, either by winning or by running out of lives.

        A match and a miss can land close enough together that both a win and
        a loss try to end the same run; ``_run_recorded`` already marks a run
        as finished, so whichever fires first is the outcome and the second
        call does nothing.
        """
        if self._run_recorded:
            return

        self.is_win = won
        self._finish_run(completed=True)
        self.is_new_high_score = self.score > self.high_score
        if self.is_new_high_score:
            self.high_score = self.score
            config.set("high_score", self.high_score)
        self.switch_screen("game_over")

    def on_unmount(self) -> None:
        # Quitting mid-run still counts the time and level played.
        self._finish_run(completed=False)

    def action_open_github(self) -> None:
        import webbrowser

        webbrowser.open("https://github.com/kanakOS01/gravitype")
