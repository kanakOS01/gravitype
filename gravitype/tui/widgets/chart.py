"""A line chart drawn with braille glyphs.

Braille packs a 2x4 grid of dots into every character cell, so a chart that is
56 cells wide and 5 tall is really a 112x20 plot - enough resolution for a
curve to read as a curve in a terminal, without pulling in a plotting library.

Points are joined by interpolation rather than left as dots, and error markers
replace the cell they land in so they sit on the curve itself.
"""

from rich.console import RenderableType
from rich.text import Text
from textual.widget import Widget

#: Dot bit for each (row, column) position inside one braille cell. Braille
#: codepoints are 0x2800 plus the OR of the dots that are raised.
_DOTS = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]

BRAILLE_BASE = 0x2800
MARKER = "×"


class BrailleChart(Widget):
    """Plots a series, marking the points that had errors."""

    COMPONENT_CLASSES = {
        "braillechart--line",
        "braillechart--marker",
        "braillechart--axis",
        "braillechart--label",
    }

    DEFAULT_CSS = """
    BrailleChart {
        height: auto;
    }
    """

    def __init__(
        self,
        series=None,
        errors=None,
        plot_width: int = 56,
        plot_height: int = 5,
        x_label: str = "",
        empty_message: str = "not enough data",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.plot_width = plot_width
        self.plot_height = plot_height
        self.x_label = x_label
        self.empty_message = empty_message
        self.set_series(series or [], errors or [])

    def set_series(self, series, errors=None) -> None:
        """Replace the plotted data and redraw."""
        self.series = [float(value) for value in series]
        errors = list(errors or [])
        # Pad or trim so every point has a matching error count.
        errors += [0] * (len(self.series) - len(errors))
        self.errors = errors[: len(self.series)]
        self.refresh()

    # --- plotting ---

    #: Columns reserved to the left of the axis for scale labels.
    GUTTER = 5

    def _usable_width(self) -> int:
        """Plot width that fits the space the layout actually gave us.

        Falls back to the configured width before the first layout pass, when
        the widget has no size yet.
        """
        available = (self.size.width or 0) - self.GUTTER - 1
        if available <= 0:
            return self.plot_width
        return max(8, min(self.plot_width, available))

    def _points(self, plot_width: int):
        """Map each sample to a (subpixel x, subpixel y) position."""
        width_dots = plot_width * 2
        height_dots = self.plot_height * 4

        low, high = min(self.series), max(self.series)
        span = high - low

        points = []
        for index, value in enumerate(self.series):
            if len(self.series) == 1:
                x = 0
            else:
                x = round(index * (width_dots - 1) / (len(self.series) - 1))
            if span <= 0:
                # A flat series has no spread; draw it down the middle rather
                # than dividing by zero or pinning it to an edge.
                y = (height_dots - 1) // 2
            else:
                y = round((1 - (value - low) / span) * (height_dots - 1))
            points.append((x, y))
        return points, low, high

    def _grid(self, plot_width: int):
        """Render the plot area to a list of (text, marker flag) rows."""
        cells = [[0] * plot_width for _ in range(self.plot_height)]
        markers = set()

        points, low, high = self._points(plot_width)

        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            steps = max(abs(x1 - x0), abs(y1 - y0)) or 1
            for step in range(steps + 1):
                x = round(x0 + (x1 - x0) * step / steps)
                y = round(y0 + (y1 - y0) * step / steps)
                cells[y // 4][x // 2] |= _DOTS[y % 4][x % 2]

        if len(points) == 1:
            x, y = points[0]
            cells[y // 4][x // 2] |= _DOTS[y % 4][x % 2]

        for (x, y), error_count in zip(points, self.errors):
            if error_count:
                markers.add((y // 4, x // 2))

        return cells, markers, low, high

    def _y_labels(self, low: float, high: float):
        """A scale label for the top, middle and bottom rows.

        A flat series has no range to label, so it gets a single label on the
        row the line actually sits on rather than the same number three times.
        """
        labels = [""] * self.plot_height

        if high - low <= 0:
            labels[(self.plot_height - 1) // 2] = f"{low:.0f}"
            return labels

        labels[0] = f"{high:.0f}"
        labels[-1] = f"{low:.0f}"
        if self.plot_height > 2:
            labels[self.plot_height // 2] = f"{(low + high) / 2:.0f}"
        return labels

    def render(self) -> RenderableType:
        line_style = self.get_component_rich_style("braillechart--line")
        marker_style = self.get_component_rich_style("braillechart--marker")
        axis_style = self.get_component_rich_style("braillechart--axis")
        label_style = self.get_component_rich_style("braillechart--label")

        gutter = self.GUTTER
        plot_width = self._usable_width()
        # A braille row is exactly as wide as the plot; let it be cropped
        # rather than wrapped, or one long row folds onto the next line and
        # shears the chart in half.
        out = Text(no_wrap=True, overflow="crop")

        if not self.series:
            out.append(" " * gutter)
            out.append(self.empty_message.center(plot_width), label_style)
            return out

        cells, markers, low, high = self._grid(plot_width)
        labels = self._y_labels(low, high)

        for row_index, row in enumerate(cells):
            out.append(f"{labels[row_index]:>{gutter - 1}} ", label_style)
            out.append("│", axis_style)
            for col_index, bits in enumerate(row):
                if (row_index, col_index) in markers:
                    out.append(MARKER, marker_style)
                elif bits:
                    out.append(chr(BRAILLE_BASE + bits), line_style)
                else:
                    out.append(" ")
            out.append("\n")

        out.append(" " * gutter)
        out.append("└" + "─" * plot_width, axis_style)

        if self.x_label:
            out.append("\n")
            out.append(" " * (gutter + 1))
            out.append(self.x_label[:plot_width], label_style)

        return out
