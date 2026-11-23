"""Remove entries written by the pre-project installer, preserving unrelated settings."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

from lonca_registry import BIN, HOME, STATE

LONCA = HOME / "lonca"
CONF = HOME / ".claude/settings.json"
CACHE = HOME / ".claude/plugins/known_marketplaces.json"
OLD_MARKET = LONCA / "extras/sui/plugins"
MCP = {"claude": ".claude.json", "codex": ".codex/config.toml", "copilot": ".copilot/mcp-config.json",
       "agy": ".gemini/config/mcp_config.json", "grok": ".grok/config.toml", "omp": ".omp/agent/mcp.json",
       "pi": ".pi/agent/mcp.json", "opencode": ".config/opencode/opencode.json"}
HARNESS_LINKS = {
    ".codex/AGENTS.md": "AGENTS.md", ".codex/rules/default.rules": "config/codex-rules/default.rules",
    ".omp/agent/RULES.md": "AGENTS.md", ".omp/agent/extensions/lonca-guard": "config/omp-guard",
    ".config/opencode/AGENTS.md": "AGENTS.md", ".config/opencode/agents/lonca-lane.md": "config/opencode/lonca-lane.md",
    ".gemini/AGENTS.md": "AGENTS.md", ".config/amp/AGENTS.md": "AGENTS.md", ".grok/AGENTS.md": "AGENTS.md",
    ".copilot/copilot-instructions.md": "AGENTS.md", ".config/crush/CRUSH.md": "AGENTS.md", ".pi/agent/AGENTS.md": "AGENTS.md",
}


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()


class Legacy:
    def __init__(self, dry=False):
        self.dry = dry
        self.directory = None

    def backup(self, path):
        if not self.directory:
            base = STATE / "migration-backups"
            base.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.directory = Path(tempfile.mkdtemp(dir=base))
            print(f"Backups: {self.directory}")
        target = self.directory / path.relative_to(HOME)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not target.exists() and not target.is_symlink():
            if path.is_symlink():
                target.symlink_to(os.readlink(path))
            elif path.is_file():
                shutil.copyfile(path, target)
                target.chmod(0o600)

    def change(self, path, data, description):
        if path.parent.resolve() != path.parent or (path.is_symlink() and data is not None):
            raise ValueError(f"refusing to edit symlink: {path}")
        if data is not None and path.read_bytes() == data:
            return
        print(f"{description}: {path}")
        if self.dry:
            return
        self.backup(path)
        if data is None:
            path.unlink()
            return
        fd, tmp = tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as out:
                os.fchmod(out.fileno(), stat.S_IMODE(path.stat().st_mode))
                out.write(data)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def marketplace(self, uninstall=False):
        for path in (CONF, CACHE):
            if not path.is_file():
                continue
            data = json.loads(path.read_bytes())
            markets = data.get("extraKnownMarketplaces", {}) if path == CONF else data
            market = markets.get("lonca", {})
            src = market.get("source", {})
            if src.get("source") != "directory":
                continue
            target = Path(src.get("path", "")).expanduser().resolve()
            if target not in (OLD_MARKET.resolve(), LONCA.resolve()):
                continue
            if uninstall or path == CONF and target == OLD_MARKET.resolve():
                del markets["lonca"]
            elif target == OLD_MARKET.resolve():
                src["path"] = str(LONCA)
                if "installLocation" in market:
                    market["installLocation"] = str(LONCA)
            else:
                continue
            self.change(path, json_bytes(data), "remove Lonca marketplace" if uninstall else "repoint Lonca marketplace")

    def harness_files(self):
        for dst, src in HARNESS_LINKS.items():
            path = HOME / dst
            if path.is_symlink() and path.resolve() == (LONCA / src).resolve():
                self.change(path, None, "unlink installed harness file")
        for dest, kind in ((".claude/agents", "agents"), (".claude/skills", "skills"), (".agents/skills", "skills"),
                           (".gemini/skills", "skills"), (".config/agents/skills", "skills")):
            for path in (HOME / dest).glob("*"):
                if path.is_symlink() and any(path.resolve() == (root / kind / path.name).resolve()
                                             for root in (LONCA, HOME / "lonca-local")):
                    self.change(path, None, "unlink installed " + kind)

        doc = HOME / ".claude/CLAUDE.md"
        if doc.is_file():
            original = doc.read_bytes()
            text = b"".join(line for line in original.splitlines(True) if line.rstrip(b"\r\n") != b"@~/lonca/AGENTS.md")
            self.change(doc, text, "remove Lonca import")

        for path in (CONF, HOME / ".codex/hooks.json"):
            if path.is_symlink() and path.resolve().is_relative_to(LONCA.resolve()):
                self.change(path, None, "unlink installed hooks")
                continue
            if not path.is_file():
                continue
            data = json.loads(path.read_bytes())
            before = json_bytes(data)
            bak = path.with_name(path.name + ".lonca-bak")
            previous = json.loads(bak.read_bytes()) if bak.is_file() else {}
            hooks_by_event = data.get("hooks", {})
            ours = any("/lonca/bin/" in hook.get("command", "") for groups in hooks_by_event.values()
                       for group in groups for hook in group.get("hooks", []))
            if not bak.exists() and not ours:
                continue
            if path == CONF:
                deny = data.get("permissions", {}).get("deny", [])
                installed = json.loads((BIN.parent / "config/claude-permissions.json").read_bytes())["deny"]
                for rule in installed:
                    if rule in deny and rule not in previous.get("permissions", {}).get("deny", []):
                        deny.remove(rule)
                for key, value in (("attribution", {"commit": "", "pr": ""}), ("includeCoAuthoredBy", False),
                                   ("autoMemoryDirectory", "~/ai-memory")):
                    if data.get(key) == value and key not in previous:
                        del data[key]
                    elif data.get(key) == value and previous.get(key) != value:
                        data[key] = previous[key]
                env = data.get("env", {})
                tmp = subprocess.check_output([BIN / "lonca-config", "tmpdir", HOME / ".cache/lonca/tmp"], text=True).strip()
                if env.get("TMPDIR") == tmp and "TMPDIR" not in previous.get("env", {}):
                    del env["TMPDIR"]
            commands = {"SessionStart": {f"{LONCA}/bin/memory-context", f"{LONCA}/bin/deja-scope --session",
                                         f"{LONCA}/bin/session-tmpdir", "cat ~/ai-memory/MEMORY.md"},
                        "PreToolUse": {f"{LONCA}/bin/ai-trace-gh --hook"}, "Stop": {f"python3 {LONCA}/config/memory-nudge.py"}}
            for event, groups in data.get("hooks", {}).items():
                for group in list(groups):
                    hooks = group.get("hooks", [])
                    for hook in list(hooks):
                        cmd = hook.get("command", "").replace("~/lonca/", str(LONCA) + "/")
                        existed = any(hook in g.get("hooks", []) for g in previous.get("hooks", {}).get(event, []))
                        if hook.get("type") == "command" and cmd in commands.get(event, ()) and not existed:
                            hooks.remove(hook)
                    if not hooks:
                        groups.remove(group)
            if json_bytes(data) != before:
                self.change(path, json_bytes(data), "remove legacy harness settings")

    def global_git(self):
        # Only edit a single, identifiable value in the user's own Git config.
        r = subprocess.run(["git", "config", "--global", "--show-origin", "--get-all", "core.hooksPath"],
                           text=True, capture_output=True)
        if r.returncode == 1:
            return
        r.check_returncode()
        lines = r.stdout.splitlines()
        if len(lines) == 1:
            origin, value = lines[0].split("\t", 1)
            path = Path(origin.removeprefix("file:"))
            if value == str(LONCA / "git-hooks") and path.is_absolute() and path.is_relative_to(HOME):
                if path.resolve() != path:
                    raise ValueError(f"refusing symlink: {path}")
                print(f"remove global core.hooksPath: {path}")
                if not self.dry:
                    self.backup(path)
                    subprocess.run(["git", "config", "--global", "--unset", "core.hooksPath"], check=True)

    def scope_settings(self):
        from lonca_registry import registered
        registry = registered()
        managed = {str(Path(repo) / ".claude/settings.local.json") for project in registry.values()
                   for repo in project["repos"]}
        directory = STATE / "deja"
        record = directory / "settings-written"
        if not record.is_file():
            return
        keep = []
        for line in record.read_text().splitlines():
            path = Path(line)
            if str(path) in managed:
                keep.append(line)
                continue
            if not path.is_absolute() or path.resolve() != path or path.parts[-2:] != (".claude", "settings.local.json"):
                raise ValueError(f"invalid legacy settings record: {path}")
            if not path.is_file():
                continue
            data = json.loads(path.read_bytes())
            value = data.get("env", {}).get("DEJA_POLICY_FILE")
            if value and Path(value).parent == directory and Path(value).suffix == ".json":
                del data["env"]["DEJA_POLICY_FILE"]
                if not data["env"]:
                    del data["env"]
                self.change(path, json_bytes(data), "remove recorded legacy session scope")
        if keep:
            self.change(record, ("\n".join(keep) + "\n").encode(), "update legacy scope record")
        else:
            self.change(record, None, "remove legacy scope record")

    def timers(self):
        if sys.platform == "darwin":
            subprocess.run([BIN / "launchd-units", "preview" if self.dry else "migrate"], check=True)
            return
        units = HOME / ".config/systemd/user"
        for name in ("deja-index", "ai-memory-commit", "kanzo-backup"):
            path = units / (name + ".service")
            if path.is_symlink() and path.resolve() == (LONCA / "config/systemd" / path.name).resolve():
                print("reload project-scoped systemd services")
                if not self.dry:
                    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
                break

    def mcp_entry(self, harness, server):
        path = HOME / MCP[harness]
        if not path.exists():
            return None
        if path.resolve() != path:
            raise ValueError(f"refusing symlink: {path}")
        if path.suffix == ".toml":
            try:
                import tomllib
            except ImportError:
                raise ValueError(f"Python 3.11+ is needed to inspect the recorded MCP entry in {path}")
            servers = tomllib.loads(path.read_text()).get("mcp_servers", {})
        else:
            data = json.loads("".join(line for line in path.read_text().splitlines(True)
                                      if not line.lstrip().startswith("//")))
            servers = data.get("mcp" if harness == "opencode" else "mcpServers", {})
        return servers.get(server)

    def remove_mcp(self):
        state = STATE / "mcp-added"
        if not state.is_file():
            return
        for line in state.read_text().splitlines():
            harness, server = line.split()
            if harness not in MCP or server not in ("kanzo", "deja"):
                continue
            entry = self.mcp_entry(harness, server)
            command = (entry or {}).get("command", "")
            argv = command if isinstance(command, list) else [command, *(entry or {}).get("args", [])]
            if entry is None or not argv or Path(argv[0]).name != server or argv[1:] != ["mcp"]:
                print(f"keep current {harness} MCP settings; release old record for {server}")
                remaining = state.read_text().splitlines()
                remaining.remove(line)
                self.change(state, "".join(row + "\n" for row in remaining).encode(), "release stale MCP record")
                continue
            print(f"remove recorded user MCP {harness} {server}")
            if not self.dry:
                self.backup(state)
                self.backup(HOME / MCP[harness])
                subprocess.run([BIN / "lonca-mcp", "remove", harness, server], check=True)
                if line in state.read_text().splitlines() or self.mcp_entry(harness, server) is not None:
                    raise ValueError(f"could not remove recorded {harness} MCP {server}; check its CLI before retrying")
        if state.is_file() and not state.read_text().strip():
            self.change(state, None, "remove empty MCP record")

    def cleanup(self):
        self.harness_files()
        self.global_git()
        self.scope_settings()
        self.remove_mcp()
