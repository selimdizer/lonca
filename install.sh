#!/bin/sh
# install.sh [--yes] [--memory-review] [--agent-tmpdir] [--sui] [--uninstall]: set Lonca up for this user (or take it out).
#   --yes             accept the defaults without asking (all harnesses found; timers on; the two opt-ins below off)
#   --memory-review   turn on the background memory review (every 2 h it sends your recent messages to Sonnet)
#   --agent-tmpdir    point Claude sessions' TMPDIR at Lonca's temp dir (for a RAM-backed or small /tmp)
#   --sui             extras/sui: lanes run sui/move-analyzer at each repo's CI SUI_VERSION; Move LSP plugin
#   --uninstall       remove what this script added (keeps ~/ai-memory, ~/lonca-local and the *.lonca-bak backups)
# Safe to re-run; backs up every config file it changes as *.lonca-bak. What it does: links the skills and agents
# into Claude Code and the harnesses you pick, the rules (AGENTS.md) into each; commands into ~/.local/bin; a global
# git core.hooksPath (repos' own hooks still run); Lonca's deny rules and hooks in ~/.claude/settings.json and, for
# Codex, ~/.codex/hooks.json; ~/ai-memory from the template; timers (systemd on Linux, launchd on macOS).
# Your private layer, ~/lonca-local (skills/, agents/, shims/, routing.md), is linked on top.
set -eu
YES=0 UN=0 MR=0 TMPQ=0 SUI=0
usage() { echo "usage: install.sh [--yes] [--memory-review] [--agent-tmpdir] [--sui] [--uninstall]   (--help: what each does)" >&2; }
for arg in "$@"; do case $arg in
  --yes) YES=1 ;; --uninstall) UN=1 ;; --memory-review) MR=1 ;; --agent-tmpdir) TMPQ=1 ;; --sui) SUI=1 ;;
  -h|--help) sed -n '2,/^set -eu/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
  *) usage; exit 2 ;; esac; done
SRC=$(cd "$(dirname "$0")" && pwd -P)
L=$HOME/lonca
say() { printf '%s\n' "$*"; }
ask() { [ $YES = 1 ] && return 0; printf '%s [y/N] ' "$1"; read -r a; [ "$a" = y ] || [ "$a" = Y ]; }
opt_in() { [ "$1" = 1 ] && return 0; [ $YES = 1 ] && return 1; printf '%s [y/N] ' "$2"; read -r a; [ "$a" = y ] || [ "$a" = Y ]; }
link() { # target link-path: never overwrites a real file
  mkdir -p "$(dirname "$2")"
  if [ -L "$2" ]; then ln -sfn "$1" "$2"
  elif [ -e "$2" ]; then say "  skip (real file exists): $2"
  else ln -s "$1" "$2"; fi
}

if [ $UN = 1 ]; then
  # every symlink that points into this checkout, the timers, the hooks path, Lonca's lines in the settings files;
  # ~/ai-memory, ~/lonca-local and the *.lonca-bak backups are yours and stay
  if command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
    for t in "$SRC"/config/systemd/*.timer; do systemctl --user disable --now "$(basename "$t")" >/dev/null 2>&1 || true; done
  fi
  [ "$(uname)" = Darwin ] && python3 "$SRC/bin/launchd-units" uninstall
  for d in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.claude/agents" "$HOME/.local/bin" "$HOME/.config/systemd/user" \
           "$HOME/.codex" "$HOME/.codex/rules" "$HOME/.omp/agent" "$HOME/.omp/agent/extensions" "$HOME/.config/opencode" "$HOME/.gemini" "$HOME/.gemini/skills" "$HOME/.copilot" "$HOME/.config/crush" "$HOME/.pi/agent" "$HOME/.config/amp" "$HOME/.config/agents/skills" "$HOME/.grok" "$HOME/lonca-local/shims" "$HOME/Library/LaunchAgents"; do
    for f in "$d"/* "$d"/.[!.]*; do
      [ -L "$f" ] || continue
      case $(readlink -f "$f" 2>/dev/null) in "$SRC"/*|"$SRC") rm "$f" ;; esac
    done
  done
  [ "$(git config --global core.hooksPath || true)" = "$HOME/lonca/git-hooks" ] && git config --global --unset core.hooksPath
  [ -f "$HOME/.claude/CLAUDE.md" ] && { grep -v "^@~/lonca/AGENTS.md$" "$HOME/.claude/CLAUDE.md" > "$HOME/.claude/CLAUDE.md.new" || true; mv "$HOME/.claude/CLAUDE.md.new" "$HOME/.claude/CLAUDE.md"; }
  python3 -I - "$SRC" <<'EOF2'
import json, os, sys
L = os.path.expanduser("~/lonca"); H = os.path.expanduser("~")
def strip(p, deny=False):
    try: s = json.load(open(p))
    except (OSError, ValueError): return
    if deny:
        ours = set(json.load(open(f"{sys.argv[1]}/config/claude-permissions.json"))["deny"])
        s.get("permissions", {})["deny"] = [r for r in s.get("permissions", {}).get("deny", []) if r not in ours]
        s.get("extraKnownMarketplaces", {}).pop("lonca", None)
    for ev, groups in s.get("hooks", {}).items():
        ours = (L, "cat ~/ai-memory/MEMORY.md")
        for g in groups: g["hooks"] = [h for h in g.get("hooks", []) if not any(o in h.get("command", "").replace("~/lonca", L).replace("~/", H + "/") or o == h.get("command") for o in ours)]
        s["hooks"][ev] = [g for g in groups if g["hooks"]]
    json.dump(s, open(p, "w"), indent=2)
strip(f"{H}/.claude/settings.json", deny=True); strip(f"{H}/.codex/hooks.json")
EOF2
  [ -L "$L" ] && rm "$L"
  say "Lonca removed. Kept: ~/ai-memory, ~/lonca-local, the *.lonca-bak backups, this checkout ($SRC), and these"
  say "settings it set in ~/.claude/settings.json: attribution off, env.TMPDIR (if you chose it), autoMemoryDirectory."
  exit 0
fi

# 1. Scripts and docs use ~/lonca: the checkout lives there or ~/lonca points at it
if [ "$(cd "$L" 2>/dev/null && pwd -P)" != "$SRC" ]; then
  [ -e "$L" ] && { say "~/lonca exists and is not this checkout ($SRC); move one of them first"; exit 1; }
  ln -s "$SRC" "$L"; say "linked ~/lonca -> $SRC"
fi
git -C "$L" config lonca.toolNamesOk true   # Lonca's own commits may name the tools it is about

# 2. Tools
say "Tools:"
for t in claude git gh python3; do command -v $t >/dev/null || { say "  missing (required): $t"; exit 1; }; done
for t in herdr hc kanzo deja; do
  if command -v $t >/dev/null; then say "  ok       $t"; else say "  missing  $t (optional; see README: what works without it)"; fi
done

# 3. Skills, agents, rules, commands, hooks
# Other harnesses: you choose which ones get Lonca (rules + skills; Claude Code always does)
found=
for h in codex omp opencode agy copilot amp grok crush pi; do
  command -v $h >/dev/null || continue
  found="$found $h"
done
pick=$found
if [ -n "$found" ] && [ $YES = 0 ]; then
  printf 'Harnesses found (agy = Antigravity):%s\nWhich get Lonca? (space-separated, Enter = all, "none" = none): ' "$found"; read -r a
  case $a in "") ;; none) pick= ;; *) pick=$a ;; esac
fi
sk=   # skill folders beyond ~/.agents/skills, for harnesses that don't read it
for h in $pick; do
  case $h in
    codex)    link "$L/AGENTS.md" "$HOME/.codex/AGENTS.md"; link "$L/config/codex-rules/default.rules" "$HOME/.codex/rules/default.rules" ;;
    omp)      link "$L/AGENTS.md" "$HOME/.omp/agent/RULES.md"; link "$L/config/omp-guard" "$HOME/.omp/agent/extensions/lonca-guard" ;;
    opencode) link "$L/AGENTS.md" "$HOME/.config/opencode/AGENTS.md" ;;
    agy)      link "$L/AGENTS.md" "$HOME/.gemini/AGENTS.md"; sk="$sk $HOME/.gemini/skills" ;;   # Antigravity CLI
    amp)      link "$L/AGENTS.md" "$HOME/.config/amp/AGENTS.md"; sk="$sk $HOME/.config/agents/skills" ;;
    grok)     link "$L/AGENTS.md" "$HOME/.grok/AGENTS.md" ;;               # xAI Grok Build; global file name from docs, unverified
    copilot)  link "$L/AGENTS.md" "$HOME/.copilot/copilot-instructions.md" ;;
    crush)    link "$L/AGENTS.md" "$HOME/.config/crush/CRUSH.md" ;;
    pi)       link "$L/AGENTS.md" "$HOME/.pi/agent/AGENTS.md" ;;
    *) say "  unknown harness: $h (skipped)"; continue ;;
  esac
  say "  linked: $h"
done
export LONCA_HARNESSES="$pick"   # read by the settings step
for s in "$L"/skills/*/ $HOME/lonca-local/skills/*/; do
  [ -f "$s/SKILL.md" ] || continue
  n=$(basename "$s")
  link "$s" "$HOME/.claude/skills/$n"        # Claude Code
  [ -n "$pick" ] && link "$s" "$HOME/.agents/skills/$n"   # read by Codex, omp, OpenCode, Copilot, Crush, Grok, pi
  for d in $sk; do link "$s" "$d/$n"; done
done
for a in "$L"/agents/*.md $HOME/lonca-local/agents/*.md; do
  [ -f "$a" ] && link "$a" "$HOME/.claude/agents/$(basename "$a")"
done
grep -qsF "@~/lonca/AGENTS.md" "$HOME/.claude/CLAUDE.md" || {
  mkdir -p "$HOME/.claude"; [ -f "$HOME/.claude/CLAUDE.md" ] && cp "$HOME/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md.lonca-bak"
  { cat "$HOME/.claude/CLAUDE.md" 2>/dev/null || true; echo "@~/lonca/AGENTS.md"; } > "$HOME/.claude/CLAUDE.md.new"
  mv "$HOME/.claude/CLAUDE.md.new" "$HOME/.claude/CLAUDE.md"; }
for c in lane lanes lonca-project merge-pr night-merge night-on ok-merge kanzo-sync; do link "$L/bin/$c" "$HOME/.local/bin/$c"; done
export LONCA_SUI=
if command -v suiup >/dev/null || [ $SUI = 1 ]; then
  if opt_in $SUI "Sui Move extra: lanes run sui/move-analyzer at each repo's CI SUI_VERSION, plus a Move LSP plugin for Claude?"; then
    link "$L/extras/sui/sui-pick" "$HOME/lonca-local/shims/sui"                  # lanes put ~/lonca-local/shims on PATH
    link "$L/extras/sui/move-analyzer" "$HOME/.local/bin/lonca-move-analyzer"   # what the plugin starts
    LONCA_SUI=1; say "  Sui extra on"
  fi
fi
hp=$(git config --global core.hooksPath || true)
case $hp in ""|*/lonca/git-hooks) git config --global core.hooksPath "$L/git-hooks" ;;
  *) say "  git core.hooksPath is $hp: left alone; add $L/git-hooks/* to it yourself" ;; esac
AT=$("$L/bin/lonca-config" tmpdir "$HOME/.cache/lonca/tmp")   # agents' temp dir (lanes always use it)
mkdir -p "$AT" "$HOME/lonca-local"   # lonca-local: your private layer (model-log.jsonl, own skills)
export LONCA_CLAUDE_TMPDIR=
opt_in $TMPQ "Claude sessions write temp files to $AT instead of /tmp (useful when /tmp is RAM or small)?" && LONCA_CLAUDE_TMPDIR=$AT
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) say "  note: $HOME/.local/bin is not on your PATH; add it so lane, merge-pr and ok-merge are found" ;; esac

# 4. Claude and Codex settings: add Lonca's deny rules and hooks, keep everything else
python3 -I - "$L" <<'EOF'
import json, os, shutil, sys
L = sys.argv[1]; H = os.path.expanduser("~")
def load(p):
    try: return json.load(open(p))
    except (OSError, ValueError): return {}
def save(p, d):
    if os.path.exists(p): shutil.copy(p, p + ".lonca-bak")
    os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(d, open(p, "w"), indent=2); open(p, "a").write("\n")
def add_hook(hooks, event, matcher, cmd):  # updates an older copy of the same hook in place
    for g in hooks.setdefault(event, []):
        for h in g.get("hooks", []):
            if h.get("command", "").replace("~/", H + "/") == cmd.replace("~/", H + "/"):
                h["command"] = cmd; return
    g = {"hooks": [{"type": "command", "command": cmd}]}
    if matcher: g["matcher"] = matcher
    hooks[event].append(g)

p = f"{H}/.claude/settings.json"; s = load(p)
deny = s.setdefault("permissions", {}).setdefault("deny", [])
deny += [r for r in json.load(open(f"{L}/config/claude-permissions.json"))["deny"] if r not in deny]
hooks = s.setdefault("hooks", {})
add_hook(hooks, "SessionStart", "startup|resume|clear|compact", f"{L}/bin/memory-context")
add_hook(hooks, "PreToolUse", "Bash", f"{L}/bin/ai-trace-gh --hook")
if os.environ.get("LONCA_CLAUDE_TMPDIR"):
    s.setdefault("env", {}).setdefault("TMPDIR", os.environ["LONCA_CLAUDE_TMPDIR"])
s["attribution"] = {"commit": "", "pr": ""}; s["includeCoAuthoredBy"] = False
s.setdefault("autoMemoryDirectory", "~/ai-memory")
if os.environ.get("LONCA_SUI"):
    s.setdefault("extraKnownMarketplaces", {})["lonca"] = {"source": {"source": "directory", "path": f"{L}/extras/sui/plugins"}}
save(p, s)

HS = os.environ.get("LONCA_HARNESSES", "").split()
if "codex" in HS:
    p = f"{H}/.codex/hooks.json"; c = load(p); hk = c.setdefault("hooks", {})
    add_hook(hk, "SessionStart", "startup|resume|clear|compact", "cat ~/ai-memory/MEMORY.md")
    add_hook(hk, "SessionStart", "startup|resume|clear|compact", f"{L}/bin/memory-context")
    add_hook(hk, "Stop", None, f"python3 {L}/config/memory-nudge.py")
    save(p, c)
print("settings: Claude" + "".join(f" + {h.capitalize()}" for h in ("codex",) if h in HS) + " updated (backups *.lonca-bak)")
EOF

# 5. Shared memory
if [ ! -d "$HOME/ai-memory" ]; then
  M=$HOME/ai-memory
  cp -r "$L/memory-template" "$M" && git -C "$M" init -q && git -C "$M" add -A &&
    git -C "$M" -c user.name=Lonca -c user.email=lonca@localhost commit -qm "memory: start from the Lonca template" && say "created ~/ai-memory"
fi

# 6. Timers. Each is skipped when its tool is missing; the memory review only when you opt in.
skip=
command -v hc >/dev/null || skip="$skip lane-watch"
command -v kanzo >/dev/null || skip="$skip kanzo-sync kanzo-backup monthly-card"
command -v deja >/dev/null || skip="$skip deja-index"
opt_in $MR "Background memory review: every 2 h, send your messages from Claude sessions since the last run (all projects) to Sonnet on your Claude plan, which saves lasting decisions to ~/ai-memory. Turn on?" || skip="$skip memory-review"
if command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
  if ask "Install the timers (lane-watch, kanzo-sync, ai-cleanup, ai-memory-commit, …; skipped:${skip:- none})?"; then
    U=$HOME/.config/systemd/user; mkdir -p "$U"
    for f in "$L"/config/systemd/*.service "$L"/config/systemd/*.timer; do link "$f" "$U/$(basename "$f")"; done
    systemctl --user daemon-reload
    for t in "$L"/config/systemd/*.timer; do
      n=$(basename "$t" .timer)
      case " $skip " in *" $n "*) continue ;; esac
      systemctl --user enable --now "$n.timer" >/dev/null 2>&1 && say "  timer on: $n"
    done
  fi
elif [ "$(uname)" = Darwin ]; then
  if ask "Install the timers as launchd agents (lane-watch, kanzo-sync, ai-cleanup, ai-memory-commit, …; skipped:${skip:- none})?"; then
    python3 "$L/bin/launchd-units" install $skip
  fi
else
  say "No systemd or launchd: run bin/lane-watch, bin/kanzo-sync and bin/ai-cleanup from cron yourself."
fi
# Kanzo board: the lead and kanzo-sync talk to it over MCP
if command -v kanzo >/dev/null && ! grep -qs '"kanzo"' "$HOME/.claude.json"; then
  claude mcp add --scope user kanzo -- kanzo mcp >/dev/null 2>&1 && say "  Kanzo MCP added to Claude Code" || say "  add Kanzo to Claude yourself: claude mcp add --scope user kanzo -- kanzo mcp"
fi
say "Lonca is set up. Start a lead in a project folder:  claude --agent lead"
