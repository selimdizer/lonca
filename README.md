<div align="center">

<img src="assets/logo-wordmark.svg" alt="Lonca" width="320">

**A guild for your coding agents.**
One lead plans and inspects, apprentices build in their own workshops, and nothing reaches the bazaar without the master's seal.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![check](https://github.com/selimdizer/lonca/actions/workflows/check.yml/badge.svg)](https://github.com/selimdizer/lonca/actions/workflows/check.yml)
[![Agents](https://img.shields.io/badge/agents-Claude%20Code%20·%20Codex%20·%20OpenCode%20·%20Copilot%20·%20more-6f42c1)](#requirements)
[![Herdr plugin](https://img.shields.io/badge/herdr-plugin-orange)](#herdr-plugin)

</div>

Give five AI agents your repo and you get five opinions, three half-finished branches, a surprise force-push and a PR
signed *"Generated with ✨"*. Lonca adds the missing structure: one lead plans the work and checks it, the agents write the
code, and nothing merges until you say so.

In an Ottoman craft guild (*lonca*) there were three ranks and one rule:

| Rank | In the guild | In Lonca |
|---|---|---|
| 🧔 **Usta** (master) | sets the standard, signs off the work | **you**: product, design, merge and prod decisions are yours |
| 🧑‍🔧 **Kalfa** (journeyman) | runs the workshop, splits the work, inspects it | **the lead**: plans, picks a model per task, briefs, verifies, reports. It does not write code |
| 🧒 **Çırak** (apprentice) | works at their own bench | **lanes**: one agent each, in its own git worktree and branch, in a terminal you can watch |

**The rule:** nothing leaves the shop without inspection. A PR merges only after verification, a review by a *different*
model family, a security pass and green CI, and only with your approval. Deny rules, command shims and git hooks stop
agents from running `gh pr merge`, pushing to `main`, force-pushing or granting merges themselves. These are guard
rails, not a sandbox: lanes run with full permissions as your user, so a determined agent could get around them.

```
             you (usta)
                │ "build X"                         ▲ "PR #12 ready: verify ✔ review ✔ security ✔ CI ✔"
                ▼                                   │  you: "evet 4f2"           ← the code for that PR
         ┌──── lead (kalfa) ───────────────────────┴──┐
         │ plan → split → route → brief → check → PR  │
         └──┬────────────────┬────────────────┬───────┘
            ▼                ▼                ▼
       lane: Claude     lane: Codex      lane: omp        each in its own worktree,
       (UI work)        (backend)        (cheap reading)  visible as a Herdr tab
            └────── DONE / QUESTION ──────────┘
```

## What it does

- 🧵 **Lanes you can see.** `lane` starts an agent in its own worktree as a [Herdr](https://herdr.dev) terminal. It reports back with `DONE: <outcome>` or asks `QUESTION: …`, and `lane-watch` tells the lead when one goes quiet.
- 🔏 **One way to merge, sized to the risk.** `merge-pr` merges only the PR's *exact* head commit, after CI and evidence from verify, review and security for that commit. A script reads the diff and sets the risk tier (docs/tests = low, auth/payments/migrations/CI/dependencies = high, the rest medium); low needs fewer checks, and you choose per project which tiers merge themselves (none, low, medium or all). Everything else waits for your `evet <code>` in chat.
- 🌙 **Night mode.** The lead asks every question up front and proposes tonight's work for its project. You answer `başla <code>` and go to bed: until the end time, every PR of that project that passes its checks merges without asking. In the morning you get what was done and the questions that came up.
- 🧠 **Memory you only fill once.** `~/ai-memory` is plain Markdown that every agent loads at start, with one group per project. Agents save decisions as they go; an optional background review catches the ones they missed.
- 📋 **A board that keeps itself current.** With [Kanzo](https://github.com/emanuele-em/kanzo), cards move by themselves: *doing* when a lane starts, *review* when its PR opens, *done* when it merges. Issues and PRs your account opens in a project's linked repos get a card too.
- 🛡️ **Guards.** Deny rules, `gh`/`git` shims and git hooks block direct merges, pushes to the default branch, force-pushes, branch deletes, co-author lines and "Generated with" lines.

## Requirements

| Tool | Used for | If it's missing |
|---|---|---|
| Claude Code, git, gh, Python ≥ 3.9 (standard library only; macOS ships it) | everything | required |
| [Herdr](https://herdr.dev) + herdr-core (`hc`) | visible lanes and their messages | `lane` refuses to start: no hidden agents, by design |
| Other agent CLIs, any you like: Codex, omp, OpenCode, Antigravity, Copilot CLI, Amp, Grok, Crush, pi | lanes on other model families (cross-family review needs at least one) | everything runs on Claude |
| [Kanzo](https://github.com/emanuele-em/kanzo) | the board | card steps are skipped |
| [deja](https://github.com/vshulcz/deja-vu) | search across past sessions | the lead asks you instead |
| semgrep, gitleaks, govulncheck | the security check's scanners | the check lists them under "Not verified" |

Timers run as systemd user units on Linux and as launchd agents on macOS; the installer sets up whichever you have.

## Install

```sh
git clone https://github.com/selimdizer/lonca ~/lonca
~/lonca/install.sh
```

From inside Herdr you can instead run `herdr plugin install selimdizer/lonca` and open the **Lonca: set up** pane.

The installer asks a few questions (or take the defaults with `--yes`; `--help` lists every flag). It is safe to run
again, and it backs up every file it changes as `*.lonca-bak`. What it changes:

- **Agent CLIs:** for each harness you pick, links `AGENTS.md` and the skills into that CLI's own folders; Claude Code
  always gets them, plus the agents in `~/.claude/agents`.
- **Claude Code settings** (`~/.claude/settings.json`): Lonca's deny rules; a SessionStart hook that loads the project's
  memory; a PreToolUse hook that checks `gh` text for AI attribution; commit and PR attribution off;
  `autoMemoryDirectory` = `~/ai-memory`; the Kanzo MCP server (if Kanzo is installed).
- **Codex** (if picked): the same memory hooks in `~/.codex/hooks.json`; `lane` marks each repo it runs Codex in as trusted.
- **MCP servers:** Kanzo and deja (when installed) in every harness you picked, through its own `mcp add` command
  (Claude Code, Codex, OpenCode, Copilot, Antigravity, Grok) or its documented `mcp.json` (omp, pi). Uninstall removes
  only the entries Lonca added.
- **Git:** a global `core.hooksPath` with Lonca's `commit-msg` and `pre-push`; every other hook name runs the repo's own
  `.git/hooks/<name>`, so your pre-commit hooks keep working. Repos that set their own `core.hooksPath` (husky,
  lefthook) keep theirs, and Lonca's hooks don't run there.
- **Commands** in `~/.local/bin`: `lane`, `lanes`, `lonca-project`, `merge-pr`, `merge-tier`, `night-on`, `kanzo-sync`.
- **Memory:** `~/ai-memory` from a template, if you don't have one.
- **Timers** (systemd on Linux, launchd on macOS): `lane-watch` (needs `hc`), `kanzo-sync`, `kanzo-backup` and
  `monthly-card` (need Kanzo), `ai-cleanup`, `ai-memory-commit`, `deja-index` (needs deja).
- **Opt-in only:**
  - `--memory-review` (or answer yes): every 2 h a timer sends your messages from Claude sessions since the last run, in
    every project, with a short excerpt of the reply each answered, to Sonnet on your Claude plan. Sonnet saves lasting
    decisions to `~/ai-memory`. It costs plan quota.
  - `--agent-tmpdir`: Claude sessions write temp files to Lonca's temp dir instead of `/tmp`. Lanes always use it.
  - `--sui`: the Sui Move extra in `extras/sui/`. Lanes run `sui`/`move-analyzer` at each repo's CI `SUI_VERSION`, and
    Claude gets a Move LSP plugin.

## Quick start

```sh
cd path/to/your/repo
claude --agent lead
> Add a dark mode toggle to the settings page.
```

The lead asks what is still open and writes a short plan. It then opens lanes (you can watch them in Herdr) and has each one
verified, reviewed by the other model family and security-checked. Finally it opens the PR and comes back with one line:

```
acme/shop#12 → main, head 9c1e4a2, tier medium (14 files, 220 lines)
verify PASS · review SHIP · security CLEAN · CI green. My opinion: safe to merge; it only touches the settings page.
To merge, write: evet 4f2
```

You answer `evet 4f2`, and the lead merges exactly that commit. The code is good for that PR's current head for one
hour: if someone pushes after the checks, the evidence no longer matches, the checks run again and you get a new code.

## Configuration

**Projects.** Lonca needs no projects folder. To group several repos into one project, put a `.lonca.toml` in the folder
that holds them (anywhere on disk; a hidden file, like `.editorconfig`; `lonca.toml` works too). Put it next to your
repos, not inside one, so it stays yours and never reaches a team repo. Only `name` is needed:

```toml
name = "shop"              # memory group ~/ai-memory/shop/ and Kanzo project slug; default: the folder's name
auto_merge = "low"         # optional: merge PRs up to this tier without asking: off | low | medium | all
wait_for_ci = false        # optional: CI checks still running don't block a merge (a failed one always does)
min_tier = "medium"        # optional: nothing in this project counts as low
high_paths = ["src/pay/*"] # optional: more paths that make a PR high tier
```

Lonca finds it the way mise and EditorConfig find theirs: a lane's worktree counts as its main repo, Lonca walks up from
there, and the closest `.lonca.toml` (or `lonca.toml`) wins. With no marker, the git repo is the project. Project-only
skills go in `<project root>/.claude/skills/`, next to the repos rather than inside a team repo.
`~/lonca/bin/lonca-project [dir]` shows what Lonca sees.

| What | Where |
|---|---|
| Rules for every agent | `~/lonca/AGENTS.md` |
| Model routing | `~/lonca-local/routing.md` if you write one, else `~/lonca/routing.md` (template; example in `examples/`) |
| Shared memory | `~/ai-memory/` (`MEMORY.md` index + one folder per project) |
| Your own skills, agents, notes | `~/lonca-local/` (linked on top of Lonca's) |
| Run folders (briefs, reports, evidence) | `~/.cache/ai-runs/<project>/` |
| Approval codes, merge log | `~/.local/state/lonca/approvals/`, `~/.cache/ai-runs/night/log` |
| Settings (optional) | `~/.config/lonca/config.toml`: `tmpdir`, `cleanup_tmp_dirs` (see `lonca-config --help`) |

**Environment variables:**

| Variable | What it does |
|---|---|
| `LONCA_PROJECT` | overrides the project name |
| `ALLOW_MAIN_PUSH=1` | lets *you* push to the default branch past the hook, on purpose |
| `LONCA_LEAD_CMD` | the command the Herdr plugin's "start a lead" runs (default `claude --agent lead`) |

**Git config.**

| Key | What it does |
|---|---|
| `lonca.strictTraces true` (global) | besides attribution lines, refuse any AI tool or model name in commits, PRs and issues |
| `lonca.toolNamesOk true` (per repo) | lifts `strictTraces` in a repo whose subject is AI tools |
| `lonca.mergeMethod merge\|squash\|rebase` (per repo) | how `merge-pr` merges; default: what the repo allows, in that order |

A repo without CI checks needs `wait_for_ci = false` in its project's `.lonca.toml` to merge at all.

**Roles and tools.** Every role gets every tool, MCP server and skill you have; nothing is listed one by one, so a
server or skill you add later reaches them too. Only the checkers (`reviewer`, `verifier`, `security-auditor`) can't
edit files (`disallowedTools: Edit, Write, NotebookEdit`): a reviewer that fixes the code it reviews would approve
its own work. The lead keeps all tools; "don't edit project code" is a rule in its instructions, since a block on
Edit/Write would protect nothing while it has Bash.

**Lane agents:** `claude:<role>`, `codex:<model>[:<effort>]`, `omp:<provider/model>`, `opencode:<provider/model>`,
`copilot:<model>`, `agy:<model>` (Antigravity), `pi:<provider/model>`, `grok:<model>`.
Crush and Amp take no starting prompt, so they get the rules and skills but don't run lanes.

## Herdr plugin

`herdr-plugin.toml` adds three entries, all in the Herdr TUI:

- **Lonca: start a lead here** opens a new tab running the lead in the focused folder.
- **Lonca: lanes** is a popup listing every lane with its agent, state, card and report.
- **Lonca: set up** runs the installer.

## Uninstall

```sh
~/lonca/install.sh --uninstall
```

This removes every link into the checkout, the timers, the hooks path, Lonca's deny rules and its hooks in Claude and
Codex. It keeps `~/ai-memory`, `~/lonca-local`, the `*.lonca-bak` backups and the checkout. It also leaves three
Claude settings, because you may have set them yourself: attribution off, `env.TMPDIR` and `autoMemoryDirectory`.

## FAQ

**Why can't the lead just write the code?** A kalfa who builds everything has no time left to inspect anything. Keeping the
lead out of the code leaves its context free for planning and checking, and every change gets a second pair of eyes.

**Why does review use a different model family?** A model tends to approve its own habits. So Claude's code goes to Codex
for review, and Codex and omp code goes to a Claude reviewer.

**Isn't approving every PR slow?** PRs up to the tier you choose merge themselves (`auto_merge`, per project or as a
default in `~/.config/lonca/config.toml`), and the rest take two words in chat; PRs that are ready together share one
code. The code proves the answer came from you, for that PR's current state: a lane message or an old "yes" can't
merge anything. These are guard rails for honest mistakes, not a sandbox against a hostile agent.

**Do I need every tool?** No: see [Requirements](#requirements). Herdr is the only one lanes insist on, because you can't
stop an agent you can't see.

## Contributing

Issues and PRs are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues privately: [SECURITY.md](SECURITY.md).

## License

MIT © 2026 Ahmet Selim Dizer. Vendored skills keep their own licences (MIT, CC-BY-SA-4.0): see [`skills/VENDOR.md`](skills/VENDOR.md).
