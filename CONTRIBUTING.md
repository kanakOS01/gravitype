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
3. Push and open a PR against `main` describing what changed and how you tested it. A screenshot or terminal recording helps a lot for anything visual.

There is no automated test suite yet. If you add one, `pytest` with tests under `tests/` is the expected shape — and adding coverage for `core/` is a genuinely useful contribution.

## Common contributions

**Adding words** — append to `TECH_WORDS` or `GENERAL_WORDS` in `gravitype/core/words.py`. Keep them lowercase, no spaces or punctuation, and note that word length decides which level a word can appear at (see `get_random_word`), so short words are as valuable as long ones.

**Adding a category** — extend the pools and the branch in `get_random_word`, then add a category button in `WelcomeScreen.compose` with id `cat-<name>`; the existing handler picks it up from the id.

**Adding a theme** — copy an existing file in `gravitype/tui/styles/themes/`, keep the same variable names, and add an option to the theme `Select` in `gravitype/tui/widgets/screens.py`. Note that `theme_active.tcss` is generated output living in `~/.gravitype/` — don't put changes there, they'll be overwritten on next launch.

**Tuning difficulty** — `GameBoard.get_ticks_for_level` controls fall speed and spawn rate; the level threshold and per-word points live in `GameScreen.on_input_changed`.

## Releasing

Maintainers only — see [RELEASING.md](RELEASING.md) for the full checklist.

## Reporting bugs

Open an issue with your OS and terminal, Python version, what you did, what you expected, and what happened. Terminal size matters for TUI layout bugs, so include it if the issue looks like a rendering problem.
