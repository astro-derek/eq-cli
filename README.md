# eq-cli

Terminal-based real-time equalizer for live audio input.

## Requirements

- Python 3.12 or newer
- pip
- A virtual environment for installation on macOS and most Linux distributions

## Installation

On macOS, Python installed via Homebrew is usually an externally managed
environment. Installing with `pip install .` against the system interpreter can
fail with `externally-managed-environment`. Use a virtual environment instead.

### Step 1. Create and activate a virtual environment

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### Step 2. Install the package

```sh
python -m pip install .
```

For development, use an editable install instead:

```sh
python -m pip install -e .
```

### Step 3. Verify the install

```sh
eq-cli --help
```

## Release And Distribution

The repository is configured to produce Python distribution artifacts from
GitHub Actions.

### CI validation

Pushes and pull requests to `main` should run a CI workflow that:

- runs `pytest`
- runs `ruff`
- runs `mypy`
- runs `python -m build`

This confirms that the repo is still capable of producing deployable Python
artifacts.

### Cut a release

To create deployable artifacts for a release:

1. Update the version in `pyproject.toml`.
2. Commit the version bump on `main`.
3. Create an annotated tag such as `v0.1.0`.
4. Push the branch and tag.

Example:

```sh
git checkout main
git pull --ff-only origin main
git add pyproject.toml
git commit -m "release v0.1.1"
git tag -a v0.1.1 -m "v0.1.1"
git push origin main --tags
```

Current manual release trigger sequence:

```sh
git checkout main
git pull --ff-only origin main
# edit pyproject.toml version
git add pyproject.toml README.md
git commit -m "release v0.1.1"
git tag -a v0.1.1 -m "v0.1.1"
git push origin main --tags
```

This manual sequence is the current source of truth for releases and is a good
candidate for future automation once the release flow has been exercised a few
times.

The release workflow builds `sdist` and `wheel` artifacts and attaches them to
the corresponding GitHub Release.

## Usage

`eq-cli` captures live input from your selected device and renders a real-time
spectrum in the terminal. A typical workflow is: pick a device, choose a
profile or mode, then tune behavior with options like refresh rate, labels,
history rows, and colors.

The examples below are grouped by common tasks so you can copy a baseline
command and then layer additional options as needed.

### List available audio input devices

```sh
eq-cli --list-devices
```

### List built-in profiles

```sh
eq-cli --list-profiles
```

### Apply convenience mode presets

```sh
eq-cli --device <identifier-or-name> --mode studio
eq-cli --device <identifier-or-name> --mode live
eq-cli --device <identifier-or-name> --mode debug
```

Mode behavior:

- `studio`: defaults toward analysis (`profile=studio`, `volume_mode=absolute`)
- `live`: defaults toward responsiveness (`refresh_rate=60`, light peak hold)
- `debug`: high-visibility labels/markers for inspection

Explicit CLI flags take precedence over mode defaults.

### Start the equalizer with a specific device

```sh
eq-cli --device <identifier-or-name>
```

### Control redraw rate (for example, 60 Hz)

```sh
eq-cli --device <identifier-or-name> --refresh-rate 60
```

Note: higher refresh rates increase CPU usage and may require smaller stream
blocks; this tool automatically adjusts stream block size based on the chosen
refresh rate.

### Set an explicit audio block size

```sh
eq-cli --device <identifier-or-name> --block-size 2048
```

`--block-size` overrides the auto-tuned audio callback size when you want more
direct control over latency and stability.

### Save a one-shot chart snapshot

```sh
eq-cli --device <identifier-or-name> --snapshot-file snapshots/current.txt
eq-cli --device <identifier-or-name> --snapshot-file snapshots/current.ansi --snapshot-format ansi
```

`--snapshot-file` captures the first usable chart frame, writes it to disk, and
exits. Use `--snapshot-format txt` for plain text or `--snapshot-format ansi`
to preserve terminal color codes.

### Set a custom graph height

```sh
eq-cli --device <identifier-or-name> --graph-height 14
```

`--graph-height` controls the number of rendered spectrum rows. If omitted, the
height is derived from the current dB scale. `--db-interval` controls dB label
density on the vertical axis rather than the physical graph height.

### Enable axis labels (opt-in)

```sh
eq-cli --device <identifier-or-name> --axis-labels
```

When axis labels are enabled, matching notches are drawn on the horizontal and
vertical axes so labeled frequencies and dB markers are easier to follow.

### Use custom horizontal label frequencies

```sh
eq-cli --device <identifier-or-name> --axis-labels --axis-frequencies 50,100,200,500,1000,5000
```

`--axis-frequencies` accepts a comma- or space-separated list of frequencies in
Hz. Labels outside the visible analysis range are skipped automatically.

### Show numeric dB labels on peak markers

```sh
eq-cli --device <identifier-or-name> --peak-db-labels
```

`--peak-db-labels` overlays rounded absolute peak dB values above the matching peak band
when that band is wide enough and there is a free row above the peak. Use
`--no-peak-db-labels` to explicitly disable them when a profile enables them.

### Configure title and dB marker style

```sh
eq-cli --device <identifier-or-name> --no-title --db-marker-style minimal
eq-cli --device <identifier-or-name> --graph-height 12 --db-marker-style all
```

### Configure peak hold behavior

```sh
eq-cli --device <identifier-or-name> --peak-hold-frames 12
```

`--peak-hold-frames` controls how many rendered frames a peak marker is held
before it starts decaying.

### Select stereo analysis mode

```sh
eq-cli --device <identifier-or-name> --channel-mode mono
eq-cli --device <identifier-or-name> --channel-mode left
eq-cli --device <identifier-or-name> --channel-mode right
eq-cli --device <identifier-or-name> --channel-mode sum
eq-cli --device <identifier-or-name> --channel-mode mid
eq-cli --device <identifier-or-name> --channel-mode side
```

`--channel-mode` controls how input channels are analyzed for the spectrum.

### Enable history view (lightweight waterfall)

```sh
eq-cli --device <identifier-or-name> --history-rows 6
eq-cli --device <identifier-or-name> --history-rows 6 --history-gradient " .:-=+*#%@"
eq-cli --device <identifier-or-name> --history-rows 6 --color-history yellow
```

`--history-rows` adds recent spectrum rows below the main plot. Set `0` to
disable history output.

`--history-gradient` controls the character ramp used by the history view from
low to high intensity.

`--color-history` controls the color of history rows independently from live
bar color.

### Use a named profile from a profile file

```sh
eq-cli --device <identifier-or-name> --profile-file profiles/theme_profiles.json --profile studio
```

Profile files can now carry both visual styling and runtime tuning values such
as `gain`, `refresh_rate`, `block_size`, `axis_frequencies`, `snapshot_file`,
`snapshot_format`, and `snapshot_dir`.

### Use a built-in profile directly

```sh
eq-cli --device <identifier-or-name> --profile studio
```

Built-in profiles:

- `default`: current standard layout and colors
- `studio`: tall wide graph, no history rows, underscore peak markers, sparse dB markers, bright colors, `absolute` volume mode, `db_range=-76..0`, `peak_hold_frames=12`, runtime snapshots default to ANSI format in `snapshots/`
- `green-based`: green-focused profile with axis/labels/bars/history in green tones and `peak_hold_frames=6`
- `minimal`: compact monochrome-style layout with minimal labeling
- `high-contrast`: labels on, dense markers, strong contrast colors, `peak_hold_frames=4`

Example invocations:

```sh
eq-cli --device <identifier-or-name> --profile default
eq-cli --device <identifier-or-name> --profile studio
eq-cli --device <identifier-or-name> --profile green-based
eq-cli --device <identifier-or-name> --profile minimal
eq-cli --device <identifier-or-name> --profile high-contrast
```

### Studio recommendation

For studio work such as checking the effect of a filter sweep on the audio
signal, prefer `absolute` volume mode so boosts and cuts remain meaningful over
time instead of being re-normalized every frame.

Recommended command:

```sh
eq-cli --device <identifier-or-name> --profile studio
```

Equivalent explicit command:

```sh
eq-cli --device <identifier-or-name> --profile studio --volume-mode absolute
```

### Override profile colors from CLI

```sh
eq-cli --device <identifier-or-name> --profile-file profiles/theme_profiles.json --profile studio --color-axis 90 --color-label bright_white --color-bar cyan --color-peak red
eq-cli --device <identifier-or-name> --profile-file profiles/theme_profiles.json --profile studio --color-history yellow
```

The same overrides work with built-in profiles:

```sh
eq-cli --device <identifier-or-name> --profile high-contrast --color-bar green --color-peak bright_red
```

### Profile file validation

Profile files are validated field-by-field. If a profile contains an unknown key,
an invalid marker style, or an unsupported color value, `eq-cli` reports the
specific profile field that failed validation.

### Start the equalizer with interactive device selection

```sh
eq-cli
```

Select a device from the numbered prompt that appears.

On startup, the CLI also prints the active render settings (profile, mode,
volume mode, channel mode, peak hold frames, history rows, and refresh rate).

During runtime on supported terminals (Windows, macOS, Linux), keyboard hotkeys are available:

- `f`: freeze/unfreeze the display
- `r`: reset peak markers
- `s`: save a snapshot of the current chart
- `p`: export the current effective profile settings
- `q`: quit

Runtime snapshots are written to the current working directory by default. You
can override the target directory with:

```sh
eq-cli --device <identifier-or-name> --snapshot-dir snapshots
```

The built-in `studio` profile defaults runtime snapshots to ANSI output in the
`snapshots/` directory.

Runtime profile exports are written to the current working directory as
`eq-cli-profile-001.json`, `eq-cli-profile-002.json`, and so on. Each file is a
valid profile file containing one profile named after the file stem, including
the current runtime tuning values that can be loaded back with `--profile-file`.

The shortcuts/status legend is shown on-screen by default and includes freeze
state (`ON`/`OFF`). You can hide it with:

```sh
eq-cli --device <identifier-or-name> --no-shortcuts
```

## Platform notes

| Platform | Tested | Notes |
|----------|--------|-------|
| Windows  | Intended | Requires PortAudio via sounddevice wheel. |
| macOS    | Intended | PortAudio is bundled in the sounddevice wheel. |
| Linux    | Intended | May require `apt install libportaudio2` or equivalent. |

## Running tests

```sh
python -m pip install -e . pytest
python -m pytest
```

## Linting and type checking

```sh
python -m pip install -e . ruff mypy
python -m ruff check .
python -m mypy src
```

