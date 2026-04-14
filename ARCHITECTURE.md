# Architecture
We want a python program that takes audio input and generates an eq graph.

## Introduction
- Use python code to generate a stand-alone user interface.
- Generate a basic CLI type interface as our first pass. 
- Include colors, a peak marker for each frequency, axis labels showing the
kHz values and dB values.
- It should be possible to specify any available audio input as the source
for the graph.
- Horizontal axis should display frequencies from 20Hz to 20kHz
- Use a logarithmic scale.

## Deployment
- Use python and pip to install the package.
- Build distribution artifacts as standard Python `sdist` and `wheel` outputs.
- Use GitHub Actions to validate builds on `main` and produce release assets
	from version tags.

## New Features
- Add a "theme" capability that allows the user to specify values for each
of the parameters and specific color codes for axis, labels, peaks and bar
values.
- Add a parameter that allows us to specify the distance between dB scale 
markers - there's no need for every row to have one.
- Add a title which is centered horizontally `eq-cli` and include the version.
- Add labels to the axes to reflect the units being used. eg: dB and Hz.

## Current Rendering Notes
- The horizontal axis uses compact intermediate markers such as `20`, `100`,
	`1k`, and `15k`, with the `Hz` suffix shown at the end of the scale.
- The built-in `studio` profile uses `absolute` volume mode because it is the
	more useful mode for observing real filter boost/cut behavior over time.

## Implemented Enhancements
- Profiles/themes are supported through built-in presets and optional JSON
	profile files.
- Profiles can also define rendering defaults such as `volume_mode`, and the
	built-in `studio` profile defaults to `absolute` mode for diagnostic use.
- Title rendering with version information is supported.
- Axis labels are supported, are opt-in through CLI parameters, and use compact
	horizontal markers such as `20`, `1k`, `15k`, and `20kHz`, with the `Hz`
	suffix shown at the end of the horizontal scale instead of on every marker.
- dB marker density is configurable.
- The horizontal and vertical axes now use a consistent rendered appearance.

## Resolved Issues
- High-frequency registration between 10k and 20k was investigated.
	- The processor does generate and detect bands above 10k.
	- The chart now includes an explicit 15k marker so the upper range is easier
		to read.
	- In `absolute` volume mode, weak high-frequency content may still appear to
		drop out because the chart uses a fixed reference level instead of
		auto-normalizing the signal. This is expected behavior, and many microphones
		and input chains also roll off strongly above about 10k.
- When there is extreme quiet or no sound coming through the device, the chart
	no longer keeps a row of bar symbols or decayed peak markers pinned to the
	minimum floor.

## Open UI Bug
- No open UI bugs currently captured here.