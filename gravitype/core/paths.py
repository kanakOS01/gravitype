"""Filesystem locations Gravitype reads and writes at runtime.

Everything lives under a single directory in the user's home, which keeps
the layout predictable and easy to document. Nothing is ever written
inside the installed package: site-packages may be read-only, and writing
there would leak one user's state into every other user on the machine.
"""

import os
import tempfile
from pathlib import Path

APP_NAME = "gravitype"

#: Set this to relocate the whole directory - useful for tests and for
#: running several configurations side by side.
HOME_ENV_VAR = "GRAVITYPE_HOME"

LEGACY_CONFIG_NAME = ".gravitype_config.json"


def app_home() -> Path:
    """The directory holding all of Gravitype's runtime state."""
    override = os.environ.get(HOME_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / f".{APP_NAME}"


def config_file() -> Path:
    """Path to the persisted settings file (high score, theme, lives)."""
    return app_home() / "config.json"


def generated_css_file() -> Path:
    """Path to the compiled active stylesheet.

    Derived output: deleting it only costs a regeneration on next launch.
    """
    return app_home() / "theme_active.tcss"


def legacy_config_file() -> Path:
    """Pre-0.3 config location: a dotfile in the working directory."""
    return Path.cwd() / LEGACY_CONFIG_NAME


def ensure_writable_dir(path: Path) -> Path:
    """Create ``path``'s parent directory, falling back to the temp dir.

    Returns the path that is actually safe to write to, which may differ
    from the one requested if the preferred location is not writable.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = Path(tempfile.gettempdir()) / APP_NAME
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / path.name
