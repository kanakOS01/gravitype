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
SCHEMA_VERSION = 2

#: Categories seeded into a fresh file. Others are added on first play, so a
#: new word category needs no migration.
KNOWN_CATEGORIES = ("tech", "general")

_COUNTERS = (
    "games_started",
    "games_completed",
    "max_level",
    "words_hit",
    "total_keystrokes",
    "error_keystrokes",
    "wpm_samples",
)

_FLOATS = ("total_play_seconds", "best_wpm", "wpm_sum")


def _new_category() -> dict:
    return {
        "games_started": 0,
        "games_completed": 0,
        "total_play_seconds": 0.0,
        "max_level": 0,
        "words_hit": 0,
        "total_keystrokes": 0,
        "error_keystrokes": 0,
        # Sum and count rather than a running mean, so the average stays
        # weighted per word instead of per run - a three-word run should not
        # sway the figure as much as a fifty-word one.
        "wpm_sum": 0.0,
        "wpm_samples": 0,
        # The best run average, not the best single word: one lucky short
        # word is noise, not a personal best.
        "best_wpm": 0.0,
    }


def _default_stats() -> dict:
    stats = _new_category()
    stats["version"] = SCHEMA_VERSION
    stats["categories"] = {c: _new_category() for c in KNOWN_CATEGORIES}
    return stats


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
        for key in _FLOATS:
            clean[key] = _as_float(data.get(key), clean[key])

        categories = data.get("categories")
        if isinstance(categories, dict):
            for name, values in categories.items():
                if not isinstance(name, str) or not isinstance(values, dict):
                    continue
                entry = _new_category()
                for key in _COUNTERS:
                    entry[key] = _as_int(values.get(key), entry[key])
                for key in _FLOATS:
                    entry[key] = _as_float(values.get(key), entry[key])
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
        self,
        category: str,
        level: int,
        seconds: float,
        completed: bool,
        session=None,
    ) -> None:
        """Fold a finished run into the totals.

        ``completed`` is only true when the run was played out to GAME OVER;
        a run abandoned with ctrl+g still contributes its level, its time and
        its typing figures, so nothing a player actually did disappears.

        ``session`` is a ``RunSession``; passing ``None`` records everything
        except the typing figures, which keeps older callers working.
        """
        entry = self._category(category)
        scopes = (self.stats, entry)

        if completed:
            for scope in scopes:
                scope["games_completed"] += 1

        level = max(0, int(level))
        for scope in scopes:
            scope["max_level"] = max(scope["max_level"], level)

        seconds = max(0.0, float(seconds))
        for scope in scopes:
            scope["total_play_seconds"] += seconds

        if session is not None:
            self._record_typing(scopes, session)

        self.save()

    def _record_typing(self, scopes, session) -> None:
        """Fold one run's typing figures into each scope."""
        for scope in scopes:
            scope["words_hit"] += session.words_hit
            scope["total_keystrokes"] += session.total_keystrokes
            scope["error_keystrokes"] += session.error_keystrokes
            scope["wpm_sum"] += sum(session.wpm_series)
            scope["wpm_samples"] += len(session.wpm_series)

        run_wpm = session.wpm
        if run_wpm is not None:
            for scope in scopes:
                scope["best_wpm"] = max(scope["best_wpm"], run_wpm)

    def snapshot(self) -> dict:
        """A read-only copy for the stats screen to render.

        Each scope carries the raw counters plus the two figures derived from
        them, so the screen does no arithmetic of its own.
        """
        snap = self._scope_snapshot(self.stats)
        snap["categories"] = {
            name: self._scope_snapshot(values)
            for name, values in self.stats["categories"].items()
        }
        return snap

    @staticmethod
    def _scope_snapshot(scope: dict) -> dict:
        snap = {key: scope[key] for key in _COUNTERS + _FLOATS}
        snap["avg_wpm"] = avg_wpm(scope)
        snap["accuracy"] = accuracy(scope)
        return snap


def avg_wpm(scope: dict):
    """Mean burst speed across every word ever typed, or ``None``."""
    samples = scope.get("wpm_samples", 0)
    if not samples:
        return None
    return scope.get("wpm_sum", 0.0) / samples


def accuracy(scope: dict):
    """Share of keystrokes that kept the input valid, or ``None``."""
    total = scope.get("total_keystrokes", 0)
    if not total:
        return None
    return 1 - (scope.get("error_keystrokes", 0) / total)


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
