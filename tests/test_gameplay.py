"""The typing loop: scoring, level-up, typo feedback and pause."""

from textual.widgets import Input

from gravitype.core.config import config
from gravitype.tui.widgets.game_board import GameBoard
from gravitype.tui.widgets.header import HeaderWidget


async def _in_game(app, pilot, category="tech"):
    app.category = category
    app.start_new_game()
    await pilot.pause()
    return app.screen.query_one(GameBoard), app.screen.query_one("#word-input", Input)


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
