import random
from rich.text import Text
from textual.message import Message
from textual.widget import Widget
from textual.reactive import reactive
from gravitype.core.words import get_random_word


class WordWidget(Widget):
    """
    Widget representing a single falling word on the board.
    """

    def __init__(self, text: str, x: int, y: int, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.x = x
        self.y = y

    def render(self) -> Text:
        return Text(self.text)

    def update_position(self, board_height: int) -> None:
        self.styles.offset = (self.x, self.y)

        # Remove existing color classes
        self.remove_class("word-safe")
        self.remove_class("word-mid")
        self.remove_class("word-danger")

        # Color shifts as it approaches the bottom
        if self.y < board_height * 0.5:
            self.add_class("word-safe")
        elif self.y < board_height * 0.8:
            self.add_class("word-mid")
        else:
            self.add_class("word-danger")


class FloatingScoreWidget(Widget):
    """
    A temporary widget showing visual feedback (+50) when a word is matched.
    """

    def __init__(self, text: str, x: int, y: int, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.x = x
        self.y = y
        self.ticks = 0

    def render(self) -> Text:
        return Text(self.text)

    def update_position(self) -> None:
        self.styles.offset = (self.x, self.y)


class GameBoard(Widget):
    """
    The main game board where words fall. Manages active words, positions,
    and posts events when words are missed.
    """

    # Reactive inputs from active game state
    level = reactive(1)
    category = reactive("mixed")
    is_paused = reactive(False)

    class WordMissed(Message):
        """Posted when a word reaches the bottom border."""

        def __init__(self, word: str) -> None:
            super().__init__()
            self.word = word

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.active_words = []
        self.floating_scores = []
        self.ticks_count = 0
        self.game_timer = None

    def on_mount(self) -> None:
        # High-frequency tick for animations and smooth tracking
        self.game_timer = self.set_interval(0.05, self.game_tick)

    def on_unmount(self) -> None:
        if self.game_timer:
            self.game_timer.stop()

    def get_ticks_for_level(self, level: int):
        """
        Returns (move_ticks, spawn_ticks)
        Higher levels result in faster movement and quicker spawning.
        """
        # Base tick: 0.05s
        if level == 1:
            return 8, 40  # 0.40s move, 2.0s spawn
        elif level == 2:
            return 6, 30  # 0.30s move, 1.5s spawn
        elif level == 3:
            return 5, 24  # 0.25s move, 1.2s spawn
        elif level == 4:
            return 4, 18  # 0.20s move, 0.9s spawn
        else:
            # Level 5 and beyond scales speed and spawns gradually higher
            move_ticks = max(2, 4 - (level - 4))
            spawn_ticks = max(10, 18 - (level - 4) * 2)
            return move_ticks, spawn_ticks

    def game_tick(self) -> None:
        if self.is_paused:
            return

        self.ticks_count += 1
        board_height = self.size.height or 20

        # Retrieve level difficulty configs
        move_ticks, spawn_ticks = self.get_ticks_for_level(self.level)

        # 1. Update floating score indicators (every 3 ticks = 0.15s)
        if self.ticks_count % 3 == 0:
            for score in self.floating_scores[:]:
                score.y -= 1
                score.ticks += 1
                if score.ticks >= 3:
                    score.remove()
                    self.floating_scores.remove(score)
                else:
                    score.update_position()

        # 2. Spawn new words
        if self.ticks_count % spawn_ticks == 0:
            word_str = get_random_word(self.category, self.level)
            self.spawn_word(word_str)

        # 3. Move active words down
        if self.ticks_count % move_ticks == 0:
            for word in self.active_words[:]:
                word.y += 1
                # Check collision with the bottom boundary
                if word.y >= board_height:
                    word.remove()
                    self.active_words.remove(word)
                    self.post_message(self.WordMissed(word.text))
                else:
                    word.update_position(board_height)

    def spawn_word(self, word_text: str) -> None:
        width = self.size.width or 80
        word_len = len(word_text)
        max_x = max(1, width - word_len - 2)

        # Attempt to find a column with no close overlaps
        best_x = random.randint(2, max_x)
        for _ in range(5):
            x = random.randint(2, max_x)
            overlapping = False
            for active in self.active_words:
                if active.y < 3 and abs(active.x - x) < (word_len + 4):
                    overlapping = True
                    break
            if not overlapping:
                best_x = x
                break

        word_widget = WordWidget(word_text, best_x, 0)
        self.mount(word_widget)
        self.active_words.append(word_widget)
        word_widget.update_position(self.size.height or 20)

    def check_match(self, typed_word: str) -> int:
        """
        Checks if the typed word matches any active words.
        If multiple words match, deletes the lowest one (highest y-coord).
        Returns points scored (0 if no match).
        """
        typed_clean = typed_word.strip()
        matches = [w for w in self.active_words if w.text == typed_clean]

        if not matches:
            return 0

        # Pick the lowest word (highest y)
        target_word = max(matches, key=lambda w: w.y)

        # Award points based on word length
        score_gain = len(target_word.text) * 10

        # Remove the matched word widget
        target_word.remove()
        self.active_words.remove(target_word)

        # Spawn score floating feedback animation
        float_widget = FloatingScoreWidget(
            f"+{score_gain}", target_word.x, target_word.y
        )
        self.mount(float_widget)
        float_widget.update_position()
        self.floating_scores.append(float_widget)

        return score_gain

    def clear_board(self) -> None:
        """Removes all active words and scores from the board."""
        for word in self.active_words:
            word.remove()
        self.active_words.clear()

        for score in self.floating_scores:
            score.remove()
        self.floating_scores.clear()

        self.ticks_count = 0
