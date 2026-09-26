"""Lifetime play statistics: accumulation, durability and formatting."""

import json

import pytest

from gravitype.core.paths import stats_file
from gravitype.core.stats import (
    KNOWN_CATEGORIES,
    SCHEMA_VERSION,
    Stats,
    format_duration,
)


def test_fresh_install_starts_at_zero(isolated_home):
    snap = Stats().snapshot()

    assert snap["games_started"] == 0
    assert snap["games_completed"] == 0
    assert snap["max_level"] == 0
    assert snap["total_play_seconds"] == 0.0
    assert set(snap["categories"]) == set(KNOWN_CATEGORIES)


def test_nothing_is_written_until_something_is_recorded(isolated_home):
    Stats()

    assert not stats_file().exists()


def test_started_counts_globally_and_per_category(isolated_home):
    s = Stats()
    s.record_game_started("tech")
    s.record_game_started("tech")
    s.record_game_started("general")

    snap = s.snapshot()
    assert snap["games_started"] == 3
    assert snap["categories"]["tech"]["games_started"] == 2
    assert snap["categories"]["general"]["games_started"] == 1


def test_completed_run_counts_as_completed(isolated_home):
    s = Stats()
    s.record_game_started("tech")
    s.record_game_finished("tech", level=5, seconds=30.0, completed=True)

    snap = s.snapshot()
    assert snap["games_started"] == 1
    assert snap["games_completed"] == 1
    assert snap["categories"]["tech"]["games_completed"] == 1


def test_abandoned_run_keeps_its_level_and_time(isolated_home):
    """Bailing out must not erase what was actually played."""
    s = Stats()
    s.record_game_started("general")
    s.record_game_finished("general", level=12, seconds=45.0, completed=False)

    snap = s.snapshot()
    assert snap["games_started"] == 1
    assert snap["games_completed"] == 0
    assert snap["max_level"] == 12
    assert snap["total_play_seconds"] == 45.0


def test_max_level_is_a_high_water_mark(isolated_home):
    s = Stats()
    for level in (4, 11, 2):
        s.record_game_finished("tech", level=level, seconds=1.0, completed=True)

    assert s.snapshot()["max_level"] == 11


def test_max_level_is_tracked_separately_per_category(isolated_home):
    s = Stats()
    s.record_game_finished("tech", level=9, seconds=1.0, completed=True)
    s.record_game_finished("general", level=3, seconds=1.0, completed=True)

    snap = s.snapshot()
    assert snap["max_level"] == 9
    assert snap["categories"]["tech"]["max_level"] == 9
    assert snap["categories"]["general"]["max_level"] == 3


def test_play_time_accumulates(isolated_home):
    s = Stats()
    s.record_game_finished("tech", level=1, seconds=10.5, completed=True)
    s.record_game_finished("tech", level=1, seconds=4.5, completed=False)

    assert s.snapshot()["total_play_seconds"] == 15.0
    assert s.snapshot()["categories"]["tech"]["total_play_seconds"] == 15.0


def test_unknown_category_is_created_on_demand(isolated_home):
    """Adding a word category later must not need a migration."""
    s = Stats()
    s.record_game_started("haskell")
    s.record_game_finished("haskell", level=2, seconds=8.0, completed=True)

    entry = s.snapshot()["categories"]["haskell"]
    assert entry == {
        "games_started": 1,
        "games_completed": 1,
        "total_play_seconds": 8.0,
        "max_level": 2,
    }


def test_category_matching_is_case_insensitive(isolated_home):
    s = Stats()
    s.record_game_started("TECH")
    s.record_game_started("tech")

    assert s.snapshot()["categories"]["tech"]["games_started"] == 2


def test_negative_inputs_are_clamped(isolated_home):
    s = Stats()
    s.record_game_finished("tech", level=-5, seconds=-30.0, completed=True)

    snap = s.snapshot()
    assert snap["max_level"] == 0
    assert snap["total_play_seconds"] == 0.0


def test_survives_a_restart(isolated_home):
    first = Stats()
    first.record_game_started("tech")
    first.record_game_finished("tech", level=7, seconds=60.0, completed=True)

    reloaded = Stats().snapshot()
    assert reloaded["games_started"] == 1
    assert reloaded["max_level"] == 7
    assert reloaded["total_play_seconds"] == 60.0


def test_written_file_records_its_schema_version(isolated_home):
    s = Stats()
    s.record_game_started("tech")

    assert json.loads(stats_file().read_text())["version"] == SCHEMA_VERSION


def test_snapshot_does_not_expose_internal_state(isolated_home):
    """The screen renders the snapshot; mutating it must not corrupt totals."""
    s = Stats()
    s.record_game_started("tech")

    snap = s.snapshot()
    snap["games_started"] = 999
    snap["categories"]["tech"]["games_started"] = 999

    assert s.snapshot()["games_started"] == 1
    assert s.snapshot()["categories"]["tech"]["games_started"] == 1


def test_corrupt_file_resets_instead_of_crashing(isolated_home):
    stats_file().parent.mkdir(parents=True, exist_ok=True)
    stats_file().write_text("garbage{{{")

    assert Stats().snapshot()["games_started"] == 0


def test_non_object_file_resets(isolated_home):
    stats_file().parent.mkdir(parents=True, exist_ok=True)
    stats_file().write_text("[1, 2, 3]")

    assert Stats().snapshot()["games_started"] == 0


def test_hand_edited_file_is_sanitised(isolated_home):
    """Nonsense values fall back to defaults; good ones survive alongside."""
    stats_file().parent.mkdir(parents=True, exist_ok=True)
    stats_file().write_text(
        json.dumps(
            {
                "games_started": "not-a-number",
                "max_level": 4,
                "categories": {
                    "tech": None,
                    "custom": {"max_level": 2},
                    123: {"max_level": 5},
                },
            }
        )
    )

    snap = Stats().snapshot()
    assert snap["games_started"] == 0
    assert snap["max_level"] == 4
    # A null category is skipped, leaving the seeded default in place.
    assert snap["categories"]["tech"]["max_level"] == 0
    # A partial category is filled out with defaults.
    assert snap["categories"]["custom"] == {
        "games_started": 0,
        "games_completed": 0,
        "total_play_seconds": 0.0,
        "max_level": 2,
    }


def test_recording_still_works_when_the_home_is_read_only(isolated_home):
    """Persistence is best-effort - the game must stay playable regardless."""
    isolated_home.mkdir(parents=True, exist_ok=True)
    isolated_home.chmod(0o500)
    try:
        s = Stats()
        s.record_game_started("tech")
        s.record_game_finished("tech", level=3, seconds=5.0, completed=True)

        # In-memory totals are correct even if the write went elsewhere.
        assert s.snapshot()["games_completed"] == 1
    finally:
        isolated_home.chmod(0o700)


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0s"),
        (0.4, "0s"),
        (9, "9s"),
        (59, "59s"),
        (60, "1m 00s"),
        (65, "1m 05s"),
        (3599, "59m 59s"),
        (3600, "1h 00m 00s"),
        (3849, "1h 04m 09s"),
        (-5, "0s"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected
