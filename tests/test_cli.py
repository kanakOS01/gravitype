"""Console entry point: seeding and launch."""

import random

from gravitype import cli


def _sample():
    return [random.random() for _ in range(5)]


def test_no_seed_leaves_the_rng_alone(monkeypatch):
    monkeypatch.delenv(cli.SEED_ENV_VAR, raising=False)
    random.seed(1)
    expected = _sample()

    random.seed(1)
    cli._apply_seed()

    assert _sample() == expected


def test_integer_seed_is_reproducible(monkeypatch):
    monkeypatch.setenv(cli.SEED_ENV_VAR, "7")

    cli._apply_seed()
    first = _sample()
    cli._apply_seed()

    assert _sample() == first


def test_non_integer_seed_is_used_as_a_string(monkeypatch):
    """A typo'd seed should still be deterministic rather than an error."""
    monkeypatch.setenv(cli.SEED_ENV_VAR, "not-a-number")

    cli._apply_seed()
    first = _sample()
    cli._apply_seed()

    assert _sample() == first


def test_empty_seed_is_ignored(monkeypatch):
    monkeypatch.setenv(cli.SEED_ENV_VAR, "")
    random.seed(3)
    expected = _sample()

    random.seed(3)
    cli._apply_seed()

    assert _sample() == expected


def test_main_seeds_then_runs(monkeypatch):
    calls = []
    monkeypatch.setenv(cli.SEED_ENV_VAR, "7")
    monkeypatch.setattr(cli, "_apply_seed", lambda: calls.append("seed"))
    monkeypatch.setattr(
        cli.GravitypeApp, "run", lambda self: calls.append("run"), raising=True
    )

    cli.main()

    assert calls == ["seed", "run"]
