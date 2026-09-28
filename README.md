# Larry Lamp for Omarchy

Bar widget for Larry's Autonomous Lamp: a ring lit in the lamp's real LED colour (breathing when it
breathes), an amber count when a Claude Code session needs you, and a panel with every session,
Larry's last words, an ask-Larry box and lamp controls. The lamp itself follows your Omarchy theme.

Talks to the lamp broker over your tailnet. Set `LAMP_URL`, or put the URL on the first line of
`~/.config/larry-lamp/url` (default `http://127.0.0.1:8443`), so the same plugin runs on every machine.
Backend: `larrylamp.py` (python3 stdlib).
