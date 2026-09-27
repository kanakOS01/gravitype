"""The typing loop: scoring, level-up, typo feedback and pause."""

import pytest
from textual.widgets import Input

from gravitype.core.config import config
from gravitype.tui.widgets.game_board import GameBoard
from gravitype.tui.widgets.header import HeaderWidget


async def _in_game(app, pilot, category="tech"):
    app.category = category
    app.start_new_game()
    await pilot.pause()
    return app.screen.query_one(GameBoard), app.screen.query_one("#word-input", Input)


def fake_clock(app):
    """Drive the session's clock by hand.

    Assigning to ``field.value`` in one go is a paste as far as the game is
    concerned - the burst starts and completes in the same event, so the
    sub-20ms guard discards it. Tests about timing type character by character
    and step this clock instead of relying on how long a pilot pause takes.
    """
    now = [0.0]
    app.session._clock = lambda: now[0]
    return now


async def type_word(pilot, field, word, clock=None, step=0.1):
    """Enter ``word`` one character at a time, as a player would."""
    for length in range(1, len(word) + 1):
        field.value = word[:length]
        if clock is not None:
            clock[0] += step
        await pilot.pause()


async def test_typing_a_falling_word_scores(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "python"
        await pilot.pause()

        assert app.score == 60
        # The field clears itself so the next word can be typed straight away.
        assert field.value == ""


async def test_score_accumulates_across_words(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)

        for word in ("git", "rust"):
            board.spawn_word(word)
            await pilot.pause()
            field.value = word
            await pilot.pause()

        assert app.score == 30 + 40


async def test_level_rises_every_150_points(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        assert app.level == 1

        for _ in range(3):
            board.spawn_word("kubernetes")
            await pilot.pause()
            field.value = "kubernetes"
            await pilot.pause()

        assert app.score == 300
        assert app.level == 3


async def test_a_wrong_prefix_flags_a_typo(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "zzz"
        await pilot.pause()
        assert field.has_class("typo")


async def test_a_valid_prefix_is_not_a_typo(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "pyt"
        await pilot.pause()
        assert not field.has_class("typo")


async def test_clearing_the_field_clears_the_typo(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "zzz"
        await pilot.pause()
        field.value = ""
        await pilot.pause()

        assert not field.has_class("typo")


async def test_header_tracks_the_game_state(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot, "general")
        header = app.screen.query_one(HeaderWidget)

        board.spawn_word("journey")
        await pilot.pause()
        field.value = "journey"
        await pilot.pause()

        assert header.score == app.score
        assert header.level == app.level
        assert header.category == "general"
        assert header.lives == app.lives


async def test_pause_disables_the_input_and_resume_restores_it(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)

        await pilot.press("escape")
        await pilot.pause()
        assert board.is_paused is True
        assert field.disabled is True
        assert "PAUSED" in field.placeholder

        await pilot.press("escape")
        await pilot.pause()
        assert board.is_paused is False
        assert field.disabled is False
        assert "PAUSED" not in field.placeholder


async def test_starting_a_game_applies_the_configured_lives(app):
    config.set("starting_lives", 8)

    async with app.run_test() as pilot:
        await pilot.pause()
        await _in_game(app, pilot)

        assert app.lives == 8


async def test_play_again_resets_score_level_and_board(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()
        field.value = "python"
        await pilot.pause()
        app.end_game()
        await pilot.pause()

        app.start_new_game()
        await pilot.pause()

        assert app.score == 0
        assert app.level == 1
        assert app.screen.query_one(GameBoard).active_words == []


async def test_ctrl_g_returns_to_the_menu(app):
    from gravitype.tui.app import MainScreen

    async with app.run_test() as pilot:
        await pilot.pause()
        await _in_game(app, pilot)

        await pilot.press("ctrl+g")
        await pilot.pause()

        assert isinstance(app.screen, MainScreen)


# --- typing measurements ---


async def test_typing_a_word_produces_a_wpm_sample(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        clock = fake_clock(app)
        board.spawn_word("python")
        await pilot.pause()

        # Six characters, so five 0.1s gaps between the first keystroke and
        # the last: 1.2 words over 0.5s = 144 WPM.
        await type_word(pilot, field, "python", clock)

        assert app.session.words_hit == 1
        assert app.session.wpm == pytest.approx(144.0)


async def test_a_pasted_word_scores_but_is_not_timed(app):
    """A whole word arriving in one event cannot be a real typing burst."""
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "python"
        await pilot.pause()

        assert app.score == 60
        assert app.session.words_hit == 0


async def test_clean_typing_keeps_accuracy_at_100(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        for length in range(1, len("python") + 1):
            field.value = "python"[:length]
            await pilot.pause()

        assert app.session.accuracy == 1.0


async def test_a_wrong_keystroke_dents_accuracy(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "p"
        await pilot.pause()
        field.value = "pz"
        await pilot.pause()

        assert app.session.total_keystrokes == 2
        assert app.session.error_keystrokes == 1
        assert app.session.accuracy == 0.5


async def test_backspaces_are_not_counted_as_keystrokes(app):
    """Accuracy is about characters typed, not corrections made."""
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()

        field.value = "py"
        await pilot.pause()
        field.value = "p"
        await pilot.pause()

        assert app.session.total_keystrokes == 1


async def test_errors_are_attributed_to_the_word_that_was_hit(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("rust")
        await pilot.pause()

        field.value = "r"
        await pilot.pause()
        field.value = "rz"
        await pilot.pause()
        field.value = "rust"
        await pilot.pause()

        assert app.session.error_series == [1]


async def test_play_again_resets_the_session(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("python")
        await pilot.pause()
        field.value = "python"
        await pilot.pause()
        app.end_game()
        await pilot.pause()

        app.start_new_game()
        await pilot.pause()

        assert app.session.words_hit == 0
        assert app.session.wpm is None
        assert app.session.total_keystrokes == 0


async def test_typing_figures_reach_the_lifetime_stats(app):
    from gravitype.core.stats import stats

    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        clock = fake_clock(app)
        board.spawn_word("python")
        await pilot.pause()
        await type_word(pilot, field, "python", clock)
        app.end_game()
        await pilot.pause()

        snap = stats.snapshot()
        assert snap["words_hit"] == 1
        assert snap["best_wpm"] > 0
        assert snap["accuracy"] is not None


# --- phrases ---


async def test_typing_a_phrase_matches_and_scores(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("borrow checker")
        await pilot.pause()

        await type_word(pilot, field, "borrow checker")

        assert app.score == 140
        assert field.value == ""


async def test_a_phrase_space_counts_as_a_keystroke(app):
    """Regression: the input is stripped before the growth test, so the space
    in a phrase used to slip past the accuracy counter."""
    phrase = "borrow checker"

    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word(phrase)
        await pilot.pause()

        await type_word(pilot, field, phrase)

        assert app.session.total_keystrokes == len(phrase)
        assert app.session.accuracy == 1.0


async def test_a_phrase_is_not_flagged_as_a_typo_partway_through(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("borrow checker")
        await pilot.pause()

        for length in range(1, len("borrow checker")):
            field.value = "borrow checker"[:length]
            await pilot.pause()
            assert not field.has_class("typo"), f"typo flagged at {length}"


async def test_a_phrase_is_timed_from_its_first_keystroke(app):
    phrase = "borrow checker"

    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        clock = fake_clock(app)
        board.spawn_word(phrase)
        await pilot.pause()

        await type_word(pilot, field, phrase, clock, step=0.1)

        # 14 chars = 2.8 words, over 13 gaps of 0.1s.
        assert app.session.words_hit == 1
        assert app.session.wpm == pytest.approx((len(phrase) / 5) / (1.3 / 60))


async def test_a_capitalised_word_must_be_typed_with_its_capitals(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("Rust")
        await pilot.pause()

        await type_word(pilot, field, "rust")

        assert app.score == 0
        assert len(board.active_words) == 1


async def test_a_capitalised_word_matches_when_typed_exactly(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("Rust")
        await pilot.pause()

        await type_word(pilot, field, "Rust")

        assert app.score == 40
        assert board.active_words == []


async def test_the_wrong_case_is_flagged_as_a_typo(app):
    """Case-sensitive matching means a lowercase start is not a valid prefix."""
    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word("Rust")
        await pilot.pause()

        field.value = "r"
        await pilot.pause()

        assert field.has_class("typo")


async def test_a_capitalised_phrase_is_not_flagged_when_typed_exactly(app):
    phrase = "Borrow Checker"

    async with app.run_test() as pilot:
        await pilot.pause()
        board, field = await _in_game(app, pilot)
        board.spawn_word(phrase)
        await pilot.pause()

        for length in range(1, len(phrase)):
            field.value = phrase[:length]
            await pilot.pause()
            assert not field.has_class("typo"), f"typo flagged at {length}"
