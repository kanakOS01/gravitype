from textual.widgets import Static
from textual.reactive import reactive


class StatusBar(Static):
    score = reactive(0)
    lives = reactive(3)

    def render(self):
        return f"Score: {self.score}   Lives: {'♥'*self.lives}"
