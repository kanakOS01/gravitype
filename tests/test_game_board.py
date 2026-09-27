"""Board mechanics: difficulty curve, matching and misses."""

import pytest

from gravitype.tui.widgets.game_board import GameBoard


@pytest.fixture
async def board(app):
    """A mounted board on the live game screen."""
    async with app.run_test() as pilot:
        await pilot.pause()
        app.start_new_game()
        await pilot.pause()
        yield app.screen.query_one(GameBoard), pilot


# --- difficulty curve (pure, no mounting needed) ---


@pytest.mark.parametrize("level", range(1, 40))
def test_intervals_never_fall_below_their_floor(level):
    move, spawn = GameBoard.get_ticks_for_level(None, level)

    assert move >= 2
    assert spawn >= 10


@pytest.mark.parametrize("level", range(1, 30))
def test_difficulty_is_monotonic(level):
    """Each level must be at least as hard as the one before it."""
    move, spawn = GameBoard.get_ticks_for_level(None, level)
    next_move, next_spawn = GameBoard.get_ticks_for_level(None, level + 1)

    assert next_move <= move
    assert next_spawn <= spawn


def test_level_one_is_the_gentlest():
    move, spawn = GameBoard.get_ticks_for_level(None, 1)

    assert move == 8
    assert spawn == 40


def test_difficulty_eventually_plateaus():
    assert GameBoard.get_ticks_for_level(None, 100) == (2, 10)


@pytest.mark.parametrize("level", [0, -5])
def test_out_of_range_levels_are_clamped_to_one(level):
    assert GameBoard.get_ticks_for_level(None, level) == (
        GameBoard.get_ticks_for_level(None, 1)
    )


# --- matching ---


async def test_typing_a_word_removes_it_and_scores_by_length(board):
    board, pilot = board
    board.spawn_word("python")
    await pilot.pause()

    assert board.check_match("python") == 60
    assert board.active_words == []


async def test_no_match_scores_nothing_and_removes_nothing(board):
    board, pilot = board
    board.spawn_word("python")
    await pilot.pause()

    assert board.check_match("rust") == 0
    assert len(board.active_words) == 1


async def test_partial_word_does_not_match(board):
    board, pilot = board
    board.spawn_word("python")
    await pilot.pause()

    assert board.check_match("pyth") == 0


async def test_surrounding_whitespace_is_ignored(board):
    board, pilot = board
    board.spawn_word("rust")
    await pilot.pause()

    assert board.check_match("  rust  ") == 40


async def test_duplicate_words_resolve_to_the_lowest_one(board):
    """The most urgent copy - the one nearest the floor - should go first."""
    board, pilot = board
    board.spawn_word("rust")
    board.spawn_word("rust")
    await pilot.pause()

    board.active_words[0].y = 2
    board.active_words[1].y = 9
    lowest = board.active_words[1]

    board.check_match("rust")

    assert lowest not in board.active_words
    assert len(board.active_words) == 1


async def test_matching_leaves_floating_feedback(board):
    board, pilot = board
    board.spawn_word("git")
    await pilot.pause()

    board.check_match("git")

    assert [w.text for w in board.floating_scores] == ["+30"]


# --- misses ---


async def test_word_reaching_the_bottom_costs_a_life(board):
    """Asserted through the app's lives rather than by intercepting
    ``post_message`` - that is Textual's own message pump, and replacing it
    deadlocks the widget."""
    board, pilot = board
    app = board.app
    lives_before = app.lives

    board.spawn_word("docker")
    await pilot.pause()
    word = board.active_words[0]
    word.y = (board.size.height or 20) - 1
    word.ticks_since_move = word.move_ticks

    board.game_tick()
    await pilot.pause()

    assert board.active_words == []
    assert app.lives == lives_before - 1


async def test_losing_the_last_life_ends_the_game(board):
    board, pilot = board
    app = board.app
    app.lives = 1

    board.spawn_word("docker")
    await pilot.pause()
    word = board.active_words[0]
    word.y = (board.size.height or 20) - 1
    word.ticks_since_move = word.move_ticks

    board.game_tick()
    await pilot.pause()

    assert app.lives == 0
    assert app.screen.__class__.__name__ == "GameOverScreen"


async def test_a_paused_board_does_not_advance(board):
    board, pilot = board
    board.spawn_word("docker")
    await pilot.pause()
    word = board.active_words[0]
    before = word.y

    board.is_paused = True
    for _ in range(50):
        board.game_tick()

    assert word.y == before
    assert len(board.active_words) == 1


# --- board reset ---


async def test_clearing_the_board_removes_everything(board):
    board, pilot = board
    board.spawn_word("redis")
    board.spawn_word("nosql")
    await pilot.pause()
    board.check_match("redis")
    board.is_paused = True

    board.clear_board()

    assert board.active_words == []
    assert board.floating_scores == []
    assert board.ticks_count == 0
    assert board.is_paused is False


async def test_spawned_words_stay_inside_the_board(board):
    board, pilot = board
    width = board.size.width or 80

    for _ in range(40):
        board.spawn_word("mongodb")
    await pilot.pause()

    for word in board.active_words:
        assert word.x >= 2
        assert word.x + len(word.text) <= width


# --- long text placement (phrase support) ---


@pytest.mark.parametrize("length", [10, 40, 80, 95, 97, 98, 120, 300])
async def test_long_text_places_without_raising(board, length):
    """Regression: max_x collapsed to 1 and randint(2, 1) raised ValueError.

    Reachable with phrases, which are far longer than any built-in word.
    """
    board, pilot = board
    text = "x" * length

    board.spawn_word(text)
    await pilot.pause()

    assert board.active_words[-1].text == text


async def test_text_wider_than_the_board_is_pinned_to_the_left(board):
    board, pilot = board
    board.spawn_word("x" * (board.size.width + 50))
    await pilot.pause()

    assert board.active_words[-1].x == 0


async def test_placement_still_insets_when_there_is_room(board):
    board, pilot = board
    for _ in range(20):
        board.spawn_word("rust")
    await pilot.pause()

    assert all(word.x >= board.MIN_X for word in board.active_words)


# --- phrases and case ---


async def test_a_phrase_matches_when_typed_in_full(board):
    board, pilot = board
    board.spawn_word("borrow checker")
    await pilot.pause()

    assert board.check_match("borrow checker") == 140
    assert board.active_words == []


async def test_a_phrase_does_not_match_on_its_first_word(board):
    board, pilot = board
    board.spawn_word("borrow checker")
    await pilot.pause()

    assert board.check_match("borrow") == 0
    assert len(board.active_words) == 1


async def test_matching_is_case_sensitive(board):
    """A set written with capitals has to be typed with them."""
    board, pilot = board
    board.spawn_word("Borrow Checker")
    await pilot.pause()

    assert board.check_match("borrow checker") == 0
    assert len(board.active_words) == 1

    assert board.check_match("Borrow Checker") > 0
    assert board.active_words == []


async def test_interior_spaces_are_significant(board):
    board, pilot = board
    board.spawn_word("borrow checker")
    await pilot.pause()

    assert board.check_match("borrowchecker") == 0


# --- the win level is tied to the difficulty curve ---


def test_win_level_sits_at_the_difficulty_plateau():
    """WIN_LEVEL must be where get_ticks_for_level stops changing.

    The cap exists because the game stops getting harder, not because 27 is a
    nice number. If the decay curve is retuned this fails and says so, rather
    than letting the game quietly end early or run on unchanged.
    """
    from gravitype.tui.app import WIN_LEVEL

    at_cap = GameBoard.get_ticks_for_level(None, WIN_LEVEL)

    # Nothing changes after the cap...
    assert at_cap == GameBoard.get_ticks_for_level(None, WIN_LEVEL + 50)
    assert at_cap == GameBoard.get_ticks_for_level(None, WIN_LEVEL + 1000)

    # ...and the level before it is still getting harder, so the cap is not
    # sitting further out than it needs to be.
    assert GameBoard.get_ticks_for_level(None, WIN_LEVEL - 1) != at_cap


def test_difficulty_is_maxed_out_at_the_win_level():
    from gravitype.tui.app import WIN_LEVEL

    move, spawn = GameBoard.get_ticks_for_level(None, WIN_LEVEL)

    assert (move, spawn) == (2, 10)
