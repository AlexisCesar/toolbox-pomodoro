# Pomodoro Addon for Toolbox

A small, dependency-free Pomodoro timer that demonstrates the Toolbox Addon API
version 1. It provides a 25 minute focus session, a 5 minute short break, and a
15 minute long break after every fourth completed focus session.

## Addon behavior

- Start, pause, and reset the current timer.
- The timer updates every second while the Pomodoro tab is open.
- When a focus countdown ends, the next break is selected and paused. Start it
  when you are ready.
- When a break ends, the next focus session is selected and paused.
- Reset returns to a focus session but keeps the completed focus session count.
- Timer state is kept in memory by Toolbox for the current app session. Closing
  Toolbox resets the timer.

## Install

Once this repository is hosted, open Toolbox and choose **Addons**. Paste the
repository's HTTPS or SSH Git URL and select **Install**. Toolbox validates the
manifest and adds Pomodoro to the sidebar.

The manifest is toolbox-addon.json. Its refresh interval is one second, so the
Toolbox host invokes this Addon once per second while its view is visible. The
Addon itself has no third-party package dependencies. Python must be available
on PATH as python.

## Develop and verify

Run the Addon tests with:

    python -m unittest -v

The tests use a controlled clock, so they do not wait for real timer intervals.

The host starts addon.py once per request. It reads a single JSON object from
stdin and writes one JSON object to stdout. Keep diagnostics on stderr; stdout
must contain only the protocol response. The Toolbox README documents the full
manifest and JSON Lines contract.
