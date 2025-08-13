from textual.widgets import Static
from textual.reactive import reactive

class PlayArea(Static):
    def render(self):
        grid = [[" "]*30 for _ in range(15)]
        grid[2][5:11] = list("python")
        grid[5][10:17] = list("gravity")
        return "\n".join("".join(row) for row in grid)

class StatusBar(Static):
    score = reactive(0)
    lives = reactive(3)

    def render(self):
        return f"Score: {self.score}   Lives: {'♥'*self.lives}"

class TypedArea(Static):
    typed = reactive("")

    def render(self):
        return f"Typed: {self.typed}"
