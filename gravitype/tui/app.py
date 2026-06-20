from textual import on
from textual.app import App
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Label, Input, ContentSwitcher
from textual.containers import Container, Horizontal
from textual.reactive import reactive

from gravitype.core.config import config, generate_theme_file
from gravitype.tui.widgets.header import HeaderWidget
from gravitype.tui.widgets.game_board import GameBoard
from gravitype.tui.widgets.main_header import MainHeader, NavItem, Banner
from gravitype.tui.widgets.screens import AboutScreen, HelpScreen, SettingsScreen


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
                yield Button("Mixed", id="cat-mixed", classes="category-btn")

            yield Label("", id="high-score-label", classes="label-info")
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
    """Displayed when lives run out, showing final stats and highscore."""

    def compose(self):
        with Container(id="game-over-container"):
            yield Label("GAME OVER", classes="game-over-title")
            yield Label(f"Score: {self.app.score:05d}", classes="subtitle")

            is_new_high = self.app.score > self.app.high_score
            high_score_text = (
                f"High Score: {max(self.app.score, self.app.high_score):05d}"
            )
            if is_new_high:
                high_score_text += " [NEW HIGH SCORE!]"

            yield Label(high_score_text, classes="label-info")
            yield Label(f"Level Reached: {self.app.level}", classes="label-info")
            yield Label(f"Category: {self.app.category.upper()}", classes="label-info")

            yield Button("PLAY AGAIN", id="btn-retry", classes="action-btn")
            yield Button("MAIN MENU", id="btn-menu", classes="action-btn")
            yield Button("QUIT GAME", id="btn-quit", classes="danger-btn")

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

    BINDINGS = [("escape", "toggle_pause", "Pause/Resume Game")]

    def compose(self):
        yield HeaderWidget()
        yield GameBoard()
        with Container(id="input-container"):
            yield Label("> ", id="keyboard-icon")
            yield Input(placeholder="Type the words as they appear...", id="word-input")

    def on_mount(self) -> None:
        self.reset_game_state()

    def on_screen_resume(self) -> None:
        self.reset_game_state()

    def reset_game_state(self) -> None:
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
        if not typed:
            event.input.remove_class("typo")
            return

        board = self.query_one(GameBoard)
        score_gained = board.check_match(typed)
        input_container = self.query_one("#input-container")

        if score_gained > 0:
            self.app.score += score_gained
            # Increase level every 150 points
            self.app.level = 1 + (self.app.score // 150)

            self.sync_game_state()

            # Reset the input box immediately (will trigger a new Changed event with empty string)
            event.input.value = ""
            event.input.remove_class("typo")

            input_container.add_class("flash-hit")
            self.set_timer(0.15, lambda: input_container.remove_class("flash-hit"))
        else:
            # Check if the currently typed string is a valid prefix of any active word
            has_valid_prefix = any(w.text.startswith(typed) for w in board.active_words)
            if not has_valid_prefix:
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

        input_widget = self.query_one("#word-input")
        if board.is_paused:
            input_widget.disabled = True
            input_widget.placeholder = "PAUSED - Press ESC to Resume"
            input_widget.value = ""
        else:
            input_widget.disabled = False
            input_widget.placeholder = "Type the words as they appear..."
            input_widget.focus()


# --- Main Screen with Header and Switcher ---
class MainScreen(Screen):
    """The base navigation container screen with a top header and switcher."""

    BINDINGS = [
        ("ctrl+q", "quit_app", "Quit"),
        ("ctrl+s", "switch_settings", "Settings"),
        ("ctrl+h", "switch_help", "Help"),
        ("ctrl+a", "switch_about", "About"),
        ("escape", "switch_play", "Play"),
        ("ctrl+p", "switch_play", "Play"),
    ]

    def compose(self):
        yield MainHeader()
        yield ContentSwitcher(
            WelcomeScreen(id="welcome"),
            SettingsScreen(id="settings"),
            HelpScreen(id="help"),
            AboutScreen(id="about"),
            initial="welcome",
        )

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

    def action_switch_play(self) -> None:
        self.switch_to_screen("welcome")

    def switch_to_screen(self, screen_name: str) -> None:
        switcher = self.query_one(ContentSwitcher)
        switcher.current = screen_name
        self.query_one(MainHeader).set_active(screen_name)
        if screen_name == "welcome":
            welcome_screen = self.query_one(WelcomeScreen)
            welcome_screen.update_high_score()

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

    CSS_PATH = "styles/theme_active.tcss"

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

    def __init__(self, *args, **kwargs) -> None:
        # Dynamically compile the active theme before calling super()
        generate_theme_file(config.get("theme"))
        super().__init__(*args, **kwargs, watch_css=True)

    def on_mount(self) -> None:
        self.high_score = config.get("high_score", 0)
        self.lives = config.get("starting_lives", 3)
        self.push_screen("main")

    def show_menu(self) -> None:
        self.switch_screen("main")

    def start_new_game(self) -> None:
        self.score = 0
        self.level = 1
        self.lives = config.get("starting_lives", 3)
        self.switch_screen("game")
        try:
            self.get_screen("game").reset_game_state()
        except Exception:
            pass

    def end_game(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
            config.set("high_score", self.high_score)
        self.switch_screen("game_over")

    def action_open_github(self) -> None:
        import webbrowser

        webbrowser.open("https://github.com/macbook/gravitype")
