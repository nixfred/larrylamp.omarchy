#!/usr/bin/env python3
"""Larry Lamp for the Omarchy bar.

  larrylamp.py watch [--interval N]   print one JSON state line every N seconds (the Service reads it)
  larrylamp.py act <action> [text]    nod | look | sleep | wake | theme-light | ask <text> | say <text> | hooks-on | hooks-off

Talks to the lamp over your tailnet: set LAMP_URL, or put the URL on the first line of
~/.config/larry-lamp/url, so the same plugin works on every machine. With neither, it talks to the
lamp services on this machine directly (HAL on 127.0.0.1:5001, broker on 127.0.0.1:5055).
Stdlib only; never raises into the bar.
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

def _base_url():
    """LAMP_URL wins; else the first line of ~/.config/larry-lamp/url; else "" (this machine)."""
    url = os.environ.get("LAMP_URL", "").strip()
    if not url:
        try:
            with open(os.path.expanduser("~/.config/larry-lamp/url")) as f:
                url = f.readline().strip()
        except OSError:
            url = ""
    return url.rstrip("/")


# A configured URL is a front door that serves HAL at / and the broker at /larry (tailscale serve).
# Without one, talk to the local services directly. The old default, http://127.0.0.1:8443, was
# never served by anything: tailscale serve listens on the tailnet address with TLS, not loopback.
_URL = _base_url()
BASE = _URL or "http://127.0.0.1:5001"
BROKER = (_URL + "/larry") if _URL else "http://127.0.0.1:5055/larry"
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


_POOL = ThreadPoolExecutor(max_workers=4)


def state():
    # In parallel: a lamp that does not answer costs one timeout per refresh, not four in a row
    futs = [_POOL.submit(safe, u) for u in (BASE + "/led/color", BROKER + "/sessions",
                                             BROKER + "/omarchy", BASE + "/voice/last-spoken")]
    led_r, ses_r, om_r, said_r = (f.result() for f in futs)
    led, ses, om, said = led_r or {}, ses_r or {}, om_r or {}, said_r or {}
    sessions = ses.get("sessions") or []

    def shown(s):
        # The broker marks sessions from a host that stopped heartbeating as stale; they never mean "needs you"
        st = s.get("state", "idle")
        return "idle" if st == "wait" and s.get("stale") else st

    prio = {"wait": 5, "fail": 4, "think": 3, "ship": 2, "idle": 1}
    top = max(sessions, key=lambda s: prio.get(shown(s), 0), default=None)
    pal = (om.get("palette") or {})
    return {
        # online = the lamp (HAL) answers; broker = the session broker answers. Either can be down alone.
        "online": led_r is not None,
        "broker": ses_r is not None,
        "led": {"on": led.get("on", False), "hex": led.get("hex") or "#000000", "effect": led.get("effect")},
        "sessions": [{"project": s.get("project", "?"), "host": s.get("host", "?"), "state": shown(s),
                      "age": s.get("age_s", 0)} for s in sessions][:12],
        "top": shown(top) if top else "none",
        "waiting": sum(1 for s in sessions if shown(s) == "wait"),
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
