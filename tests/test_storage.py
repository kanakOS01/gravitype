import json
import tempfile
import unittest
from pathlib import Path

from gravitype.core.storage import DEFAULT_CONFIG, GravitypeStorage


class StorageTests(unittest.TestCase):
    def test_creates_default_config_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = GravitypeStorage(Path(tmp) / ".gravitype", Path(tmp))

            self.assertEqual(storage.load_config(), DEFAULT_CONFIG)
            self.assertEqual(storage.load_history(), [])
            self.assertTrue((Path(tmp) / ".gravitype" / "config.json").exists())
            self.assertTrue((Path(tmp) / ".gravitype" / "history.json").exists())

    def test_migrates_legacy_config_when_home_config_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / ".gravitype_config.json"
            legacy.write_text(
                json.dumps(
                    {
                        "high_score": 420,
                        "theme": "nord",
                        "sound_enabled": False,
                        "starting_lives": 5,
                    }
                ),
                encoding="utf-8",
            )
            storage = GravitypeStorage(root / ".gravitype", root)

            config = storage.load_config()

            self.assertEqual(config["high_score"], 420)
            self.assertEqual(config["theme"], "nord")
            self.assertFalse(config["sound_enabled"])
            self.assertEqual(config["starting_lives"], 5)

    def test_corrupt_history_is_backed_up_and_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / ".gravitype"
            data_dir.mkdir()
            (data_dir / "history.json").write_text("{bad", encoding="utf-8")
            storage = GravitypeStorage(data_dir, Path(tmp))

            self.assertEqual(storage.load_history(), [])
            self.assertTrue(list(data_dir.glob("history.json.*.bak")))
            self.assertEqual(json.loads((data_dir / "history.json").read_text()), [])

    def test_append_game_and_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = GravitypeStorage(Path(tmp) / ".gravitype", Path(tmp))
            storage.append_game(
                {
                    "started_at": "2026-07-14T10:00:00+00:00",
                    "ended_at": "2026-07-14T10:01:00+00:00",
                    "duration_seconds": 60,
                    "category": "tech",
                    "score": 120,
                    "level_reached": 1,
                    "starting_lives": 3,
                    "lives_remaining": 0,
                    "words_cleared": 8,
                    "words_missed": 3,
                }
            )
            storage.append_game(
                {
                    "started_at": "2026-07-14T10:02:00+00:00",
                    "ended_at": "2026-07-14T10:03:30+00:00",
                    "duration_seconds": 90,
                    "category": "mixed",
                    "score": 300,
                    "level_reached": 3,
                    "starting_lives": 3,
                    "lives_remaining": 0,
                    "words_cleared": 20,
                    "words_missed": 3,
                }
            )

            stats = storage.get_stats()

            self.assertEqual(stats["games_played"], 2)
            self.assertEqual(stats["high_score"], 300)
            self.assertEqual(stats["average_score"], 210)
            self.assertEqual(stats["best_level"], 3)
            self.assertEqual(stats["total_words_cleared"], 28)
            self.assertEqual(stats["total_misses"], 6)
            self.assertEqual(stats["by_category"]["tech"]["games"], 1)
            self.assertEqual(stats["by_category"]["mixed"]["high_score"], 300)


if __name__ == "__main__":
    unittest.main()
