#!/usr/bin/env python3
"""A throwaway home, nested repos, a linked worktree and an unrelated checkout."""
import json
import os
import runpy
import subprocess
import tempfile
import tomllib
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
AGENTS = ("CLAUDE.local.md", ".claude/settings.local.json", ".codex/config.toml",
          ".codex/rules/lonca.rules", ".codex/hooks.json")


def run(*args, cwd=None, ok=True, **kwargs):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kwargs)
    if ok and result.returncode:
        raise AssertionError((args, result.stdout, result.stderr))
    if not ok:
        assert result.returncode != 0, args
    return result.stdout.strip()


def git(repo, *args, **kwargs):
    return run("git", "-C", repo, *args, **kwargs)


def snapshot(repo, paths):
    return {name: (repo / name).read_bytes() if (repo / name).is_file() else None for name in paths}


def test(base):
    home = base / "home"
    home.mkdir()
    os.environ.update(HOME=str(home), GIT_CONFIG_NOSYSTEM="1", XDG_CONFIG_HOME=str(home / ".config"))
    for key in ("LONCA_PROJECT", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "DEJA_POLICY_FILE"):
        os.environ.pop(key, None)
    (home / "lonca").symlink_to(SRC, target_is_directory=True)
    # CI exercises the files the CLI reads, plus the local-scope installer contract.
    stub = base / "bin/claude"
    stub.parent.mkdir()
    stub.write_text('''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
assert args.pop(0) == "plugin"
p = Path(".claude/settings.local.json")
installed = Path(".git/plugin-test-install")
if args == ["list", "--json"]:
    print(json.dumps([{"id": "lonca@lonca", "scope": "local", "projectPath": str(Path.cwd())}] if installed.exists() else []))
    sys.exit(0)
assert args[-2:] == ["--scope", "local"] or args[-3:] == ["--scope", "local", "--keep-data"]
data = json.loads(p.read_bytes()) if p.exists() else {}
if args[:2] == ["marketplace", "add"]:
    data.setdefault("extraKnownMarketplaces", {})["lonca"] = {"source": {"source": "directory", "path": args[2]}}
elif args[:2] == ["install", "lonca@lonca"]:
    data.setdefault("enabledPlugins", {})["lonca@lonca"] = True
    installed.touch()
elif args[:2] == ["uninstall", "lonca@lonca"]:
    data["enabledPlugins"].pop("lonca@lonca")
    installed.unlink()
else:
    raise AssertionError(args)
p.parent.mkdir(exist_ok=True)
p.write_text(json.dumps(data))
''')
    stub.chmod(0o755)
    os.environ["PATH"] = str(stub.parent) + os.pathsep + os.environ["PATH"]
    root = base / "Project space"
    a, b, lane, other = root / "api", root / "more/ui", base / "lane", base / "unrelated"
    for repo in (a, b, other):
        repo.mkdir(parents=True)
        git(repo, "init", "-q")
    git(a, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "--allow-empty", "-m", "Initial fixture")
    git(a, "worktree", "add", "-q", "--detach", lane)
    git(b, "config", "--local", "core.hooksPath", "team-hooks")
    (a / ".claude").mkdir()
    (a / ".claude/settings.local.json").write_text('{"permissions":{"allow":["Read"]},"env":{"keep":"yes"}}')
    (a / ".codex").mkdir()
    (a / ".codex/config.toml").write_text('model = "existing"\n[mcp_servers.other]\ncommand = "other"')
    (a / ".codex/hooks.json").write_text('{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo existing"}]}]}}')
    (a / "CLAUDE.local.md").write_text("Private notes without final newline")
    files = (*AGENTS, ".git/info/exclude", ".git/config")
    baseline = {repo: snapshot(repo, files) for repo in (a, b, other)}
    assert not run(SRC / "bin/lonca-project", other, ok=False)
    assert not run(SRC / "bin/deja-scope", other, ok=False)
    def lonca(*args, **kwargs):
        return run(SRC / "bin/lonca", *args, **kwargs)
    lonca("init", root)
    report = lonca("status", root)
    assert "own hooksPath: team-hooks" in report and "Claude plugin enabled, settings on, Codex on" in report
    assert str(root) in lonca("status")
    for repo in (a, b, lane):
        assert run(SRC / "bin/lonca-project", repo).endswith("\t" + str(root))
        assert run(SRC / "bin/lonca-project", "--claude-agent", "reviewer", repo) == "lonca:reviewer"
        origin = git(repo, "config", "--show-origin", "--get", "core.hooksPath")
        assert origin.startswith("file:") and origin.endswith("\t" + ("team-hooks" if repo == b else str(home / "lonca/git-hooks"))), origin
    git(other, "config", "--show-origin", "--get", "core.hooksPath", ok=False)
    for repo in (a, b):
        settings = json.loads((repo / AGENTS[1]).read_bytes())
        policy = Path(settings["env"]["DEJA_POLICY_FILE"])
        assert policy.is_file() and settings["enabledPlugins"]["lonca@lonca"]
        assert set(json.loads((SRC / "config/claude-permissions.json").read_bytes())["deny"]) <= set(settings["permissions"]["deny"])
        assert "@~/lonca/AGENTS.md" in (repo / AGENTS[0]).read_text().splitlines()
        cfg = tomllib.loads((repo / AGENTS[2]).read_text())
        assert cfg["mcp_servers"]["deja"]["env"]["DEJA_POLICY_FILE"] == str(policy)
        assert cfg["mcp_servers"]["kanzo"]["args"] == ["mcp"]
        assert (repo / AGENTS[3]).read_bytes() == (SRC / "config/codex-rules/default.rules").read_bytes()
        for path in AGENTS:
            assert git(repo, "check-ignore", "--", path) == path
        assert not git(repo, "status", "--porcelain")
    assert json.loads((a / AGENTS[1]).read_bytes())["env"]["keep"] == "yes"
    assert tomllib.loads((a / AGENTS[2]).read_text())["model"] == "existing"
    assert "echo existing" in (a / AGENTS[4]).read_text()
    installed = {r: snapshot(r, files) for r in (a, b)}
    lonca("init", root)
    assert all(snapshot(r, files) == installed[r] for r in installed)
    later = root / "new"
    later.mkdir()
    git(later, "init", "-q")
    assert "repo not initialised" in lonca("status", root)
    lonca("init", root)
    assert "repo not initialised" not in lonca("status", root)
    (root / "notes").mkdir()
    run(SRC / "bin/deja-scope", "--refresh")
    lonca("remove", root)
    assert not (root / ".lonca.toml").exists()
    assert not policy.exists() and not policy.with_suffix(".root").exists()
    assert not list((home / ".local/state/lonca/projects").glob("*.json"))
    for repo in (a, b, other):
        assert snapshot(repo, files) == baseline[repo], repo
    assert not (a / ".codex/rules").exists() and not (b / ".claude").exists()
    assert not run(SRC / "bin/lonca-project", lane, ok=False)
    # A single repository is also a project. A pre-existing marker is retained.
    (other / "lonca.toml").write_text('name = "custom"\n')
    lonca("init", "--agents", "codex", other)
    assert not (other / ".claude").exists() and not (other / ".lonca.toml").exists()
    assert run(SRC / "bin/lonca-project", other).startswith("custom\t")
    # A user's later edits stay in place and the registry stays available for a retry.
    config = other / ".codex/config.toml"
    old = config.read_bytes()
    config.write_bytes(old + b"# personal edit\n")
    lonca("remove", other, ok=False)
    assert config.read_bytes().endswith(b"# personal edit\n")
    config.write_bytes(old)
    lonca("remove", other)
    assert (other / "lonca.toml").read_text() == 'name = "custom"\n'
    (other / "lonca.toml").unlink()
    lonca("init", "--agents", "claude", other)
    assert git(other, "check-ignore", ".lonca.toml") == ".lonca.toml"
    assert not (other / ".codex").exists() and not git(other, "status", "--porcelain")
    lonca("remove", other)
    assert snapshot(other, files) == baseline[other]
    assert not (home / ".gitconfig").exists()


def off_switch(base):
    # Invoke hook entry points directly with inert input in a disposable home.
    repo = base / "hooks-test"
    repo.mkdir()
    git(repo, "init", "-q")
    env = dict(os.environ, LONCA="0", HOME=str(base), CLAUDE_ENV_FILE=str(base / "env"))
    hook_event = json.dumps({"cwd": str(repo), "session_id": "test"})
    for program, args in (("bin/deja-scope", ["--session"]), ("bin/memory-context", []),
                          ("bin/session-tmpdir", []), ("bin/ai-trace-gh", ["--hook"])):
        assert not run(SRC / program, *args, cwd=repo, env=env, input=hook_event)
    hooks = runpy.run_path(str(SRC / "bin/lonca"))["codex_hooks"]()
    (base / "lonca").symlink_to(SRC, target_is_directory=True)
    for groups in hooks["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                assert not run("sh", "-c", hook["command"], cwd=repo, env=env, input=hook_event)
    assert not (base / "env").exists()
    # Native hooks still receive Git's input when Lonca is off.
    for name in ("pre-push", "commit-msg"):
        native = repo / ".git/hooks" / name
        native.write_text('#!/bin/sh\ncat > native-input\n')
        native.chmod(0o755)
        run(SRC / "git-hooks" / name, "test", cwd=repo, env=env, input="native input\n")
        assert (repo / "native-input").read_text() == "native input\n"


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as dirname:
        base = Path(dirname).resolve()
        off_switch(base)
        test(base)
    print("per-project layout passed")
