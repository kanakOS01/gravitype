"""Lifetime play statistics.

Kept in its own file rather than alongside the settings in ``config.json``:
the config is a flat map of scalars with a fixed set of keys, while stats are
nested per category and grow as new categories appear. Mixing the two would
mean one schema serving two very different jobs.

Like the config, persistence is best-effort - a missing, unreadable or
corrupt file resets the counters instead of stopping you from playing.
"""

import json

from gravitype.core.paths import ensure_writable_dir, stats_file

#: Bumped if the on-disk shape ever changes, so a future version can migrate
#: rather than guess what it is looking at.
SCHEMA_VERSION = 1

#: Categories seeded into a fresh file. Others are added on first play, so a
#: new word category needs no migration.
KNOWN_CATEGORIES = ("tech", "general")

_COUNTERS = ("games_started", "games_completed", "max_level")


def _new_category() -> dict:
    return {
        "games_started": 0,
        "games_completed": 0,
        "total_play_seconds": 0.0,
        "max_level": 0,
    }


def _default_stats() -> dict:
    return {
        "version": SCHEMA_VERSION,
        "games_started": 0,
        "games_completed": 0,
        "total_play_seconds": 0.0,
        "max_level": 0,
        "categories": {c: _new_category() for c in KNOWN_CATEGORIES},
    }


def format_duration(seconds: float) -> str:
    """Render a duration as ``1h 04m 09s``, dropping empty leading units."""
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)

    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


class Stats:
    def __init__(self):
        self.stats_path = stats_file()
        self.stats = _default_stats()
        self.load()

    def load(self):
        if not self.stats_path.exists():
            return

        try:
            with open(self.stats_path, "r") as f:
                data = json.load(f)
        except (OSError, ValueError):
            self.stats = _default_stats()
            return

        if not isinstance(data, dict):
            self.stats = _default_stats()
            return

        self.stats = self._sanitise(data)

    def _sanitise(self, data: dict) -> dict:
        """Merge a loaded file onto the defaults, dropping anything odd.

        Hand-edited files and files written by a future version both land
        here, so every value is coerced rather than trusted.
        """
        clean = _default_stats()

        for key in _COUNTERS:
            clean[key] = _as_int(data.get(key), clean[key])
        clean["total_play_seconds"] = _as_float(
            data.get("total_play_seconds"), clean["total_play_seconds"]
        )

        categories = data.get("categories")
        if isinstance(categories, dict):
            for name, values in categories.items():
                if not isinstance(name, str) or not isinstance(values, dict):
                    continue
                entry = _new_category()
                for key in _COUNTERS:
                    entry[key] = _as_int(values.get(key), entry[key])
                entry["total_play_seconds"] = _as_float(
                    values.get("total_play_seconds"), entry["total_play_seconds"]
                )
                clean["categories"][name] = entry

        return clean

    def save(self):
        try:
            path = ensure_writable_dir(self.stats_path)
            self.stats_path = path
            with open(path, "w") as f:
                json.dump(self.stats, f, indent=4)
        except OSError:
            # Persistence is best-effort; the game stays playable without it.
            pass

    def _category(self, category: str) -> dict:
        name = (category or "tech").lower()
        return self.stats["categories"].setdefault(name, _new_category())

    def record_game_started(self, category: str) -> None:
        """Count a run that has just begun, whether or not it is finished."""
        entry = self._category(category)
        self.stats["games_started"] += 1
        entry["games_started"] += 1
        self.save()

    def record_game_finished(
        self, category: str, level: int, seconds: float, completed: bool
    ) -> None:
        """Fold a finished run into the totals.

        ``completed`` is only true when the run was played out to GAME OVER;
        a run abandoned with ctrl+g still contributes its level and its time,
        so nothing a player actually did disappears from the page.
        """
        entry = self._category(category)

        if completed:
            self.stats["games_completed"] += 1
            entry["games_completed"] += 1

        level = max(0, int(level))
        self.stats["max_level"] = max(self.stats["max_level"], level)
        entry["max_level"] = max(entry["max_level"], level)

        seconds = max(0.0, float(seconds))
        self.stats["total_play_seconds"] += seconds
        entry["total_play_seconds"] += seconds

        self.save()

    def snapshot(self) -> dict:
        """A read-only copy for the stats screen to render."""
        return {
            "games_started": self.stats["games_started"],
            "games_completed": self.stats["games_completed"],
            "total_play_seconds": self.stats["total_play_seconds"],
            "max_level": self.stats["max_level"],
            "categories": {
                name: dict(values) for name, values in self.stats["categories"].items()
            },
        }


def _as_int(value, fallback: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return fallback


def _as_float(value, fallback: float) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return fallback


stats = Stats()
