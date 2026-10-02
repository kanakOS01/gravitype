"""The theme catalogue: every family resolves, in both appearances."""

import re
from pathlib import Path

import pytest

from gravitype.core.config import generate_theme_file
from gravitype.core.themes import (
    DEFAULT_FAMILY,
    LEGACY_THEME_ALIASES,
    MODES,
    THEME_FAMILIES,
    family_options,
    normalize_family,
    normalize_mode,
    other_mode,
    resolve,
)

THEMES_DIR = Path(__file__).parent.parent / "gravitype" / "tui" / "styles" / "themes"

#: Every variable base.tcss can reference. A theme missing one of these styles
#: part of the UI with nothing, which is why this is checked per file rather
#: than left to the first player who notices.
REQUIRED_VARIABLES = {
    "$bg-color",
    "$main-color",
    "$caret-color",
    "$sub-color",
    "$sub-alt-color",
    "$text-color",
    "$error-color",
    "$error-extra-color",
    "$colorful-error-color",
    "$colorful-error-extra-color",
    "$flash-hit-color",
    "$flash-miss-color",
}

ALL_VARIANTS = [(family, mode) for family in THEME_FAMILIES for mode in MODES]


def _declared_variables(path):
    return {
        line.split(":", 1)[0].strip()
        for line in path.read_text().splitlines()
        if line.strip().startswith("$") and ":" in line
    }


@pytest.mark.parametrize("family, mode", ALL_VARIANTS)
def test_every_variant_has_a_complete_stylesheet(family, mode):
    path = THEMES_DIR / f"{resolve(family, mode)}.tcss"

    assert path.exists(), f"{family} ({mode}) has no stylesheet"
    assert _declared_variables(path) == REQUIRED_VARIABLES


def test_base_stylesheet_has_no_hardcoded_colours():
    """Anything not driven by a variable ignores the chosen theme."""
    base = (THEMES_DIR.parent / "base.tcss").read_text()

    offenders = [
        line for line in base.splitlines() if re.search(r":\s*#[0-9a-fA-F]{3,8}", line)
    ]
    assert offenders == []


def test_dark_and_light_are_different_files():
    for family in THEME_FAMILIES:
        assert resolve(family, "dark") != resolve(family, "light")


def test_unknown_family_and_mode_fall_back():
    assert normalize_family("no-such-theme") == DEFAULT_FAMILY
    assert normalize_mode("sideways") == "dark"
    assert resolve("no-such-theme", "sideways") == resolve(DEFAULT_FAMILY, "dark")


def test_legacy_names_migrate_onto_the_same_palette():
    for legacy, family in LEGACY_THEME_ALIASES.items():
        assert normalize_family(legacy) == family
        # The migrated family still points at the stylesheet it used to name.
        assert resolve(family, "dark") == legacy


def test_other_mode_flips():
    assert other_mode("dark") == "light"
    assert other_mode("light") == "dark"
    # An unreadable stored value is treated as dark, so the first press lights up.
    assert other_mode("nonsense") == "light"


def test_family_options_cover_the_catalogue():
    assert [family for _, family in family_options()] == list(THEME_FAMILIES)


@pytest.mark.parametrize("family, mode", ALL_VARIANTS)
def test_generate_theme_file_compiles_every_variant(isolated_home, family, mode):
    css = generate_theme_file(family, mode).read_text()

    assert resolve(family, mode) in css.splitlines()[0]
    for variable in REQUIRED_VARIABLES:
        assert f"{variable}:" in css
