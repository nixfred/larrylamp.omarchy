#!/usr/bin/env python3
"""Larry Lamp for the Omarchy bar.

  larrylamp.py watch [--interval N]   print one JSON state line every N seconds (the Service reads it)
  larrylamp.py act <action> [text]    nod | look | sleep | wake | theme-light | ask <text> | say <text> | hooks-on | hooks-off

Which lamp: ~/.config/larry-lamp/target.env, written by `lamp target sim|real` (larry-lamp repo),
so the bar follows the cutover from the simulator to the real lamp with nothing to edit here.
Precedence: environment (LAMP_URL, LAMP_BROKER) > target.env > the older one-line
~/.config/larry-lamp/url > this machine (HAL 127.0.0.1:5001, broker 127.0.0.1:5055).

Tokens are read from files, never from this plugin: the lamp's (LAMP_TOKEN_FILE in target.env,
sent as a Bearer to the HAL) and the broker's (~/.config/larry-lamp/broker.token, sent as
X-Larry-Token). Stdlib only; never raises into the bar.
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

CONF = os.environ.get("LARRY_LAMP_CONF") or os.path.expanduser("~/.config/larry-lamp")
LOCAL_HAL = "http://127.0.0.1:5001"
LOCAL_BROKER = "http://127.0.0.1:5055/larry"


def _read(path):
    try:
        with open(os.path.expanduser(path)) as f:
            return f.read()
    except OSError:
        return ""


def _first_line(path):
    lines = _read(path).strip().splitlines()
    return lines[0].strip() if lines else ""


def _target():
    """LAMP_* settings: target.env, then the legacy url file, then non-empty environment."""
    t = {}
    for line in _read(os.path.join(CONF, "target.env")).splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            t[k.strip()] = v.strip().strip("\"'")
    if not t.get("LAMP_URL"):
        url = _first_line(os.path.join(CONF, "url")).rstrip("/")
        if url:  # the older front door: HAL at /, broker at /larry
            t.setdefault("LAMP_URL", url)
            t.setdefault("LAMP_BROKER", url + "/larry")
    t.update({k: v for k, v in os.environ.items() if k.startswith("LAMP_") and v})
    return t


_T = _target()
BASE = (_T.get("LAMP_URL") or LOCAL_HAL).rstrip("/")
# The simulator and the real lamp never serve /larry: the broker lives next to the bar
BROKER = (_T.get("LAMP_BROKER") or LOCAL_BROKER).rstrip("/")
TARGET = _T.get("LAMP_TARGET", "")
HAL_TOKEN = _T.get("LAMP_TOKEN") or (_first_line(_T["LAMP_TOKEN_FILE"]) if _T.get("LAMP_TOKEN_FILE") else "")
BROKER_TOKEN = _T.get("LAMP_BROKER_TOKEN") or _first_line(
    _T.get("LAMP_BROKER_TOKEN_FILE") or os.path.join(CONF, "broker.token"))
DISABLED = os.path.join(CONF, "disabled")


def call(url, body=None, timeout=4):
    data = None if body is None else json.dumps(body).encode()
    headers = {"content-type": "application/json"}
    if url.startswith(BROKER + "/"):
        if BROKER_TOKEN:
            headers["x-larry-token"] = BROKER_TOKEN
    elif HAL_TOKEN:
        headers["authorization"] = "Bearer " + HAL_TOKEN
    req = urllib.request.Request(url, data=data, method="GET" if body is None else "POST", headers=headers)
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
        "target": TARGET or ("sim" if BASE == LOCAL_HAL else ""),
        "t": int(time.time()),
    }


def act(action, text=""):
    if action == "nod":
        return safe(BASE + "/servo/play", {"recording": "nod"})
    if action == "look":
        return safe(BASE + "/servo/aim", {"direction": "user"})
    if action == "sleep":
        safe(BASE + "/servo/play", {"recording": "sleepy"})
        # transient: a muted lamp keeps its mic-muted light (a plain /led/off would dismiss it)
        return safe(BASE + "/led/off", {"transient": True})
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
