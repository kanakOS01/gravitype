from textual.widgets import Static


class PlayArea(Static):
    def render(self):
        grid = [[" "]*30 for _ in range(15)]
        grid[2][5:11] = list("python")
        grid[5][10:17] = list("gravity")
        return "\n".join("".join(row) for row in grid)
