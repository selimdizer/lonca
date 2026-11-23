#!/usr/bin/env python3
"""Exercise job boundaries without registering a real project or contacting a service."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import time

BIN = Path(__file__).resolve().parents[1] / "bin"


def check(home):
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"), PYTHONDONTWRITEBYTECODE="1")
    env.pop("LONCA_PROJECT", None)
    logs = home / "calls"
    stubs = home / "bin"
    stubs.mkdir()
    for name in ("gh", "hc", "kanzo", "claude", "deja"):
        cli = stubs / name
        cli.write_text('#!/bin/sh\necho invoked >> "$HOME/calls"\nexit 1\n')
        cli.chmod(0o755)
    env["PATH"] = str(stubs) + os.pathsep + env["PATH"]

    def run(program, *args, **kwargs):
        return subprocess.run([program, *args], cwd=home, env=env, text=True, capture_output=True, check=True, **kwargs).stdout

    (home / "lonca").symlink_to(BIN.parent)
    for name in ("lane-watch", "ai-cleanup", "memory-review", "kanzo-sync", "monthly-card"):
        run(BIN / name)
    for job in ("deja-index", "ai-memory-commit", "kanzo-backup"):
        run(BIN / "project-job", job)
    assert not logs.exists() and not (home / ".local/state/lonca").exists()

    root = home / "project"
    root.mkdir()
    run("git", "-C", root, "init", "-q")
    (root / ".lonca.toml").write_text('name = "test"')
    registry = home / ".local/state/lonca/projects"
    registry.mkdir(parents=True)
    digest = hashlib.sha256(os.fsencode(root)).hexdigest()
    common = root / ".git"
    st = common.stat()
    (registry / (digest + ".json")).write_text(json.dumps({"root": str(root), "repos": {str(root): {
        "ready": True, "common": str(common), "identity": [st.st_dev, st.st_ino]}}}))
    temp = home / ".cache/lonca/tmp"
    temp.mkdir(parents=True)
    other = temp / "session-personal"
    other.mkdir()
    event = json.dumps({"cwd": str(root), "session_id": "fixture"})
    env["CLAUDE_ENV_FILE"] = str(home / "session-env")
    env.pop("TMPDIR", None)
    run(BIN / "session-tmpdir", input=event)
    owned = Path((home / "session-env").read_text().strip().split("=", 1)[1])
    assert owned.parent == temp and owned.exists()
    assert str(owned) in run(BIN / "ai-cleanup", "--dry-run", "--tmp-age-hours", "0")
    run(BIN / "ai-cleanup", "--tmp-age-hours", "0")
    assert not owned.exists() and other.is_dir()
    # A name or path alone never proves ownership of a replacement directory.
    run(BIN / "session-tmpdir", input=event)
    owned = Path((home / "session-env").read_text().strip().splitlines()[-1].split("=", 1)[1])
    owned.rename(home / "previous-directory")
    owned.mkdir()
    run(BIN / "ai-cleanup", "--tmp-age-hours", "0")
    assert owned.is_dir()

    encoded = re.sub(r"[^a-zA-Z0-9]", "-", str(root))
    folder = home / ".claude/projects" / encoded
    folder.mkdir(parents=True)
    def event_for(cwd, text):
        return json.dumps({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cwd": str(cwd),
                           "type": "user", "message": {"content": text}})
    (folder / "fixture.jsonl").write_text(event_for(root, "inside sample") + "\n" + event_for(home, "outside sample"))
    run(BIN / "memory-review", "--dry-run")
    summary, = (home / ".cache/ai-runs/setup/history-mining").glob("review-*.md")
    assert "inside sample" in summary.read_text() and "outside sample" not in summary.read_text()
    assert not logs.exists()


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as folder:
        check(Path(folder).resolve())
    print("project job boundaries passed")
