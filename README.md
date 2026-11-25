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

- 🧵 **Lanes you can see.** `lane` starts an agent in its own worktree as a [Herdr](https://herdr.dev) terminal. It reports back with `DONE: <outcome>` or asks `QUESTION: …`, and `lane-watch` tells the lead when one goes quiet. A read lane that fails says so in its DONE; the brief may set a report length other than 30 lines.
- 🔏 **One way to merge, sized to the risk.** `merge-pr` merges only the PR's *exact* head commit, after CI and evidence from verify, review and security for that commit. A script reads the diff and sets the risk tier (docs/tests = low, auth/payments/migrations/CI/dependencies = high, the rest medium); low needs fewer checks, and you choose per project which tiers merge themselves (none, low, medium or all). Everything else waits for your `evet <code>` in chat.
- 🌙 **Night mode.** The lead asks every question up front and proposes tonight's work for its project. You answer `başla <code>` and go to bed: until the end time, every PR of that project that passes its checks merges without asking. In the morning you get what was done and the questions that came up.
- 🧠 **Memory you only fill once.** `~/ai-memory` is plain Markdown that every agent loads at start, with one group per project. Agents save decisions as they go; an optional background review catches the ones they missed.
- 📋 **A board that keeps itself current.** With [Kanzo](https://github.com/emanuele-em/kanzo), cards move by themselves: *doing* when a lane starts, *review* when its PR opens, *done* when it merges. Issues and PRs your account opens in a project's linked repos get a card too.
- 🧯 **Machine load.** Containers a lane starts carry its name (`docker` shim: label `lonca.lane`, compose project) and go when the lane closes; heavy suites wait for one of N machine-wide slots (`~/lonca/bin/test-slot -- <cmd>`); `lane --browser` gives only the Claude lane that needs one a chrome-devtools browser.
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

Timers run as systemd user units on Linux and as launchd agents on macOS; pass `--timers` to enable them.

## Install

```sh
git clone https://github.com/selimdizer/lonca ~/lonca
~/lonca/install.sh
```

From inside Herdr you can instead run `herdr plugin install selimdizer/lonca` and open the **Lonca: set up** pane.

The installer links the commands in `~/.local/bin` and creates `~/ai-memory` from a template on first install. Run `lonca init <folder>`
in your shell, or tell your lead **“set this up for Lonca.”** The bundled `lonca` skill walks through
agent selection and reports which guards are active. Each project's init registers the `~/lonca` marketplace with local scope.
Outside a project, a plain terminal session starts without Lonca. Run `lonca init <folder>` there, or
open the folder from Herdr to see the setup hint when the session starts.

- `--timers` enables cleanup and lane monitoring for registered projects and board sync and backups
  for their Kanzo slugs. A read lane on a temp copy counts as the registered project its marker names. The monthly maintenance card requires its configured project to be registered.
- `--timers --memory-review` also reviews recent owner messages from registered projects. It uses your Claude plan.
- `--sui` installs the Sui version selector and Move LSP launcher. In an initialized project, run
  `claude plugin install move-lsp@lonca --scope local` to use the language server from the same marketplace.

Cleanup checks Lonca's record of each worktree, terminal, run and temporary directory. Older lanes
without ownership records stay in place. With `--timers`, `ai-memory-commit` commits changes in
`~/ai-memory` hourly. If deja is available, `deja-index` indexes machine-wide session history every
30 minutes. Project policy limits which sessions an agent can recall at read time.

### Migrate an existing installation

From the owner's shell, preview the changes, then run the same command without `--dry-run`:

```sh
lonca migrate --dry-run
lonca migrate
```

Migration includes registered roots, marked folders under `~/Work`, the marked `~/lonca` checkout,
and markers found in previous Lonca scope records. Pass additional roots as arguments to both commands.
It moves the old Move marketplace to `~/lonca`, initializes the projects, and then removes identified
global entries. Each migration writes the removed settings, import lines and link targets to a private
`changes.jsonl` under `~/.local/state/lonca/migration-backups/`. Personal MCP credentials stay in
their original files. Migration and the optional cleanup timer prune migration backups after 30 days.
A successful uninstall prunes them immediately.
Migration keeps skill and agent links into `~/lonca-local`. Full uninstall removes those links and
keeps their targets. Known installer hook commands are removed even from a repeated installation.
Migration removes each exact match for a shipped deny rule from the user settings, including duplicates
and matches present in an older backup. The receipt records each removed rule. Custom rules keep their order.
Migration also removes the rules earlier releases shipped and the current list no longer has.
Migration and uninstall also clear the old installer’s exact attribution settings and its optional
`env.TMPDIR` value. A distinct prior value in the backup is restored. `autoMemoryDirectory` stays in
`~/.claude/settings.json`: Claude reads it only from user settings.
If a command stops, correct the reported problem and repeat it.

Both interactive and read-only omp lanes load Kanzo and deja through the lane extension. Deja receives
the project's policy. Migration also removes the user-level Kanzo and deja entries the legacy installer
recorded for OpenCode, Copilot, Antigravity, Grok and pi: these CLIs get them per project now (see
[Per-project setup](#per-project-setup)). Opt them in with `lonca init --agents` before you migrate.

## Quick start

```sh
lonca init path/to/your/repo
cd path/to/your/repo
claude --agent lonca:lead
> Add a dark mode toggle to the settings page.
```

The lead asks what is still open and writes a short plan. It then opens lanes (you can watch them in Herdr) and has each one
verified, reviewed by the other model family and security-checked. Finally it opens the PR and comes back with one line:

```
acme/shop#12 → main, head 9c1e4a2, tier medium (14 files, 220 lines)
verify PASS · review SHIP · security CLEAN · CI green. My opinion: safe to merge; it only touches the settings page.
To merge, write: evet 4f2
```

You answer `evet 4f2` (or `yes 4f2`, `ok 4f2`: any language, the code is what binds), and the lead merges exactly that
commit. The code is good for that PR's current head and base branch for one hour: if someone pushes after the checks,
the evidence no longer matches, the checks run again and you get a new code. With several PRs ready, the lead asks
once (`merge-pr --ask`): one code for exactly the PRs it shows you, never one an earlier question used. Only a lead
merges; `merge-pr` refuses to run inside a lane.

## Configuration

### Per-project setup

The owner or lead runs init. A lane that needs setup asks its lead. Only the owner runs remove.
The init, migration and removal integration test runs on GitHub CI, outside the lane shims.

```sh
lonca init ~/work/shop                    # one repo, or a folder containing several repos
lonca status ~/work/shop                  # includes newly cloned repos and configuration conflicts
lonca init ~/work/shop                    # pick up new repos
lonca status                              # all registered projects
lonca remove ~/work/shop
```

The default agents are Claude and Codex. Start with `--agents codex` or `--agents claude` to select one.
Running init again can add an agent. The other agent CLIs are opt-in (`--agents claude,codex,pi`): init gives
each one Kanzo, deja (with the project's policy) and a line pointing to the Lonca rules, in the files its own docs
name, kept out of Git like the rest:

| Agent | MCP servers | Rules |
|-------|-------------|-------|
| `opencode` | `.opencode/opencode.json` | the same file (`instructions`) |
| `copilot` | `.github/mcp.json` | `.github/instructions/lonca.instructions.md` |
| `pi` | `.pi/mcp.json` | `.pi/APPEND_SYSTEM.md` (replaces a personal `~/.pi/agent/APPEND_SYSTEM.md`) |
| `grok` | `.grok/config.toml` | `.grok/rules/lonca.md` |
| `agy` (Antigravity) | `.agents/mcp_config.json` | `.agents/rules/lonca.md` |

Copilot, pi and Grok read these files only in a folder you trust. Lane worktrees don't have them: OpenCode and
Copilot lanes get Kanzo and deja per run, and `lane` copies the pi, Grok and Antigravity files into the worktree,
so those lanes need the agent opted in. A Codex lead started in a project folder that is not a repository reads only
that folder's `AGENTS.md` (Codex finds no project root there), so init adds the pointer line to it. Each repository gets its own local Git hooks setting, which Git also
uses in linked worktrees. Inside a lane, Git also inherits Lonca’s hooks path for commands in sibling
and newly cloned repositories. Status lists linked worktrees inside the project next to their main checkout.
A repository with a custom hooks path keeps it. `LONCA=0` silences memory, deja-scope and temporary-directory
automation for that process and its children. The default-branch push guard, attribution checks and the
repository's native Git hooks still run. The owner can remove the project integration with `lonca remove`.
The git shim refuses `GIT_CONFIG_PARAMETERS` that sets a hooks path, an include or an alias, alias
writes (`git config alias.*`, `git -c alias.*`), `--no-verify` on commit, merge, pull and push, and `-n` on commit. In a lane it also refuses any git command whose environment
lost Lonca's `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0` and `GIT_CONFIG_VALUE_0`: test suites that clean the
git environment fail there. The deny rule `Bash(*GIT_CONFIG_*)` also stops Claude leads from running
check steps that export `GIT_CONFIG_GLOBAL`. Run those in a plain shell or on CI.

### Questions for the owner

Every decision a lead asks the owner stays in `<project root>/.lonca/questions.md` until it is answered, so
"what is still open?" is read from the file, not from a session's memory. Init hides `.lonca/` from Git at a
repository root (`.git/info/exclude`); `remove` keeps the file and, while it exists, that exclusion.

```sh
lonca questions                           # open questions of this project, oldest first (--all: every one)
lonca questions add --by lead --title "Who gets the leftover cent?" --context "10.00 / 3" \
  --option "The first sharer" --option "The payer" --recommend A    # prints its id, e.g. Q-4
lonca questions answer Q-4 "A"            # the owner's words; drop Q-4 "<why>" retires it
```

Ids count up per project and are never reused; answered and dropped questions keep their block. Only the lead
records answers: lanes may add but not answer or drop. The file is the only copy: never `git clean -x` a project
root without keeping `.lonca/`.

- Claude Code installs `lonca@lonca` with local scope. Its agents, skills, hooks and MCP servers come
  from the local marketplace. Init also installs these protections at a non-Git project root for leads. Personal settings hold the deny rules and deja policy, and
  `CLAUDE.local.md` imports `@~/lonca/AGENTS.md`. Use a CLI with local marketplace scope support.
  Personal settings also turn off Claude's commit and PR signature (`attribution`, `includeCoAuthoredBy`).
  Init replaces an existing `attribution` or `includeCoAuthoredBy` value there, and remove restores it.
  Claude lanes get the same two settings through `--settings`, since their worktrees have no personal settings.
  Folders without Lonca get Claude's default signature.
- Codex reads the project's `.codex/config.toml`, `.codex/rules/lonca.rules` and `.codex/hooks.json`.
  Trust the project and review the hooks in `/hooks`.
- Init merges personal files, registers the project and keeps private backups under
  `~/.local/state/lonca/projects/`. It adds generated paths to Git's local exclude file.
  Tracked target files and symlinks produce a diagnostic. Remove restores the original bytes. If a managed
  file has since been edited, remove takes out Lonca's entries and keeps personal changes. Private backup
  files can contain the same sensitive values as the original settings. For a missing or moved checkout,
  remove reports its path and keeps its recovery index beside the backups.

Status flags surviving legacy settings. Init reports an unrelated marketplace name collision before
installing anything. A marker in the project root names the project and
can set its merge policy. For a marker inside a repository, merge checks use the base branch's copy of the policy. For example:

```toml
name = "shop"              # memory group ~/ai-memory/shop/ and Kanzo project slug; default: the folder's name
auto_merge = "low"         # optional: merge PRs up to this tier without asking: off | low | medium | all
wait_for_ci = false        # optional: CI checks still running don't block a merge (a failed one always does)
min_tier = "medium"        # optional: nothing in this project counts as low
high_paths = ["src/pay/*"] # optional: more paths that make a PR high tier
```

Lonca finds it the way mise and EditorConfig find theirs: a lane's worktree counts as its main repo, Lonca walks up from
there, and the closest `.lonca.toml` (or `lonca.toml`) wins. A directory without a project marker in its ancestry is outside Lonca. Project-only
skills go in `<project root>/.claude/skills/`, next to the repos rather than inside a team repo.
`~/lonca/bin/lonca-project [dir]` shows what Lonca sees.

| What | Where |
|---|---|
| Rules for every agent | `~/lonca/AGENTS.md` |
| Model routing | `~/lonca-local/routing.md` if you write one, else `~/lonca/routing.md` (template; example in `examples/`) |
| Shared memory | `~/ai-memory/` (`MEMORY.md` index + one folder per project) |
| Your own skills, agents, notes | `~/lonca-local/` (private files stay there) |
| Run folders (briefs, reports, evidence) | `~/.cache/ai-runs/<project>/` |
| Approval codes, merge log | `~/.local/state/lonca/approvals/`, `~/.local/state/lonca/merge.log` |
| Per-project deja scope | `~/.local/state/lonca/deja/<project>.json` |
| Settings (optional) | `~/.config/lonca/config.toml`: `tmpdir`, `auto_merge`, `test_slots` (see `lonca-config --help`) |

**Environment variables:**

| Variable | What it does |
|---|---|
| `LONCA_PROJECT` | overrides the project name |
| `ALLOW_MAIN_PUSH=1` | lets *you* push to the default branch past the hook, on purpose |
| `LONCA_LEAD_CMD` | the command the Herdr plugin's "start a lead" runs (uses `claude --agent lonca:lead` in plugin-enabled repos) |

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

**Each project sees only itself.** In a project, agents get only that project's past sessions from deja.
`deja-scope` writes a deja policy per project that leaves out every session outside it, including projects that don't
exist yet; other projects' names appear nowhere in it. `lane` starts every lane with it (`DEJA_POLICY_FILE`; Codex
gets it through its MCP server config, since Codex starts MCP servers with a minimal environment), the Herdr action
starts the lead with it, and a Claude hook gives it to every session started in a project: at once for Bash, and for
the deja MCP tool from the next session in that folder (through `.claude/settings.local.json`, kept out of git).
Kanzo has no such setting, so agents are told to use only their project's cards. A question for another project goes
to its lead: `leads` lists the agent sessions open in project folders. Like the other limits, this guards against
accidents, not a hostile agent: lanes have full permissions and can read any file.

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

Uninstall restores the registered projects, removes installed tool links and timers, and cleans up
legacy harness settings and migration backups. Your checkout, memory and private extensions stay in place.

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
