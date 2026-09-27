"""Shared fixtures.

Every test runs against a throwaway ``GRAVITYPE_HOME`` so nothing touches the
developer's real save. Two details make that harder than it looks:

- ``config`` and ``stats`` are module-level singletons built at import time,
  so they have already resolved their paths before any test runs.
- ``paths.legacy_config_file()`` resolves against the *current directory*, and
  the repo root contains a ``.gravitype_config.json``. Without pinning the cwd,
  running pytest from the repo root would load the maintainer's old settings.

The autouse fixture below deals with both.
"""

import pytest

from gravitype.core import paths
from gravitype.core.config import config
from gravitype.core.stats import stats


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point all runtime state at a per-test directory.

    Yields the directory, so a test can assert on the files written there.
    """
    home = tmp_path / "home"
    monkeypatch.setenv(paths.HOME_ENV_VAR, str(home))

    # Keep the legacy-dotfile lookup away from the repo root.
    monkeypatch.chdir(tmp_path)

    # Re-run the singletons' __init__ rather than reloading their modules:
    # app.py holds direct references to these objects, and a reload would
    # leave it pointing at stale copies.
    config.__init__()
    stats.__init__()

    yield home


@pytest.fixture
def app():
    """A fresh ``GravitypeApp``, built after the home is already isolated."""
    from gravitype.tui.app import GravitypeApp

    return GravitypeApp()
