# Feature 0024: Deployment and Distribution Automation

## Status
Completed

## Objective
Add repository automation and documentation so `eq-cli` can consistently produce deployable Python distribution artifacts from CI and release tags.

## Scope
- Add a CI workflow that validates tests, linting, typing, and package buildability on pushes and pull requests.
- Add a release workflow that builds `sdist` and `wheel` artifacts from version tags and publishes them as GitHub Release assets.
- Document the git and release steps required to create deployable artifacts.
- Keep the implementation aligned with the existing Python packaging configuration in `pyproject.toml`.

## Out of Scope
- Publishing to PyPI.
- Building standalone native binaries.
- Homebrew packaging.
- OS-specific installer packaging.

## Dependencies
- Existing packaging metadata in `pyproject.toml`.
- Existing test/lint/type commands already used in local development.
- GitHub repository Actions and Releases features.

## Implementation Plan
1. Add a feature document and checklist entry before implementation.
2. Add a CI workflow for pushes and pull requests to `main`.
3. Add a tag-driven release workflow that builds `dist/` artifacts and attaches them to a GitHub Release.
4. Update repository docs with the git/tag steps for creating release artifacts.
5. Validate the build locally and review the workflow files for correctness.

## Acceptance Criteria
- A GitHub Actions CI workflow exists and runs tests, Ruff, mypy, and `python -m build`.
- A GitHub Actions release workflow exists and builds wheel and source artifacts for tags like `v0.1.0`.
- The release workflow publishes the built artifacts to a GitHub Release.
- The README or other project docs explain the required git actions to cut a release.
- Local validation still passes after the automation files are added.

## Results
- Added a CI workflow at `.github/workflows/ci.yml` that runs `pytest`, `ruff`, `mypy`, and `python -m build` on pushes and pull requests to `main`.
- Added a tag-driven release workflow at `.github/workflows/release.yml` that builds `sdist` and `wheel` artifacts for tags matching `v*` and attaches them to a GitHub Release.
- Updated `README.md` with the git steps required to cut a release and produce deployable artifacts.
- Updated `ARCHITECTURE.md` to reflect the GitHub Actions-based artifact build and release flow.
- Local validation after the workflow changes passed:
	- `pytest`: `140 passed`
	- `ruff`: passed
	- `mypy`: passed
	- `python -m build`: successfully produced `eq_cli-0.1.0.tar.gz` and `eq_cli-0.1.0-py3-none-any.whl`

## Risks
- The current automation publishes GitHub Release assets only; PyPI publishing is still a separate future step.
- The workflows assume standard GitHub Actions permissions and release access on the repository.
- This release flow builds Python package artifacts, not standalone executables.

## Definition of Done
- CI workflow is present and validates test, lint, type, and build steps.
- Tag-driven release workflow is present and publishes build artifacts to GitHub Releases.
- Release git actions are documented.
- Local validation and package build succeed.