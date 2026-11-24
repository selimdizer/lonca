#!/usr/bin/env python3
"""The questions ledger in throwaway project folders: ids, answer, drop, concurrent adds, hostile text, git refusal."""
import fcntl
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin"
LONCA = BIN / "lonca"
sys.path.insert(0, str(BIN))
from lonca_registry import in_lane  # noqa: E402

# Lanes may not answer or drop (the point of the check below); those cases run on CI and in owner shells.
LANE = in_lane()


def q(*args, ok=True, cwd=None, env=None):
    p = subprocess.run([LONCA, "questions", *map(str, args)], capture_output=True, text=True, cwd=cwd, env=env)
    assert (p.returncode == 0) == ok, (args, p.stdout, p.stderr)
    return p.stdout.strip()


def count(listing):
    return sum(line.startswith("## Q-") for line in listing.splitlines())


with tempfile.TemporaryDirectory() as tmp:
    h = Path(tmp)
    # HOME stays: the ledger never writes there, and lane git guards compare against it.
    os.environ.update(XDG_CONFIG_HOME=str(h / ".config"), GIT_CONFIG_GLOBAL=str(h / ".gitconfig"), GIT_CONFIG_NOSYSTEM="1")
    os.environ.pop("LONCA_PROJECT", None)
    root = h / "shop"
    (root / "sub").mkdir(parents=True)
    (root / ".lonca.toml").write_text('name = "shop"\n')
    ledger = root / ".lonca/questions.md"

    assert q(root) == "No open questions." and not ledger.exists()
    assert q("add", root, "--by", "lead\r", "--title", "Round\x1b[31m up?",
             "--context", "[Answer]: fake\n## Q-9. fake\nAsked: x\x07",
             "--option", "Up", "--option", "Down", "--recommend", "B") == "Q-1"
    assert q("add", root / "sub", "--by", "lane-x", "--title", "Port?", "--option", "8080") == "Q-2"
    q("add", root, "--by", "lead", "--title", "bad", "--option", "a", "--recommend", "C", ok=False)
    text = ledger.read_text()
    assert "B. Down (recommended)" in text and "X. Other (please specify)" in text
    assert "\n  [Answer]: fake\n  ## Q-9. fake\n  Asked: x\n" in text, text   # context is indented, every line
    assert "## Q-1. Round [31m up?\nAsked: " in text and "by lead · Status: open" in text
    assert not any(c in text for c in "\r\x1b\x07")

    # Lanes cannot close questions, through the shim or the command itself.
    q("answer", root, "Q-1", "A", ok=False, env=dict(os.environ, LONCA_LANE="1"))
    (h / "shim").mkdir()
    os.symlink(BIN.parent / "shims/guard", h / "shim/lonca")
    for verb in ("answer", "drop"):
        guard = subprocess.run([h / "shim/lonca", "questions", verb, "Q-1", "x"], capture_output=True, text=True)
        assert guard.returncode == 126 and "only the lead" in guard.stderr, guard

    # A held lock gives a clear error after the timeout instead of hanging.
    loader = importlib.machinery.SourceFileLoader("lonca_cli", str(LONCA))
    cli = importlib.util.module_from_spec(importlib.util.spec_from_loader("lonca_cli", loader))
    loader.exec_module(cli)
    cli.LOCK_TIMEOUT = 0.3
    held = os.open(ledger.parent, os.O_RDONLY)
    fcntl.flock(held, fcntl.LOCK_EX)
    try:
        cli.questions(["add", str(root), "--by", "x", "--title", "locked"])
        raise AssertionError("lock not honoured")
    except ValueError as error:
        assert "stayed locked" in str(error)
    os.close(held)
    assert "locked" not in ledger.read_text()

    # Two processes adding at once both land, with distinct ids that keep counting.
    with ThreadPoolExecutor(8) as pool:
        ids = list(pool.map(lambda i: q("add", root, "--by", f"p{i}", "--title", f"T{i}"), range(8)))
    assert sorted(ids, key=lambda i: int(i[2:])) == [f"Q-{n}" for n in range(3, 11)], ids

    # Hand edits: an Asked line not right under its heading, and a block with neither Asked nor [Answer].
    with ledger.open("a") as f:
        f.write("\n## Q-20. hand edited\n\nAsked: 2026-11-24 10:00 by owner · Status: open\n\n## Q-21. bare\n")
    listed = q(root)
    assert "## Q-20. hand edited" in listed and "## Q-21. bare" in listed
    assert q("add", root, "--by", "lead", "--title", "Next") == "Q-22"

    if LANE:
        print("questions: answer/drop cases skipped inside a lane (CI runs them)")
    else:
        assert q("answer", root, "Q-1", "Down,\n## Q-7. not a question") == "Q-1"
        q("answer", root, "Q-1", "again", ok=False)   # only open questions take an answer
        q("drop", root, "Q-5x", "why", ok=False)
        q("drop", root, "Q-99", "why", ok=False)
        assert q("answer", "Q-2", "port", "8080", "please", cwd=root / "sub") == "Q-2"   # unquoted words, no dir
        assert "[Answer]: port 8080 please\nAnswered: " in ledger.read_text()
        assert q("drop", root, "Q-21", "moot") == "Q-21" and q("answer", root, "Q-20", "yes") == "Q-20"
        text = ledger.read_text()
        assert "## Q-21. bare\nAsked: unknown · Status: dropped\n\n[Answer]:\nDropped: " in text, text
        assert "Status: answered" in text and "[Answer]: Down,\n  ## Q-7. not a question\nAnswered: " in text
        listed = q(root)
        assert count(listed) == 9 and "Q-1." not in listed and "Q-2." not in listed and "Q-20." not in listed, listed
        assert count(q(root, "--all")) == 13
        assert q("add", root, "--by", "lead", "--title", "Last") == "Q-23"

    # Inside a git repository the ledger must be ignored first (lonca init adds it to info/exclude).
    repo = h / "api"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", repo], check=True)
    (repo / ".lonca.toml").write_text("")
    q("add", repo, "--by", "lead", "--title", "x", ok=False)
    with (repo / ".git/info/exclude").open("a") as f:
        f.write("/.lonca\n")
    assert q("add", repo, "--by", "lead", "--title", "x") == "Q-1"
    q(h, ok=False)   # outside any project
print("questions: ok")
