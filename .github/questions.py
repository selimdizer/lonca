#!/usr/bin/env python3
"""The questions ledger in throwaway project folders: ids, answer, drop, concurrent adds, git refusal."""
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LONCA = Path(__file__).resolve().parents[1] / "bin/lonca"


def q(*args, ok=True):
    p = subprocess.run([LONCA, "questions", *map(str, args)], capture_output=True, text=True)
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
    assert q("add", root, "--by", "lead", "--title", "Round up?", "--context", "10 / 3\n## Q-9. fake\nAsked: x",
             "--option", "Up", "--option", "Down", "--recommend", "B") == "Q-1"
    assert q("add", root / "sub", "--by", "lane-x", "--title", "Port?", "--option", "8080") == "Q-2"
    q("add", root, "--by", "lead", "--title", "bad", "--option", "a", "--recommend", "C", ok=False)
    text = ledger.read_text()
    assert "B. Down (recommended)" in text and "X. Other (please specify)" in text and "  ## Q-9. fake" in text
    assert "by lead · Status: open" in text

    assert q("answer", root, "Q-1", "Down,\n## Q-7. not a question") == "Q-1"
    q("answer", root, "Q-1", "again", ok=False)   # only open questions take an answer
    q("drop", root, "Q-5", "why", ok=False)
    listed = q(root)
    assert listed.startswith("## Q-2. Port?") and "Q-1" not in listed, listed
    assert count(q(root, "--all")) == 2
    text = ledger.read_text()
    assert "Status: answered" in text and "[Answer]: Down,\n  ## Q-7. not a question\nAnswered: " in text

    # Two processes adding at once both land, with distinct ids that keep counting.
    with ThreadPoolExecutor(8) as pool:
        ids = list(pool.map(lambda i: q("add", root, "--by", f"p{i}", "--title", f"T{i}"), range(8)))
    assert sorted(ids, key=lambda i: int(i[2:])) == [f"Q-{n}" for n in range(3, 11)], ids
    assert q("drop", root, "Q-2", "moot") == "Q-2"
    assert q("add", root, "--by", "lead", "--title", "Next") == "Q-11"
    assert count(q(root)) == 9 and "Status: dropped" in ledger.read_text()
    assert count(q(root, "--all")) == 11

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
