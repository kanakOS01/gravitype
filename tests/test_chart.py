"""Braille chart rendering.

Asserted against the rendered text rather than internal state, so the tests
fail on what a player would actually see.
"""

import pytest

from gravitype.tui.widgets.bignum import BigNumber
from gravitype.tui.widgets.chart import BRAILLE_BASE, MARKER, BrailleChart


@pytest.fixture(autouse=True)
def _no_styles(monkeypatch):
    """Component styles need a running app; the glyphs do not."""
    monkeypatch.setattr(
        BrailleChart, "get_component_rich_style", lambda self, name: "", raising=False
    )
    monkeypatch.setattr(
        BigNumber, "get_component_rich_style", lambda self, name: "", raising=False
    )


def render(series, errors=None, **kwargs):
    return BrailleChart(series, errors, **kwargs).render().plain


def plot_lines(text, height=5):
    """Just the plot rows, with the label gutter and axis stripped."""
    return [line[BrailleChart.GUTTER + 1 :] for line in text.split("\n")[:height]]


def is_braille(char):
    return BRAILLE_BASE <= ord(char) < BRAILLE_BASE + 256


# --- degenerate input ---


def test_empty_series_shows_the_empty_message():
    text = render([], [], empty_message="nothing here")

    assert "nothing here" in text
    assert MARKER not in text


def test_empty_series_does_not_raise_on_min_max():
    """The obvious crash: min() of an empty sequence."""
    assert render([]) is not None


def test_a_single_sample_plots_one_point():
    text = render([67])
    plotted = [c for line in plot_lines(text) for c in line if is_braille(c)]

    assert len(plotted) == 1


def test_a_single_sample_labels_only_its_own_row():
    """Three identical scale labels would be noise, not a scale."""
    labels = [line[: BrailleChart.GUTTER] for line in render([67]).split("\n")[:5]]

    assert [label.strip() for label in labels].count("67") == 1


def test_a_flat_series_draws_a_line_not_a_crash():
    """A zero span must not divide by zero or pin the line to an edge."""
    text = render([60] * 8)
    lines = plot_lines(text)
    drawn = [index for index, line in enumerate(lines) if line.strip()]

    assert drawn == [2]


# --- plotting ---


def test_the_curve_is_continuous():
    """Points are joined, so every column carries ink."""
    series = [10, 90, 20, 80, 30, 70]
    lines = plot_lines(render(series, plot_width=40))

    for column in range(40):
        assert any(column < len(line) and is_braille(line[column]) for line in lines), (
            f"column {column} is empty"
        )


def test_higher_values_sit_higher():
    rising = plot_lines(render([10, 90], plot_width=20))
    first_col = [i for i, line in enumerate(rising) if is_braille(line[0])]
    last_col = [i for i, line in enumerate(rising) if is_braille(line[19])]

    # Row 0 is the top, so the larger value has the smaller row index.
    assert min(last_col) < min(first_col)


def test_the_scale_labels_bound_the_data():
    text = render([37, 122, 68])

    assert "122" in text
    assert "37" in text


def test_the_axis_spans_the_plot():
    text = render([1, 2, 3], plot_width=30)
    axis = [line for line in text.split("\n") if "└" in line][0]

    assert axis.count("─") == 30


def test_the_x_label_is_rendered():
    assert "word 1" in render([1, 2], x_label="word 1")


def test_a_long_x_label_is_cropped_not_wrapped():
    text = render([1, 2], plot_width=20, x_label="x" * 100)

    assert all(len(line) <= 26 for line in text.split("\n"))


# --- error markers ---


def test_errors_place_markers_on_the_curve():
    text = render([50, 60, 70], [0, 2, 0])

    assert text.count(MARKER) == 1


def test_no_errors_means_no_markers():
    assert MARKER not in render([50, 60, 70], [0, 0, 0])


def test_every_flagged_sample_gets_a_marker():
    text = render([10, 90, 20, 80], [1, 1, 1, 1], plot_width=40)

    assert text.count(MARKER) == 4


def test_a_marker_replaces_the_cell_at_its_own_point():
    """The marker should sit where the sample is, not on a separate row."""
    without = plot_lines(render([10, 90], [0, 0], plot_width=20))
    with_marker = plot_lines(render([10, 90], [0, 1], plot_width=20))

    row = next(i for i, line in enumerate(with_marker) if MARKER in line)
    column = with_marker[row].index(MARKER)

    assert is_braille(without[row][column])


def test_a_short_error_list_is_padded():
    """Fewer errors than samples must not raise or mis-align."""
    assert render([10, 20, 30], [1]).count(MARKER) == 1


def test_a_long_error_list_is_trimmed():
    assert render([10, 20], [1, 1, 1, 1, 1]).count(MARKER) == 2


# --- updating ---


def test_set_series_replaces_the_data():
    chart = BrailleChart([1, 2, 3])
    chart.set_series([50, 60], [0, 1])

    assert chart.series == [50.0, 60.0]
    assert chart.errors == [0, 1]
    assert chart.render().plain.count(MARKER) == 1


def test_integers_are_accepted_as_well_as_floats():
    assert BrailleChart([1, 2]).series == [1.0, 2.0]


# --- big numbers ---


def test_big_number_renders_three_rows():
    assert BigNumber("wpm", "67").render().plain.count("\n") == 3


def test_big_number_without_a_label_has_no_heading_row():
    assert BigNumber("", "67").render().plain.count("\n") == 2


def test_big_number_includes_its_label():
    assert "wpm" in BigNumber("wpm", "67").render().plain


def test_big_number_handles_the_em_dash_placeholder():
    """An empty run shows a dash; it must not fall through to a KeyError."""
    assert BigNumber("wpm", "—").render().plain is not None


def test_big_number_handles_percent_signs():
    assert BigNumber("acc", "91%").render().plain is not None


def test_big_number_falls_back_to_blanks_for_unknown_characters():
    rendered = BigNumber("", "?").render().plain

    assert rendered.strip() == ""
