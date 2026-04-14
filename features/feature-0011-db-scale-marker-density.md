# Feature 0011: dB Scale Marker Density

## Status
Planned

## Goal
Add explicit marker density modes so not every dB row needs a marker.

## Requirements
- Add mode parameter for marker style: all, spaced, minimal.
- Keep existing db-interval behavior.
- Ensure row prefixes and marker visuals match selected mode.

## Acceptance Criteria
- [ ] all mode shows marker every row.
- [ ] spaced mode respects db-interval spacing.
- [ ] minimal mode shows only max, midpoint, min markers.
- [ ] Tests verify each mode.
