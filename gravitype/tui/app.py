import json
import os
from textual.app import App
from textual.screen import Screen
from textual.widgets import Button, Label, Static, Input
from textual.containers import Container, Horizontal
from textual.reactive import reactive

from gravitype.tui.widgets.header import HeaderWidget
from gravitype.tui.widgets.game_board import GameBoard


# --- Welcome/Start Menu Screen ---
class WelcomeScreen(Screen):
    """The initial welcome screen for category selection and game start."""

    def compose(self):
        with Container(id="menu-container"):
            yield Static(
                "  ________                      .__  __                      \n"
                " /  _____/___________ ___  __ _|__|/  |_ ___.__.______   ____ \n"
                "/   \\  __\\_  __ \\__  \\\\  \\/ /|  |  \\   __<   |  |\\____ \\_/ __ \\\n"
                "\\    \\_\\  \\  | \\// __ \\\\   / |  |  ||  |  \\___  ||  |_> >  ___/\n"
                " \\______  /__|  (____  /\\_/  |____/ |__|  / ____||   __/ \\___  >\n"
                "        \\/           \\/                   \\/     |__|        \\/ ",
                classes="title",
            )
            yield Label(
                "A Neon Gravity Typing Game in your Terminal", classes="subtitle"
            )

            yield Label("Select Category:")
            with Horizontal(id="category-container"):
                yield Button("Tech", id="cat-tech", classes="category-btn active")
                yield Button("General", id="cat-general", classes="category-btn")
                yield Button("Mixed", id="cat-mixed", classes="category-btn")

            yield Button("START GAME", id="btn-start", classes="action-btn")

    def on_mount(self) -> None:
        # Sync initial state
        self.app.category = "tech"

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
            yield Label("⌨️", id="keyboard-icon")
            yield Input(placeholder="Type the words as they appear...", id="word-input")

    def on_mount(self) -> None:
        self.query_one("#word-input").focus()
        self.sync_game_state()

    def sync_game_state(self) -> None:
        header = self.query_one(HeaderWidget)
        board = self.query_one(GameBoard)

        header.score = self.app.score
        header.level = self.app.level
        header.category = self.app.category
        header.lives = self.app.lives

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
        self.app.lives -= 1
        self.sync_game_state()

        input_container = self.query_one("#input-container")
        input_container.add_class("flash-miss")
        self.set_timer(0.15, lambda: input_container.remove_class("flash-miss"))
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


# --- Main Gravitype Application ---
class GravitypeApp(App):
    """Main Textual App orchestrating user state, menus, and file state."""

    CSS_PATH = "styles/game.tcss"

    SCREENS = {
        "welcome": WelcomeScreen,
        "game": GameScreen,
        "game_over": GameOverScreen,
    }

    score = reactive(0)
    level = reactive(1)
    lives = reactive(3)
    category = reactive("tech")
    high_score = reactive(0)

    def on_mount(self) -> None:
        self.load_high_score()
        self.push_screen("welcome")

    def load_high_score(self) -> None:
        try:
            if os.path.exists(".highscores.json"):
                with open(".highscores.json", "r") as f:
                    data = json.load(f)
                    self.high_score = data.get("high_score", 0)
        except Exception:
            self.high_score = 0

    def save_high_score(self) -> None:
        try:
            with open(".highscores.json", "w") as f:
                json.dump({"high_score": self.high_score}, f)
        except Exception:
            pass

    def show_menu(self) -> None:
        self.switch_screen("welcome")

    def start_new_game(self) -> None:
        self.score = 0
        self.level = 1
        self.lives = 3
        self.switch_screen("game")

    def end_game(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        self.switch_screen("game_over")
