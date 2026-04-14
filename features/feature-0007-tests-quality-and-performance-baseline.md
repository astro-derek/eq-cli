# Feature 0007: Tests, Quality, and Performance Baseline

## Status
Completed

## Objective
Establish quality gates and performance baselines to protect correctness and real-time behavior as the codebase grows.

## Scope
- Unit tests for DSP, selection, rendering helpers.
- Integration smoke tests for end-to-end startup path.
- Lint and type-check enforcement.
- Performance benchmark for 20+ FPS target.

## Out of Scope
- Long-running soak tests in MVP.

## Dependencies
- Feature 0001 through Feature 0006.

## Implementation Plan
1. Expand test matrix by module.
2. Add reusable fakes for audio devices and synthetic frames.
3. Add performance test for frame processing and render pacing.
4. Add CI command set for pytest, ruff, and mypy.

## TDD Tasks
1. Add failing tests for edge cases not yet covered.
2. Implement minimal fixes to satisfy each failing test.
3. Add failing perf assertion for update-rate target.
4. Optimize code paths until test passes.
5. Run full suite and capture baseline numbers.

## Acceptance Criteria
- Core modules have meaningful automated coverage.
- Full test suite passes consistently.
- Ruff and mypy checks pass.
- Performance baseline demonstrates at least 20 updates/second under defined test conditions.

## Risks
- Performance tests can be flaky if environment-dependent.

## Definition of Done
- Quality gates are documented and repeatable.
- Baseline metrics are recorded for regression comparison.
