# Changelog

All notable changes to Lonca. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

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

[0.3.2]: https://github.com/selimdizer/lonca/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/selimdizer/lonca/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/selimdizer/lonca/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/selimdizer/lonca/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/selimdizer/lonca/releases/tag/v0.1.0
