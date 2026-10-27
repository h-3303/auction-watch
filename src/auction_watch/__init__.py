"""auction-watch: twice-daily domain auction scans and pre-close push alerts."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import notify, runner, sources, state

STATE_FILE = Path(os.environ.get("STATE_FILE", "state.enc"))


def _load(key):
    return state.unseal(STATE_FILE.read_bytes(), key) if STATE_FILE.exists() else {"watch": [], "gems_seen": []}


def _save(st, key):
    STATE_FILE.write_bytes(state.seal(st, key))


def main(argv=None):
    cmd = (argv or sys.argv[1:] or ["tick"])[0]
    key, topic = os.environ["STATE_KEY"], os.environ["NTFY_TOPIC"]
    push = lambda title, body, click: notify.push(topic, title, body, click)
    now = datetime.now(timezone.utc)
    st = _load(key)
    if cmd == "tick":
        changed = runner.tick(st, now, sources.live_price, push)
        # No domain names in logs: the repo is public.
        print(f"tick: {len(st['watch'])} watched, changed={changed}")
        if changed:
            _save(st, key)
    elif cmd == "scan":
        with sources.HumbleWorth() as hw:
            picks = runner.scan(st, sources.godaddy_rows(), now, hw.estimate, push)
            fresh = runner.gems(st, hw.gems(), push)
        hw = sum(1 for p in picks if p.get("estimate_source") == "humbleworth")
        print(f"scan: {len(picks)} auction picks ({hw} HumbleWorth-valued), {len(fresh)} registrable gems, "
              f"{len(st['watch'])} watched")
        _save(st, key)
    elif cmd == "show":
        for i in sorted(st["watch"], key=lambda i: i["close"]):
            print(i["close"], i["domain"], f"max ${i['max_bid']}", "alerted" if i.get("alerted") else "")
    else:
        sys.exit(f"unknown command {cmd!r}; use tick, scan or show")
