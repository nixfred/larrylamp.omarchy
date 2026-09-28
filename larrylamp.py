#!/usr/bin/env python3
"""Larry Lamp for the Omarchy bar.

  larrylamp.py watch [--interval N]   print one JSON state line every N seconds (the Service reads it)
  larrylamp.py act <action> [text]    nod | look | sleep | wake | theme-light | ask <text> | say <text> | hooks-on | hooks-off

Talks to the lamp over your tailnet: set LAMP_URL, or put the URL on the first line of
~/.config/larry-lamp/url, so the same plugin works on every machine. Stdlib only; never raises into the bar.
"""
import json
import os
import sys
import time
import urllib.request

def _base_url():
    """LAMP_URL wins; else the first line of ~/.config/larry-lamp/url; else this machine."""
    url = os.environ.get("LAMP_URL", "").strip()
    if not url:
        try:
            with open(os.path.expanduser("~/.config/larry-lamp/url")) as f:
                url = f.readline().strip()
        except OSError:
            url = ""
    return (url or "http://127.0.0.1:8443").rstrip("/")


BASE = _base_url()
BROKER = BASE + "/larry"
DISABLED = os.path.expanduser("~/.config/larry-lamp/disabled")


def call(url, body=None, timeout=4):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="GET" if body is None else "POST",
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def safe(url, body=None, timeout=4):
    try:
        return call(url, body, timeout)
    except Exception:
        return None


def state():
    led = safe(BASE + "/led/color") or {}
    ses = safe(BROKER + "/sessions") or {}
    om = safe(BROKER + "/omarchy") or {}
    said = safe(BASE + "/voice/last-spoken") or {}
    sessions = ses.get("sessions") or []
    prio = {"wait": 5, "fail": 4, "think": 3, "ship": 2, "idle": 1}
    top = max(sessions, key=lambda s: prio.get(s.get("state"), 0), default=None)
    pal = (om.get("palette") or {})
    return {
        "online": bool(led),
        "led": {"on": led.get("on", False), "hex": led.get("hex") or "#000000", "effect": led.get("effect")},
        "sessions": [{"project": s.get("project", "?"), "host": s.get("host", "?"), "state": s.get("state", "idle"),
                      "age": s.get("age_s", 0)} for s in sessions][:12],
        "top": top.get("state") if top else "none",
        "waiting": sum(1 for s in sessions if s.get("state") == "wait"),
        "theme": pal.get("name", ""),
        "accent": (pal.get("colors") or {}).get("accent", ""),
        "locked": bool(om.get("locked")),
        "said": (said.get("text") or "")[:160],
        "saidSeq": said.get("seq", 0),
        "hooks": not os.path.exists(DISABLED),
        "console": BASE + "/static/larry-lamp.html",
        "t": int(time.time()),
    }


def act(action, text=""):
    if action == "nod":
        return safe(BASE + "/servo/play", {"recording": "nod"})
    if action == "look":
        return safe(BASE + "/servo/aim", {"direction": "user"})
    if action == "sleep":
        safe(BASE + "/servo/play", {"recording": "sleepy"})
        return safe(BASE + "/led/off", {})
    if action == "wake":
        return safe(BASE + "/servo/play", {"recording": "greeting"})
    if action == "theme-light":
        return safe(BROKER + "/omarchy/event", {"event": "theme-set", "arg": ""})
    if action == "ask" and text.strip():
        return safe(BROKER + "/ask", {"text": text.strip()[:1000]}, timeout=8)
    if action == "say" and text.strip():
        return safe(BASE + "/voice/speak", {"text": text.strip()[:600]})
    if action == "hooks-off":
        os.makedirs(os.path.dirname(DISABLED), exist_ok=True)
        open(DISABLED, "a").close()
        return {"ok": True}
    if action == "hooks-on":
        try:
            os.remove(DISABLED)
        except FileNotFoundError:
            pass
        return {"ok": True}
    return None


def main():
    args = sys.argv[1:]
    if not args or args[0] == "watch":
        interval = 2.0
        if "--interval" in args:
            try:
                interval = max(1.0, float(args[args.index("--interval") + 1]))
            except (ValueError, IndexError):
                pass
        try:
            while True:
                print(json.dumps(state()), flush=True)
                time.sleep(interval)
        except (BrokenPipeError, KeyboardInterrupt):
            sys.exit(0)
    elif args[0] == "act" and len(args) >= 2:
        r = act(args[1], " ".join(args[2:]))
        print(json.dumps({"ok": r is not None}))
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
