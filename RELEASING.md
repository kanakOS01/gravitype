# Releasing

Maintainer notes for cutting a new Gravitype release. Contributors don't need this —
see [CONTRIBUTING.md](CONTRIBUTING.md) instead.

Releases go to two places: the package on [PyPI](https://pypi.org/project/gravitype/)
and a tagged release on GitHub. Do PyPI first, so a rejected upload doesn't leave a tag
pointing at a version nobody can install.

## 1. Bump the version

`version` in `pyproject.toml` is the single source of truth. PyPI refuses to accept a
version it has already seen, even if you deleted the release, so every upload needs a
fresh number.

If the release changes maturity, update the `Development Status` classifier to match.

## 2. Build

```bash
rm -rf dist/
uv lock
uv build
```

Always clear `dist/` first, or `uv publish` will try to upload stale artifacts from
previous versions alongside the new ones.

## 3. Validate

```bash
uvx twine check dist/*
```

**Do not skip this.** `uv build` performs no metadata validation and will happily produce
a wheel that PyPI rejects. Both the wheel and the sdist must report `PASSED`.

The `hatchling>=1.27,<1.28` pin in `pyproject.toml` exists because of this check: newer
hatchling emits `Metadata-Version: 2.5`, which PyPI does not accept. If you ever relax
that pin, `twine check` is what will tell you it broke.

Also confirm the styles made it in — the app has no CSS without them:

```bash
python3 -c "import zipfile,glob; print([n for n in zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist() if n.endswith('.tcss')])"
```

Expect 8 `.tcss` files: `base.tcss` plus the seven themes.

## 4. Smoke-test the built artifact

Test the wheel, not your working copy, and do it from a directory outside the repo —
otherwise Python imports the local `gravitype/` package and everything looks fine
regardless of what you actually built.

```bash
cd /tmp
python3 -m venv /tmp/gt-test
/tmp/gt-test/bin/pip install ~/path/to/gravitype/dist/gravitype-X.Y.Z-py3-none-any.whl
GRAVITYPE_HOME=/tmp/gt-home /tmp/gt-test/bin/gravitype
```

Set `GRAVITYPE_HOME` so the test doesn't overwrite your real config and high score.

Prefer a plain `venv` over `uv run --with` here. uv caches installed archives by name and
version, so rebuilding the same version repeatedly can silently install a stale copy —
and while your local version matches one already on PyPI, uv may resolve the published
package instead of your file. A `venv` has neither problem.

## 5. Publish to PyPI

```bash
uv publish dist/*
```

Needs a PyPI token in `UV_PUBLISH_TOKEN`, or a trusted publisher configured for the repo.

## 6. Commit and tag

```bash
git add pyproject.toml uv.lock
git commit -m "chore: release vX.Y.Z"
git push

git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

Annotated tags (`-a`), and **never move a published tag**. A tag records the commit that
was released. Later documentation fixes get their own commits, not a relocated tag.

## 7. Create the GitHub release

The `gh` CLI acts as whichever account is currently active, and only an account with
write access to `kanakOS01/gravitype` can create a release:

```bash
gh auth status                      # check which account is active
gh auth switch --user kanakOS01     # if it isn't the personal one
```

```bash
gh release create vX.Y.Z dist/* \
  --repo kanakOS01/gravitype \
  --title "vX.Y.Z" \
  --notes "..."
```

Attaching `dist/*` puts the wheel and sdist on the release page. Release notes can be
edited afterwards with `gh release edit` without touching the tag.

Switch `gh` back afterwards if you changed it.

## After a release

Two things do **not** update on their own:

- **The PyPI project page.** Its description is baked in from `README.md` at upload time
  and cannot be edited afterwards. README changes only appear on PyPI with the next
  release, so fold documentation fixes into a real release rather than cutting one for
  them alone.
- **`install.sh`.** The curl URL in the README points at `main`, so the installer follows
  the default branch rather than the tag. Anything you break on `main` breaks installs
  immediately — pin the URL to a tag if you'd rather that not be true.
