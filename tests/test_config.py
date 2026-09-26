"""Settings persistence, coercion and the pre-0.3 migration path."""

import json

import pytest

from gravitype.core.config import (
    DEFAULT_CONFIG,
    Config,
    generate_theme_file,
)
from gravitype.core.paths import config_file, legacy_config_file


def test_fresh_install_writes_defaults(isolated_home):
    cfg = Config()

    assert cfg.config == DEFAULT_CONFIG
    assert json.loads((isolated_home / "config.json").read_text()) == DEFAULT_CONFIG


def test_roundtrips_through_disk(isolated_home):
    Config().set("high_score", 4321)

    assert Config().get("high_score") == 4321


@pytest.mark.parametrize(
    "key, written, expected",
    [
        ("high_score", "1500", 1500),
        ("high_score", 12.9, 12),
        ("starting_lives", "8", 8),
        ("sound_enabled", 0, False),
        ("sound_enabled", "anything-truthy", True),
        ("theme", 42, "42"),
    ],
)
def test_values_are_coerced_to_the_default_type(isolated_home, key, written, expected):
    config_file().write_text(json.dumps({key: written}))

    assert Config().get(key) == expected


def test_unknown_keys_are_dropped(isolated_home):
    config_file().write_text(json.dumps({"high_score": 10, "not_a_setting": "x"}))

    cfg = Config()
    assert cfg.get("high_score") == 10
    assert "not_a_setting" not in cfg.config


def test_set_ignores_unknown_keys(isolated_home):
    cfg = Config()
    cfg.set("not_a_setting", "x")

    assert "not_a_setting" not in cfg.config


def test_uncoercible_value_keeps_the_default(isolated_home):
    config_file().write_text(json.dumps({"high_score": "not-a-number"}))

    assert Config().get("high_score") == DEFAULT_CONFIG["high_score"]


def test_corrupt_file_falls_back_to_defaults(isolated_home):
    config_file().parent.mkdir(parents=True, exist_ok=True)
    config_file().write_text("{ this is not json")

    assert Config().config == DEFAULT_CONFIG


def test_legacy_dotfile_is_migrated_forward(isolated_home, tmp_path):
    """Upgrading from pre-0.3 must not silently reset the high score."""
    # Refreshing the singletons already wrote a default config; clear it so
    # this looks like a machine that has only ever run the old version.
    config_file().unlink(missing_ok=True)

    legacy = legacy_config_file()
    legacy.write_text(json.dumps({"high_score": 910, "theme": "nord"}))

    cfg = Config()

    assert cfg.get("high_score") == 910
    assert cfg.get("theme") == "nord"
    # Migrated into the new location...
    assert json.loads(config_file().read_text())["high_score"] == 910
    # ...and the original left in place, so a downgrade still finds it.
    assert legacy.exists()


def test_new_config_wins_over_legacy_dotfile(isolated_home):
    legacy_config_file().write_text(json.dumps({"high_score": 910}))
    config_file().parent.mkdir(parents=True, exist_ok=True)
    config_file().write_text(json.dumps({"high_score": 1790}))

    assert Config().get("high_score") == 1790


def test_get_falls_back_to_the_documented_default(isolated_home):
    assert Config().get("nope") is None
    assert Config().get("nope", "fallback") == "fallback"


def test_generate_theme_file_concatenates_theme_and_base(isolated_home):
    written = generate_theme_file("nord")

    css = written.read_text()
    assert written.parent == isolated_home
    assert "nord" in css.splitlines()[0]
    # base.tcss contributes the shared rules.
    assert "Footer" in css


def test_generate_theme_file_falls_back_to_dracula(isolated_home):
    css = generate_theme_file("no-such-theme").read_text()

    assert "dracula" in css.splitlines()[0]
