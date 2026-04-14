# Feature 0005: Peak Markers and Visual Stability

## Status
Completed

## Objective
Add per-band peak markers with gradual decay and improve visual stability of the CLI equalizer output.

## Scope
- Maintain peak state for each of 32 bands.
- Implement gradual decay function.
- Render peak markers distinctly from bar levels.
- Reduce flicker and jitter caused by rapid frame deltas.

## Out of Scope
- Alternative peak modes (hold-then-drop, sticky).

## Dependencies
- Feature 0003.
- Feature 0004.

## Implementation Plan
1. Add peak tracker component with typed state.
2. Implement decay update function with configurable rate.
3. Integrate peak state into render frame model.
4. Tune visual smoothing to balance responsiveness and stability.

## TDD Tasks
1. Write failing tests for peak rise and decay behavior.
2. Write failing tests for per-band independence.
3. Write failing render tests for marker placement.
4. Implement tracker and renderer integration.
5. Run targeted tests, then full suite.

## Acceptance Criteria
- Each band has a visible peak marker.
- Peaks rise immediately when signal increases.
- Peaks decay gradually when signal decreases.
- Visual output remains stable without excessive flicker.

## Risks
- Decay tuning may trade off responsiveness.

## Definition of Done
- All peak behavior tests pass.
- Manual runtime behavior matches expected UX.
