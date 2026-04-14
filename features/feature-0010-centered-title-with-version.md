# Feature 0010: Centered Title With Version

## Status
Planned

## Goal
Show a centered title line with app name and version.

## Requirements
- Default title text: eq-cli v<version>.
- Version resolved from package metadata with safe fallback.
- Title can be disabled via CLI parameter.

## Acceptance Criteria
- [ ] Title appears centered to graph width.
- [ ] Title includes version.
- [ ] Title opt-out works.
- [ ] Tests verify centering and toggle behavior.
