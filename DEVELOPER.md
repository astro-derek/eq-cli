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
python -m pip install -e .
```

## Running Tests

```sh
python -m pip install -e . pytest
python -m pytest
```

## Linting and Type Checking

```sh
python -m pip install -e . ruff mypy
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

### Cut a Release

To create deployable artifacts for a release:

1. Update the version in `pyproject.toml`.
2. Commit the version bump on `main`.
3. Create an annotated tag such as `v0.1.0`.
4. Push the branch and tag.

Example:

```sh
git checkout main
git pull --ff-only origin main
git add pyproject.toml
git commit -m "release v0.1.1"
git tag -a v0.1.1 -m "v0.1.1"
git push origin main --tags
```

Current manual release trigger sequence:

```sh
git checkout main
git pull --ff-only origin main
# edit pyproject.toml version
git add pyproject.toml README.md
git commit -m "release v0.1.1"
git tag -a v0.1.1 -m "v0.1.1"
git push origin main --tags
```

This manual sequence is the current source of truth for releases and is a good
candidate for future automation once the release flow has been exercised a few
times.

The release workflow builds `sdist` and `wheel` artifacts and attaches them to
the corresponding GitHub Release.
