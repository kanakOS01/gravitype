from pathlib import Path
from gravitype.core.storage import DEFAULT_CONFIG, storage


class Config:
    def __init__(self):
        self.storage = storage
        self.config_path = self.storage.config_path
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        self.config = self.storage.load_config()

    def save(self):
        self.storage.save_config(self.config)

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
