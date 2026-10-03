"""Navigation, screen wiring and the settings/stats pages."""

import pytest

from gravitype.core.config import config
from gravitype.core.stats import stats
from gravitype.core.themes import resolve
from gravitype.tui.app import GameOverScreen, GameScreen, MainScreen, WelcomeScreen
from gravitype.tui.widgets.main_header import MainHeader, NavItem
from gravitype.tui.widgets.screens import StatsScreen
from gravitype.tui.widgets.table import Table

NAV = {
    "ctrl+p": "welcome",
    "ctrl+t": "stats",
    "ctrl+s": "settings",
    "ctrl+h": "help",
    "ctrl+a": "about",
}


def _main(app):
    return next(s for s in app.screen_stack if isinstance(s, MainScreen))


def _current(app):
    from textual.widgets import ContentSwitcher

    return _main(app).query_one(ContentSwitcher).current


# --- navigation ---


async def test_starts_on_the_welcome_screen(app):
    async with app.run_test() as pilot:
        await pilot.pause()

        assert _current(app) == "welcome"


@pytest.mark.parametrize("key, expected", sorted(NAV.items()))
async def test_keybinds_switch_screens(app, key, expected):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(key)
        await pilot.pause()

        assert _current(app) == expected


async def test_escape_returns_to_play(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+a")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert _current(app) == "welcome"


async def test_every_nav_item_has_a_screen_behind_it(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        main = _main(app)

        for item in main.query(NavItem):
            main.switch_to_screen(item.screen_name)
            await pilot.pause()
            assert _current(app) == item.screen_name


async def test_the_active_nav_item_follows_the_current_screen(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        active = [
            i.screen_name for i in _main(app).query(NavItem) if i.has_class("active")
        ]
        assert active == ["stats"]


async def test_nav_includes_stats(app):
    async with app.run_test() as pilot:
        await pilot.pause()

        names = [
            i.screen_name for i in _main(app).query(MainHeader).first().query(NavItem)
        ]
        assert names == ["welcome", "stats", "settings", "help", "about"]


# --- welcome screen ---


async def test_the_dropdown_sets_the_app_category(app):
    async with app.run_test() as pilot:
        await pilot.pause()

        await _choose_category(pilot, app, "general")
        assert app.category == "general"

        await _choose_category(pilot, app, "tech")
        assert app.category == "tech"


async def test_high_score_is_shown_from_config(app):
    config.set("high_score", 1234)

    async with app.run_test() as pilot:
        await pilot.pause()
        _main(app).query_one(WelcomeScreen).update_high_score()
        await pilot.pause()

        label = _main(app).query_one("#high-score-label")
        assert "1234" in label.content


async def test_beating_the_high_score_persists_it(app):
    config.set("high_score", 100)

    async with app.run_test() as pilot:
        await pilot.pause()
        app.high_score = 100
        app.start_new_game()
        await pilot.pause()
        app.score = 555
        app.end_game()
        await pilot.pause()

        assert app.is_new_high_score is True
        assert config.get("high_score") == 555


async def test_a_lower_score_leaves_the_high_score_alone(app):
    config.set("high_score", 900)

    async with app.run_test() as pilot:
        await pilot.pause()
        app.high_score = 900
        app.start_new_game()
        await pilot.pause()
        app.score = 100
        app.end_game()
        await pilot.pause()

        assert app.is_new_high_score is False
        assert config.get("high_score") == 900


# --- settings ---


async def test_changing_lives_updates_config_and_the_app(app):
    from textual.widgets import Select

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

        _main(app).query_one("#select-lives", Select).value = "8"
        await pilot.pause()

        assert config.get("starting_lives") == 8
        assert app.lives == 8


async def test_changing_theme_regenerates_the_stylesheet(app, isolated_home):
    from textual.widgets import Select

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

        _main(app).query_one("#select-theme", Select).value = "nord"
        await pilot.pause()

        assert config.get("theme") == "nord"
        assert (
            "nord" in (isolated_home / "theme_active.tcss").read_text().splitlines()[0]
        )


@pytest.mark.parametrize("key", ["ctrl+n", "ctrl+enter"])
async def test_quick_play_starts_a_run_from_the_menu(app, key):
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press(key)
        await pilot.pause()

        assert isinstance(app.screen, GameScreen)


async def test_quick_play_works_from_a_non_play_page(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        await pilot.press("ctrl+n")
        await pilot.pause()

        assert isinstance(app.screen, GameScreen)


async def test_quick_play_keeps_the_chosen_category(app):
    from textual.widgets import Select

    async with app.run_test() as pilot:
        await pilot.pause()
        _main(app).query_one("#category-select", Select).value = "general"
        await pilot.pause()

        await pilot.press("ctrl+n")
        await pilot.pause()

        assert app.category == "general"


async def test_quick_play_leaves_a_run_in_progress_alone(app):
    """The shortcut skips the menu; it does not discard the game you are in."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+n")
        await pilot.pause()
        app.score = 420

        await pilot.press("ctrl+n")
        await pilot.pause()

        assert app.score == 420


async def test_quick_play_restarts_from_the_results_screen(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+n")
        await pilot.pause()
        app.end_game(won=False)
        await pilot.pause()
        assert isinstance(app.screen, GameOverScreen)

        await pilot.press("ctrl+n")
        await pilot.pause()

        assert isinstance(app.screen, GameScreen)
        assert app.score == 0


async def test_ctrl_l_flips_the_appearance_and_repaints(app, isolated_home):
    async with app.run_test() as pilot:
        await pilot.pause()
        assert config.get("mode") == "dark"

        await pilot.press("ctrl+l")
        await pilot.pause()

        assert config.get("mode") == "light"
        active = (isolated_home / "theme_active.tcss").read_text()
        assert resolve(config.get("theme"), "light") in active.splitlines()[0]

        await pilot.press("ctrl+l")
        await pilot.pause()

        assert config.get("mode") == "dark"


async def test_ctrl_l_works_mid_run_despite_the_focused_input(app):
    """The game Input binds plenty of ctrl keys; this one has to win."""
    async with app.run_test() as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()

        await pilot.press("ctrl+l")
        await pilot.pause()

        assert config.get("mode") == "light"


async def test_appearance_select_keeps_the_chosen_theme(app, isolated_home):
    from textual.widgets import Select

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

        _main(app).query_one("#select-theme", Select).value = "gruvbox"
        await pilot.pause()
        _main(app).query_one("#select-mode", Select).value = "light"
        await pilot.pause()

        # Switching appearance stays inside the palette the player picked.
        assert config.get("theme") == "gruvbox"
        assert config.get("mode") == "light"
        active = (isolated_home / "theme_active.tcss").read_text()
        assert "gruvbox_light" in active.splitlines()[0]


async def test_toggling_mode_syncs_the_settings_dropdown(app):
    from textual.widgets import Select

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

        await pilot.press("ctrl+l")
        await pilot.pause()

        assert _main(app).query_one("#select-mode", Select).value == "light"


async def test_sound_toggle_persists(app):
    from textual.widgets import Select

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

        _main(app).query_one("#select-sound", Select).value = "off"
        await pilot.pause()

        assert config.get("sound_enabled") is False


# --- stats screen ---


def _rows(app, table_id):
    return _main(app).query_one(StatsScreen).query_one(f"#{table_id}", Table).keys


async def test_stats_screen_starts_empty(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        rows = dict(_rows(app, "stats-lifetime"))
        assert rows["Games Started"] == "0"
        assert rows["Games Completed"] == "0"
        assert rows["Max Level Reached"] == "0"
        assert rows["Total Time Played"] == "0s"


async def test_stats_screen_reflects_play(app):
    stats.record_game_started("tech")
    stats.record_game_finished("tech", level=12, seconds=3900.0, completed=True)
    stats.record_game_started("general")
    stats.record_game_finished("general", level=4, seconds=245.0, completed=False)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        rows = dict(_rows(app, "stats-lifetime"))
        assert rows["Games Started"] == "2"
        assert rows["Games Completed"] == "1"
        assert rows["Max Level Reached"] == "12"
        assert rows["Total Time Played"] == "1h 09m 05s"

        # No session was passed, so the typing columns stay empty.
        assert dict(_rows(app, "stats-categories")) == {
            "TECH": "lvl 12 · 1/1 · — · — · 1h 05m 00s",
            "GENERAL": "lvl 4 · 0/1 · — · — · 4m 05s",
        }


async def test_stats_screen_refreshes_after_a_run(app):
    """The page must not go stale between visits."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert dict(_rows(app, "stats-lifetime"))["Games Started"] == "0"

        await pilot.press("escape")
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        app.level = 3
        app.end_game()
        await pilot.pause()
        app.show_menu()
        await pilot.pause()

        await pilot.press("ctrl+t")
        await pilot.pause()

        lifetime = dict(_rows(app, "stats-lifetime"))
        assert lifetime["Games Started"] == "1"
        assert lifetime["Games Completed"] == "1"
        assert lifetime["Max Level Reached"] == "3"


async def test_help_table_is_unaffected_by_the_stats_table_options(app):
    """The stats page reuses Table; the keybind tables must look unchanged."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+h")
        await pilot.pause()

        # Targeted at the two keybind tables by title rather than by excluding
        # every other table, so adding a table elsewhere doesn't silently
        # widen what this claims to cover.
        keybind_tables = [
            table
            for table in _main(app).query(Table)
            if table.title in {"General Navigation", "Active Gameplay"}
        ]
        assert len(keybind_tables) == 2

        for table in keybind_tables:
            assert table.title_prefix == Table.DEFAULT_TITLE_PREFIX
            assert table.key_ratio == 1


# --- results screen ---


def _feed_run(app, words, seconds=0.5, errors=0):
    """Fill the session with a synthetic run, without going through the UI."""
    now = [0.0]
    app.session._clock = lambda: now[0]
    for word in words:
        app.session.start_word()
        for index, _ in enumerate(word):
            app.session.record_keystroke(index >= errors)
        now[0] += seconds
        app.session.record_hit(word)


def _screen_text(app):
    return "\n".join(
        "".join(segment.text for segment in strip)
        for strip in app.screen._compositor.render_strips()
    )


async def test_results_screen_shows_wpm_and_accuracy(app):
    from gravitype.tui.widgets.bignum import BigNumber

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        _feed_run(app, ["python"] * 4)
        app.end_game()
        await pilot.pause()

        assert app.screen.query_one("#result-wpm", BigNumber).value == "144"
        assert app.screen.query_one("#result-acc", BigNumber).value == "100"


async def test_results_screen_plots_one_point_per_word(app):
    from gravitype.tui.widgets.chart import BrailleChart

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        _feed_run(app, ["python", "rust", "docker"])
        app.end_game()
        await pilot.pause()

        assert len(app.screen.query_one(BrailleChart).series) == 3


async def test_results_screen_marks_words_with_errors(app):
    from gravitype.tui.widgets.chart import MARKER, BrailleChart

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        _feed_run(app, ["python", "rust", "docker"], errors=2)
        app.end_game()
        await pilot.pause()

        chart = app.screen.query_one(BrailleChart)
        assert chart.errors == [2, 2, 2]
        assert MARKER in chart.render().plain


async def test_results_screen_shows_the_secondary_stats(app):
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        _feed_run(app, ["python", "rust"])
        app.score, app.level = 1250, 9
        app.end_game()
        await pilot.pause()

        text = _screen_text(app)
        for heading in ("score", "level", "words hit", "time"):
            assert heading in text
        assert "01250" in text
        assert "TECH" in text


async def test_results_screen_survives_a_run_with_no_words(app):
    """Losing before typing anything must not crash or show NaN."""
    from gravitype.tui.widgets.bignum import BigNumber
    from gravitype.tui.widgets.chart import BrailleChart

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        app.end_game()
        await pilot.pause()

        assert app.screen.query_one("#result-wpm", BigNumber).value == "—"
        assert app.screen.query_one("#result-acc", BigNumber).value == "—"
        assert app.screen.query_one(BrailleChart).series == []
        assert "no words typed" in _screen_text(app)


async def test_results_screen_keeps_its_buttons(app):
    from textual.widgets import Button

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        app.end_game()
        await pilot.pause()

        ids = {button.id for button in app.screen.query(Button)}
        assert {"btn-retry", "btn-menu", "btn-quit"} <= ids


async def test_results_screen_badges_a_new_high_score(app):
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.high_score = 10
        app.start_new_game()
        await pilot.pause()
        app.score = 900
        app.end_game()
        await pilot.pause()

        assert "NEW HIGH SCORE" in _screen_text(app)


async def test_results_screen_shows_the_high_score_when_not_beaten(app):
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.high_score = 5000
        app.start_new_game()
        await pilot.pause()
        app.score = 100
        app.end_game()
        await pilot.pause()

        text = _screen_text(app)
        assert "NEW HIGH SCORE" not in text
        assert "05000" in text


async def test_chart_never_overflows_its_column(app):
    """A wrapped braille row shears the chart in half."""
    from gravitype.tui.widgets.chart import BrailleChart

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        _feed_run(app, ["kubernetes"] * 20)
        app.end_game()
        await pilot.pause()

        chart = app.screen.query_one(BrailleChart)
        width = chart.size.width
        for line in chart.render().plain.split("\n"):
            assert len(line) <= width


# --- stats page: typing figures ---


async def test_stats_page_shows_typing_figures(app):
    stats.record_game_started("tech")
    stats.record_game_finished(
        "tech", level=4, seconds=60.0, completed=True, session=_built_session()
    )

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        rows = dict(_rows(app, "stats-lifetime"))
        assert rows["Best WPM"] == "144"
        assert rows["Average WPM"] == "144"
        assert rows["Accuracy"] == "100%"
        assert rows["Words Typed"] == "2"


async def test_stats_page_dashes_when_nothing_typed(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        rows = dict(_rows(app, "stats-lifetime"))
        assert rows["Best WPM"] == "—"
        assert rows["Average WPM"] == "—"
        assert rows["Accuracy"] == "—"


def _built_session():
    from gravitype.core.session import RunSession

    now = [0.0]
    session = RunSession(clock=lambda: now[0])
    for word in ("python", "python"):
        session.start_word()
        for _ in word:
            session.record_keystroke(True)
        now[0] += 0.5
        session.record_hit(word)
    return session


# --- custom word sets in the menu ---


def _write_set(isolated_home, name, text):
    from gravitype.core.paths import words_dir

    directory = words_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _category_select(app):
    from textual.widgets import Select

    return _main(app).query_one("#category-select", Select)


def _categories(app):
    """The categories the dropdown offers, in order, as the player sees them.

    Read off the overlay's public options rather than the Select's private
    option list, and lowercased back to the category names the app uses.
    """
    from textual.widgets._select import SelectOverlay

    overlay = _category_select(app).query_one(SelectOverlay)
    return [str(option.prompt).lower() for option in overlay.options]


async def _choose_category(pilot, app, name):
    """Pick a category the way the dropdown exposes it."""
    _category_select(app).value = name
    await pilot.pause()


async def test_only_builtins_without_custom_sets(app):
    async with app.run_test() as pilot:
        await pilot.pause()

        assert _categories(app) == ["tech", "general"]


async def test_a_custom_set_appears_as_a_category(app, isolated_home):
    _write_set(isolated_home, "rust", "rust\ncargo\n")

    async with app.run_test() as pilot:
        await pilot.pause()

        assert _categories(app) == ["tech", "general", "rust"]


async def test_builtins_come_first_then_sets_alphabetically(app, isolated_home):
    _write_set(isolated_home, "zebra", "zebra\n")
    _write_set(isolated_home, "alpha", "alpha\n")

    async with app.run_test() as pilot:
        await pilot.pause()

        assert _categories(app) == ["tech", "general", "alpha", "zebra"]


async def test_selecting_a_custom_set_sets_the_category(app, isolated_home):
    _write_set(isolated_home, "rust", "rust\ncargo\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await _choose_category(pilot, app, "rust")

        assert app.category == "rust"


async def test_the_dropdown_shows_the_selected_category(app, isolated_home):
    _write_set(isolated_home, "rust", "rust\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await _choose_category(pilot, app, "rust")

        assert _category_select(app).value == "rust"


async def test_a_set_added_mid_session_appears_on_the_next_visit(app, isolated_home):
    """No restart needed - the menu re-scans on the way back."""
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "rust" not in _categories(app)

        _write_set(isolated_home, "rust", "rust\n")
        await pilot.press("ctrl+a")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert "rust" in _categories(app)


async def test_the_selection_survives_a_refresh(app, isolated_home):
    _write_set(isolated_home, "rust", "rust\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await _choose_category(pilot, app, "rust")

        await pilot.press("ctrl+a")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert app.category == "rust"
        assert _category_select(app).value == "rust"


async def test_a_deleted_set_disappears_and_selection_falls_back(app, isolated_home):
    path = _write_set(isolated_home, "rust", "rust\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await _choose_category(pilot, app, "rust")
        assert app.category == "rust"

        path.unlink()
        await pilot.press("ctrl+a")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert "rust" not in _categories(app)
        assert app.category == "tech"


async def test_a_set_named_after_a_builtin_is_not_offered_twice(app, isolated_home):
    _write_set(isolated_home, "tech", "not-a-real-word\n")

    async with app.run_test() as pilot:
        await pilot.pause()

        assert _categories(app) == ["tech", "general"]


async def test_refreshing_does_not_duplicate_options(app, isolated_home):
    """A refresh that changes nothing should leave the dropdown alone."""
    _write_set(isolated_home, "rust", "rust\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        for _ in range(3):
            await pilot.press("ctrl+a")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        assert _categories(app) == ["tech", "general", "rust"]


async def test_playing_a_custom_set_draws_from_it(app, isolated_home):
    from gravitype.tui.widgets.game_board import GameBoard

    _write_set(isolated_home, "rust", "rust\ncargo\ncrate\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await _choose_category(pilot, app, "rust")
        app.start_new_game()
        await pilot.pause()

        board = app.screen.query_one(GameBoard)
        for _ in range(15):
            board.game_tick()
        await pilot.pause()

        for word in board.active_words:
            assert word.text in {"rust", "cargo", "crate"}


# --- custom sets on the help and stats pages ---


def _help_rows(app):
    from gravitype.tui.widgets.screens import HelpScreen

    return dict(
        _main(app).query_one(HelpScreen).query_one("#help-word-sets", Table).keys
    )


async def test_help_lists_loaded_sets(app, isolated_home):
    _write_set(isolated_home, "rust", "rust\ncargo\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+h")
        await pilot.pause()

        assert _help_rows(app)["RUST"] == "2 entries"


async def test_help_explains_a_skipped_file(app, isolated_home):
    """A file that fails to load is otherwise invisible."""
    _write_set(isolated_home, "blank", "\n\n")
    _write_set(isolated_home, "tech", "nope\n")

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+h")
        await pilot.pause()

        rows = _help_rows(app)
        assert "no usable entries" in rows["blank.txt"]
        assert "reserved" in rows["tech.txt"]


async def test_help_says_so_when_there_are_no_sets(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+h")
        await pilot.pause()

        assert "none yet" in _help_rows(app)


async def test_stats_hides_a_category_whose_set_is_gone(app, isolated_home):
    path = _write_set(isolated_home, "rust", "rust\n")
    stats.record_game_started("rust")
    stats.record_game_finished("rust", level=5, seconds=60.0, completed=True)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert "RUST" in dict(_rows(app, "stats-categories"))

        path.unlink()
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        assert "RUST" not in dict(_rows(app, "stats-categories"))
        # Hidden, not erased - the history is still real.
        assert stats.snapshot()["categories"]["rust"]["max_level"] == 5
