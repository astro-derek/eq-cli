# Feature 0009: Theme Capability System

## Status
Planned

## Goal
Add profile-based theming with configurable ANSI colors for axis, labels, bars, and peaks.

## Requirements
- Support loading a profile from a file path.
- Support selecting a named profile from that file.
- Allow per-flag CLI overrides for colors.
- Preserve monochrome fallback when color is disabled.

## Acceptance Criteria
- [ ] CLI accepts profile file and profile name.
- [ ] Renderer uses profile colors for bars, peaks, axis, and labels.
- [ ] Invalid profile file produces clear error.
- [ ] Tests cover profile loading and color application.
