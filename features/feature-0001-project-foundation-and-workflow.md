# Feature 0001: Project Foundation and Workflow

## Status
Completed

## Objective
Create a clean Python project baseline with tooling, entrypoints, and test scaffolding so all subsequent features can be built with TDD.

## Scope
- Create source layout and package boundaries.
- Add CLI entrypoint skeleton.
- Configure formatting, linting, typing, and tests.
- Add developer run/test commands.

## Out of Scope
- Live audio capture.
- Spectrum processing.
- Real-time rendering.

## Dependencies
- None.

## Implementation Plan
1. Create package structure:
   - src/eq_cli/
   - tests/
2. Add initial modules:
   - app.py for orchestration
   - cli.py for argument parsing
   - config.py for runtime options
3. Add tooling config files:
   - pyproject.toml with pytest, ruff, mypy setup
4. Add minimal smoke test for entrypoint.
5. Add README usage section with local setup commands.

## TDD Tasks
1. Write failing test that CLI help command exits successfully.
2. Implement minimal argparse-based CLI to satisfy test.
3. Write failing import/smoke test for app startup function.
4. Implement startup function with typed interfaces.
5. Run targeted tests, then full test suite.

## Acceptance Criteria
- Project has runnable CLI entrypoint.
- pytest runs and passes with baseline tests.
- Ruff and mypy configuration is present.
- Public functions include type hints and docstrings.
- Developer setup and run instructions are documented.

## Risks
- Early over-design of module boundaries.

## Definition of Done
- All acceptance criteria met.
- Tests pass locally.
- Plan status updated to Completed when implemented.
