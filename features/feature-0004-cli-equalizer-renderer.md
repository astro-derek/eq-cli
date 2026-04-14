# Feature 0004: CLI Equalizer Renderer

## Status
Completed

## Objective
Render a real-time terminal equalizer graph using 32 bands, axis labels, and dB scale, with automatic fallback to monochrome when color is unavailable.

## Scope
- Terminal canvas lifecycle (clear/redraw in place).
- Horizontal frequency labels for 20 Hz to 20 kHz.
- Vertical dB scale labels.
- Colorized bars with monochrome fallback.
- Frame refresh loop integration.

## Out of Scope
- Peak decay logic details (handled in Feature 0005).

## Dependencies
- Feature 0001.
- Feature 0003.

## Implementation Plan
1. Define renderer interfaces and frame model.
2. Implement axis generation helpers:
   - frequency tick labels
   - dB tick labels
3. Implement text buffer renderer with optional ANSI colors.
4. Integrate refresh loop without flooding terminal history.
5. Add capability detection and monochrome fallback path.

## TDD Tasks
1. Write failing snapshot tests for axis layout.
2. Write failing tests for color-on and monochrome output modes.
3. Write failing tests that redraw updates in place.
4. Implement renderer incrementally to satisfy tests.
5. Run targeted tests, then full suite.

## Acceptance Criteria
- Graph displays 32 bars with labeled frequency and dB axes.
- Color mode works on capable terminals.
- Monochrome fallback activates automatically when needed.
- Rendering loop remains readable and stable at runtime.

## Risks
- Terminal width constraints can break label readability.
- ANSI support differences across shells/OS.

## Definition of Done
- Snapshot and behavior tests pass.
- Manual smoke run validates readability on target terminals.
