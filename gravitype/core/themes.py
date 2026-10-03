"""The theme catalogue: which palettes exist, in which appearance.

A *family* is a palette identity ("Dracula"), and each family has one
stylesheet per mode. ``config["theme"]`` stores the family id, so flipping
between dark and light keeps you in the palette you chose.

Family ids are deliberately mode-free, which is why the two stored values
that used to carry a mode in their name are migrated by
``LEGACY_THEME_ALIASES``. The stylesheet *filenames* keep whatever they
have always been called, so no file on disk had to be renamed.
"""

#: ``family id -> (label, dark stylesheet, light stylesheet)``, in the order
#: the Settings dropdown lists them.
THEME_FAMILIES = {
    "dracula": ("Dracula", "dracula", "dracula_light"),
    "nord": ("Nord", "nord", "nord_light"),
    "tokyonight": ("Tokyo Night", "tokyonight", "tokyonight_light"),
    "gruvbox": ("Gruvbox", "gruvbox_dark", "gruvbox_light"),
    "catppuccin": ("Catppuccin", "catppuccin", "catppuccin_latte"),
    "cyberspace": ("Cyberspace", "cyberspace", "cyberspace_light"),
    "80s_after_dark": ("80s After Dark", "80s_after_dark", "80s_after_dark_light"),
    "solarized": ("Solarized", "solarized_dark", "solarized_light"),
}

#: Pre-1.2 configs stored a stylesheet name where a family id now goes. Only
#: the two that named their own mode actually differ.
LEGACY_THEME_ALIASES = {
    "gruvbox_dark": "gruvbox",
    "solarized_dark": "solarized",
}

MODES = ("dark", "light")

DEFAULT_FAMILY = "dracula"
DEFAULT_MODE = "dark"


def family_options():
    """``(label, family id)`` pairs for the Settings dropdown."""
    return [(label, family) for family, (label, _, _) in THEME_FAMILIES.items()]


def normalize_family(family) -> str:
    """Map a stored ``theme`` value onto a known family id."""
    family = LEGACY_THEME_ALIASES.get(family, family)
    return family if family in THEME_FAMILIES else DEFAULT_FAMILY


def normalize_mode(mode) -> str:
    return mode if mode in MODES else DEFAULT_MODE


def other_mode(mode) -> str:
    """The mode ``ctrl+l`` flips to."""
    return "dark" if normalize_mode(mode) == "light" else "light"


def resolve(family, mode) -> str:
    """The stylesheet name for a family in a given mode.

    Both arguments are normalised first, so an unknown or hand-edited config
    lands on the default palette rather than on a missing file.
    """
    label_dark_light = THEME_FAMILIES[normalize_family(family)]
    return (
        label_dark_light[1] if normalize_mode(mode) == "dark" else label_dark_light[2]
    )
