"""Run lifecycle: what each way of ending a game records.

These drive the real app through Textual's test pilot, because the rules live
in how ``GravitypeApp``'s exit paths call ``_finish_run`` - not in ``core``.

The clock is never monkeypatched: ``asyncio`` reads ``time.monotonic`` too, and
patching it out from under the event loop is a good way to hang the suite.
Instead, tests that care about elapsed time backdate ``_run_started_at``.
"""

import time

import pytest

from gravitype.core.stats import stats


async def _start(pilot, app, category="tech"):
    app.category = category
    app.start_new_game()
    await pilot.pause()


def _snap():
    return stats.snapshot()


async def test_starting_a_game_is_recorded_immediately(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)

        snap = _snap()
        assert snap["games_started"] == 1
        assert snap["games_completed"] == 0
        assert snap["categories"]["tech"]["games_started"] == 1


async def test_game_over_counts_as_completed(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.level = 6
        app.end_game()
        await pilot.pause()

        snap = _snap()
        assert snap["games_started"] == 1
        assert snap["games_completed"] == 1
        assert snap["max_level"] == 6


async def test_exiting_with_ctrl_g_is_started_but_not_completed(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app, "general")
        app.level = 4
        await pilot.press("ctrl+g")
        await pilot.pause()

        snap = _snap()
        assert snap["games_started"] == 1
        assert snap["games_completed"] == 0
        # The level reached still counts - it was genuinely played.
        assert snap["max_level"] == 4
        assert snap["categories"]["general"]["max_level"] == 4


async def test_quitting_mid_run_still_records_the_run(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.level = 9
        await pilot.press("ctrl+q")
        await pilot.pause()

    snap = _snap()
    assert snap["games_started"] == 1
    assert snap["games_completed"] == 0
    assert snap["max_level"] == 9


async def test_play_again_closes_out_the_previous_run(app):
    """PLAY AGAIN from the game-over screen starts a second run, not a third."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.level = 5
        app.end_game()
        await pilot.pause()

        app.start_new_game()
        await pilot.pause()
        app.level = 8
        app.end_game()
        await pilot.pause()

        snap = _snap()
        assert snap["games_started"] == 2
        assert snap["games_completed"] == 2
        assert snap["max_level"] == 8


async def test_main_menu_after_game_over_does_not_double_count(app):
    """The run is already recorded; returning to the menu must be a no-op."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.end_game()
        await pilot.pause()
        app.show_menu()
        await pilot.pause()

        snap = _snap()
        assert snap["games_started"] == 1
        assert snap["games_completed"] == 1


async def test_finish_run_is_idempotent(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)

        app._finish_run(completed=True)
        app._finish_run(completed=True)
        app._finish_run(completed=False)
        await pilot.pause()

        assert _snap()["games_completed"] == 1


async def test_time_outside_a_run_is_not_recorded(app):
    """Sitting on the menu is not play time."""
    async with app.run_test() as pilot:
        await pilot.pause()
        app._finish_run(completed=False)
        await pilot.pause()

        assert _snap() == stats.snapshot()
        assert _snap()["games_started"] == 0
        assert _snap()["total_play_seconds"] == 0.0


async def test_elapsed_time_is_banked_on_finish(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)

        app._run_started_at = time.monotonic() - 10.0
        app.end_game()
        await pilot.pause()

        assert 10.0 <= _snap()["total_play_seconds"] < 11.0


async def test_paused_time_is_excluded(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)

        # Five seconds of play, then pause.
        app._run_started_at = time.monotonic() - 5.0
        await pilot.press("escape")
        await pilot.pause()
        banked = app._run_active_seconds
        assert 5.0 <= banked < 6.0

        # Time passes while paused; none of it should count.
        await pilot.pause()
        assert app._run_active_seconds == banked
        assert app._run_started_at is None

        # Resume restarts the clock from now, not from the pause point.
        await pilot.press("escape")
        await pilot.pause()
        assert app._run_started_at is not None

        app.end_game()
        await pilot.pause()
        assert banked <= _snap()["total_play_seconds"] < banked + 1.0


async def test_pause_toggles_are_ignored_once_the_run_is_recorded(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.end_game()
        await pilot.pause()

        banked = app._run_active_seconds
        app.set_run_paused(True)
        app.set_run_paused(False)

        assert app._run_active_seconds == banked
        assert app._run_started_at is None


async def test_a_new_run_starts_from_a_clean_clock(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app._run_started_at = time.monotonic() - 30.0
        app.end_game()
        await pilot.pause()

        await _start(pilot, app)
        assert app._run_active_seconds == 0.0
        assert app._run_started_at is not None


@pytest.mark.parametrize("category", ["tech", "general"])
async def test_per_category_totals_track_the_category_played(app, category):
    other = "general" if category == "tech" else "tech"

    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app, category)
        app.level = 7
        app.end_game()
        await pilot.pause()

        snap = _snap()
        assert snap["categories"][category]["games_completed"] == 1
        assert snap["categories"][category]["max_level"] == 7
        assert snap["categories"][other]["games_started"] == 0
        assert snap["categories"][other]["max_level"] == 0


async def test_stats_survive_across_app_instances(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.level = 11
        app.end_game()
        await pilot.pause()

    from gravitype.tui.app import GravitypeApp

    second = GravitypeApp()
    async with second.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, second)
        await pilot.press("ctrl+q")

    snap = _snap()
    assert snap["games_started"] == 2
    assert snap["games_completed"] == 1
    assert snap["max_level"] == 11


# --- winning ---


def _win_threshold():
    from gravitype.tui.app import POINTS_PER_LEVEL, WIN_LEVEL

    return (WIN_LEVEL - 1) * POINTS_PER_LEVEL


async def test_a_win_records_as_a_completed_game(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.score = _win_threshold()
        app.end_game(won=True)
        await pilot.pause()

        snap = _snap()
        assert snap["games_started"] == 1
        assert snap["games_completed"] == 1
        assert app.is_win is True


async def test_a_win_updates_the_high_score(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.high_score = 100
        await _start(pilot, app)
        app.score = _win_threshold()
        app.end_game(won=True)
        await pilot.pause()

        assert app.is_new_high_score is True
        assert app.high_score == _win_threshold()


async def test_a_win_and_a_loss_record_only_one_run(app):
    """A match and a miss can land close enough together to both end the run."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)

        app.end_game(won=True)
        app.end_game(won=False)
        await pilot.pause()

        assert _snap()["games_completed"] == 1
        # The first outcome stands; the second call is a no-op.
        assert app.is_win is True


async def test_a_loss_after_a_win_does_not_flip_the_outcome(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await _start(pilot, app)
        app.end_game(won=True)
        await pilot.pause()

        # The loss path fires on the next missed word.
        app.end_game()
        await pilot.pause()

        assert app.is_win is True


async def test_ending_a_run_that_never_started_is_a_no_op(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        app.end_game(won=True)
        await pilot.pause()

        assert _snap()["games_completed"] == 0
