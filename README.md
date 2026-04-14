# eq-cli

Terminal-based real-time equalizer for live audio input.

## Requirements

- Python 3.12 or newer
- pip

## Installation

### Step 1. Install dependencies

```sh
pip install -r requirements.txt
```

Or install directly from the project folder:

```sh
pip install .
```

### Step 2. Verify the install

```sh
eq-cli --help
```

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

### Enable axis labels (opt-in)

```sh
eq-cli --device <identifier-or-name> --axis-labels
```

### Configure title and dB marker style

```sh
eq-cli --device <identifier-or-name> --no-title --db-marker-style minimal
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

### Use a built-in profile directly

```sh
eq-cli --device <identifier-or-name> --profile studio
```

Built-in profiles:

- `default`: current standard layout and colors
- `studio`: title on, labels on, sparse dB markers, bright colors, `absolute` volume mode, `peak_hold_frames=12`
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
- `q`: quit

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
pip install pytest
pytest
```

## Linting and type checking

```sh
pip install ruff mypy
ruff check .
mypy src
```

