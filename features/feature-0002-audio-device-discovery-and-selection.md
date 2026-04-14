# Feature 0002: Audio Device Discovery and Selection

## Status
Completed

## Objective
Enable users to list and select microphone/input devices via CLI argument and interactive prompt.

## Scope
- Enumerate available input devices from audio backend.
- Provide deterministic device identifiers.
- Support selection through:
  - --device argument
  - interactive picker when argument is absent
- Provide clear errors for invalid device selection.

## Out of Scope
- Loopback/system audio capture.
- Continuous stream processing.

## Dependencies
- Feature 0001.

## Implementation Plan
1. Introduce audio adapter interface for device discovery.
2. Implement concrete backend wrapper for device listing.
3. Add CLI options:
   - --list-devices
   - --device <id-or-name>
4. Add interactive selection fallback when no device provided.
5. Add validation and actionable error messaging.

## TDD Tasks
1. Write failing unit tests for parsing and validating device arguments.
2. Write failing tests for interactive selection flow using mocked adapter.
3. Implement adapter protocol and fake adapter for tests.
4. Implement production device discovery wrapper.
5. Add tests for not-found and no-device scenarios.
6. Run targeted tests, then full suite.

## Acceptance Criteria
- --list-devices prints available input devices with stable IDs.
- --device accepts valid ID/name and selects device.
- Missing --device triggers interactive prompt selection.
- Invalid device returns clear error and non-zero exit.
- Behavior is deterministic across runs on same machine state.

## Risks
- Audio backend returns inconsistent device names across platforms.
- Interactive prompts may behave differently in non-TTY contexts.

## Definition of Done
- Acceptance criteria verified by tests and manual smoke check.
- Cross-platform behavior assumptions documented.
