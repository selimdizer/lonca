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
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               GIT_CONFIG_GLOBAL=str(home / ".gitconfig"), GIT_CONFIG_NOSYSTEM="1", PYTHONDONTWRITEBYTECODE="1")
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
    run(BIN / "project-job", "kanzo-backup")
    memory = home / "ai-memory"
    memory.mkdir()
    run("git", "-C", memory, "init", "-q")
    (memory / "MEMORY.md").write_text("fixture")
    run(BIN / "project-job", "ai-memory-commit")
    run(BIN / "project-job", "ai-memory-commit")
    assert run("git", "-C", memory, "rev-list", "--count", "HEAD").strip() == "1"
    assert run("git", "-C", memory, "show", "HEAD:MEMORY.md") == "fixture"
    assert not logs.exists() and not (home / ".local/state/lonca").exists()

    backups = home / ".local/state/lonca/migration-backups"
    create_backup = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from lonca_legacy import Legacy
legacy = Legacy()
legacy.backup(Path.home() / ".gitconfig", {"core.hooksPath": "fixture"})
print(legacy.directory)
"""
    backup = Path(run("python3", "-c", create_backup, str(BIN)).splitlines()[-1])
    receipt = backup / "changes.jsonl"
    assert receipt.stat().st_mode & 0o777 == 0o600
    assert json.loads(receipt.read_bytes())["removed"] == {"core.hooksPath": "fixture"}
    old_layout = backups / "tmp12345678"
    (old_layout / "filesystem").mkdir(parents=True)
    foreign = backups / "personal"
    foreign.mkdir()
    recent = backups / "migration-87654321"
    recent.mkdir()
    (recent / "changes.jsonl").touch()
    for folder in (backup, old_layout, foreign):
        os.utime(folder, (1, 1))
    assert str(backup) in run(BIN / "ai-cleanup", "--dry-run") and backup.exists()
    run(BIN / "ai-cleanup")
    assert not backup.exists() and not old_layout.exists() and recent.exists() and foreign.exists()

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
    # A single unavailable directory must not stop the rest of the sweep or lose its receipt.
    run(BIN / "session-tmpdir", input=json.dumps({"cwd": str(root), "session_id": "second"}))
    second = Path((home / "session-env").read_text().strip().splitlines()[-1].split("=", 1)[1])
    sweep = """import runpy, shutil, sys
from pathlib import Path
from unittest.mock import patch
program, unavailable = sys.argv[1:]
sys.path.insert(0, str(Path(program).parent))
sys.argv = [program, "--tmp-age-hours", "0"]
rmtree = shutil.rmtree
def remove(path):
    if path.name == unavailable:
        raise PermissionError("temporary fixture error")
    return rmtree(path)
with patch("shutil.rmtree", remove):
    runpy.run_path(program, run_name="__main__")
"""
    out = run("python3", "-c", sweep, BIN / "ai-cleanup", owned.name)
    assert "could not remove" in out and owned.is_dir() and not second.exists()
    assert "temporary fixture error" in (home / ".cache/ai-runs/setup/cleanup.log").read_text()
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
    nested = root / "other-project"
    nested.mkdir()
    (nested / ".lonca.toml").touch()
    (folder / "fixture.jsonl").write_text("\n".join([event_for(root, "inside sample"), event_for(home, "outside sample"),
                                                    event_for(nested, "unregistered nested sample")]))
    run(BIN / "memory-review", "--dry-run")
    summary, = (home / ".cache/ai-runs/setup/history-mining").glob("review-*.md")
    assert "inside sample" in summary.read_text() and "outside sample" not in summary.read_text() and "nested sample" not in summary.read_text()
    assert not logs.exists()

    # A second linked checkout of the same repo has no lane receipt.
    run("git", "-C", root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "--allow-empty", "-m", "Fixture")
    wt_base = home / ".herdr/worktrees" / (home.name + "-project")
    wt = wt_base / "feat-demo"
    personal = wt_base / "personal"
    wt_base.mkdir(parents=True)
    run("git", "-C", root, "worktree", "add", "-qb", "feat/demo", wt)
    run("git", "-C", root, "worktree", "add", "-qb", "personal", personal)
    result = home / ".cache/ai-runs/test/demo/result"
    result.parent.mkdir(parents=True)
    lane_temp = temp / "lane-demo-private"
    lane_temp.mkdir()
    run(BIN / "lane-record", "lane-demo", wt, "", "fixture", "main", result, "", "feat/demo", root, root, lane_temp)
    oid = run("git", "-C", wt, "rev-parse", "HEAD").strip()
    prs = [{"headRefName": branch, "headRefOid": oid, "number": 1, "state": "CLOSED"}
           for branch in ("feat/demo", "personal")]
    gh = stubs / "gh"
    gh.write_text("#!/bin/sh\necho '" + json.dumps(prs) + "'\n")
    dry = run(BIN / "ai-cleanup", "--dry-run")
    assert str(wt) in dry and str(personal) not in dry

    run("git", "-C", root, "remote", "add", "origin", "https://example.invalid/own/repo.git")
    tasks = [{"key": "test#" + str(i), "title": name, "status": "doing",
              "url": "https://example.invalid/" + name + "/issues/1"} for i, name in enumerate(("own/repo", "other/no"))]
    board = {"projects": [{"slug": "test", "repos": ["own/repo", "other/no"], "tasks": tasks}]}
    (stubs / "kanzo").write_text("#!/bin/sh\n"
        'test "$*" = "export --project test --format json" || exit 1\n'
        + "echo '" + json.dumps(board) + "'\n")
    gh.write_text("""#!/bin/sh
echo "$*" >> "$HOME/calls"
case "$*" in
  "auth status") echo "Logged in to example.invalid account fixture" ;;
  *" user") echo '{"login":"fixture"}' ;;
  *"/issues/1") echo '{"state":"closed"}' ;;
  *) echo '[]' ;;
esac
""")
    out = run(BIN / "kanzo-sync", "--dry-run")
    assert "own/repo#1" in out and "other/no" not in logs.read_text()

    # Read lanes on temp copies: watched when the copy's marker names a registered project, else not.
    (stubs / "hc").write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
home = Path(os.environ["HOME"])
terms = json.loads((home / "terms.json").read_text())
with open(home / "hc.calls", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
if sys.argv[1:3] == ["ls", "--json"]:
    print(json.dumps({"terminals": [{"address": "lead-1", "agent": "claude", "state": "live", "cwd": terms["lead-cwd"]}]}))
elif sys.argv[1] == "get" and sys.argv[2] == "lead-1":
    print(json.dumps({"labels": {"lonca.role": "lead"}, "foreground": {"cwd": terms["lead-cwd"]}}))
elif sys.argv[1] == "get":
    if sys.argv[2] not in terms:
        sys.exit(1)
    print(json.dumps(terms[sys.argv[2]]))
""")
    terms = home / "terms.json"
    terms.write_text(json.dumps({"lead-cwd": str(root)}))
    lanes = {}
    for lane, name in (("copy-ours", "test"), ("copy-stranger", "stranger")):
        copy = home / "copies" / lane / "src"
        copy.mkdir(parents=True)
        (copy / ".lonca.toml").write_text(f'name = "{name}"')
        result = home / ".cache/ai-runs" / name / lane / "read.result.md"
        result.parent.mkdir(parents=True)
        ltemp = temp / ("lane-" + lane)
        ltemp.mkdir()
        run(BIN / "lane-record", lane, copy, "lead-1", "omp:fixture", "-", result, "", "", copy, copy, ltemp)
        lanes[lane] = result
    calls = home / "hc.calls"
    gh_before = logs.read_text()
    out = run(BIN / "lane-watch")
    assert "STALLED: copy-ours" in out and "STALLED: copy-stranger" not in out
    assert any(line.startswith("send lead-1 STALLED: copy-ours") for line in calls.read_text().splitlines())
    assert "copy-stranger" not in calls.read_text()
    for result in lanes.values():
        result.write_text("report")
        os.utime(result, (time.time() - 700, time.time() - 700))
    terms.write_text(json.dumps({"lead-cwd": str(root), "copy-ours": {"state": "finished"},
                                 "copy-stranger": {"state": "finished"}}))
    out = run(BIN / "lane-watch")
    assert "removed the finished terminal of read lane copy-ours" in out and "READY" not in out
    assert "rm copy-ours" in calls.read_text().splitlines() and "copy-stranger" not in calls.read_text()
    assert "pr list --head" not in logs.read_text()[len(gh_before):]   # a read lane has no PR to check
    run(BIN / "ai-cleanup", "--dry-run")   # the other record readers accept the mapped record
    run(BIN / "kanzo-sync", "--dry-run")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as folder:
        check(Path(folder).resolve())
    print("project job boundaries passed")
