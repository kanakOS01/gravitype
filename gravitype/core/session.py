"""Typing measurements for a single run.

Kept free of Textual so the maths can be unit-tested without spinning up an
app, per the layering rule in CONTRIBUTING.

Why *burst* WPM rather than session WPM: the player does not control how much
there is to type - ``GameBoard.get_ticks_for_level`` does. At level 1 a word
arrives every two seconds, which caps any player at roughly 27 WPM however fast
they type, so a session average would mostly restate the level reached. Timing
each word from its first keystroke to its match measures the player instead.
"""

import time

#: Standard typing-test convention: a "word" is five characters.
CHARS_PER_WORD = 5

#: Bursts faster than this are discarded. A paste, a key-repeat storm or a
#: test driving the clock by hand can otherwise report thousands of WPM.
MIN_BURST_SECONDS = 0.02


class RunSession:
    """Accumulates per-word timings and keystroke accuracy for one run."""

    def __init__(self, clock=time.monotonic):
        # Injectable so tests can step time instead of sleeping.
        self._clock = clock
        self.reset()

    def reset(self) -> None:
        """Clear everything, ready for a new run."""
        self._word_started_at = None
        self._errors_this_word = 0
        #: One ``(wpm, errors)`` pair per word hit, in the order they were hit.
        self.samples = []
        self.total_keystrokes = 0
        self.error_keystrokes = 0

    # --- recording ---

    def start_word(self) -> None:
        """Called when the input goes from empty to non-empty."""
        if self._word_started_at is None:
            self._word_started_at = self._clock()

    def record_keystroke(self, valid_prefix: bool) -> None:
        """Count one typed character, and whether it kept the input valid.

        ``valid_prefix`` is the condition the game already evaluates to decide
        whether to flash the input red.
        """
        self.total_keystrokes += 1
        if not valid_prefix:
            self.error_keystrokes += 1
            self._errors_this_word += 1

    def record_hit(self, word: str) -> None:
        """Close the current burst, turning it into a WPM sample."""
        started = self._word_started_at
        self._word_started_at = None
        errors, self._errors_this_word = self._errors_this_word, 0

        if started is None:
            return

        elapsed = self._clock() - started
        if elapsed < MIN_BURST_SECONDS:
            return

        wpm = (len(word) / CHARS_PER_WORD) / (elapsed / 60)
        self.samples.append((wpm, errors))

    def abandon_word(self) -> None:
        """Drop the in-flight burst without recording it.

        Used when the board is cleared underneath the player - the elapsed
        time is real but it was not spent typing the word that follows.
        """
        self._word_started_at = None
        self._errors_this_word = 0

    # --- derived figures ---

    @property
    def words_hit(self) -> int:
        return len(self.samples)

    @property
    def wpm_series(self) -> list:
        return [wpm for wpm, _ in self.samples]

    @property
    def error_series(self) -> list:
        return [errors for _, errors in self.samples]

    @property
    def wpm(self):
        """Mean burst speed for the run, or ``None`` if nothing was typed."""
        series = self.wpm_series
        if not series:
            return None
        return sum(series) / len(series)

    @property
    def best_burst(self):
        """Fastest single word, or ``None``."""
        series = self.wpm_series
        return max(series) if series else None

    @property
    def accuracy(self):
        """Share of keystrokes that kept the input valid, as a 0-1 fraction."""
        if not self.total_keystrokes:
            return None
        return 1 - (self.error_keystrokes / self.total_keystrokes)


def format_wpm(value) -> str:
    """Render a WPM figure, or an em dash when there is nothing to show."""
    return "—" if value is None else f"{value:.0f}"


def format_percent(value, suffix: str = "%") -> str:
    """Render a 0-1 fraction as a percentage, or an em dash.

    ``suffix`` is dropped for the oversized digits on the results screen,
    where a block-drawn ``%`` is more of a smudge than a symbol.
    """
    return "—" if value is None else f"{value * 100:.0f}{suffix}"
