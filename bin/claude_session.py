"""Pair overlapping legacy and plugin SessionStart calls in Claude's session directory."""
import fcntl
import hashlib
import json
import os
import time
from pathlib import Path


def duplicate(hook, event):
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file or not event.get("session_id"):
        return False
    source = "plugin" if os.environ.get("CLAUDE_PLUGIN_ROOT") else "settings"
    fingerprint = hashlib.sha256(json.dumps([hook, event], sort_keys=True).encode()).hexdigest()
    path = Path(env_file).parent / (".lonca-" + hook)
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "r+") as state:
            fcntl.flock(state, fcntl.LOCK_EX)
            previous = state.read().split()
            now = time.monotonic()
            paired = (len(previous) == 3 and previous[0] != source and previous[1] == fingerprint
                      and 0 <= now - float(previous[2]) < 10)
            state.seek(0)
            state.truncate()
            if not paired:
                state.write(f"{source} {fingerprint} {now}")
            return paired
    except (OSError, ValueError):
        return False  # Missing session state must never suppress automation.
