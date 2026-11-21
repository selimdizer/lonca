# Changelog

All notable changes to Lonca. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

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
