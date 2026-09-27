"""Word pools and the level-based length filter."""

import random

import pytest

from gravitype.core.words import GENERAL_WORDS, TECH_WORDS, get_random_word

POOLS = {"tech": TECH_WORDS, "general": GENERAL_WORDS}

#: The length window each level draws from, per ``get_random_word``'s docstring.
LEVEL_BOUNDS = {1: (3, 5), 2: (4, 7), 3: (5, 9), 4: (6, None), 9: (6, None)}


@pytest.mark.parametrize("name, pool", POOLS.items())
def test_pools_are_non_empty(name, pool):
    assert pool


@pytest.mark.parametrize("name, pool", POOLS.items())
def test_words_are_lowercase_and_unpunctuated(name, pool):
    """CONTRIBUTING asks for lowercase, no spaces or punctuation."""
    offenders = [w for w in pool if not w.isalpha() or w != w.lower()]

    assert offenders == []


@pytest.mark.parametrize("name, pool", POOLS.items())
def test_pools_have_no_duplicates(name, pool):
    duplicates = {w for w in pool if pool.count(w) > 1}

    assert duplicates == set()


@pytest.mark.parametrize("name, pool", POOLS.items())
def test_every_level_band_has_words_to_draw_from(name, pool):
    """If a band empties, the level silently falls back to the whole pool."""
    for level, (low, high) in LEVEL_BOUNDS.items():
        matching = [
            w for w in pool if len(w) >= low and (high is None or len(w) <= high)
        ]
        assert matching, f"{name} has no words for level {level}"


@pytest.mark.parametrize("category", ["tech", "general"])
@pytest.mark.parametrize("level", sorted(LEVEL_BOUNDS))
def test_words_respect_the_level_length_window(category, level):
    low, high = LEVEL_BOUNDS[level]

    for _ in range(200):
        word = get_random_word(category, level)
        assert len(word) >= low
        if high is not None:
            assert len(word) <= high


@pytest.mark.parametrize("category", ["tech", "general"])
def test_words_come_from_the_requested_pool(category):
    pool = set(POOLS[category])

    for level in LEVEL_BOUNDS:
        assert get_random_word(category, level) in pool


def test_category_is_case_insensitive():
    assert get_random_word("GENERAL", 1) in set(GENERAL_WORDS)


def test_unknown_category_falls_back_to_tech():
    assert get_random_word("no-such-category", 1) in set(TECH_WORDS)


def test_defaults_to_tech_level_one():
    word = get_random_word()

    assert word in set(TECH_WORDS)
    assert 3 <= len(word) <= 5


def test_level_zero_and_negative_levels_do_not_crash():
    """Levels start at 1, but nothing should explode if that ever changes."""
    for level in (0, -1):
        assert get_random_word("tech", level) in set(TECH_WORDS)


def test_seeding_makes_word_choice_reproducible():
    """Underpins GRAVITYPE_SEED, which the demo recordings rely on."""
    random.seed(7)
    first = [get_random_word("tech", 3) for _ in range(20)]

    random.seed(7)
    assert [get_random_word("tech", 3) for _ in range(20)] == first
