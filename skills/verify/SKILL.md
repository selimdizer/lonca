---
name: verify
description: Prove a lane is done in any repo by running the same checks its CI runs. Use before reporting a lane as done or opening a PR. If the project has its own verify skill (project skills live in the project root, the folder with `lonca.toml`, under `.claude/skills/`, e.g. `verify-shop`), use that one instead.
---

# Verify a lane (any repo)

1. Project skill first: if a `verify-<project>` skill matches this repo, follow it and stop here.
2. Find what CI runs: `.github/workflows/*.yml` (jobs that trigger on the changed paths), then `Makefile` / `justfile` targets, `package.json` scripts, `pyproject.toml`, `go.mod`, `Move.toml`. Read the files; don't guess commands.
3. Run those steps in the lane's worktree, same commands, same order. Changed tests first for fast feedback, then the full set.
4. Added files: `git status --porcelain --ignored` must show no new `!!` that the code needs (ignored files pass locally, fail in CI).
5. Exercise the change for real when it is user-facing (run the CLI, hit the endpoint, open the page).
6. Leave the worktree as you found it: run Python with `PYTHONDONTWRITEBYTECODE=1`; remove untracked caches your runs created (`git status --porcelain` before/after).
7. Move (Sui): use the Sui version the repo's CI pins — `~/lonca/bin/sui` (also in the shims PATH) picks it from `SUI_VERSION` in `.github/workflows`; a newer toolchain rewrites `Move.lock` revs. A stale lock (manifest changed, lock not) is rewritten by any build, CI's version too. Unless the lane changed dependencies on purpose, `git diff --quiet -- '*Move.lock'` must hold after your runs; restore any rewritten lock with `git checkout -- <file>` and report a stale lock to the owner.
8. Anything you could not run (missing service, credentials, platform) is FAIL / not verified, never OK.

Report: per check, the command → pass/fail with key output lines, then "Not verified".
