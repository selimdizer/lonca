# Changelog

All notable changes to Lonca. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

- `lonca questions` keeps every question for the owner in `<project root>/.lonca/questions.md` (AI-DLC's block format: id, who asked and when, options with the recommended one marked, `[Answer]:`) until it is answered or dropped; `lonca init` hides `.lonca/` from Git at a repository root and `lonca remove` keeps the file and its exclusion. Lanes may add questions but not answer or drop them. Leads add each question they ask and list open ones from the file on "açık sorular" and status checks.
- Agents delete with the literal path written in the command (a `$VAR` or `$(…)` path makes Claude ask even in bypass mode, so runs waited for the owner), and use only containers, databases and services they started, named after their lane: a lane removed a shared-name container while verifiers had test databases in it.
- Installation now provides commands and memory templates. Run `lonca init` from an owner or lead session
  to register the root plugin marketplace locally and set up the project.
- `lonca migrate --dry-run [roots...]` previews the move from global settings. Migration initializes projects
  and records the removed global settings. These backups expire after 30 days or on uninstall. Timers are opt-in. Project jobs require registration. Shared memory commits and machine-wide history indexing remain available.
- Lanes check project guards before launch and carry Git hooks into fresh clones. Folder roots receive local lead protections. Cleanup requires a matching ownership record.
- `lonca init` turns off Claude's commit and PR signature (`attribution`, `includeCoAuthoredBy`) in the project's personal settings, and `lonca remove` takes it out again; folders without Lonca get Claude's default signature. Migration still removes these values from `~/.claude/settings.json` and keeps `autoMemoryDirectory` there. It also removes the `session-scope` hook and the deny rules earlier releases shipped (`ok-merge`, `merge-grants`, `night-on`, `git push * main*`).
- The git shim refuses `GIT_CONFIG_PARAMETERS` that set a hooks path, an include or an alias, alias writes (an alias can hide a hook skip), `--no-verify` anywhere on commit, merge, pull and push (`--no-verify-signatures` still works), and `-n` on commit (also inside `-an`). In a lane it also refuses any git command whose environment lost the lane's `GIT_CONFIG_*` values (test suites that clean the git environment fail in lanes). Claude lanes turn off Claude's commit and PR signature through `--settings`. Read lanes skip the project Git guard check, so they run on temp copies outside Git again. A read lane on an unregistered temp copy whose marker carries a registered project's name is watched and cleaned up as that project's lane (STALLED, terminal removal); a copy of an unregistered project is not.
- Lane names start with the project's name (from the lane's project marker, not the folder: a read lane in a temp copy named src gets its project's name), headless read lanes print one line saying the report appears when they finish, and lane-watch removes a finished read lane's terminal 10 min after its report.
- STALLED and READY go to the recorded session only while it runs a session of the lane's project; otherwise to the project's one live lead, or, when the project has no lead, to the live session outside every project that started the lane (setup work). `LONCA_PROJECT` is ignored by lane-watch.
- Night mode updates a lane whose base moved by merging the base into it (no rebase, no force-push). The rule against starting other agents now covers lanes and other agent CLIs only; subagents inside a session are fine.
- `lane-watch` sends STALLED and READY to the project's current lead when the terminal recorded for a lane no longer runs an agent session (a lead restarted in a new terminal), and updates the lane record; with no single current lead the line waits instead of going to a terminal that may run something else; `leads --json` lists the sessions for it.
- `lane-watch` sends the lead one `READY: <repo>#<pr> head <sha>` per head when a lane's PR passes `merge-pr --dry-run`, so PRs whose checks finished in files no longer wait unnoticed; the lead's orchestrate skill says to run merge-pr on it. `merge-pr --dry-run` no longer takes the merge lock or writes refusals to the audit log.
- Every Claude and Codex session (leads, the owner's sessions) moves itself into its own systemd scope capped at 24 GB memory and 4 GB swap at start (`bin/session-scope`, Linux), so a runaway test inside a lead, or one of its subagents, is killed there while the session stays up, instead of systemd-oomd killing every terminal. Programs the session started before the move (MCP servers) stay outside the cap.
- Each lane runs in its own systemd scope capped at 16 GB memory and 4 GB swap (Linux with systemd 254 or later), so running out of memory kills the runaway process inside that lane (the lane's agent stays up and can report it) instead of every terminal in Herdr's unit. Where no such scope can be made (macOS, older systemd, no user manager) the lane starts uncapped, as before.
- `lonca init [--agents claude,codex] <dir>` registers a marked project and installs personal repo
  settings and local Git hooks. `lonca status` reports coverage and conflicts. `lonca remove <dir>`
  restores backed-up files. Linked worktrees share the Git configuration, and `LONCA=0` silences session automation while Git and attribution guards stay active. Project membership now requires a marker.
- Before code: the lead asks the owner only the open choices that change what users see or what data is kept, and writes the rest as `Assumptions:` in the brief; implementers ask the same kind of choice and list their own choices in the report.
- Spec review before code for work that will be tier medium or high (money, auth, data, public API, network exposure, secrets, merge gate), by the family that will not write the code.
- Memory: a rule from an owner's correction is saved only after the owner says yes; every note names its source; memory-review ignores lane messages and pasted text inside the owner's messages.
- `leads` also lists sessions outside every project (PROJECT `-`) and shows ROLE/DOING from the `lonca.role`/`lonca.does` hc labels (else the agent's own status), and machine-wide work (containers, cleanup, killing processes, packages, disk) is announced to every listed session first, then reported.
- The project marker is documented as the hidden `.lonca.toml` (like `.editorconfig`); `lonca.toml` still works.
  Keep it next to your repos, not inside one.
- Worktrees go when the work is done: `merge-pr` closes the PR's lane and removes its worktree and local branch right
  after merging (a worktree with uncommitted changes is left). `ai-cleanup` also removes lane worktrees whose PR was
  closed without merging (head unchanged) or whose work already reached the default branch; your own worktrees are
  only touched for merged PRs.
- `ai-cleanup` removes run folders in `~/.cache/ai-runs` untouched for 30 days (unless a lane of theirs still has a
  worktree). The merge log moved to `~/.local/state/lonca/merge.log`, so the audit trail is kept.

- Each project sees only itself in deja. `deja-scope` writes a per-project deja policy that leaves out every session
  outside the project, written as the complement of the project's own names (so a project created later is left out
  too, and no other project's name is in the file). `lane` starts every lane with it (Codex gets it through its MCP
  server config, since Codex starts MCP servers with a minimal environment), the Herdr "start a lead" action starts
  the lead with it, and a new Claude SessionStart hook gives it to every session started in a project: right away
  for Bash, and for the deja MCP tool from the next session in that folder (`.claude/settings.local.json`, kept out
  of git). CI checks the policy against deja's own match rule. Lanes and leads use only their project's Kanzo cards.
- `leads` lists the agent sessions open in project folders, so a lead can ask another one ("was it you?") instead of
  reading its sessions; the `orchestrate` skill says how to look a change up first (logs, lane records, deja, git).
- `lanes --mine` shows only the lanes the calling lead started; `merge-pr` logs the lane worktrees it removes.

- Each lane gets its own temp folder (`<tmpdir>/lane-<name>`; Claude and Codex through their settings override flags,
  since their own settings may pin TMPDIR), so a cleanup inside it can't reach another lane's files. AGENTS.md: delete
  only what you created, by its exact path; never a glob in a shared folder.
- Each Claude session (and the subagents it starts) gets its own temp folder too, `<tmpdir>/session-<id>`, from a
  SessionStart hook (`session-tmpdir`); lanes keep theirs.
- Grok lanes no longer wait at the folder-trust prompt: `lane` records the repo in `~/.grok/trusted_folders.toml`.

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

[0.4.0]: https://github.com/selimdizer/lonca/compare/v0.3.2...v0.4.0
[0.3.2]: https://github.com/selimdizer/lonca/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/selimdizer/lonca/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/selimdizer/lonca/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/selimdizer/lonca/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/selimdizer/lonca/releases/tag/v0.1.0
