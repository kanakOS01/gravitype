"""Word pools and the level-based length filter."""

import pathlib
import random

import pytest

from gravitype.core import words as words_module
from gravitype.core.paths import words_dir
from gravitype.core.words import (
    BUILTIN_CATEGORIES,
    GENERAL_WORDS,
    TECH_WORDS,
    available_categories,
    custom_sets,
    get_random_word,
    is_typeable,
    parse_word_file,
    skipped_files,
    word_pool,
)

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


# --- custom word sets ---


@pytest.fixture
def make_set(isolated_home):
    """Write a word set file and reload the registry."""

    def _make(name, text):
        directory = words_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = pathlib.Path(directory) / f"{name}.txt"
        path.write_text(text, encoding="utf-8")
        words_module.refresh()
        return path

    return _make


@pytest.fixture(autouse=True)
def _clean_registry(isolated_home):
    """Each test starts with only the built-ins loaded."""
    words_module.refresh()
    yield
    words_module.refresh()


# --- parsing ---


def test_one_entry_per_line():
    assert parse_word_file("rust\ncargo\n") == ["rust", "cargo"]


def test_blank_lines_are_dropped():
    assert parse_word_file("rust\n\n\ncargo\n\n") == ["rust", "cargo"]


def test_surrounding_whitespace_is_trimmed():
    assert parse_word_file("  rust  \n\tcargo\t\n") == ["rust", "cargo"]


def test_phrases_are_kept_whole():
    """Interior spaces are the point: a set may contain phrases."""
    assert parse_word_file("borrow checker\nthe quick brown fox\n") == [
        "borrow checker",
        "the quick brown fox",
    ]


def test_case_is_preserved():
    assert parse_word_file("Rust\nCARGO\n") == ["Rust", "CARGO"]


def test_punctuation_and_digits_are_kept():
    assert parse_word_file("don't\nutf-8\npython3\n") == ["don't", "utf-8", "python3"]


def test_non_ascii_entries_are_rejected():
    """Accented and non-Latin text cannot be typed on a plain keyboard."""
    assert parse_word_file("cafe\ncafé\nnaïve\n日本語\n") == ["cafe"]


def test_duplicates_are_removed_keeping_first_appearance():
    """A repeated entry should not become twice as likely to spawn."""
    assert parse_word_file("rust\ncargo\nrust\n") == ["rust", "cargo"]


def test_duplicates_are_case_sensitive():
    """Matching is case-sensitive, so these are three different entries."""
    assert parse_word_file("Rust\nrust\nRUST\nRust\n") == ["Rust", "rust", "RUST"]


def test_an_empty_file_yields_nothing():
    assert parse_word_file("") == []


def test_undecodable_content_is_rejected():
    """A binary file decodes to replacement chars that can never be typed."""
    assert parse_word_file("rust\n���\n") == ["rust"]


def test_control_characters_are_rejected():
    assert parse_word_file("rust\n\x00\x01\x02\n") == ["rust"]


@pytest.mark.parametrize(
    "entry, expected",
    [
        ("rust", True),
        ("borrow checker", True),
        ("Borrow Checker", True),
        ("utf-8!", True),
        ("python3", True),
        ("", False),
        ("café", False),
        ("日本語", False),
        ("�", False),
        ("a�b", False),
        ("\x07", False),
        ("a\tb", False),
    ],
)
def test_is_typeable(entry, expected):
    assert is_typeable(entry) is expected


# --- discovery ---


def test_no_words_directory_leaves_the_builtins(isolated_home):
    words_module.refresh()

    assert available_categories() == list(BUILTIN_CATEGORIES)
    assert custom_sets() == {}


def test_a_set_becomes_a_category(make_set):
    make_set("rust", "rust\ncargo\n")

    assert "rust" in available_categories()
    assert word_pool("rust") == ["rust", "cargo"]


def test_builtins_come_first_then_sets_alphabetically(make_set):
    make_set("zebra", "zebra\n")
    make_set("alpha", "alpha\n")

    assert available_categories() == ["tech", "general", "alpha", "zebra"]


def test_set_names_are_lowercased(make_set):
    make_set("Proverbs", "a stitch in time\n")

    assert "proverbs" in available_categories()
    assert word_pool("PROVERBS") == ["a stitch in time"]


def test_a_set_cannot_shadow_a_builtin(make_set):
    make_set("tech", "not-a-real-tech-word\n")

    assert word_pool("tech") is words_module.TECH_WORDS
    assert "tech.txt" in skipped_files()


def test_an_empty_set_is_skipped(make_set):
    """An empty pool would make random.choice raise at spawn time."""
    make_set("blank", "\n\n   \n")

    assert "blank" not in available_categories()
    assert "blank.txt" in skipped_files()


def test_a_binary_file_is_skipped(isolated_home):
    directory = words_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (pathlib.Path(directory) / "binary.txt").write_bytes(bytes(range(256)) * 4)
    words_module.refresh()

    assert "binary" not in available_categories()


def test_non_txt_files_are_ignored(isolated_home):
    directory = words_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (pathlib.Path(directory) / "notes.md").write_text("rust\n")
    words_module.refresh()

    assert "notes" not in available_categories()


def test_refresh_picks_up_a_new_file(make_set):
    assert "rust" not in available_categories()

    make_set("rust", "rust\n")

    assert "rust" in available_categories()


def test_refresh_drops_a_deleted_file(make_set):
    path = make_set("rust", "rust\n")
    assert "rust" in available_categories()

    path.unlink()
    words_module.refresh()

    assert "rust" not in available_categories()


def test_an_unreadable_file_is_skipped_not_raised(make_set):
    path = make_set("rust", "rust\n")
    path.chmod(0o000)
    try:
        words_module.refresh()
        assert "rust" not in available_categories()
        assert "rust.txt" in skipped_files()
    finally:
        path.chmod(0o600)


# --- drawing words from a custom set ---


def test_words_are_drawn_from_the_custom_set(make_set):
    make_set("rust", "rust\ncargo\ncrate\n")

    for level in (1, 2, 3, 5):
        for _ in range(20):
            assert get_random_word("rust", level) in {"rust", "cargo", "crate"}


def test_a_phrase_only_set_falls_back_at_low_levels(make_set):
    """Phrases are too long for the level 1-3 bands; the pool is used whole."""
    phrases = ["a rolling stone gathers no moss", "the quick brown fox"]
    make_set("proverbs", "\n".join(phrases) + "\n")

    for level in (1, 2, 3):
        assert get_random_word("proverbs", level) in phrases


def test_an_unknown_category_still_falls_back_to_tech(make_set):
    make_set("rust", "rust\n")

    assert get_random_word("no-such-set", 1) in set(TECH_WORDS)


def test_builtin_categories_are_unaffected_by_custom_sets(make_set):
    make_set("rust", "rust\n")

    assert word_pool("tech") is words_module.TECH_WORDS
    assert word_pool("general") is words_module.GENERAL_WORDS
