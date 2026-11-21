# Changelog

All notable changes to Lonca. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

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
