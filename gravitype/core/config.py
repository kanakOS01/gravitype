import json
from pathlib import Path

DEFAULT_CONFIG = {
    "high_score": 0,
    "theme": "dracula",
    "sound_enabled": True,
    "starting_lives": 3,
}


class Config:
    def __init__(self):
        self.config_path = Path(".gravitype_config.json")
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    user_data = json.load(f)
                    for k, v in user_data.items():
                        if k in DEFAULT_CONFIG:
                            # Safely cast to expected type
                            if isinstance(DEFAULT_CONFIG[k], bool):
                                self.config[k] = bool(v)
                            elif isinstance(DEFAULT_CONFIG[k], int):
                                self.config[k] = int(v)
                            else:
                                self.config[k] = str(v)
            except Exception:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.save()

    def save(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.config.get(
            key, default if default is not None else DEFAULT_CONFIG.get(key)
        )

    def set(self, key, value):
        if key in DEFAULT_CONFIG:
            if isinstance(DEFAULT_CONFIG[key], bool):
                self.config[key] = bool(value)
            elif isinstance(DEFAULT_CONFIG[key], int):
                self.config[key] = int(value)
            else:
                self.config[key] = str(value)
            self.save()


config = Config()


def generate_theme_file(theme_name: str) -> None:
    """
    Combines the selected theme variables and base styles into theme_active.tcss
    """
    pkg_dir = Path(__file__).parent.parent
    themes_dir = pkg_dir / "tui" / "styles" / "themes"
    theme_path = themes_dir / f"{theme_name}.tcss"

    if not theme_path.exists():
        theme_path = themes_dir / "dracula.tcss"
        theme_name = "dracula"

    base_path = pkg_dir / "tui" / "styles" / "base.tcss"
    active_path = pkg_dir / "tui" / "styles" / "theme_active.tcss"

    try:
        theme_css = ""
        if theme_path.exists():
            with open(theme_path, "r") as f:
                theme_css = f.read()

        base_css = ""
        if base_path.exists():
            with open(base_path, "r") as f:
                base_css = f.read()

        active_path.parent.mkdir(parents=True, exist_ok=True)
        with open(active_path, "w") as f:
            f.write(f"/* Automatically generated active theme: {theme_name} */\n")
            f.write(theme_css)
            f.write("\n")
            f.write(base_css)
    except Exception:
        pass
