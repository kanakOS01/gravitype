import json
from pathlib import Path

from gravitype.core.paths import (
    config_file,
    ensure_writable_dir,
    generated_css_file,
    legacy_config_file,
)

DEFAULT_CONFIG = {
    "high_score": 0,
    "theme": "dracula",
    "sound_enabled": True,
    "starting_lives": 3,
}


def _coerce(key, value):
    """Cast a loaded value to the type of its default."""
    if isinstance(DEFAULT_CONFIG[key], bool):
        return bool(value)
    if isinstance(DEFAULT_CONFIG[key], int):
        return int(value)
    return str(value)


class Config:
    def __init__(self):
        self.config_path = config_file()
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        source = self.config_path
        if not source.exists():
            # Fall back to the pre-0.3 dotfile so upgrading keeps your
            # high score and settings instead of silently resetting them.
            legacy = legacy_config_file()
            source = legacy if legacy.exists() else None

        if source is None:
            self.save()
            return

        try:
            with open(source, "r") as f:
                user_data = json.load(f)
        except (OSError, ValueError):
            self.config = DEFAULT_CONFIG.copy()
            return

        for k, v in user_data.items():
            if k in DEFAULT_CONFIG:
                try:
                    self.config[k] = _coerce(k, v)
                except (TypeError, ValueError):
                    pass

        if source != self.config_path:
            # Migrate the legacy file forward. The original is left in
            # place so a downgrade still finds it.
            self.save()

    def save(self):
        try:
            path = ensure_writable_dir(self.config_path)
            self.config_path = path
            with open(path, "w") as f:
                json.dump(self.config, f, indent=4)
        except OSError:
            # Persistence is best-effort; the game stays playable without it.
            pass

    def get(self, key, default=None):
        return self.config.get(
            key, default if default is not None else DEFAULT_CONFIG.get(key)
        )

    def set(self, key, value):
        if key in DEFAULT_CONFIG:
            try:
                self.config[key] = _coerce(key, value)
            except (TypeError, ValueError):
                return
            self.save()


config = Config()


def generate_theme_file(theme_name: str) -> Path:
    """Compile the selected theme plus the base styles into one stylesheet.

    Written outside the package so an installed, read-only copy still works.
    Returns the path written, which the app passes to Textual as its CSS.
    """
    styles_dir = Path(__file__).parent.parent / "tui" / "styles"
    themes_dir = styles_dir / "themes"

    theme_path = themes_dir / f"{theme_name}.tcss"
    if not theme_path.exists():
        theme_name = "dracula"
        theme_path = themes_dir / "dracula.tcss"

    base_path = styles_dir / "base.tcss"
    active_path = ensure_writable_dir(generated_css_file())

    theme_css = theme_path.read_text() if theme_path.exists() else ""
    base_css = base_path.read_text() if base_path.exists() else ""

    with open(active_path, "w") as f:
        f.write(f"/* Automatically generated active theme: {theme_name} */\n")
        f.write(theme_css)
        f.write("\n")
        f.write(base_css)

    return active_path
