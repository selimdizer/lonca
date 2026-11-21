---
name: security-check
description: Security pass for every finished lane - local scanners on the diff, then a risk-based review; deep differential review when the change touches auth, access control, queries, secrets, money, file/URL handling, crypto, external calls or LLM prompts/tools. Use after a lane passes verification, before the PR is reported.
---

# Security check (every lane)

Read-only. Never print secret values (name file:line only). Reports go to `$RUN/<lane>.security.md`, never into the repo.

## 1. Scanners (always, on the lane's worktree)
- Secrets: `mise exec gitleaks@latest -- gitleaks git --no-banner --log-opts="origin/main..HEAD"` (only the lane's commits).
- Code patterns: `uvx --python 3.13 semgrep scan --config p/default --metrics off --quiet $(git diff --name-only origin/main...HEAD)` (Python 3.15 crashes semgrep; metrics off keeps code local).
- Go dependencies/stdlib: `govulncheck ./...` in each changed Go module.
- New or upgraded dependencies (go.mod, package.json, lockfiles, pyproject, Move.toml): use the `supply-chain-risk-auditor` skill on just those packages; `npm audit --omit=dev` for changed Node apps.
Say which scanner ran and which failed to run.

## 2. Risk classification
HIGH if the diff touches any of: authn/authz, tenant or row checks, SQL/queries, secrets/config, money or billing, file paths/uploads/URL fetching, crypto, deserialization, shell/exec, external calls, LLM prompts or tool definitions, CI/workflows, smart contracts (Move). Otherwise LOW. A refactor of HIGH code is HIGH.

## 3. Review
- LOW: read the diff once for the list in step 2 and for unsafe defaults (debug on, CORS `*`, verbose errors to users).
- HIGH: run the `differential-review` skill on `origin/main...HEAD`, writing its report to `$RUN/<lane>.security.md`. For Move contracts also check capability/ownership checks, object transfer rules and arithmetic overflow paths.
- Every finding through the `fp-check` skill before it is reported; drop the false positives, say how many were dropped.

## 4. Output (at most 30 lines)
`SECURITY: CLEAN` or `SECURITY: FINDINGS (n), highest: LOW|MEDIUM|HIGH` (the worst finding's severity, not the diff's risk class), then `HEAD: <git rev-parse HEAD you checked>` and the risk level, then each finding: `file:line — issue (CWE) — exploit scenario — smallest fix — confidence`. Then "Not verified". A HIGH finding blocks the PR report until fixed or the owner accepts it.
