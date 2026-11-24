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


def fixture_home(home):
    return dict(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
                GIT_CONFIG_GLOBAL=str(home / ".gitconfig"), GIT_CONFIG_NOSYSTEM="1")


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
    os.environ.update(fixture_home(home))
    for key in ("LONCA_PROJECT", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "DEJA_POLICY_FILE"):
        os.environ.pop(key, None)
    (home / "lonca").symlink_to(SRC, target_is_directory=True)
    # CI exercises the files the CLI reads, plus the local-scope installer contract.
    stub = base / "bin/claude"
    stub.parent.mkdir()
    stub.write_text('''#!/usr/bin/env python3
import hashlib, json, sys
from pathlib import Path
args = sys.argv[1:]
if args == ["mcp", "remove", "--scope", "user", "kanzo"]:
    path = Path.home() / ".claude.json"
    data = json.loads(path.read_bytes())
    del data["mcpServers"]["kanzo"]
    data["openSessionUpdate"] = True
    path.write_text(json.dumps(data))
    sys.exit(0)
assert args.pop(0) == "plugin"
p = Path(".claude/settings.local.json")
installed = Path.home() / ("plugin-test-" + hashlib.sha256(bytes(Path.cwd())).hexdigest())
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
    (a / ".codex/config.toml").write_text('model = "existing"\n[mcp_servers.other]\ncommand = "other"\nenv = { TOKEN = "project-only-fixture" }')
    (a / ".codex/hooks.json").write_text('{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo existing"}]}]}}')
    (a / "CLAUDE.local.md").write_text("Private notes without final newline")
    files = (*AGENTS, ".git/info/exclude", ".git/config")
    baseline = {repo: snapshot(repo, files) for repo in (a, b, other)}
    assert not run(SRC / "bin/lonca-project", other, ok=False)
    none = Path(run(SRC / "bin/deja-scope", other))
    assert json.loads(none.read_bytes()) == {"ignore": ["*", "*/*"]}
    assert not run(SRC / "bin/deja-scope", base, ok=False)
    unmarked = base / "unmarked"
    unmarked.mkdir()
    git(unmarked, "init", "-q")
    assert run(SRC / "bin/deja-scope", "--session", input=json.dumps({"cwd": str(unmarked)}),
               env=dict(os.environ, CLAUDE_ENV_FILE=str(base / "session-env")))
    assert str(none) in (base / "session-env").read_text()
    assert str(unmarked) in run(SRC / "bin/lonca", "status")
    def lonca(*args, **kwargs):
        return run(SRC / "bin/lonca", *args, **kwargs)
    internal = root / "lanes" / "feature"
    git(a, "worktree", "add", "-q", "--detach", internal)
    for name in ("node_modules", "vendor", "target", ".venv"):
        ignored = a / name / "dependency"
        ignored.mkdir(parents=True)
        git(ignored, "init", "-q")
    catalog = home / ".claude/plugins/known_marketplaces.json"
    catalog.parent.mkdir(parents=True)
    collision = '{"lonca":{"source":{"source":"directory","path":"/old/sui"}}}'
    catalog.write_text(collision)
    lonca("init", root, ok=False)
    assert catalog.read_text() == collision and not (root / ".lonca.toml").exists()
    catalog.unlink()
    global_settings = home / ".claude/settings.json"
    global_settings.write_text(json.dumps({"extraKnownMarketplaces": json.loads(collision)}))
    lonca("init", root, ok=False)
    assert not (root / ".lonca.toml").exists()
    global_settings.unlink()
    external = root / "external-lane"
    host = base / "outside-owner"
    host.mkdir()
    git(host, "init", "-q")
    git(host, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "Fixture")
    git(host, "worktree", "add", "-q", "--detach", external)
    rejected = subprocess.run([SRC / "bin/lonca", "init", root], capture_output=True, text=True)
    assert rejected.returncode and "repository outside this project" in rejected.stderr
    git(host, "worktree", "remove", external)
    (root / "CLAUDE.local.md").write_text("root notes\n")
    lonca("init", root)
    private_state = home / ".local/state/lonca/projects"
    assert not any(b"project-only-fixture" in f.read_bytes() for f in private_state.rglob("*") if f.is_file())
    assert run(SRC / "bin/lonca-project", "--claude-agent", "lead", root) == "lonca:lead"
    root_settings = json.loads((root / AGENTS[1]).read_bytes())
    assert set(json.loads((SRC / "config/claude-permissions.json").read_bytes())["deny"]) <= set(root_settings["permissions"]["deny"])
    assert "@~/lonca/AGENTS.md" in (root / AGENTS[0]).read_text().splitlines()
    assert Path(root_settings["env"]["DEJA_POLICY_FILE"]).is_file()
    report = lonca("status", root)
    assert "Codex lead guards are unavailable" in report
    assert f"{root}: Claude lead guards on" in report
    assert "own hooksPath: team-hooks" in report and "Claude plugin enabled, settings on, Codex on" in report
    assert str(root) in lonca("status")
    assert f"{internal}: linked worktree of {a}" in report
    assert not (internal / AGENTS[0]).exists() and "dependency" not in report
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
        assert settings["attribution"] == {"commit": "", "pr": ""} and settings["includeCoAuthoredBy"] is False
        assert '"$HOME/lonca/bin/session-scope"' in [h["command"] for g in json.loads((repo / AGENTS[4]).read_bytes())["hooks"]["SessionStart"] for h in g["hooks"]]
        assert set(json.loads((SRC / "config/claude-permissions.json").read_bytes())["deny"]) <= set(settings["permissions"]["deny"])
        assert "@~/lonca/AGENTS.md" in (repo / AGENTS[0]).read_text().splitlines()
        cfg = tomllib.loads((repo / AGENTS[2]).read_text())
        assert cfg["mcp_servers"]["deja"]["env"]["DEJA_POLICY_FILE"] == str(policy)
        assert cfg["mcp_servers"]["kanzo"]["args"] == ["mcp"]
        assert (repo / AGENTS[3]).read_bytes() == (SRC / "config/codex-rules/default.rules").read_bytes()
        for path in AGENTS:
            assert git(repo, "check-ignore", "--", path) == path
        assert not git(repo, "status", "--porcelain", "--", *AGENTS)
    assert json.loads((a / AGENTS[1]).read_bytes())["env"]["keep"] == "yes"
    assert tomllib.loads((a / AGENTS[2]).read_text())["model"] == "existing"
    assert "echo existing" in (a / AGENTS[4]).read_text()
    installed = {r: snapshot(r, files) for r in (a, b)}
    lonca("init", root)
    assert all(snapshot(r, files) == installed[r] for r in installed)
    (root / AGENTS[0]).write_text("updated root notes\n")
    assert "Claude lead guards missing" in lonca("status", root)
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
    assert (root / AGENTS[0]).read_text() == "updated root notes\n" and not (root / AGENTS[1]).exists()
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
    config = other / ".codex/config.toml"
    config.write_bytes(config.read_bytes() + b'[mcp_servers.my_tool]\ncommand = "mine"\n')
    lonca("init", other)
    lonca("remove", other)
    assert tomllib.loads(config.read_text()) == {"mcp_servers": {"my_tool": {"command": "mine"}}}
    config.unlink()
    config.parent.rmdir()
    assert (other / "lonca.toml").read_text() == 'name = "custom"\n'
    (other / "lonca.toml").unlink()
    lonca("init", "--agents", "claude", other)
    assert git(other, "check-ignore", ".lonca.toml") == ".lonca.toml"
    assert not (other / ".codex").exists() and not git(other, "status", "--porcelain")
    lonca("remove", other)
    assert snapshot(other, files) == baseline[other]
    # Later edits in each personal format survive repair and uninstall.
    lonca("init", "--agents", "claude,codex", a)
    settings_path = a / AGENTS[1]
    values = json.loads(settings_path.read_bytes())
    values["permissions"]["allow"].append("Write(notes)")
    values["permissions"]["deny"].clear()
    settings_path.write_text(json.dumps(values))
    assert "guard rules missing" in lonca("status", a)
    with (a / AGENTS[0]).open("a") as f:
        f.write("Later note\n")
    with (a / ".git/info/exclude").open("a") as f:
        f.write("/later-ignore\n")
    hookfile = a / AGENTS[4]
    hooks = json.loads(hookfile.read_bytes())
    hooks["hooks"]["Stop"].append({"hooks": [{"type": "command", "command": "echo later"}]})
    hookfile.write_text(json.dumps(hooks))
    lonca("init", a)
    assert "guard rules missing" not in lonca("status", a)
    lonca("remove", a)
    assert json.loads(settings_path.read_bytes()) == {"permissions": {"allow": ["Read", "Write(notes)"]}, "env": {"keep": "yes"}}
    assert "Later note" in (a / AGENTS[0]).read_text() and "@~/lonca" not in (a / AGENTS[0]).read_text()
    assert "/later-ignore" in (a / ".git/info/exclude").read_text()
    assert [g["hooks"][0]["command"] for g in json.loads(hookfile.read_bytes())["hooks"]["Stop"]] == ["echo existing", "echo later"]
    lonca("init", "--agents", "codex", other)
    moved = base / "moved"
    other.rename(moved)
    assert "skipping its checkout" in lonca("remove", other)
    assert not list((home / ".local/state/lonca/projects").glob("*.json"))
    assert not (home / ".gitconfig").exists()


def legacy_defaults(home):
    return {"attribution": {"commit": "", "pr": ""}, "includeCoAuthoredBy": False,
            "env": {"TMPDIR": str(home / ".cache/lonca/tmp")}}


def direct_uninstall(base):
    # A direct uninstall must clean the original polluted installation without a preceding migration.
    shipped = json.loads((SRC / "config/claude-permissions.json").read_bytes())["deny"]
    # autoMemoryDirectory is user-level only: uninstall keeps it.
    personal = {"permissions": {"deny": ["Read(private)"]}, "theme": "dark", "env": {"KEEP": "yes"},
                "autoMemoryDirectory": "~/ai-memory"}
    custom = {"attribution": {"commit": "personal", "pr": ""}, "includeCoAuthoredBy": True,
              "env": {"KEEP": "yes", "TMPDIR": "/my-temp"}}
    for case in ("polluted", "personal-current", "personal-backup"):
        home = base / ("uninstall-" + case)
        settings = home / ".claude/settings.json"
        settings.parent.mkdir(parents=True)
        (home / "lonca").symlink_to(SRC)
        owned = legacy_defaults(home)
        old = {**personal, **owned, "permissions": {"deny": [*shipped, "Read(private)"]},
               "env": {**personal["env"], **owned["env"]}}
        current = {**old, **custom} if case == "personal-current" else old
        before = {**personal, **custom} if case == "personal-backup" else old
        settings.write_text(json.dumps(current))
        settings.with_suffix(".json.lonca-bak").write_text(json.dumps(before))
        run("sh", SRC / "install.sh", "--uninstall", env=dict(os.environ, **fixture_home(home)))
        assert json.loads(settings.read_bytes()) == (personal if case == "polluted" else {**personal, **custom}), case


def migration(base):
    # test() has installed a fake local-scope plugin CLI in this temporary HOME.
    home = Path.home()
    repo = home / "Work/marked project"
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / ".lonca.toml").write_text('name = "fixture"')
    explicit = home / "explicit"
    explicit.mkdir()
    git(explicit, "init", "-q")
    run("git", "config", "--global", "core.hooksPath", str(home / "lonca/git-hooks"))
    old_source = str(home / "lonca/extras/sui/plugins")
    market = {"lonca": {"source": {"source": "directory", "path": old_source}}}
    catalog = home / ".claude/plugins/known_marketplaces.json"
    catalog.write_text(json.dumps(market))
    settings = home / ".claude/settings.json"
    shipped = json.loads((SRC / "config/claude-permissions.json").read_bytes())["deny"]
    assert "Bash(*GIT_CONFIG_*)" in shipped
    owned = [*shipped, shipped[0], "Bash(ok-merge*)", "Bash(git push * main*)"]  # with rules earlier releases shipped
    private = ["Edit(~/.local/state/lonca/private/**)", "Bash(git clean ./private)"]
    defaults = legacy_defaults(home)
    settings.write_text(json.dumps({
        **defaults,
        "autoMemoryDirectory": "~/ai-memory",
        "extraKnownMarketplaces": market,
        "permissions": {"deny": [private[0], *owned, private[1]]},
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": str(home / "lonca/bin/memory-context")},
                                        {"type": "command", "command": str(home / "lonca/bin/session-scope")},
                                        {"type": "command", "command": "echo personal"}]}],
            "PreToolUse": [{"hooks": [{"type": "command", "command": "~/lonca/bin/ai-trace-gh --hook"}]}],
        },
    }))
    settings.with_suffix(".json.lonca-bak").write_bytes(settings.read_bytes())
    hooks = home / ".codex/hooks.json"
    hooks.parent.mkdir(exist_ok=True)
    stop = {"type": "command", "command": "python3 ~/lonca/config/memory-nudge.py"}
    personal = {"type": "command", "command": "python3 ~/lonca/config/memory-nudge.py --personal"}
    old_hooks = {"hooks": {"Stop": [{"hooks": [stop, personal]}],
                           "SessionStart": [{"hooks": [{"type": "command", "command": "cat ~/ai-memory/MEMORY.md"},
                                                       {"type": "command", "command": str(home / "lonca/bin/session-scope")}]}]}}
    hooks.write_text(json.dumps(old_hooks))
    hooks.with_suffix(".json.lonca-bak").write_bytes(hooks.read_bytes())
    private_links = []
    for kind, name in (("agents", "reviewer.md"), ("skills", "private-skill")):
        target = home / "lonca-local" / kind / name
        target.parent.mkdir(parents=True)
        if kind == "agents":
            target.write_text("private agent")
        else:
            target.mkdir()
        link = home / ".claude" / kind / name
        link.parent.mkdir(parents=True)
        link.symlink_to(target)
        private_links.append((link, target))
    copilot = home / ".copilot/config.json"
    copilot.parent.mkdir()
    copilot.write_text(json.dumps({"trustedFolders": [str(home / ".herdr/worktrees"), "/personal"]}))
    doc = home / ".claude/CLAUDE.md"
    doc.write_text("personal\n@~/lonca/AGENTS.md\n")
    codex = home / ".codex/AGENTS.md"
    codex.parent.mkdir(exist_ok=True)
    codex.symlink_to(home / "lonca/AGENTS.md")
    mcp = home / ".omp/agent/mcp.json"
    mcp.parent.mkdir(parents=True)
    private_server = {"env": {"TOKEN": "global-only-fixture"}}
    standard = {"command": "kanzo", "args": ["mcp"]}
    mcp.write_text(json.dumps({"mcpServers": {"kanzo": standard, "private": private_server}}))
    claude_mcp = home / ".claude.json"
    customized = {"command": "deja", "args": ["mcp"], **private_server}
    claude_mcp.write_text(json.dumps({"clientState": "global-only-fixture", "mcpServers": {"kanzo": standard, "deja": customized}}))
    state = home / ".local/state/lonca/mcp-added"
    deferred = home / ".pi/agent/mcp.json"
    deferred.parent.mkdir(parents=True)
    original_pi = '{"mcpServers":{"deja":{"command":"deja","args":["mcp"]},"personal":{}}}'
    deferred.write_text(original_pi)
    state.write_text("omp kanzo\nclaude kanzo\nclaude deja\npi deja\n")
    script = SRC / "bin/lonca"
    originals = {p: p.read_bytes() for p in (catalog, settings, doc, mcp, state, home / ".gitconfig")}
    preview = run(script, "migrate", "--dry-run", explicit)
    assert all(str(p) in preview for p in (settings, codex, doc, explicit, repo, catalog))
    assert all(p.read_bytes() == data for p, data in originals.items())
    assert not list((home / ".local/state/lonca/projects").glob("*.json"))
    assert not (home / ".local/state/lonca/migration-backups").exists()
    run(script, "migrate", explicit)
    assert run(script, "status", "--lane", repo)
    assert not codex.is_symlink() and doc.read_text() == "personal\n"
    cleaned = json.loads(settings.read_bytes())
    assert cleaned["permissions"]["deny"] == private
    assert not ({"attribution", "includeCoAuthoredBy"} & cleaned.keys())
    assert cleaned["autoMemoryDirectory"] == "~/ai-memory"
    assert "TMPDIR" not in cleaned.get("env", {})
    assert "echo personal" in settings.read_text()
    assert all(c not in settings.read_text() for c in ("/bin/memory-context", "/bin/ai-trace-gh", "/bin/session-scope"))
    assert json.loads(hooks.read_text())["hooks"]["Stop"] == [{"hooks": [personal]}]
    assert "cat ~/ai-memory" not in hooks.read_text() and "/bin/session-scope" not in hooks.read_text()
    assert all(link.is_symlink() for link, _ in private_links)
    assert str(home / ".herdr/worktrees") in json.loads(copilot.read_text())["trustedFolders"]
    assert json.loads(mcp.read_bytes()) == {"mcpServers": {"private": private_server}}
    assert json.loads(claude_mcp.read_bytes()) == {"clientState": "global-only-fixture", "mcpServers": {"deja": customized},
                                                 "openSessionUpdate": True}
    assert not mcp.with_name("mcp.json.lonca-bak").exists()
    assert state.read_text() == "pi deja\n" and deferred.read_text() == original_pi
    status = run(script, "status", repo)
    assert "still global: pi MCP deja" in status and "global install still present" not in status
    assert "outside a Lonca project" in run(script, "outside-session", cwd=base)
    assert json.loads(catalog.read_bytes())["lonca"]["source"]["path"] == str(home / "lonca")
    run("git", "config", "--global", "--get", "core.hooksPath", ok=False)
    assert git(repo, "config", "--local", "--get", "core.hooksPath") == str(home / "lonca/git-hooks")
    assert git(explicit, "config", "--local", "--get", "core.hooksPath") == str(home / "lonca/git-hooks")
    # Capture both real launcher forms at the terminal boundary. The smoke test
    # in omp-lane.py checks MCP discovery with the actual CLI when available.
    hc = base / "bin/hc"
    hc.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1] == "run":
    Path(os.environ["HOME"], "terminal.json").write_text(json.dumps(sys.argv[1:]))
""")
    hc.chmod(0o755)
    git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "--allow-empty", "-m", "Fixture")
    origin = base / "fixture-origin"
    run("git", "clone", "--bare", repo, origin)
    git(repo, "remote", "add", "origin", origin)
    main = git(repo, "branch", "--show-current")
    brief = base / "demo.brief"
    brief.write_text("Read the fixture.")
    sibling = base / "sibling"
    run("git", "clone", "-q", origin, sibling)
    git(sibling, "config", "--get", "core.hooksPath", ok=False)
    for flags, branch, model in [(["--read"], "read", "example/small"), ([], "feat/fixture", "github-copilot/test")]:
        result = home / ".cache/ai-runs/fixture/run" / (branch.split("/")[-1] + ".result")
        run(SRC / "bin/lane", *flags, repo, branch, "omp:" + model, brief, result, main)
        argv = json.loads((home / "terminal.json").read_bytes())
        assert '--extension "$HOME/lonca/config/omp-lane"' in argv[-1]
        assert any(arg.startswith("DEJA_POLICY_FILE=") for arg in argv)
        lane_env = dict(arg.split("=", 1) for arg in argv if arg.startswith("GIT_CONFIG_"))
        hooks_path = git(sibling, "config", "--get", "core.hooksPath", env=dict(os.environ, **lane_env))
        assert hooks_path == str(home / "lonca/git-hooks")
        assert all(os.access(Path(hooks_path) / hook, os.X_OK) for hook in ("pre-push", "commit-msg"))
        rec = json.loads(Path(str(result) + ".lane.json").read_bytes())
        assert Path(rec["temp"]).is_dir() and Path(rec["project"]) == repo
    # A read lane on a temp copy outside Git: no Git guard check, its own marker is the project.
    copy = base / "read-copy"
    copy.mkdir()
    (copy / ".lonca.toml").write_text('name = "fixture"')
    result = home / ".cache/ai-runs/fixture/run/copy.result"
    run(SRC / "bin/lane", "--read", copy, "copy", "omp:example/small", brief, result)
    assert "--tools read,grep,glob" in json.loads((home / "terminal.json").read_bytes())[-1]
    assert json.loads(Path(str(result) + ".lane.json").read_bytes())["worktree"] == str(copy.resolve())
    guards = repo / ".codex/rules/lonca.rules"
    guards.write_text("")
    denied = subprocess.run([script, "status", "--lane", repo], capture_output=True, text=True)
    assert denied.returncode and "lonca init" in denied.stderr
    run(script, "migrate")
    assert run(script, "status", "--lane", repo)
    backups = list((home / ".local/state/lonca/migration-backups").iterdir())
    assert backups
    records = [json.loads(line) for directory in backups for line in (directory / "changes.jsonl").read_text().splitlines()]
    assert any(r["path"] == str(claude_mcp) and r["removed"] == {"mcpServers": {"kanzo": standard}} for r in records)
    recorded_deny = [rule for record in records if record["path"] == str(settings)
                     for rule in record["removed"].get("permissions", {}).get("deny", [])]
    assert recorded_deny == owned
    assert any(r["path"] == str(settings) and all(r["removed"].get(k) == v for k, v in defaults.items())
               for r in records)
    assert all("global-only-fixture" not in json.dumps(r) for r in records)
    run(script, "migrate")
    assert backups == list((home / ".local/state/lonca/migration-backups").iterdir())
    run("sh", SRC / "install.sh", "--uninstall")
    assert not (explicit / ".lonca.toml").exists() and (repo / ".lonca.toml").exists()
    assert not guards.exists()
    assert all(not link.is_symlink() and target.exists() for link, target in private_links)
    assert json.loads(copilot.read_text())["trustedFolders"] == ["/personal"]
    assert not list((home / ".local/state/lonca/projects").glob("*.json"))
    assert not any(p.exists() for p in backups) and "private" in settings.read_text()
    assert not any((home / ".local/state/lonca/migration-backups").iterdir())
    assert not state.exists() and json.loads(deferred.read_bytes())["mcpServers"] == {"personal": {}}


def overlapping_hooks(base):
    home = base / "hook-home"
    home.mkdir()
    (home / "lonca").symlink_to(SRC, target_is_directory=True)
    project = home / "demo"
    project.mkdir()
    (project / ".lonca.toml").touch()
    env = dict(os.environ, **fixture_home(home), CLAUDE_ENV_FILE=str(home / "session-env"))
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    env.pop("DEJA_POLICY_FILE", None)
    env.pop("LONCA", None)
    event = json.dumps({"session_id": "fixture", "source": "startup", "cwd": str(project)})
    for order in ((env, dict(env, CLAUDE_PLUGIN_ROOT=str(SRC))), (dict(env, CLAUDE_PLUGIN_ROOT=str(SRC)), env)):
        outputs = [run(SRC / "bin/memory-context", env=e, input=event) for e in order]
        assert sum(bool(out) for out in outputs) == 1, outputs
        for e in order:
            run(SRC / "bin/deja-scope", "--session", env=e, input=event)
    assert (home / "session-env").read_text().count("export DEJA_POLICY_FILE=") == 2
    assert run(SRC / "bin/memory-context", env=env, input=event)


def off_switch(base):
    # Invoke hook entry points directly with inert input in a disposable home.
    repo = base / "hooks-test"
    repo.mkdir()
    git(repo, "init", "-q")
    env = dict(os.environ, **fixture_home(base), LONCA="0", CLAUDE_ENV_FILE=str(base / "env"))
    hook_event = json.dumps({"cwd": str(repo), "session_id": "test"})
    for program, args in (("bin/deja-scope", ["--session"]), ("bin/memory-context", []),
                          ("bin/session-tmpdir", []), ("bin/session-scope", []), ("bin/ai-trace-gh", ["--hook"])):
        assert not run(SRC / program, *args, cwd=repo, env=env, input=hook_event)
    hooks = runpy.run_path(str(SRC / "bin/lonca"))["codex_hooks"]()
    (base / "lonca").symlink_to(SRC, target_is_directory=True)
    for groups in hooks["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                assert not run("sh", "-c", hook["command"], cwd=repo, env=env, input=hook_event)
    assert not (base / "env").exists()
    # No push takes place. Both guards must reject the inert input with automation off.
    git(repo, "remote", "add", "origin", "https://example.invalid/test")
    trace = "Co-Authored-By: Claude <noreply@anthropic.com>"
    message = repo / "test"
    message.write_text(trace)
    run(SRC / "git-hooks/commit-msg", "test", cwd=repo, env=env, ok=False)
    run(SRC / "git-hooks/pre-push", "origin", cwd=repo, env=env, input="x 1 refs/heads/main 2\n", ok=False)
    run(SRC / "bin/ai-trace-gh", "--hook", cwd=repo, env=env,
        input=json.dumps({"tool_input": {"command": f"gh pr comment 1 --body '{trace}'"}}), ok=False)
    message.write_text("Ordinary message")
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
        os.environ.update(fixture_home(base))
        overlapping_hooks(base)
        off_switch(base)
        test(base)
        migration(base)
        direct_uninstall(base)
    print("per-project layout passed")
