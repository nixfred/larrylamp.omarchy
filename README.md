<p align="center">
  <img src="assets/banner.svg" alt="Larry Lamp for Omarchy" width="100%">
</p>

<p align="center">
  <img alt="Omarchy plugin" src="https://img.shields.io/badge/Omarchy-bar%20plugin-22e3ff?style=flat-square">
  <img alt="Quickshell QML" src="https://img.shields.io/badge/Quickshell-QML-41cd52?style=flat-square&logo=qt&logoColor=white">
  <img alt="Python stdlib" src="https://img.shields.io/badge/python3-stdlib%20only-3776ab?style=flat-square&logo=python&logoColor=white">
  <img alt="Version" src="https://img.shields.io/badge/version-0.1.0-ffb020?style=flat-square">
  <img alt="License MIT" src="https://img.shields.io/badge/license-MIT-2dff9a?style=flat-square">
</p>

# Larry Lamp for Omarchy

Bar widget for Larry's Autonomous Lamp: a ring lit in the lamp's real LED colour (breathing when it
breathes), an amber count when a Claude Code session needs you, and a panel with every session,
Larry's last words, an ask-Larry box and lamp controls. The lamp itself follows your Omarchy theme.

## How it fits together

<p align="center">
  <img src="assets/architecture.svg" alt="Bar widget and panel read a Quickshell service that runs larrylamp.py, which polls the lamp HAL and the session broker" width="100%">
</p>

- **BarWidget.qml**: the ring on the bar, in the colour the lamp's LED ring shows right now, plus an
  amber badge with the number of sessions waiting on you.
- **LampPanel.qml**: click the ring. Sessions, what Larry last said, an ask box, nod / look / wake /
  sleep / theme light, mute this machine's sessions, open the console.
- **Service.qml**: runs `larrylamp.py watch` and keeps its latest JSON line. Actions run as one-shot
  processes with an argv list, never through a shell, so a slow lamp never blocks the bar.
- **larrylamp.py**: python3 standard library only. Polls the lamp HAL and the session broker in
  parallel and never raises into the bar. The bar tells "lamp not answering" apart from "nothing
  answering", so sessions keep working while the lamp is off.

## Where it looks for the lamp

1. `LAMP_URL`, or the first line of `~/.config/larry-lamp/url`: one URL that serves the lamp HAL at
   `/` and the broker at `/larry` (for example a `tailscale serve` front door), so the same plugin
   runs on every machine.
2. Otherwise this machine's services directly: HAL on `http://127.0.0.1:5001`, broker on
   `http://127.0.0.1:5055/larry`.

## Install

Copy or symlink this directory to `~/.config/omarchy/plugins/nixfred.larrylamp`, then add
**Larry Lamp** to your bar from the Omarchy bar settings. Open the panel from a script with
`omarchy-shell nixfred.larrylamp toggle`.

## License

MIT, see [LICENSE](LICENSE).
