"""Remove entries written by the pre-project installer, preserving unrelated settings."""
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

from lonca_registry import BIN, HOME, STATE

LONCA = HOME / "lonca"
CONF = HOME / ".claude/settings.json"
CACHE = HOME / ".claude/plugins/known_marketplaces.json"
OLD_MARKET = LONCA / "extras/sui/plugins"
MCP = {"claude": ".claude.json", "codex": ".codex/config.toml", "copilot": ".copilot/mcp-config.json",
       "agy": ".gemini/config/mcp_config.json", "grok": ".grok/config.toml", "omp": ".omp/agent/mcp.json",
       "pi": ".pi/agent/mcp.json", "opencode": ".config/opencode/opencode.json"}
DEFERRED_MCP = {"opencode", "copilot", "agy", "grok", "pi"}
HARNESS_LINKS = {
    ".codex/AGENTS.md": "AGENTS.md", ".codex/rules/default.rules": "config/codex-rules/default.rules",
    ".omp/agent/RULES.md": "AGENTS.md", ".omp/agent/extensions/lonca-guard": "config/omp-guard",
    ".config/opencode/AGENTS.md": "AGENTS.md", ".config/opencode/agents/lonca-lane.md": "config/opencode/lonca-lane.md",
    ".gemini/AGENTS.md": "AGENTS.md", ".config/amp/AGENTS.md": "AGENTS.md", ".grok/AGENTS.md": "AGENTS.md",
    ".copilot/copilot-instructions.md": "AGENTS.md", ".config/crush/CRUSH.md": "AGENTS.md", ".pi/agent/AGENTS.md": "AGENTS.md",
}


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()


def deferred_mcp():
    for harness in sorted(DEFERRED_MCP):
        for server in ("kanzo", "deja"):
            try:
                entry = Legacy.mcp_entry(harness, server)
            except ValueError:
                print(f"  cannot inspect {harness} MCP file", file=sys.stderr)
                break
            if entry is not None:
                yield harness, server


class Legacy:
    def __init__(self, dry=False):
        self.dry = dry
        self.directory = None

    def prune(self, uninstall=False):
        base = STATE / "migration-backups"
        if base.resolve() != base:
            raise ValueError(f"refusing symlink: {base}")
        if not base.is_dir():
            return
        for folder in base.iterdir():
            if folder.is_symlink() or not folder.is_dir() or folder.stat().st_uid != os.getuid():
                continue
            # Previous releases used mkdtemp's default name and a filesystem/ tree.
            legacy = re.fullmatch(r"tmp[a-z0-9_]{8}", folder.name) and (folder / "filesystem").is_dir()
            receipt = re.fullmatch(r"migration-[a-z0-9_]{8}", folder.name) and (folder / "changes.jsonl").is_file()
            if (legacy or receipt) and (uninstall or folder.stat().st_mtime <= time.time() - 30 * 86400):
                print(f"prune migration backup: {folder}")
                if not self.dry:
                    shutil.rmtree(folder)

    def backup(self, path, removed):
        if not self.directory:
            base = STATE / "migration-backups"
            if base.resolve() != base:
                raise ValueError(f"refusing symlink: {base}")
            base.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.directory = Path(tempfile.mkdtemp(prefix="migration-", dir=base))
            print(f"Migration backup: {self.directory / 'changes.jsonl'}")
        with (self.directory / "changes.jsonl").open("a", opener=lambda p, f: os.open(p, f, 0o600)) as out:
            out.write(json.dumps({"path": str(path), "removed": removed}, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())

    def change(self, path, data, description, removed=None):
        if path.parent.resolve() != path.parent or (path.is_symlink() and data is not None):
            raise ValueError(f"refusing to edit symlink: {path}")
        if data is not None and path.read_bytes() == data:
            return
        print(f"{description}: {path}")
        if self.dry:
            return
        if removed is None:
            removed = {"symlink": os.readlink(path)}
        self.backup(path, removed)
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
            removed = {"source": {"source": "directory", "path": src["path"]}}
            if market.get("installLocation") in (str(target), str(OLD_MARKET), str(LONCA)):
                removed["installLocation"] = market["installLocation"]
            if uninstall or path == CONF and target == OLD_MARKET.resolve():
                del markets["lonca"]
            elif target == OLD_MARKET.resolve():
                src["path"] = str(LONCA)
                if "installLocation" in market:
                    market["installLocation"] = str(LONCA)
            else:
                continue
            self.change(path, json_bytes(data), "remove Lonca marketplace" if uninstall else "repoint Lonca marketplace",
                        {"lonca": removed} if path == CACHE else {"extraKnownMarketplaces": {"lonca": removed}})

    def harness_files(self, uninstall):
        link_roots = (LONCA, HOME / "lonca-local") if uninstall else (LONCA,)
        for dst, src in HARNESS_LINKS.items():
            path = HOME / dst
            if path.is_symlink() and path.resolve() == (LONCA / src).resolve():
                self.change(path, None, "unlink installed harness file")
        for dest, kind in ((".claude/agents", "agents"), (".claude/skills", "skills"), (".agents/skills", "skills"),
                           (".gemini/skills", "skills"), (".config/agents/skills", "skills")):
            for path in (HOME / dest).glob("*"):
                if path.is_symlink() and any(path.resolve() == (root / kind / path.name).resolve()
                                             for root in link_roots):
                    self.change(path, None, "unlink installed " + kind)

        doc = HOME / ".claude/CLAUDE.md"
        if doc.is_file():
            original = doc.read_bytes()
            text = b"".join(line for line in original.splitlines(True) if line.rstrip(b"\r\n") != b"@~/lonca/AGENTS.md")
            previous = doc.with_name(doc.name + ".lonca-bak")
            if text != original and (not previous.is_file() or b"@~/lonca/AGENTS.md" not in previous.read_bytes().splitlines()):
                self.change(doc, text if text or previous.exists() else None, "remove Lonca import", {"line": "@~/lonca/AGENTS.md"})

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
            removed = {}
            hooks_by_event = data.get("hooks", {})
            commands = {"SessionStart": {f"{LONCA}/bin/memory-context", f"{LONCA}/bin/deja-scope --session",
                                         f"{LONCA}/bin/session-tmpdir", "cat ~/ai-memory/MEMORY.md"},
                        "PreToolUse": {f"{LONCA}/bin/ai-trace-gh --hook"}, "Stop": {f"python3 {LONCA}/config/memory-nudge.py"}}
            def installed_hook(event, hook):
                cmd = hook.get("command", "").replace("~/lonca/", str(LONCA) + "/")
                return hook.get("type") == "command" and cmd in commands.get(event, ())

            ours = any(installed_hook(event, hook) for event, groups in hooks_by_event.items()
                       for group in groups for hook in group.get("hooks", []))
            if not bak.exists() and not ours:
                continue
            if path == CONF:
                deny = data.get("permissions", {}).get("deny", [])
                installed = json.loads((BIN.parent / "config/claude-permissions.json").read_bytes())["deny"]
                prior_deny = previous.get("permissions", {}).get("deny", [])
                retained = [r for r in installed if r in deny and r in prior_deny]
                if retained:
                    print(f"keep {len(retained)} matching deny rules already in {bak}")
                for rule in installed:
                    if rule in deny and rule not in prior_deny:
                        print(f"  remove deny rule {rule}")
                        removed.setdefault("permissions", {}).setdefault("deny", []).append(rule)
                        deny.remove(rule)
                if not deny and "deny" not in previous.get("permissions", {}):
                    data.get("permissions", {}).pop("deny", None)
                if not data.get("permissions") and "permissions" not in previous:
                    data.pop("permissions", None)
                for key, value in (("attribution", {"commit": "", "pr": ""}), ("includeCoAuthoredBy", False),
                                   ("autoMemoryDirectory", "~/ai-memory")):
                    if data.get(key) == value and key not in previous:
                        print(f"  remove {key}")
                        removed[key] = value
                        del data[key]
                    elif data.get(key) == value and previous.get(key) != value:
                        print(f"  restore {key} from backup")
                        removed[key] = value
                        data[key] = previous[key]
                env = data.get("env", {})
                tmp = subprocess.check_output([BIN / "lonca-config", "tmpdir", HOME / ".cache/lonca/tmp"], text=True).strip()
                if env.get("TMPDIR") == tmp and "TMPDIR" not in previous.get("env", {}):
                    print("  remove env.TMPDIR")
                    removed["env"] = {"TMPDIR": tmp}
                    del env["TMPDIR"]
                    if not env and "env" not in previous:
                        data.pop("env", None)
            for event, groups in list(data.get("hooks", {}).items()):
                for group in list(groups):
                    hooks = group.get("hooks", [])
                    count = len(hooks)
                    removed_hooks = []
                    for hook in list(hooks):
                        # The legacy installer overwrote its backup on repeated installs.
                        if installed_hook(event, hook):
                            print(f"  remove {event} hook: {hook['command']}")
                            removed_hooks.append({"type": "command", "command": hook["command"]})
                            hooks.remove(hook)
                    if removed_hooks:
                        group_copy = {"hooks": removed_hooks}
                        if "matcher" in group:
                            group_copy["matcher"] = group["matcher"]
                        removed.setdefault("hooks", {}).setdefault(event, []).append(group_copy)
                    if count and not hooks:
                        groups.remove(group)
                if not groups and event not in previous.get("hooks", {}):
                    del data["hooks"][event]
            if data.get("hooks") == {} and "hooks" not in previous:
                del data["hooks"]
            if json_bytes(data) != before:
                if bak.is_file() and previous == data:
                    desired = bak.read_bytes()
                else:
                    desired = json_bytes(data) if data or bak.exists() else None
                self.change(path, desired, "remove legacy harness settings", removed)

        # Older installers did not record whether this folder was already trusted.
        # Migration respects an existing trust grant. Full uninstall retires this shared folder grant.
        trust = HOME / ".copilot/config.json"
        if trust.is_file():
            def copilot_settings(path):
                return json.loads("".join(line for line in path.read_text().splitlines(True)
                                          if not line.lstrip().startswith("//")))
            before = trust.with_name(trust.name + ".lonca-bak")
            settings = copilot_settings(trust)
            folder = str(HOME / ".herdr/worktrees")
            if folder in settings.get("trustedFolders", []):
                if uninstall or before.is_file() and folder not in copilot_settings(before).get("trustedFolders", []):
                    settings["trustedFolders"].remove(folder)
                    comments = "".join(l for l in trust.read_text().splitlines(True) if l.lstrip().startswith("//"))
                    self.change(trust, comments.encode() + json_bytes(settings), "remove legacy worktree trust",
                                {"trustedFolders": [folder]})
                else:
                    print(f"keep existing worktree trust in {trust} (ownership unrecorded)")

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
                    self.backup(path, {"core.hooksPath": value})
                    subprocess.run(["git", "config", "--global", "--unset", "core.hooksPath"], check=True)

    def scope_settings(self, upcoming):
        from lonca_registry import registered
        registry = registered()
        managed = {str(Path(repo) / ".claude/settings.local.json") for project in registry.values()
                   for repo in project["repos"]}
        managed.update(str(root / ".claude/settings.local.json") for root, p in registry.items() if p.get("root_claude"))
        managed.update(str(repo / ".claude/settings.local.json") for repo in upcoming)
        directory = STATE / "deja"
        record = directory / "settings-written"
        if not record.is_file():
            return
        keep = []
        lines = record.read_text().splitlines()
        for line in lines:
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
                self.change(path, json_bytes(data), "remove recorded legacy session scope",
                            {"env": {"DEJA_POLICY_FILE": value}})
        if keep:
            self.change(record, ("\n".join(keep) + "\n").encode(), "update legacy scope record",
                        {"lines": [line for line in lines if line not in keep]})
        else:
            self.change(record, None, "remove legacy scope record", {"lines": lines})

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

    @staticmethod
    def mcp_entry(harness, server):
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

    def remove_mcp(self, uninstall):
        state = STATE / "mcp-added"
        if not state.is_file():
            return
        for line in state.read_text().splitlines():
            harness, server = line.split()
            if harness not in MCP or server not in ("kanzo", "deja"):
                continue
            if harness in DEFERRED_MCP and not uninstall:
                print(f"still global: {harness} MCP {server}")
                continue
            entry = self.mcp_entry(harness, server)
            command = (entry or {}).get("command", "")
            argv = command if isinstance(command, list) else [command, *(entry or {}).get("args", [])]
            # Only remove the plain stdio registration installed by lonca-mcp.
            # A customized environment, URL or credential belongs to its owner.
            simple = (isinstance(entry, dict) and set(entry) <= {"type", "command", "args", "env", "enabled"}
                      and entry.get("type", "stdio") in ("stdio", "local") and not entry.get("env")
                      and entry.get("enabled", True) is True)
            if not simple or not argv or Path(argv[0]).name != server or argv[1:] != ["mcp"]:
                print(f"keep current {harness} MCP settings; release old record for {server}")
                remaining = state.read_text().splitlines()
                remaining.remove(line)
                self.change(state, "".join(row + "\n" for row in remaining).encode(), "release stale MCP record", {"line": line})
                continue
            print(f"remove recorded user MCP {harness} {server}")
            if not self.dry:
                path = HOME / MCP[harness]
                key = "mcp_servers" if path.suffix == ".toml" else "mcp" if harness == "opencode" else "mcpServers"
                removed = {key: {server: entry}}
                if harness == "claude":
                    data = json.loads(path.read_bytes())
                    del data[key][server]
                    self.change(path, json_bytes(data), "remove user MCP entry", removed)
                    remaining = [row for row in state.read_text().splitlines() if row != line]
                    self.change(state, "".join(row + "\n" for row in remaining).encode(), "update MCP record", {"line": line})
                else:
                    self.backup(state, {"line": line})
                    self.backup(path, removed)
                    subprocess.run([BIN / "lonca-mcp", "remove", harness, server], check=True)
                current = state.read_text().splitlines()
                if self.mcp_entry(harness, server) is not None and line not in current:
                    current.append(line)
                    self.change(state, "".join(row + "\n" for row in current).encode(), "retain pending MCP removal", {"line_added": line})
                if line in current:
                    raise ValueError(f"could not remove recorded {harness} MCP {server}; check its CLI before retrying")
        if state.is_file() and not state.read_text().strip():
            self.change(state, None, "remove empty MCP record", {"lines": []})

    def cleanup(self, uninstall=False, upcoming=()):
        self.harness_files(uninstall)
        self.global_git()
        self.scope_settings(upcoming)
        self.remove_mcp(uninstall)
