"""Where runtime state lands, and what happens when it can't."""

import os
import tempfile
from pathlib import Path

from gravitype.core import paths


def test_app_home_follows_env_override(isolated_home):
    assert paths.app_home() == isolated_home


def test_app_home_defaults_under_user_home(monkeypatch):
    monkeypatch.delenv(paths.HOME_ENV_VAR, raising=False)
    assert paths.app_home() == Path.home() / ".gravitype"


def test_app_home_expands_tilde(monkeypatch):
    monkeypatch.setenv(paths.HOME_ENV_VAR, "~/somewhere")
    assert paths.app_home() == Path.home() / "somewhere"


def test_state_files_sit_under_app_home(isolated_home):
    for resolved in (
        paths.config_file(),
        paths.stats_file(),
        paths.generated_css_file(),
    ):
        assert resolved.parent == isolated_home

    assert paths.config_file().name == "config.json"
    assert paths.stats_file().name == "stats.json"


def test_state_files_are_never_inside_the_package(isolated_home):
    """site-packages may be read-only, and writing there leaks between users."""
    package_dir = Path(paths.__file__).parent.parent.resolve()
    for resolved in (paths.config_file(), paths.stats_file()):
        assert package_dir not in resolved.resolve().parents


def test_legacy_config_resolves_against_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert paths.legacy_config_file() == tmp_path / ".gravitype_config.json"


def test_ensure_writable_dir_creates_missing_parents(tmp_path):
    target = tmp_path / "a" / "b" / "c.json"
    assert paths.ensure_writable_dir(target) == target
    assert target.parent.is_dir()


def test_ensure_writable_dir_falls_back_when_home_is_read_only(tmp_path):
    """A read-only home must degrade to the temp dir, not raise."""
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        target = locked / "nested" / "config.json"
        resolved = paths.ensure_writable_dir(target)

        assert resolved != target
        assert resolved.name == "config.json"
        assert resolved.parent == Path(tempfile.gettempdir()) / paths.APP_NAME
    finally:
        # Let pytest's tmp_path cleanup remove it.
        locked.chmod(0o700)


def test_ensure_writable_dir_is_idempotent(tmp_path):
    target = tmp_path / "x" / "config.json"
    assert paths.ensure_writable_dir(target) == paths.ensure_writable_dir(target)


def test_home_env_var_name_is_stable():
    """Documented in the README and CONTRIBUTING; renaming it breaks users."""
    assert paths.HOME_ENV_VAR == "GRAVITYPE_HOME"
    assert os.environ.get(paths.HOME_ENV_VAR)
