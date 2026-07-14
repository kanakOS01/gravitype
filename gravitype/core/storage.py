import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIG = {
    "high_score": 0,
    "theme": "dracula",
    "sound_enabled": True,
    "starting_lives": 3,
}


class GravitypeStorage:
    """Persistent app data under ~/.gravitype."""

    def __init__(
        self, data_dir: Optional[Path] = None, legacy_dir: Optional[Path] = None
    ):
        self.data_dir = data_dir or (Path.home() / ".gravitype")
        self.legacy_dir = legacy_dir or Path.cwd()
        self.config_path = self.data_dir / "config.json"
        self.history_path = self.data_dir / "history.json"

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        self.ensure_data_dir()
        if not self.config_path.exists():
            config = self._load_legacy_config() or DEFAULT_CONFIG.copy()
            self.save_config(config)
            return self._sanitize_config(config)

        try:
            data = self._read_json(self.config_path)
            if not isinstance(data, dict):
                raise ValueError("config must be an object")
            return self._sanitize_config(data)
        except Exception:
            self._backup_bad_file(self.config_path)
            config = DEFAULT_CONFIG.copy()
            self.save_config(config)
            return config

    def save_config(self, config: Dict[str, Any]) -> None:
        self.ensure_data_dir()
        self._write_json(self.config_path, self._sanitize_config(config))

    def load_history(self) -> List[Dict[str, Any]]:
        self.ensure_data_dir()
        if not self.history_path.exists():
            self._write_json(self.history_path, [])
            return []

        try:
            data = self._read_json(self.history_path)
            if not isinstance(data, list):
                raise ValueError("history must be a list")
            return [item for item in data if isinstance(item, dict)]
        except Exception:
            self._backup_bad_file(self.history_path)
            self._write_json(self.history_path, [])
            return []

    def append_game(self, game: Dict[str, Any]) -> Dict[str, Any]:
        history = self.load_history()
        record = {
            "id": str(game.get("id") or uuid.uuid4()),
            "started_at": str(game.get("started_at") or self._now()),
            "ended_at": str(game.get("ended_at") or self._now()),
            "duration_seconds": int(game.get("duration_seconds", 0) or 0),
            "category": str(game.get("category", "mixed")),
            "score": int(game.get("score", 0) or 0),
            "level_reached": int(game.get("level_reached", 1) or 1),
            "starting_lives": int(game.get("starting_lives", 3) or 3),
            "lives_remaining": int(game.get("lives_remaining", 0) or 0),
            "words_cleared": int(game.get("words_cleared", 0) or 0),
            "words_missed": int(game.get("words_missed", 0) or 0),
        }
        history.append(record)
        self._write_json(self.history_path, history)
        return record

    def get_stats(self) -> Dict[str, Any]:
        history = self.load_history()
        games_played = len(history)
        total_score = sum(int(game.get("score", 0) or 0) for game in history)
        total_words_cleared = sum(
            int(game.get("words_cleared", 0) or 0) for game in history
        )
        total_misses = sum(int(game.get("words_missed", 0) or 0) for game in history)
        high_score = max([0] + [int(game.get("score", 0) or 0) for game in history])
        best_level = max(
            [0] + [int(game.get("level_reached", 0) or 0) for game in history]
        )
        by_category: Dict[str, Dict[str, int]] = {}

        for game in history:
            category = str(game.get("category", "mixed")).lower()
            bucket = by_category.setdefault(
                category,
                {"games": 0, "high_score": 0, "words_cleared": 0, "misses": 0},
            )
            bucket["games"] += 1
            bucket["high_score"] = max(
                bucket["high_score"], int(game.get("score", 0) or 0)
            )
            bucket["words_cleared"] += int(game.get("words_cleared", 0) or 0)
            bucket["misses"] += int(game.get("words_missed", 0) or 0)

        return {
            "games_played": games_played,
            "high_score": high_score,
            "average_score": round(total_score / games_played) if games_played else 0,
            "best_level": best_level,
            "total_words_cleared": total_words_cleared,
            "total_misses": total_misses,
            "by_category": by_category,
            "recent_games": list(reversed(history[-10:])),
        }

    def _load_legacy_config(self) -> Optional[Dict[str, Any]]:
        legacy_path = self.legacy_dir / ".gravitype_config.json"
        if not legacy_path.exists():
            return None
        try:
            data = self._read_json(legacy_path)
            if isinstance(data, dict):
                return self._sanitize_config(data)
        except Exception:
            return None
        return None

    def _sanitize_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        config = DEFAULT_CONFIG.copy()
        for key, default in DEFAULT_CONFIG.items():
            if key not in data:
                continue
            value = data[key]
            try:
                if isinstance(default, bool):
                    config[key] = bool(value)
                elif isinstance(default, int):
                    config[key] = int(value)
                else:
                    config[key] = str(value)
            except Exception:
                config[key] = default
        return config

    def _backup_bad_file(self, path: Path) -> None:
        if not path.exists():
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
        path.replace(backup_path)

    def _read_json(self, path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _write_json(self, path: Path, data: Any) -> None:
        self.ensure_data_dir()
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)
            file.write("\n")
        temp_path.replace(path)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


storage = GravitypeStorage()
