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

## Features

- Falling-word gameplay with difficulty that ramps up as you score
- Two word categories: **Tech** and **General**
- 7 colour themes (Dracula, Nord, Tokyo Night, Gruvbox, Catppuccin, Cyberspace, 80s After Dark)
- Configurable starting lives (3 / 5 / 8) and bell-on-miss sound
- Persistent high score
- Pause, in-game help and keybind reference

## Requirements

Python 3.9+ (developed on 3.12). Any terminal with 256-colour support.

## Install

The quickest way, which puts `gravitype` on your PATH in an isolated environment:

```bash
uv tool install gravitype
```

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

Settings are edited in-game (`ctrl+s`) and stored in `.gravitype_config.json` in the directory you launch from:

```json
{
    "high_score": 1790,
    "theme": "dracula",
    "sound_enabled": true,
    "starting_lives": 5
}
```

Unknown keys are ignored and a corrupt file falls back to defaults, so it is safe to delete the file to reset everything.

## Project layout

```
gravitype/
  cli.py                     console entry point
  __main__.py                enables `python -m gravitype`
  core/
    config.py                config load/save + theme compilation
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
      theme_active.tcss      generated — do not edit by hand
```

Themes work by concatenation: on startup `generate_theme_file()` writes the selected theme's variables plus `base.tcss` into `theme_active.tcss`, which is the app's `CSS_PATH`. Adding a theme means dropping a new `.tcss` of variables into `themes/` and adding it to the Settings dropdown.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

Colour themes are inspired by and adapted from [Smassh](https://github.com/kraanzu/smassh).

## License

[MIT](LICENSE) © Kanak Tanwar
