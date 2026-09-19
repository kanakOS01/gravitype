# Gravitype

A terminal typing game where words fall from the sky. Type them before they hit the bottom — miss one and you lose a life.

Built with [Textual](https://textual.textualize.io/).

```
 ██████╗ ██████╗  █████╗ ██╗   ██╗██╗████████╗██╗   ██╗██████╗ ███████╗
██╔════╝ ██╔══██╗██╔══██╗██║   ██║██║╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝
██║  ███╗██████╔╝███████║██║   ██║██║   ██║    ╚████╔╝ ██████╔╝█████╗
██║   ██║██╔══██╗██╔══██║╚██╗ ██╔╝██║   ██║     ╚██╔╝  ██╔═══╝ ██╔══╝
╚██████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║   ██║      ██║   ██║     ███████╗
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝   ╚═╝      ╚═╝   ╚═╝     ╚══════╝
```

[![PyPI](https://img.shields.io/pypi/v/gravitype.svg)](https://pypi.org/project/gravitype/)
[![Python versions](https://img.shields.io/pypi/pyversions/gravitype.svg)](https://pypi.org/project/gravitype/)
[![License](https://img.shields.io/pypi/l/gravitype.svg)](LICENSE)

## Requirements

Python 3.9+ (developed on 3.12). Any terminal with 256-colour support.

## Install

Gravitype is on PyPI: **[pypi.org/project/gravitype](https://pypi.org/project/gravitype/)**

The quickest way, which puts `gravitype` on your PATH in an isolated environment:

```bash
uv tool install gravitype
```

Or let a script work out the details for you:

```bash
curl -LsSf https://raw.githubusercontent.com/kanakOS01/gravitype/main/install.sh | sh
```

That installs uv if you don't have it, then installs Gravitype with it. Piping a script
into a shell runs whatever that URL serves, so if you'd rather not, every command below
does the same job by hand — [read the script first](install.sh) if you want to check.

Or with pipx, or plain pip:

```bash
pipx install gravitype
pip install gravitype
```

Then launch it:

```bash
gravitype
```

`python -m gravitype` works too, if you'd rather not rely on the script being on your PATH.

### Running from source

```bash
git clone https://github.com/kanakOS01/gravitype.git
cd gravitype
uv sync
uv run gravitype
```

## Features

- Falling-word gameplay with difficulty that ramps up as you score
- Two word categories: **Tech** and **General**
- 7 colour themes (Dracula, Nord, Tokyo Night, Gruvbox, Catppuccin, Cyberspace, 80s After Dark)
- Configurable starting lives (3 / 5 / 8) and bell-on-miss sound
- Persistent high score
- Pause, in-game help and keybind reference

## How to play

Words spawn at the top of the board and drift down. Type a word and it disappears the moment the text matches — no Enter needed. Points are `10 × word length`, and every 150 points bumps you up a level, which makes words fall faster, spawn more often and get longer.

If a word reaches the bottom you lose a life. At zero lives the run ends and your score is checked against the high score.

The input box flashes on a hit, and turns red the moment what you have typed is no longer the prefix of any word on screen.

### Keybinds

**Menu**

| Key | Action |
| --- | --- |
| `ctrl+p` / `escape` | Play / back to menu |
| `ctrl+s` | Settings |
| `ctrl+h` | Help |
| `ctrl+a` | About |
| `ctrl+q` | Quit |

**In game**

| Key | Action |
| --- | --- |
| `escape` | Pause / resume |
| `ctrl+g` | Quit to menu (run is not scored) |
| `ctrl+w` | Clear the word being typed |

## Configuration

Settings are edited in-game (`ctrl+s`) and stored in `~/.gravitype/`, so your high score follows you regardless of which directory you launch from:

```
~/.gravitype/
  config.json            your settings and high score
  theme_active.tcss      generated stylesheet, safe to delete
```

Set `GRAVITYPE_HOME` to relocate that directory — handy for keeping separate profiles, or for trying things out without touching your real save:

```bash
GRAVITYPE_HOME=/tmp/gravitype-test gravitype
```

`config.json` is plain JSON, so you can edit it by hand if you prefer:

```json
{
    "high_score": 1790,
    "theme": "dracula",
    "sound_enabled": true,
    "starting_lives": 5
}
```

Unknown keys are ignored and a corrupt file falls back to defaults, so it is safe to delete the file to reset everything.

Versions before 0.3 kept this as a `.gravitype_config.json` dotfile in the working directory. If `~/.gravitype/config.json` does not exist yet, Gravitype reads that dotfile once and migrates your settings forward, leaving the original where it is. An existing `~/.gravitype/config.json` always takes precedence.

## Project layout

```
gravitype/
  cli.py                     console entry point
  __main__.py                enables `python -m gravitype`
  core/
    config.py                config load/save + theme compilation
    paths.py                 per-user config and cache locations
    words.py                 word pools and level-based word picking
  tui/
    app.py                   app, screens and game loop wiring
    widgets/
      game_board.py          falling words, collision, scoring
      header.py              in-game score/level/lives bar
      main_header.py         banner and nav tabs
      screens.py             settings, help, about
      table.py               keybind table
    styles/
      base.tcss              layout and component styles
      themes/*.tcss          colour variables per theme
```

Themes work by concatenation: on startup `generate_theme_file()` writes the selected theme's variables plus `base.tcss` into `~/.gravitype/theme_active.tcss`, and hands that path to Textual as the app's stylesheet. It is written outside the package so an installed, read-only copy still works, and it is safe to delete — it regenerates on next launch. Adding a theme means dropping a new `.tcss` of variables into `themes/` and adding it to the Settings dropdown.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

Colour themes are inspired by and adapted from [Smassh](https://github.com/kraanzu/smassh).

## License

[MIT](LICENSE) © Kanak Tanwar
