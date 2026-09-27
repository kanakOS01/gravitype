# Contributing to Gravitype

Thanks for taking an interest. Bug reports, new word lists, themes and gameplay tweaks are all welcome.

## Setup

```bash
git clone https://github.com/kanakOS01/gravitype.git
cd gravitype
uv sync                 # installs runtime + dev dependencies
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
```

Both hook types matter: `pre-commit` runs Ruff, `commit-msg` runs Commitizen on your message.

Run the game:

```bash
uv run gravitype
```

For development, run it under the Textual dev console so `print()` and tracebacks are visible instead of being swallowed by the TUI:

```bash
uv run textual console                                  # terminal 1
uv run textual run --dev gravitype.tui.app:GravitypeApp  # terminal 2
```

`watch_css=True` is set on the app and points at `~/.gravitype/theme_active.tcss`, so writing to that file reloads live. Edits to `base.tcss` or a theme file in the repo only take effect after a restart, since the active file is recompiled from them on startup.

## Code style

Ruff handles both linting and formatting; the pre-commit hook runs `ruff check --fix` and `ruff format`. To run them yourself:

```bash
uv run ruff check --fix .
uv run ruff format .
```

Beyond that, match what's already there:

- Type hints on function signatures, docstrings on classes and non-obvious methods.
- Widgets live in `gravitype/tui/widgets/`, one concern per module. Pure game logic (word selection, config) belongs in `gravitype/core/` and should not import Textual.
- Never write to a path inside the installed package. Runtime state goes through `gravitype/core/paths.py`, which resolves `~/.gravitype/` (or `GRAVITYPE_HOME`) — site-packages may be read-only, and writing there leaks one user's state into everyone else's. Set `GRAVITYPE_HOME` when testing so you don't clobber your own save.
- Cross-widget communication goes through Textual messages (see `GameBoard.WordMissed`) or app-level reactives — not by reaching into another widget's internals.
- No `print()` in committed code.

## Tests

`pytest` with everything under `tests/`. The commit hooks don't run it — the suite takes about 25 seconds, which is too long to pay on every commit — so run it yourself before you push. CI runs it on every PR.

Run the whole suite, or narrow it down:

```bash
uv run pytest                        # everything
uv run pytest tests/test_stats.py    # one file
uv run pytest -k pause               # one idea
uv run pytest -x -q                  # stop at the first failure
```

Two layers:

- **`core/`** — plain unit tests for `config`, `paths`, `stats` and `words`. No Textual, no event loop, fast.
- **TUI** — `test_app_runs.py`, `test_app_ui.py`, `test_gameplay.py` and `test_game_board.py` drive the real app through Textual's `run_test()` pilot, pressing keys and asserting on what the widgets end up holding. `asyncio_mode = "auto"` is set in `pyproject.toml`, so a test is async just by being `async def` — no decorator needed.

Things worth knowing before you add a test:

- The autouse `isolated_home` fixture in `conftest.py` points `GRAVITYPE_HOME` at a temp directory and re-initialises the `config` and `stats` singletons, so no test can see or clobber your real save. It also pins the working directory, because `paths.legacy_config_file()` resolves against the cwd and the repo root contains a `.gravitype_config.json`.
- Use the `app` fixture to get a `GravitypeApp` built *after* that isolation is in place.
- Don't monkeypatch `time.monotonic` — `asyncio` reads it too, and patching it deadlocks the event loop. To test elapsed time, backdate `app._run_started_at` instead (see `test_app_runs.py`).
- Don't replace a widget's `post_message` to capture events; that is Textual's own message pump and swapping it hangs the widget. Assert on the consequence instead — a missed word is visible as `app.lives` going down.
- `await pilot.pause()` after anything that changes state, so the app has a chance to process it.

## Commits

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/); Commitizen enforces this at commit time.

```
feat: add sound toggle to settings
fix: reset board state on play again
refactor: move word filtering into core
docs: document theme pipeline
```

If you'd rather be prompted through the format, install Commitizen (`uv tool install commitizen`) and use `cz commit`.

## Making changes

1. Branch off `main` — `feat/short-description` or `fix/short-description`.
2. Make the change and play a few rounds to confirm nothing regressed: start a game, miss words, pause, game over, play again, main menu, change theme and lives in settings.
3. Add or update tests for what you changed, and run `uv run pytest`.
4. Push and open a PR against `main` describing what changed and how you tested it. A screenshot or terminal recording helps a lot for anything visual. CI runs Ruff and the test suite on Python 3.9 through 3.13; it has to be green before a PR can merge.

## Common contributions

**Adding words** — append to `TECH_WORDS` or `GENERAL_WORDS` in `gravitype/core/words.py`. Keep them lowercase, no spaces or punctuation, and note that word length decides which level a word can appear at (see `get_random_word`), so short words are as valuable as long ones. (The built-in pools hold to that rule; a player's own set is deliberately looser and may contain phrases and capitals.)

**Adding a category** — usually no code is needed: a `.txt` file in `~/.gravitype/words/` becomes a category on its own (see [Custom word sets](README.md#custom-word-sets)). To add one that *ships with the game*, add the pool to `gravitype/core/words.py`, list its name in `BUILTIN_CATEGORIES` and return it from `word_pool`. The menu builds its dropdown from `available_categories()`, so nothing in the UI needs touching.

**Adding a theme** — copy an existing file in `gravitype/tui/styles/themes/`, keep the same variable names, and add an option to the theme `Select` in `gravitype/tui/widgets/screens.py`. Note that `theme_active.tcss` is generated output living in `~/.gravitype/` — don't put changes there, they'll be overwritten on next launch.

**Tuning difficulty** — `GameBoard.get_ticks_for_level` controls fall speed and spawn rate; the level threshold and per-word points live in `GameScreen.on_input_changed`.

## Recording demos

The GIFs in the README are recorded with [asciinema](https://asciinema.org/) and
converted with [agg](https://github.com/asciinema/agg):

```bash
brew install asciinema agg
```

Record a session, play through the beats, then stop with `Ctrl+D`:

```bash
export GRAVITYPE_SEED=7 GRAVITYPE_HOME=$(mktemp -d)
asciinema rec docs/demo.cast --overwrite
gravitype
```

Convert it to a GIF:

```bash
agg docs/demo.cast docs/demo.gif --font-size 18 --theme dracula
```


## Releasing

Maintainers only — see [RELEASING.md](RELEASING.md) for the full checklist.

## Reporting bugs

Open an issue with your OS and terminal, Python version, what you did, what you expected, and what happened. Terminal size matters for TUI layout bugs, so include it if the issue looks like a rendering problem.
