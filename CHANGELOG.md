# Changelog

All notable changes to Lonca. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security

- The lane git guard checks git aliases already in git config by their expansion: `git ci -n` with `alias.ci = commit`
  and `git br -D` with `alias.br = branch` are refused like the commands they stand for, and a `!` shell alias is
  refused when a git command in its text (also `git-<cmd>`) breaks a rule; quotes and backslashes in alias text do
  not hide a flag, and an alias named like a built-in is not expanded, as git ignores it (lonca#414).
- merge-tier rates prompts for timer-started model runs (`config/*.prompt.md`, `config/monthly-card.md`) and, in any
  project, `AGENT.md` (any case) and `.opencode/agent/*.md` as high (lonca#435).
- merge-pr ignores an exported `MERGE_PR_SEAL`: `--ask` hands its children the internal `--seal <file>` instead, so a
  stray variable no longer makes a plain run exit 0 without merging (lonca#435).

### Fixed

- The lane git guard decides by the git subcommand and its own options, not by the whole command line: words in a
  commit, tag, merge or notes message, an `--author`, a `-c` value or a path after `--` no longer get a command
  refused (`git commit -m "clean up X"`, `-m "fix: push to main later"`). Every refusal stays, and `push -d`,
  `push -uf`, `branch -Dq` and `refs/heads/main` refspecs are now refused too (lonca#414).
- ai-cleanup removes approval batch and key files older than 2 h (codes live 1 h), so unused asks no longer pile up
  until no code is free (lonca#435). A file merge-pr removes during the sweep no longer stops the cleanup.

## [0.5.0] - 2026-11-25

Lonca now lives per project: nothing global, every rule, guard and hook comes from the project you are in.

### Upgrading from 0.4

- Preview with `lonca migrate --dry-run`, then run `lonca migrate`. It sets up your registered projects and removes
  the global install; what it removed is backed up under `~/.local/state/lonca/migration-backups/` (kept 30 days).
- Start leads with `claude --agent lonca:lead`.
- Sessions outside a project folder (no `.lonca.toml` above them) get no Lonca rules.
- Each new project needs `lonca init <dir>` once.
- A repo with its own `core.hooksPath` keeps it and gets no Lonca git hooks: unset it first, then run `lonca init`
  again. A global one needs `git config --global --unset core.hooksPath`, a repo one `git config --unset core.hooksPath`.

### Known limits

- Not tried on macOS.
- MCP servers for the other CLIs (agy, copilot, grok, opencode, pi) are still registered globally (lonca#361).
- Open low findings in the merge gate (lonca#435) and in the lane git guard (aliases, lonca#414).

### Added

- `lonca init [--agents claude,codex] <dir>` registers a marked project and installs, with local scope, the `lonca`
  plugin from the `~/lonca` marketplace, personal repo settings and local Git hooks (linked worktrees share them);
  folder roots get local lead protections. `lonca status` reports coverage and conflicts, `lonca remove <dir>` restores
  the backed-up files. A folder belongs to a project only through a marker: the hidden `.lonca.toml` (`lonca.toml`
  still works), kept next to your repos, not inside one. `LONCA=0` silences session automation; Git and attribution
  guards stay active.
- `lonca migrate --dry-run [roots...]` previews the move from the global install and `lonca migrate` does it: it
  initializes the projects and records the removed global settings. Backups expire after 30 days or on uninstall.
  Timers are opt-in and project jobs need a registered project; shared-memory commits and machine-wide history
  indexing stay available.
- `lonca questions` keeps every question for the owner in `<project root>/.lonca/questions.md` (block format: id, who
  asked and when, options with the recommended one marked, `[Answer]:`) until it is answered or dropped. `lonca init`
  hides `.lonca/` from Git at a repository root; `lonca remove` keeps the file and its exclusion. Lanes may add
  questions but not answer or drop them. Leads record each question they ask, list open ones on "açık sorular" and
  status checks, and act on an answer they did not record only after finding the owner's own message for it.
- `~/lonca/bin/test-slot [-n N] -- <command>`: heavy test suites wait for one of N machine-wide slots (`test_slots`
  in `~/.config/lonca/config.toml`, default 2); a nested call inside a held slot runs at once. It says once who holds
  the slots and passes the exit code through. The orchestrate skill, implementer and verifier send live/integration
  tests, `-race`, perf runs and full gates through it.
- Containers carry their lane: lanes get `LONCA_LANE=<lane>`, the `docker` shim adds `--label lonca.lane=<lane>` to
  `docker run`/`create` and sets `COMPOSE_PROJECT_NAME=lonca-lane-<lane>` for `docker compose` when the caller set
  none. When a lane closes (`ai-cleanup` once its worktree is gone, `lane-watch` when it closes an empty lane) its
  containers and that compose project's networks are removed and logged; named volumes stay and are named in the log.
- `lane --browser` starts a Claude lane with `--mcp-config ~/lonca-local/mcp/chrome-devtools.json` (refused when the
  file is missing; Codex and omp lanes don't take it).
- Each project sees only itself in deja: `deja-scope` writes a per-project policy that leaves out every session
  outside the project, written as the complement of the project's own names (projects created later are left out
  too, no other project's name is in the file). Lanes, the Herdr "start a lead" action and a SessionStart hook in
  every project session use it (Codex through its MCP server config); CI checks it against deja's own match rule.
  Lanes and leads use only their project's Kanzo cards.
- `leads` lists the agent sessions in project folders and outside every project (PROJECT `-`), with ROLE/DOING from
  the `lonca.role`/`lonca.does` hc labels (else the agent's own status); `leads --json` too. A lead asks another one
  ("was it you?") instead of reading its sessions, and the orchestrate skill says how to look a change up first.
  Machine-wide work (containers, cleanup, killing processes, packages, disk) is announced to every listed session
  first, then reported.
- `lanes --mine` shows only the lanes the calling lead started.
- `lane-watch` sends the lead one `READY: <repo>#<pr> head <sha>` per head when a lane's PR passes
  `merge-pr --dry-run`; the orchestrate skill says to run merge-pr on it.
- `merge-pr --ask <repo-dir> <run-dir> <pr>:<lane> ...` checks several PRs and prints one code for exactly that list
  (nothing if one is refused).
- Memory caps (Linux): every Claude and Codex session in a project moves itself into its own systemd scope (24 GB
  memory, 4 GB swap; `bin/session-scope`), and each lane runs in its own scope (16 GB memory, 4 GB swap; systemd 254
  or later), so a runaway process is killed inside it instead of systemd-oomd killing every terminal. Programs a
  session started before the move (MCP servers) stay outside the cap; where no scope can be made the lane starts
  uncapped, as before.
- Temp folders per lane (`<tmpdir>/lane-<name>`, passed to Claude and Codex through their settings override flags)
  and per Claude session (`<tmpdir>/session-<id>`, SessionStart hook `session-tmpdir`; its subagents share it).

### Changed

- `install.sh` installs only the commands and memory templates; projects are set up with `lonca init`.
- `lonca init` turns off Claude's commit and PR signature (`attribution`, `includeCoAuthoredBy`) in the project's
  personal settings and `lonca remove` takes it out again; folders without Lonca get Claude's default signature.
  Claude lanes get the same settings through `--settings`. Migration removes these values from
  `~/.claude/settings.json` (keeping `autoMemoryDirectory`), the global `session-scope` hook and the deny rules
  earlier releases shipped (`ok-merge`, `merge-grants`, `night-on`, `git push * main*`).
- Approval codes: every ask prints a new code, never one still on file; a code approves only the PRs it was printed
  for, is bound to the base branch as well as the head, and ends when the last of them merges or after 1 h. The owner
  may answer with the code in any language.
- `merge-pr` ignores `LONCA_PROJECT`; a night past its end time or cap asks the owner instead of refusing, and the
  night cap counts a merge from the moment it starts. `merge-pr --dry-run` no longer takes the merge lock or writes
  refusals to the audit log.
- Worktrees go when the work is done: `merge-pr` closes the PR's lane and removes its worktree, local branch and the
  terminals in it right after merging (a worktree with uncommitted changes is left; removals are logged).
  `ai-cleanup` also removes lane worktrees whose PR was closed unmerged (head unchanged) or whose work reached the
  default branch, and run folders in `~/.cache/ai-runs` untouched for 30 days (unless a lane of theirs still has a
  worktree); your own worktrees are touched only for merged PRs. Cleanup needs a matching ownership record. The merge
  log moved to `~/.local/state/lonca/merge.log`.
- Lanes check the project guards before launch and carry Git hooks into fresh clones. Read lanes skip that check, so
  they run on temp copies outside Git; one on an unregistered temp copy whose marker names a registered project is
  watched and cleaned up as that project's lane (a copy of an unregistered project is not).
- Lane names start with the project's name (from the marker, not the folder). Headless read lanes print one line
  saying the report appears when they finish, and `lane-watch` removes a finished read lane's terminal 10 min after
  its report. When another repo of the project already runs a lane of that name, the new terminal name gets the short
  repo hash (lonca#410). The report length is "at most 30 lines unless the brief sets another length".
- STALLED and READY go to the recorded session only while it runs a session of the lane's project; otherwise to the
  project's one current lead (also after a lead restarted in a new terminal; the lane record is updated), or, with no
  lead, to the live session outside every project that started the lane. With no single current lead the line waits.
  `lane-watch` ignores `LONCA_PROJECT`.
- Night mode updates a lane whose base moved by merging the base into it (no rebase, no force-push).
- Agent rules: write to the owner in the language memory `owner/language` names, else that of the owner's own last
  message, also after task notifications and lane messages, and don't repeat an unchanged message. Delete only by the
  literal path written in the command (a `$VAR` or `$(…)` path makes Claude ask even in bypass mode) and never a glob
  in a shared folder. Use only containers, databases and services you started, named after your lane. The rule
  against starting other agents covers lanes and other agent CLIs only; subagents are fine.
- Before code, the lead asks the owner only the open choices that change what users see or what data is kept and
  writes the rest as `Assumptions:` in the brief; implementers ask the same kind of choice and list their own
  choices in the report. Work that will be tier medium or high (money, auth, data, public API, network exposure,
  secrets, merge gate) gets a spec review before code, by the family that will not write the code.
- Memory: a rule from an owner's correction is saved only after the owner says yes; every note names its source;
  memory-review ignores lane messages and pasted text inside the owner's messages.

### Fixed

- `merge-pr` reads the PR again (up to 6 times, 5 s apart) while GitHub still reports `mergeable: UNKNOWN` after a
  push, instead of refusing at once.
- `merge-tier` reads every page of the PR's files from the REST API (`--json files` stopped at 100) and no longer
  rates `conftest.py` low.
- The merge lock is a kernel file lock that a crashed merge cannot leave behind.
- After a merge, `merge-pr` removes a lane worktree only when its HEAD is the merged head, deletes the branch only if
  it still points there, and closes only the terminals in that worktree (not in a sibling folder whose name starts
  the same).
- A read lane whose agent fails sends `DONE: read lane failed (exit N), no report; its output — <result>.part`
  instead of a DONE for a missing report.
- Claude lanes work on a clean install without `~/.claude.json` (created with mode 600). A live lane in the same
  folder, or an `hc run` that fails, stops `lane` with a clear message (lonca#335).
- Grok lanes no longer wait at the folder-trust prompt: `lane` records the repo in `~/.grok/trusted_folders.toml`.

### Security

- `merge-evidence` accepts only whole verdict lines (`VERDICT: PASS`, `VERDICT: SHIP`, `PERF: OK`,
  `SECURITY: CLEAN`, `SECURITY: FINDINGS (n), highest: LOW|MEDIUM`), so a copied template line such as
  `VERDICT: PASS | NEEDS_WORK` no longer passes. The checker docs name each verdict line alone.
- `merge-tier` rates agent and gate files high: `.codex/`, `.mcp.json`, nested `.claude/` and `skills/`,
  `agents/*.md`, `routing.md`, git hooks, `shims/`, `install.sh`, `Makefile`, `bin/merge-*`, `night-on`, Lonca's agent
  config (`config/codex-rules|omp-guard|omp-lane|opencode/`, `bin/lane`, `.claude-plugin/`) and `AGENTS.md`/`CLAUDE.md`
  (also `.override`/`.local`) in any folder or case. A file list shorter than the PR's file count (GitHub lists at
  most 3000) is high.
- `merge-tier` fetches `origin/<base>` (explicit refspec, 60 s timeout) before reading the project's `.lonca.toml`
  there, also from a lane worktree, and refuses when it cannot or the repo has no origin, instead of falling back to
  the global `auto_merge` or a working tree's copy.
- `merge-pr` and `night-on` refuse to run inside a lane (`LONCA_LANE`).
- The git shim refuses `GIT_CONFIG_PARAMETERS` that set a hooks path, an include or an alias, alias writes (an alias
  can hide a hook skip), `--no-verify` anywhere on commit, merge, pull and push (`--no-verify-signatures` still
  works), and `-n` on commit (also inside `-an`). In a lane it also refuses any git command whose environment lost
  the lane's `GIT_CONFIG_*` values (test suites that clean the git environment fail in lanes).

## [0.4.0] - 2026-11-22

Merging, simplified (after a three-family council review): risk tiers for the checks, one setting for approval.
- `merge-tier`: the PR's risk tier from its own diff. High: CI/deploy/infra, migrations and SQL, dependency manifests
  and lock files, env/secrets, auth/payment paths, agent instructions, renames/deletes, `lonca.toml`. Low: only docs
  and tests, at most 10 files and 100 lines. Medium: the rest. Projects can raise the floor (`min_tier`) or add
  `high_paths`; the lead can only raise a tier. Evidence follows the tier (PERF required for high, and for medium
  when a perf check ran).
- `merge-pr` is the only merge command. Approval: the project's `auto_merge` (off | low | medium | all; per project in
  `lonca.toml`, default in `~/.config/lonca/config.toml`), the project's night mode, or the owner's `evet <code>` in
  chat: a code bound to the PR's head for one hour; PRs asked together share one code.
- Night mode is per project: the lead runs `night-on --request <project> <HH:MM> [<max>]`, the owner answers
  `başla <code>`; until the end time every PR of the project that passes its checks merges. `night-on --off` ends it.
- `wait_for_ci = false` (per project) lets still-running CI checks pass; a failed check always blocks.
- Removed: `ok-merge` and its `--fast` grant, `night-merge`, per-night repo lists, merge caps per day.
- Agents inherit every tool, MCP server and skill. Before, `tools:` allow-lists hid all MCP servers (Kanzo, deja,
  context7, chrome-devtools…), ToolSearch, and from the checkers even skills, so Claude leads and lanes could not
  update Kanzo cards or use deja's MCP tool. Now only the checkers (reviewer, verifier, security-auditor) are
  read-only (`disallowedTools`); the lead and implementer have everything.
- deja is the first stop for any "was this decided / is anything pending" check, and every lane prompt says so; a
  status check ends with a Kanzo card for every open item.
- Kanzo and deja MCP servers in every harness you pick, through each CLI's own `mcp add` (or its documented
  `mcp.json`); uninstall removes only what Lonca added.
- Folder trust the documented way instead of keystrokes: Claude (the main checkout in its projects config, which
  covers every worktree), Copilot (`trustedFolders` = ~/.herdr/worktrees), Antigravity (`--settings
  trustedWorkspaces` per worktree). OpenCode lanes use `opencode mini --standalone --agent lonca-lane --model …
  --prompt …`, so the prompt is submitted and its tools run inside the lane with Lonca's guards.
- `lane-watch` closes a lane that wrote its report 10+ min ago and left nothing behind (no commits, no changes:
  review, council or test lanes), and removes its worktree and never-pushed branch.

## [0.3.2] - 2026-11-22

Fixes from an independent council review (three model families):
- `merge-evidence`: each verdict counts only for the `HEAD:` line right after it. Before, a PASS judged on commit A
  could pass for commit B once a later check appended `HEAD: B` to the same file.
- `ok-merge`: PR numbers after the first are plain numbers (`a/b#1 2 3`); an unquoted `#2` is a shell comment, so the
  documented batch form granted only the first PR. CI now really tests grants and the evidence gate.
- `merge-pr`/`night-merge`: one merge at a time (a lock), so two lanes can't both take the night's last merge.
- Guard shim also blocks `git push … main|master` (repos whose own hooksPath skips Lonca's pre-push).
- Lanes answer Antigravity's folder-trust prompt.

## [0.3.1] - 2026-11-22

- The guard shim and `ai-trace-gh` find Lonca from their own path, so they work from any checkout (CI has no `~/lonca`).

## [0.3.0] - 2026-11-22

Safer defaults for new users; the behaviour you had is one setting away.
- AI-trace check refuses attribution lines only; the tool-name ban is `git config --global lonca.strictTraces true`.
- `ai-cleanup` clears only Lonca's own temp dir unless `cleanup_tmp_dirs` in `~/.config/lonca/config.toml` names more.
- Opt-in: background memory review (`--memory-review`), Claude sessions' TMPDIR (`--agent-tmpdir`), Sui Move extra
  (`--sui`, now in `extras/sui/`). Lanes always use Lonca's per-user temp dir (`tmpdir` setting).
- Git hooks: every hook name Lonca doesn't use runs the repo's own `.git/hooks/<name>`; `pre-push` also protects the
  remote's default branch.
- `merge-pr` merges with the method the repo allows (or `lonca.mergeMethod`); messages name the command you ran.
- `ok-merge` takes several repos in one line (`a/b#1 #2 c/d#3`); a bare `#N` belongs to the repo before it.
- Guard shim also blocks `push +ref`, branch deletes by push, and `-c core.hooksPath=…`; more deny rules (grant files,
  `push --delete`); the main-push rule no longer catches branches that only start with `main`.
- Lanes: TMPDIR reaches the terminal (hc passes no environment), Claude's and Copilot's folder-trust prompts are
  answered, `--read` lanes fail when omp fails, the lane record is written as JSON, `lane --help`.
- Generic `routing.md` template; your own goes in `~/lonca-local/routing.md` (example in `examples/`).
- Skills and agents: consistent DONE format, base branch instead of `main`, optional scanners, full PR template.
- Removed: Gemini CLI and goose (Antigravity replaces Gemini CLI); personal configs and the gopls wrapper.

## [0.2.0] - 2026-11-21

- macOS: timers as launchd agents; portable `date`/`stat`/`realpath`/hash; Python 3.9+ (no `tomllib` needed).
- The installer asks which harnesses get Lonca: Codex, omp, OpenCode, Antigravity, Copilot CLI, Amp, Grok,
  Crush, pi (Claude Code always).
- Lane agents for OpenCode, Copilot, Antigravity, pi and Grok (each run end to end).
- Logo, icons and social preview.

## [0.1.0] - 2026-11-21

First public release.

- `lane`: one agent per git worktree and branch, as a visible Herdr terminal; `lane --read` for read-only questions;
  lanes report `DONE: <outcome>` or ask `QUESTION: …`.
- The lead (`agents/lead.md`, `skills/orchestrate`): plan, split, route, brief, verify, cross-family review, security, PR.
- One merge path: `merge-pr` / `night-merge` with `ok-merge` / `night-on` grants and per-commit evidence files.
- Night mode.
- Guards: deny rules, `gh`/`git` shims, `commit-msg` and `pre-push` hooks, AI-attribution checks.
- Shared memory template, project discovery with `lonca.toml`, background memory review.
- `kanzo-sync`, `lane-watch`, `ai-cleanup` and their timers.
- `install.sh` (with `--uninstall`) and the Herdr plugin.

[Unreleased]: https://github.com/selimdizer/lonca/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/selimdizer/lonca/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/selimdizer/lonca/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/selimdizer/lonca/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/selimdizer/lonca/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/selimdizer/lonca/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/selimdizer/lonca/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/selimdizer/lonca/releases/tag/v0.1.0
