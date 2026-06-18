from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class HeaderWidget(Widget):
    """
    A custom header widget displaying:
    - Score (left)
    - Level and Category (middle)
    - Remaining Lives as hearts (right)
    """

    score = reactive(0)
    level = reactive(1)
    category = reactive("mixed")
    lives = reactive(3)
    max_lives = reactive(3)

    def compose(self):
        self.score_label = Label("SCORE: 00000", classes="header-score")
        self.info_label = Label("LEVEL 1 | MIXED", classes="header-info")
        self.lives_label = Label("LIVES: 3", classes="header-lives")

        yield self.score_label
        yield self.info_label
        yield self.lives_label

    def watch_score(self, new_score: int) -> None:
        if hasattr(self, "score_label"):
            self.score_label.update(f"SCORE: {new_score:05d}")

    def update_info(self) -> None:
        if hasattr(self, "info_label"):
            self.info_label.update(f"LEVEL {self.level} | {self.category.upper()}")

    def watch_level(self, new_level: int) -> None:
        self.update_info()

    def watch_category(self, new_category: str) -> None:
        self.update_info()

    def watch_lives(self, new_lives: int) -> None:
        if hasattr(self, "lives_label"):
            self.lives_label.update(f"LIVES: {max(0, new_lives)}")
