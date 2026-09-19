"""Console entry point for Gravitype."""

import os
import random

from gravitype.tui.app import GravitypeApp

#: Seeds the global RNG, making word choice and spawn positions repeatable.
#: Used for recording demos; unset in normal play.
SEED_ENV_VAR = "GRAVITYPE_SEED"


def _apply_seed() -> None:
    seed = os.environ.get(SEED_ENV_VAR)
    if not seed:
        return
    try:
        random.seed(int(seed))
    except ValueError:
        random.seed(seed)


def main() -> None:
    """Launch the Gravitype TUI."""
    _apply_seed()
    GravitypeApp().run()
