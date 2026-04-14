# Feature 0020: Spectrum Processing Refresh-Rate Headroom

## Status
Completed

## Objective
Profile and optimize the current Python implementation to increase refresh-rate headroom without changing user-visible behavior, starting with the actual DSP hot path in spectrum aggregation.

## Scope
- Profile the current frame-processing path to identify the dominant per-frame costs.
- Optimize `SpectrumProcessor.process_frame(...)` to reduce repeated allocations and mask construction.
- Preserve current spectrum behavior, including band edge handling, relative-mode smoothing, and absolute-mode calibration.
- Keep return types and public CLI behavior unchanged.
- Update tests to cover frame-size changes and round-trip correctness during optimization.

## Out of Scope
- Rewriting the application in Rust.
- Redesigning the renderer or terminal redraw strategy in this pass.
- Changing user-facing defaults or profile settings.
- Introducing optional compiled extensions.

## Dependencies
- Existing spectrum processing implementation in `src/eq_cli/spectrum.py`.
- Existing performance baseline in `tests/test_spectrum.py`.
- Existing audio/render loop behavior, which should continue to work unchanged after the optimization.

## Implementation Plan
1. Add characterization tests for repeated frame processing and frame-size changes.
2. Capture a local before/after profile of the current `process_frame(...)` hot path.
3. Cache frame-size-specific data inside `SpectrumProcessor`, including the Hann window and FFT frequency bins.
4. Replace per-band boolean mask construction with precomputed contiguous FFT-bin index ranges.
5. Reuse stable data such as band center tuples to reduce per-frame conversion churn.
6. Re-run targeted tests, then full validation, and capture the new local profile result.

## TDD Tasks
1. Add failing tests for consistent output across repeated same-size frames.
2. Add failing tests for correct behavior when frame size changes between calls.
3. Add a local benchmarking/profiling step to measure current `process_frame(...)` timing.
4. Implement minimal caching and aggregation changes until the tests pass.
5. Re-run the coarse throughput test and compare local profiling output before and after.

## Acceptance Criteria
- The optimized processor preserves current visible spectrum behavior.
- The processor supports repeated calls with the same frame size and changing frame sizes without incorrect caching.
- The current test suite, Ruff, and mypy all pass.
- Local profiling shows a measurable reduction in `process_frame(...)` runtime.

## Results
- Replaced per-band boolean mask construction with cached FFT-bin index ranges.
- Cached frame-size-specific Hann windows and FFT frequency bins.
- Reused the precomputed band-center tuple instead of rebuilding it every frame.
- Local side-by-side benchmark of the old boolean-mask path versus the optimized path showed:
	- frame size `2048`: about `3.30x` faster
	- frame size `4096`: about `3.43x` faster

## Risks
- Band-edge off-by-one errors can change high-frequency or Nyquist-bin behavior.
- Relative-mode smoothing can drift if the normalization path changes unintentionally.
- Cache invalidation bugs can appear when frame size changes between frames.
- End-to-end refresh rate may still be limited by terminal redraw even after DSP optimization.

## Definition of Done
- The DSP hot path is optimized with tests protecting correctness.
- Local profiling numbers are captured and summarized.
- The implementation checklist is updated after validation passes.