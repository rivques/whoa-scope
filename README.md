# Whoa-Scope
This repository is a fork of [rivques](https://github.com/rivques/whoa-scope)'s fork of the original O-Scope software by [Bradley Minch](https://github.com/bminch/O-Scope). It includes even more several small tweaks and improvements over the original O-Scope software.

Themes|Tooltips|Settings 
---|---|---
![A screenshot of Whoa-Scope in shark theme](/docs-pics/whoascope-theme.png)|![A screenshot of Whoa-Scope's tooltips](/docs-pics/whoascope-tooltips.png)|![A screenshot of Whoa-Scope's settings menu](/docs-pics/whoascope-settings.png)

## Installation
To install Whoa-Scope, head to the [releases](https://github.com/rivques/whoa-scope/releases) on rivques' repository and download the latest version.

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
0. Go to rivques' repo.
1. Install the [`uv` package manager](https://docs.astral.sh/uv/).
2. Clone this repository.
3. From the `Software` directory, run `uv run python O-Scope.py`.

## Packaging
To package Whoa-Scope into a single .exe, run `uv run pyinstaller --log-level INFO .\Whoa-Scope_win.spec` (substituting linux or mac .specs as appropriate).
The output file should appear in `./dist`.
