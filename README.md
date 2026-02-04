# Whoa-Scope
This repository is a fork of the O-Scope software by [Bradley Minch](https://github.com/bminch/O-Scope). It includes several small tweaks and improvements over the original O-Scope software.

Themes|Tooltips|Settings 
---|---|---
![A screenshot of Whoa-Scope in shark theme](/docs-pics/whoascope-theme.png)|![A screenshot of Whoa-Scope's tooltips](/docs-pics/whoascope-tooltips.png)|![A screenshot of Whoa-Scope's settings menu](/docs-pics/whoascope-settings.png)

## Installation
To install Whoa-Scope, head to the [releases](https://github.com/rivques/whoa-scope/releases) and download the latest version.

## Current changes from base O-Scope
* Custom color themes (light mode, etc. Feel free to request more!)
* Hover tips to describe what buttons do
* Increased window size on launch
* Improved voltmeter text formatting
* Choice of fonts and font size (Atkinson Hyperlegible, OpenDyslexic)
* Underlying codebase changes (separate UI from code, use `uv` for package management)
* Changes made by Brad after the public build was released (incl. improved USB connection management)

## Planned Changes
* Use native file picker when saving data files
* Customizeable hotkeys
* Add text to icons/arrows describing what they do
* Allow popping overlays into separate windows (difficult, poorly supported by the UI library)

## Development
To develop the project:
0. Install the [`uv` package manager](https://docs.astral.sh/uv/).
1. Clone this repository.
2. From the `Software` directory, run `uv run python O-Scope.py`.
3. Make code changes and see the results!

## Packaging
To package Whoa-Scope into a single .exe, run `uv run pyinstaller --log-level INFO .\Whoa-Scope_win.spec` (substituting linux or mac .specs as appropriate).
The output file should appear in `./dist`.
