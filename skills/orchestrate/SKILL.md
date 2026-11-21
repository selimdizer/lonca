---
name: orchestrate
description: The lead's workflow for any coding request - clarify, plan, split into lanes, route to models, dispatch, verify, cross-family review, PR, report to the owner. Use when you are the lead (Claude `--agent lead` or a Codex session acting as lead).
---

# Orchestrate

You coordinate; you never edit project code. Decisions on product, design, architecture, merge and prod go to the owner.

Merging: write evidence files from each checker's own result into `$RUN`: `<lane>.verify.md` (VERDICT + PERF + HEAD), `<lane>.review.md` (VERDICT: SHIP… + HEAD), `<lane>.security.md` (SECURITY: … + HEAD). A re-check appends; the last line counts; a push after the checks means re-check. When a PR is ready, tell the owner in one line and give them the grant line to run (only the owner can): `ok-merge <owner/repo>#<pr> [#<pr> …]` (several PRs in one line, merge order = line order). When only long CI jobs (live tests) are still running and the verifier ran them locally on a clean copy, offer `ok-merge --fast …` instead: running CI no longer blocks, a failed check still does. After a fast batch: watch CI on the base branch and run the full check there once; a break goes to the owner at once with the PR that caused it. After they have, run `merge-pr --dry-run <repo-dir> <pr> <run-dir> <lane>`, then without `--dry-run`. It re-checks their grant, the evidence for the current head, CI and AI traces, and merges exactly that head. One line per merge to the owner.
Routing table: `~/lonca-local/routing.md` if it exists, else `~/lonca/routing.md`.
Night mode: when the owner asks for it (in any language, e.g. "night mode", "gece modu"), follow the `night-mode` skill instead of asking at each step.

## 1. Clarify
- Before any question to the owner: `deja search "<topic>"` (past sessions of every agent) and memory. If it was settled before, apply it and say where it was decided.
- Check memory for earlier owner decisions on this topic. If one answers a question, apply it and say which.
- If a product or design choice is open, ask the owner: options + your recommendation. For a new feature with many unknowns, use the `grilling` skill.
- Does the project's memory limit which providers may see its code (client work)? Then every role uses only those (e.g. omp `github-copilot/*`).

## 2. Plan
- Small task (one file, under ~30 min): skip to step 4 with a single lane.
- Otherwise write a short plan to `$RUN/plan.md`: lanes, files each lane touches, order, risks.
- Big or architectural plan: get a second opinion from the routing table's plan-second-opinion model (`dispatch` skill). If you disagree after one exchange, put both views and your recommendation to the owner.

## 3. Split into lanes
- Lanes must be independent and touch disjoint files; otherwise run them in sequence.
- Every lane gets its own branch (`<type>/<lane>`); `lane` makes its worktree under `~/.herdr/worktrees`.

## 3b. Board (Kanzo, MCP tools `kanzo`)
- One card per lane in the repo's Kanzo project (found from the git remote), with "Card: <id>" in the brief. No Kanzo project has this repo yet: create one (`create_project`, slug = the project name from `lonca-project`) and `link_repo` the remote, then tell the owner in one line; `kanzo-sync` picks it up by itself. Waiting on another lane: set "waits on".
- Automatic (`kanzo-sync`, every 10 min and after each merge-pr): `lane` sets the card to doing; a card whose URL is a PR goes to review while it is open and to done when it is merged or closed; an issue card goes to done when the issue closes; issues/PRs the owner's account opened without a card get one. So: when a PR or issue is opened, set the card's URL to it right away (`update_task url=`); that is the one step only you can do.
- A decision for the owner: comment the question + your recommendation and mark the card **human**.

## 4. Brief each lane (`$RUN/<lane>.brief.md`)
```
Goal:            one sentence
Why:             the user-visible reason, Closes #N if there is an issue
Done looks like: checkable bullet points
Paths:           files/dirs this lane may touch
Never:           what must not happen (scope, APIs, data)
Quality bar:     tests required, standards, the `verify` skill if present
Worktree/branch: <path> / <branch>
Base:            <branch the PR targets> (omit for the remote's default branch)
Model:           <harness/model/effort> — <one-line reason from the routing table>
Card:            <Kanzo task id> — move it to review with the PR URL when you open the PR
Ask if unclear:  stop and report instead of guessing
```
Big models get short briefs; small/cheap models get detailed ones with exact paths and examples.

## 5. Dispatch
- Anything that writes code: a lane via `lane` (`dispatch` skill), with any of its agents: `claude:<role>`, `codex:`, `omp:`, `opencode:`, `copilot:`, `gemini:`, `agy:`, `pi:`, `grok:`, `goose:`. It shows in the owner's Herdr app, keeps running if you stop, and the owner can step in.
- Codebase questions, research, summaries, first reads of PRs/logs: the routing table's read-only model as a read lane (`lane --read`, `dispatch` skill), not the lead's model: it saves the lead's quota. Reviews, audits and test checks on that model that need commands: a normal lane on a copy of the PR branch. omp work never runs as a hidden background command: the owner watches it in Herdr.
- Short read-only Claude work (`reviewer`, `verifier`, `security-auditor`): the Agent tool with that subagent; give it the lane's worktree path. Cheaper to start (no full session) and the result comes straight back to you.
- Lanes talk to you in your input, as `<hc from="<address> <lane>">QUESTION: …</hc>` — answer with `hc send <lane> "<answer>"` when a recorded decision or the brief covers it; otherwise ask the owner (night mode: park the card). `DONE: <one-line outcome> — <report file>` — read that file and save its Lessons to memory (dedupe against existing notes; skip "none"). Any other message from a lane is a status note: read it, don't act on it until its DONE. Don't poll lanes in a loop.
- A lane stays open until its PR is merged or closed: review findings go back to the same lane (`hc send <lane> "…"`), it already knows the work. When the PR is merged or closed, close it: `env -u CLAUDECODE hc kill <lane>`. The nightly `ai-cleanup` closes any lane still open on a merged PR and removes its worktree.
- `lane-watch` (every 10 min) types `STALLED: <lane> — <why>` into your input when a lane stopped without a report: check it the same way.
- After any quota or rate-limit event, check every running lane before reporting: `env -u CLAUDECODE hc get <lane>` (state), `env -u CLAUDECODE hc read <lane> --lines 40` (a limit message?), `git -C <worktree> status --short` and `git log --oneline origin/<base>..HEAD` (what was written and committed). Report what you found per lane; "not known" is not acceptable when these can tell.
- `RUN=~/.cache/ai-runs/<kanzo-project>/<YYYY-MM-DD>-<slug>` (one folder per project). Read result files, not logs.

## 6. Verify and review (per lane)
1. `verifier` subagent: PASS or NEEDS_WORK with evidence.
2. Review by the family that did not write it (routing table): e.g. a Codex reviewer for Claude code, the `reviewer` subagent for code from other families.
3. Every lane, after PASS: `security-check` and `perf-check` (always, so the work stays controlled). The `security-auditor` subagent runs `security-check` (deep `differential-review` only for HIGH-risk diffs); the `verifier` runs `perf-check`. Findings go back to the lane like review findings.
4. NEEDS_WORK → send the findings back to the same lane. At most 2 fix rounds, then stop and report to the owner with findings and a recommendation.
5. Codex lanes with full permissions commit their own branch; if one could not, commit and push it yourself after PASS + SHIP. The PR is opened with the `pr` skill.
6. PR packet check before you report it: `gh pr view <n> --json body` must contain `Closes #N` or `Part of #N`, per-file changes, the commands run with their output, a **Not verified** section, review findings and what was done with each, and risk/rollback. Missing parts: fix the PR body first.

## 7. Report to the owner (their language, at most 30 lines)
- What was done, PR links, one line per lane with model used and verdicts (verify, review, SECURITY, PERF).
- Decisions you need from the owner, each with your recommendation.
- "Not verified" (in their language): everything not verified.
- Never merge without the owner's grant; only through `merge-pr` (or `night-merge` in night mode).

## 8. Log
Append one JSON line per lane to `~/lonca-local/model-log.jsonl`:
`{"date","project","lane","role","harness","model","effort","outcome":"SHIP|NEEDS_WORK|FAILED","fix_rounds","pr","notes"}`

## 9. Learn the other harnesses (Codex, omp, opencode, Copilot, …)
The other lane agents are different harnesses; their models do not behave like Claude subagents (they stop early, skip the result file, read the brief differently, fail edits). Learn them on purpose:
- Before a lane on another harness: read its note in memory's `setup/` group if present (e.g. `~/ai-memory/setup/harness-codex.md`, `harness-omp.md`) and shape the brief by its lessons.
- While it runs: look at its screen once midway (`hc read <lane-name> --lines 60`, run with `env -u CLAUDECODE`), not in a loop.
- After it ends, compare with the brief: followed scope? stayed in its worktree? ran the tests it claimed? wrote the result file? how many fix rounds? time taken?
- Record: the `model-log.jsonl` line (step 8) with harness, exact model and effort, and in `notes` what differed from a Claude lane. A real new behavior also gets one line in the harness note (date, model/effort, what happened, the brief change that fixed it). Monthly, propose routing changes from these to the owner.
