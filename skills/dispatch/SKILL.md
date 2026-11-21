---
name: dispatch
description: Exact, tested commands to start another agent CLI (Claude, Codex, Copilot, opencode, omp) headless and collect its result. Use when your brief allows you to hand work to another agent or model, or when you are the lead routing work.
---

# Dispatching work to other agents

Only dispatch when you are the lead or your brief explicitly allows it. Workers never dispatch on their own.

## Contract for every dispatch
- Write the brief to a file first: goal, why, done-looks-like, never, quality bar, "ask if unclear".
- One run directory per job, under its project: `RUN=~/.cache/ai-runs/<kanzo-project>/<date>-<slug>` (e.g. `shop/2026-11-21-cart-fix`); each lane writes its final message to `$RUN/<lane>.md`. Read that file, not the logs.
- Run long jobs in the background; never poll with sleep loops.
- Writers work in their own git worktree (`$WT`). Reviewers get read-only access.
- Pick the model from `~/lonca/routing.md`. Writer and reviewer must be different families (Claude vs OpenAI).
- An empty or missing result file means the run failed: retry once, then report it. Never treat it as success.

## Commands (tested 2026-11-20 unless marked)

Anything that writes code runs only through `lane <repo> <branch> <agent> <brief> <result> [base]` (`~/lonca/bin/lane`; base default = the remote's default branch, e.g. a repo whose PRs target `test`): it makes the worktree under `~/.herdr/worktrees`, runs the agent as a herdr-core (`hc`) terminal the owner sees in the Herdr app (started from a lead inside the app, it opens as a tab in the lead's space), starts the agent with full permissions and the guard shims, and the agent writes its report to `<result>`. Wait for that file. Agents: `claude:<role>`, `codex:<model>[:<effort>]` (default xhigh; interactive, so the app shows its status), `omp:<provider/model>`. Closing a lane's tab in the Herdr app kills the lane.
Never start or restart the hc core from an agent shell (it would inherit your session variables, incl. your messaging token, into every terminal); `lane` strips them first. The raw commands below are only for short Claude/Codex read-only work (review, second opinion); omp work always goes through `lane` (below). Raw commands they run outside hc, so always prefix them with `PATH=$HOME/lonca/shims:$PATH` (guards gh/git/pkill when permissions are bypassed).

### Claude Code
```bash
# a role (model, effort, tools and rules come from ~/.claude/agents/<role>.md)
claude -p --agent implementer --permission-mode bypassPermissions < brief.md > $RUN/$L.md   # roles: implementer, reviewer, verifier, security-auditor
# plain model, no role
claude -p --model fable --effort medium < brief.md > $RUN/$L.md                     # models: fable, opus, sonnet, haiku
```
Always use `--agent <role>` for lanes, so the role's tool limits apply. Headless runs need `bypassPermissions` (nobody can answer a prompt); the deny rules and pre-push hook still apply in that mode (tested 2026-11-20). Inside Claude Code use the Agent tool with the same subagent names.

### Codex
```bash
# writer
codex exec -C $WT --dangerously-bypass-approvals-and-sandbox --disable apps -m gpt-6.2-sol -c model_reasoning_effort=xhigh --ephemeral -o $RUN/$L.md - < brief.md
# reviewer (read-only)
codex exec -C $WT -s read-only --disable apps -m gpt-6.2-astra -c model_reasoning_effort=high --ephemeral -o $RUN/$L.review.md - < review-brief.md
codex exec review --base main      # built-in diff review, run inside $WT
```
With the bypass flag Codex can commit its own lane branch (lanes run with full permissions); the shims and pre-push hook still block merge, push to main, force-push and the other hard limits.
Read-only Codex can't run tools that write caches (`uvx`, `npm`): it falls back to `python -m pytest` etc. Test results come from the `verifier`; the Codex reviewer reads and reasons.

### GitHub Copilot models (client work whose memory allows only Copilot)
The Copilot CLI is not used. Copilot models run inside omp (see below) with `--model github-copilot/<model>`.

### omp work is always a lane (the owner sees it in Herdr)
```sh
# questions, code reading, research: read-only lane, no worktree, read/grep/glob only; its answer is the report, DONE comes by itself
lane --read <repo-dir> <short-name> omp:opencode-go/deepseek-v4.1-flash $RUN/<name>.brief.md $RUN/<name>.md
# review / audit / test check that needs commands: a normal lane, all tools, its own worktree on a fresh copy of the PR branch
lane <repo-dir> review/<lane> omp:opencode-go/deepseek-v4.1-flash $RUN/<lane>.review-brief.md $RUN/<lane>.review.md <pr-branch>
```
Read lanes run in the repo folder itself, so they get no write/edit/shell tools. Review lanes may run tests, `git log/diff` and linters; the brief says "do not edit, commit or push". Several parts of one sweep = several lanes, one per part. Close finished lanes with `env -u CLAUDECODE hc kill <name>` after reading the report. On opencode-go use only small models (owner): `deepseek-v4.1-flash` first; `hy4-flash-free` (free) only for non-client, non-sensitive code. See routing.md. Tested 2026-11-21: read lane on lonca answered with file:line in 14 s, report written, DONE arrived.

### omp (harness for Copilot, opencode go and z.ai GLM)
```bash
omp -p --no-session --model <provider/model> "$(cat brief.md)" > $RUN/$L.md
#   github-copilot/<model>        client work limited to Copilot; ALSO pass
#                                 --smol github-copilot/claude-sonnet-5.5 --slow github-copilot/claude-opus-5.5
#                                 (omp's default helpers are DeepSeek/GLM; `lane` adds these itself)
#   opencode-go/deepseek-v4.1-flash  cheap first-pass review, code reading
#   zai/glm-5.3-flash             cheap mechanical work
# default with no --model: Opus 5.5 via Copilot, thinking medium
```
Hard limits are enforced by the `lonca-guard` extension (`~/lonca/config/omp-guard`) and `~/.omp/agent/RULES.md`.
Tested 2026-11-20: github-copilot (claude-opus-5.5, claude-sonnet-5.5), opencode-go (deepseek-v4.1-flash), zai (glm-5.3); kanzo + chrome-devtools MCP work.

## Never
- Full-permission flags only together with the guard shims in PATH.
- No Max effort and no fast mode.
- Don't send client code to a provider its project memory does not allow.
