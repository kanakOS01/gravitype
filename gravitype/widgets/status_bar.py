from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.color import Color
from textual.widget import Widget
from textual.widgets import Input, ProgressBar, Digits
from textual.reactive import reactive
from rich.text import Text


class InputArea(Input):
    """Displays current typed text (center)"""


class Score(Digits):
    """Displays score (left)"""


class LifeBar(Widget):
    """Displays LifeBar (right)"""

    def render(self) -> Text:
        filled_blocks = "█" * self.lives
        empty_blocks = "░" * (self.max_lives - self.lives)

        # Set base color for filled blocks using self.styles.color
        if self.lives > self.max_lives * 0.6:
            self.styles.color = Color(0, 200, 0, a=0.5)      # green
        elif self.lives > self.max_lives * 0.3:
            self.styles.color = Color(255, 255, 0, a=0.5)    # yellow
        else:
            self.styles.color = Color(255, 0, 0, a=0.5)      # red

        text = Text()
        text.append(filled_blocks)  # Uses self.styles.color
        text.append(empty_blocks, style="grey35")  # Static grey for empty

        return text

    

    # def render(self) -> Text:
    #     # Color with alpha — 0.5 = 50% transparency
    #     blocks = Text("█" * self.lives)
    #     self.styles.color = Color(191, 78, 96, a=0.5)
    #     return blocks


class StatusBar(HorizontalGroup):
    
    score = reactive('000')
    lives = reactive(8)
    max_lives = reactive(25)

    def compose(self) -> ComposeResult:
        self.score_widget = Score(self.score)
        self.input_area = InputArea(
            placeholder="your words will appear here"
        )
        self.life_bar = LifeBar()
        self.life_bar.max_lives = self.max_lives
        self.life_bar.lives = self.lives

        yield self.score_widget
        yield self.input_area
        yield self.life_bar
