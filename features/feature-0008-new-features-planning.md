# Feature 0008: New Features Planning - Post-MVP Enhancements

## Status
Completed

## Overview
The ARCHITECTURE.md document outlines several "New Features" that extend the core MVP functionality. This document organizes them into actionable feature requests and identifies implementation priorities.

## Features from ARCHITECTURE.md

### 1. Theme Capability System (Feature 0009)
**Description:** Allow users to specify a complete visual theme with customizable parameters and color codes for:
- Axis (border/frame)
- Axis labels (frequency and dB text)
- Peak markers
- Bar values (spectrum bars)
- Background and foreground colors

**Current State:**
- Built-in profiles are available directly through `--profile`.
- Optional JSON profile files are supported through `--profile-file`.
- Individual overrides exist for `--color-axis`, `--color-label`, `--color-bar`, and `--color-peak`.
- Profiles can define rendering defaults including `volume_mode`.

**Implemented:**
- Added built-in profiles: `default`, `studio`, `minimal`, and `high-contrast`.
- Added file-based profile loading with schema validation.
- Added CLI color overrides and profile-based defaults.
- Added profile-level `volume_mode`, with `studio` defaulting to `absolute`.

**Acceptance Criteria:**
- [x] At least 3 predefined themes/profiles are available
- [x] Individual color flags override profile settings
- [x] Custom profile behavior can be tested without relying only on file-based themes
- [x] Existing `--bar-char` and `--peak-char` behavior remains supported
- [x] Tests verify profile loading and color handling

---

### 2. Centered Title with Version Display (Feature 0010)
**Description:** Display a centered title "eq-cli" with version number at the top of the graph output.

**Current State:**
- Title and version display are implemented.
- Title can be disabled with `--no-title`.

**Implemented:**
- Version is resolved dynamically from package metadata.
- The renderer shows a centered title row.
- Title visibility is controlled by CLI flags and profiles.

**Acceptance Criteria:**
- [x] Title displays centered, matching graph width
- [x] Version is read from package metadata
- [x] Title can be toggled on/off via CLI flag
- [x] Tests verify title centering behavior
- [x] Title does not interfere with rendering behavior

---

### 3. Enhanced dB Scale Marker Distance Control (Feature 0011)
**Description:** Allow user to specify spacing between dB scale markers on the vertical axis ("there's no need for every row to have one").

**Current State:**
- `--db-interval` controls row spacing.
- `--db-marker-style` supports `all`, `spaced`, and `minimal`.
- Profiles can set marker style defaults.

**Implemented:**
- Added explicit marker density modes.
- Minimal mode reduces marker clutter significantly.
- Tests cover marker-style behavior.

**Acceptance Criteria:**
- [x] `--db-interval` remains supported
- [x] `--db-marker-style all` shows every marker row
- [x] `--db-marker-style spaced` is supported
- [x] `--db-marker-style minimal` reduces output to key rows
- [x] Tests verify marker behavior

---

### 4. Improved Axis Labels and Layout (Feature 0012)
**Description:** Enhance readability and clarity of axis labels for both frequency (horizontal) and dB (vertical).

**Current State:**
- Frequency labels are distributed across two rows at key points such as `20`, `100`, `1k`, `10k`, `15k`, and terminal `20kHz`.
- dB labels are distributed based on dB range and marker style.
- Horizontal and vertical axis styling is now consistent.

**Implemented / Current Scope:**
- Added unit-aware axis labels with a compact trailing `Hz` convention.
- Added independent axis and label colors.
- Added consistent axis styling between vertical and horizontal axes.

**Acceptance Criteria:**
- [x] Frequency labels include the terminal `Hz` unit marker in the rendered scale
- [x] dB labels include dB units
- [ ] Optional `--axis-frame` flag adds box borders
- [ ] Label alignment controlled by `--label-align`
- [x] Axis labels can be colored independently via `--color-label`
- [x] Tests verify label placement and formatting
- [x] Layout remains aligned when labels are enabled or disabled

---

## Feature Interdependencies

```
Feature 0009 (Theme) ← depends on color infrastructure
Feature 0010 (Title) ← no dependencies (can run in parallel)
Feature 0011 (dB Markers) ← existing --db-interval, verify + enhance
Feature 0012 (Axis Labels) ← extends existing label distribution logic
```

## Implementation Priority

**Phase 1 (High Priority):**
- Feature 0010: Centered title (quick win, high visibility)
- Feature 0011: Enhanced dB markers (small enhancement to existing feature)

**Phase 2 (Medium Priority):**
- Feature 0012: Improved axis labels (UX polish)

**Phase 3 (Lower Priority):**
- Feature 0009: Theme system (larger refactor, nice-to-have)

## Estimated Scope

| Feature | Tests | UI Changes | Backend | Complexity |
|---------|-------|-----------|---------|------------|
| 0010 | 3-4   | Minor     | Minor   | Low        |
| 0011 | 2-3   | None      | Minor   | Low        |
| 0012 | 4-5   | Moderate  | Minor   | Medium     |
| 0009 | 6-8   | Major     | Moderate | High       |

## Implementation Outcome

1. Implemented profile-based theme file support via `--profile-file` and `--profile`.
2. Added centered title with version and title toggle support.
3. Added dB marker styles: `all`, `spaced`, and `minimal`.
4. Made axis labels opt-in via `--axis-labels`.
5. Added color override flags: `--color-axis`, `--color-label`, `--color-bar`, `--color-peak`.
6. Added built-in profiles and profile schema validation, including profile-level `volume_mode` defaults.
7. Set the built-in `studio` profile to use `absolute` volume mode for diagnostic/studio use.
8. Investigated/fixed high-frequency visibility concern by adding explicit `15k` axis marker and regression tests validating bins exist between 10k and 20k.
9. Updated horizontal axis labeling to use compact markers with a single trailing `Hz` suffix at the end of the scale.

## Notes

- The architecture statement "20Hz to 20000kHz" appears to be a units typo; implementation uses 20 Hz to 20 kHz.

---

## Remaining Optional Enhancements

- Add an optional boxed axis/frame mode.
- Add label alignment controls if different horizontal label anchoring is needed.
- Add a `--list-profiles` command for discoverability.
