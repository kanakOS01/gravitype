"""Navigation, screen wiring and the settings/stats pages."""

import pytest

from gravitype.core.config import config
from gravitype.core.stats import stats
from gravitype.tui.app import MainScreen, WelcomeScreen
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


async def test_category_buttons_set_the_app_category(app):
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.click("#cat-general")
        await pilot.pause()

        assert app.category == "general"

        await pilot.click("#cat-tech")
        await pilot.pause()
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

        assert dict(_rows(app, "stats-lifetime")) == {
            "Games Started": "0",
            "Games Completed": "0",
            "Max Level Reached": "0",
            "Total Time Played": "0s",
        }


async def test_stats_screen_reflects_play(app):
    stats.record_game_started("tech")
    stats.record_game_finished("tech", level=12, seconds=3900.0, completed=True)
    stats.record_game_started("general")
    stats.record_game_finished("general", level=4, seconds=245.0, completed=False)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("ctrl+t")
        await pilot.pause()

        assert dict(_rows(app, "stats-lifetime")) == {
            "Games Started": "2",
            "Games Completed": "1",
            "Max Level Reached": "12",
            "Total Time Played": "1h 09m 05s",
        }
        assert dict(_rows(app, "stats-categories")) == {
            "TECH": "lvl 12 · 1/1 · 1h 05m 00s",
            "GENERAL": "lvl 4 · 0/1 · 4m 05s",
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

        for table in _main(app).query(Table):
            if table.id in {"stats-lifetime", "stats-categories"}:
                continue
            assert table.title_prefix == Table.DEFAULT_TITLE_PREFIX
            assert table.key_ratio == 1
