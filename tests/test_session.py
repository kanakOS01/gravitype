"""Burst WPM and keystroke accuracy.

Driven through an injected clock rather than real time, so the arithmetic is
asserted exactly instead of within a tolerance.
"""

import pytest

from gravitype.core.session import (
    MIN_BURST_SECONDS,
    RunSession,
    format_percent,
    format_wpm,
)


class FakeClock:
    """A clock the test advances by hand."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def session(clock):
    return RunSession(clock=clock)


def type_word(session, clock, word, seconds, errors=0):
    """Type ``word`` over ``seconds``, with ``errors`` bad keystrokes."""
    session.start_word()
    for index, _ in enumerate(word):
        session.record_keystroke(index >= errors)
    clock.advance(seconds)
    session.record_hit(word)


# --- burst maths ---


def test_a_fresh_session_has_nothing_to_report(session):
    assert session.wpm is None
    assert session.accuracy is None
    assert session.best_burst is None
    assert session.words_hit == 0
    assert session.wpm_series == []


def test_burst_wpm_uses_the_five_character_convention(session, clock):
    # "python" is 6 chars = 1.2 words; over 1s that is 72 WPM.
    type_word(session, clock, "python", 1.0)

    assert session.wpm == pytest.approx(72.0)


def test_a_faster_burst_scores_higher(session, clock):
    type_word(session, clock, "python", 0.5)

    assert session.wpm == pytest.approx(144.0)


def test_run_wpm_is_the_mean_of_its_bursts(session, clock):
    type_word(session, clock, "python", 1.0)  # 72
    type_word(session, clock, "python", 0.5)  # 144

    assert session.wpm == pytest.approx(108.0)
    assert session.best_burst == pytest.approx(144.0)


def test_idle_time_between_words_is_not_counted(session, clock):
    """The clock only runs from the first keystroke of a word."""
    clock.advance(30.0)
    type_word(session, clock, "python", 1.0)
    clock.advance(30.0)

    assert session.wpm == pytest.approx(72.0)


def test_words_hit_counts_samples(session, clock):
    for _ in range(3):
        type_word(session, clock, "rust", 0.5)

    assert session.words_hit == 3
    assert len(session.wpm_series) == 3


def test_an_implausibly_fast_burst_is_discarded(session, clock):
    """Guards against a paste or key-repeat reporting thousands of WPM."""
    session.start_word()
    clock.advance(MIN_BURST_SECONDS / 2)
    session.record_hit("python")

    assert session.words_hit == 0
    assert session.wpm is None


def test_a_hit_without_a_start_is_ignored(session, clock):
    """Defensive: a match with no recorded burst must not invent a sample."""
    session.record_hit("python")

    assert session.words_hit == 0


def test_start_word_is_idempotent_within_a_word(session, clock):
    """Only the first keystroke starts the clock."""
    session.start_word()
    clock.advance(1.0)
    session.start_word()
    clock.advance(1.0)
    session.record_hit("python")

    # Two seconds total, not one.
    assert session.wpm == pytest.approx(36.0)


def test_abandoning_a_word_drops_the_burst(session, clock):
    session.start_word()
    clock.advance(5.0)
    session.abandon_word()

    type_word(session, clock, "python", 1.0)

    assert session.words_hit == 1
    assert session.wpm == pytest.approx(72.0)


# --- accuracy ---


def test_clean_typing_is_full_accuracy(session, clock):
    type_word(session, clock, "python", 1.0)

    assert session.accuracy == 1.0
    assert session.total_keystrokes == 6
    assert session.error_keystrokes == 0


def test_bad_keystrokes_reduce_accuracy(session, clock):
    # 6 keystrokes, first 2 invalid.
    type_word(session, clock, "python", 1.0, errors=2)

    assert session.error_keystrokes == 2
    assert session.accuracy == pytest.approx(4 / 6)


def test_accuracy_spans_the_whole_run(session, clock):
    type_word(session, clock, "rust", 1.0, errors=1)
    type_word(session, clock, "rust", 1.0)

    assert session.total_keystrokes == 8
    assert session.error_keystrokes == 1
    assert session.accuracy == pytest.approx(7 / 8)


def test_errors_are_attributed_to_the_word_being_typed(session, clock):
    type_word(session, clock, "rust", 1.0, errors=1)
    type_word(session, clock, "rust", 1.0)
    type_word(session, clock, "rust", 1.0, errors=2)

    assert session.error_series == [1, 0, 2]


def test_error_attribution_resets_between_words(session, clock):
    type_word(session, clock, "rust", 1.0, errors=3)
    type_word(session, clock, "rust", 1.0)

    assert session.error_series[1] == 0


def test_a_discarded_burst_still_counts_its_keystrokes(session, clock):
    """Accuracy is about what you typed, not whether the word was timed."""
    session.start_word()
    session.record_keystroke(False)
    clock.advance(MIN_BURST_SECONDS / 2)
    session.record_hit("python")

    assert session.words_hit == 0
    assert session.accuracy == 0.0


# --- reset ---


def test_reset_clears_everything(session, clock):
    type_word(session, clock, "python", 1.0, errors=2)
    session.reset()

    assert session.wpm is None
    assert session.accuracy is None
    assert session.words_hit == 0
    assert session.total_keystrokes == 0
    assert session.error_keystrokes == 0


def test_reset_drops_an_in_flight_burst(session, clock):
    session.start_word()
    clock.advance(10.0)
    session.reset()

    type_word(session, clock, "python", 1.0)

    assert session.wpm == pytest.approx(72.0)


# --- formatting ---


@pytest.mark.parametrize(
    "value, expected",
    [(None, "—"), (0.0, "0"), (67.4, "67"), (67.5, "68"), (144.0, "144")],
)
def test_format_wpm(value, expected):
    assert format_wpm(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(None, "—"), (0.0, "0%"), (0.914, "91%"), (1.0, "100%")],
)
def test_format_percent(value, expected):
    assert format_percent(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(None, "—"), (0.0, "0"), (0.914, "91"), (1.0, "100")],
)
def test_format_percent_without_a_suffix(value, expected):
    """The results screen drops the sign; a block-drawn % is a smudge."""
    assert format_percent(value, suffix="") == expected
