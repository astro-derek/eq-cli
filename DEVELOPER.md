# Developer Guide

This document covers development setup, testing, linting, and release
procedures for `eq-cli`.

## Development Setup

### Requirements

- Python 3.12 or newer
- pip

### Install in editable mode

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

The `dev` extras install `pytest`, `pytest-cov`, `ruff`, and `mypy` in one
step.

## Running Tests

```sh
python -m pytest
```

Collect coverage at the same time:

```sh
python -m pytest --cov=eq_cli
```

## Linting and Type Checking

```sh
python -m ruff check .
python -m mypy src
```

## Release and Distribution

The repository is configured to produce Python distribution artifacts from
GitHub Actions.

### CI Validation

Pushes and pull requests to `main` run a CI workflow that:

- runs `pytest`
- runs `ruff`
- runs `mypy`
- runs `python -m build`

This confirms that the repo is still capable of producing deployable Python
artifacts.

The release workflow also runs the same `pytest`, `ruff`, and `mypy` checks
before building artifacts, preventing a broken release from being published.

### Cut a Release

To create deployable artifacts for a release:

1. Ensure `main` is up to date.
2. Read the current project version from `pyproject.toml`.
3. Create an annotated tag such as `v0.1.0`.
4. Push the tag.

Versioning is now automated: every push to `main` runs the
`.github/workflows/bump-version.yml` workflow, which increments the patch
version in `pyproject.toml` and commits it back to `main`.

Example:

```sh
git checkout main
git pull --ff-only origin main
VERSION=$(python - <<'PY'
from pathlib import Path
import re

match = re.search(r'(?m)^version = "([^"]+)"$', Path("pyproject.toml").read_text())
if match is None:
    raise SystemExit("Unable to read version from pyproject.toml")
print(match.group(1))
PY
)
git tag -a "v${VERSION}" -m "v${VERSION}"
git push origin "v${VERSION}"
```

The release workflow builds `sdist` and `wheel` artifacts and attaches them to
the corresponding GitHub Release.

## Changelog and Security

Notable changes between releases are tracked in [CHANGELOG.md](CHANGELOG.md).

For reporting security vulnerabilities, see [SECURITY.md](SECURITY.md).
