<div align="center">

# 🏛️ Lonca

**A guild for your coding agents.**
One lead plans and inspects, apprentices build in their own workshops, and nothing reaches the bazaar without the master's seal.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![check](https://github.com/selimdizer/lonca/actions/workflows/check.yml/badge.svg)](https://github.com/selimdizer/lonca/actions/workflows/check.yml)
[![Agents](https://img.shields.io/badge/agents-Claude%20Code%20·%20Codex%20·%20omp-6f42c1)](#requirements)
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
model family, a security pass and green CI, and only when you grant it. Agents cannot run `gh pr merge`, push to `main`,
force-push, or grant themselves that permission.

```
             you (usta)
                │ "build X"                         ▲ "PR #12 ready: verify ✔ review ✔ security ✔ CI ✔"
                ▼                                   │  ok-merge acme/shop#12    ← only you can run this
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
- 🔏 **One way to merge.** `merge-pr` merges only the PR's *exact* head commit, and only after your one-time grant (`ok-merge`), evidence files from verify, review and security for that commit, green CI, and a PR with no AI attribution.
- 🌙 **Night mode.** The lead asks every question up front. You give one start line and go to bed; the lead works through the tagged cards and merges green PRs within the limits you set.
- 🧠 **Memory you only fill once.** `~/ai-memory` is plain Markdown that every agent loads at start, with one group per project. A background reviewer saves your decisions.
- 📋 **A board that keeps itself current.** With [Kanzo](https://github.com/emanuele-em/kanzo), cards move by themselves: *doing* when a lane starts, *review* when its PR opens, *done* when it merges.
- 🛡️ **Guards.** Deny rules, `gh`/`git` shims and git hooks block direct merges, pushes to `main`, force-pushes, co-author lines and "Generated with" lines.

## Requirements

| Tool | Used for | If it's missing |
|---|---|---|
| Claude Code, git, gh, Python ≥ 3.9 (standard library only; macOS ships it) | everything | required |
| [Herdr](https://herdr.dev) + herdr-core (`hc`) | visible lanes and their messages | `lane` refuses to start: no hidden agents, by design |
| Codex CLI | cross-family review, backend lanes | everything runs on Claude |
| omp | cheap reading and review lanes, Copilot models | reading runs on Claude Explore / Sonnet |
| [Kanzo](https://github.com/emanuele-em/kanzo) | the board | card steps are skipped |
| [deja](https://github.com/vshulcz/deja-vu) | search across past sessions | the lead asks you instead |

Timers run as systemd user units on Linux and as launchd agents on macOS; the installer sets up whichever you have.

## Install

```sh
git clone https://github.com/selimdizer/lonca ~/lonca
~/lonca/install.sh
```

From inside Herdr you can instead run `herdr plugin install selimdizer/lonca` and open the **Lonca: set up** pane.

The installer is safe to run again, and it backs up every file it changes as `*.lonca-bak`. It does the following:

- links the skills and agents into Claude Code, Codex and omp;
- puts the guild rules (`AGENTS.md`) in front of every harness;
- adds Lonca's deny rules and hooks to `~/.claude/settings.json` and `~/.codex/hooks.json`;
- sets the git hooks;
- creates `~/ai-memory` from a template;
- installs the timers.

## Quick start

```sh
cd path/to/your/repo
claude --agent lead
> Add a dark mode toggle to the settings page.
```

The lead asks what is still open and writes a short plan. It then opens lanes (you can watch them in Herdr) and has each one
verified, reviewed by the other model family and security-checked. Finally it opens the PR and comes back with one line:

```
PR #12 ready (verify PASS · review SHIP · security CLEAN · CI green)
ok-merge acme/shop#12
```

You run that line, and the lead merges exactly that commit. If someone pushes after the checks, the evidence no longer
matches the PR's head, so the checks run again before any merge.

## Configuration

**Projects.** Lonca needs no projects folder. To group several repos into one project, put a `lonca.toml` in the folder
that holds them (anywhere on disk). It is a one-line file:

```toml
name = "shop"    # memory group ~/ai-memory/shop/ and Kanzo project slug; default: the folder's name
```

Lonca finds it the way mise and EditorConfig find theirs: a lane's worktree counts as its main repo, Lonca walks up from
there, and the closest `lonca.toml` (or `.lonca.toml`) wins. With no marker, the git repo is the project. Project-only
skills go in `<project root>/.claude/skills/`, next to the repos rather than inside a team repo.
`~/lonca/bin/lonca-project [dir]` shows what Lonca sees.

| What | Where |
|---|---|
| Rules for every agent | `~/lonca/AGENTS.md` |
| Model routing | `~/lonca/routing.md` |
| Shared memory | `~/ai-memory/` (`MEMORY.md` index + one folder per project) |
| Your own skills, agents, notes | `~/lonca-local/` (linked on top of Lonca's) |
| Run folders (briefs, reports, evidence) | `~/.cache/ai-runs/<project>/` |
| Merge grants | `~/.local/state/lonca/merge-grants/` |

**Environment variables:**

| Variable | What it does |
|---|---|
| `LONCA_PROJECT` | overrides the project name |
| `ALLOW_MAIN_PUSH=1` | lets *you* push to `main` past the hook, on purpose |

**Git config.** Set `git config lonca.toolNamesOk true` in a repo whose subject is AI tools (Lonca itself is one). Tool
names are then allowed in that repo's commits and PRs; co-author lines are still rejected.

## Herdr plugin

`herdr-plugin.toml` adds three entries, all in the Herdr TUI:

- **Lonca: start a lead here** opens a new tab running the lead in the focused folder.
- **Lonca: lanes** is a popup listing every lane with its agent, state, card and report.
- **Lonca: set up** runs the installer.

## Uninstall

```sh
~/lonca/install.sh --uninstall
```

This removes every link that points into the checkout, the timers, the hooks path, and Lonca's deny rules and hooks.
It keeps `~/ai-memory`, `~/lonca-local`, the `*.lonca-bak` backups and the checkout itself.

## FAQ

**Why can't the lead just write the code?** A kalfa who builds everything has no time left to inspect anything. Keeping the
lead out of the code leaves its context free for planning and checking, and every change gets a second pair of eyes.

**Why does review use a different model family?** A model tends to approve its own habits. So Claude's code goes to Codex
for review, and Codex and omp code goes to a Claude reviewer.

**Isn't `ok-merge` slow?** It's one line. `ok-merge --fast a/b#1 #2 #3` grants a whole batch without waiting for long CI
jobs, though a failed check still blocks. You can speed things up; the agents can't.

**Do I need every tool?** No: see [Requirements](#requirements). Herdr is the only one lanes insist on, because you can't
stop an agent you can't see.

## Contributing

Issues and PRs are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues privately: [SECURITY.md](SECURITY.md).

## License

MIT © 2026 Ahmet Selim Dizer. Vendored skills keep their own licences (MIT, CC-BY-SA-4.0): see [`skills/VENDOR.md`](skills/VENDOR.md).
