---
name: dispatch
description: Exact commands to start another agent CLI (Claude, Codex, omp, opencode, Copilot, Antigravity, pi, Grok) as a lane or headless and collect its result. Use when your brief allows you to hand work to another agent or model, or when you are the lead routing work.
---

# Dispatching work to other agents

Only dispatch when you are the lead or your brief explicitly allows it. Workers never dispatch on their own.

## Contract for every dispatch
- Write the brief to a file first: goal, why, done-looks-like, never, quality bar, "ask if unclear".
- One run directory per job, under its project: `RUN=~/.cache/ai-runs/<kanzo-project>/<YYYY-MM-DD>-<slug>` (e.g. `shop/<date>-cart-fix`); each lane writes its final message to `$RUN/<lane>.md`. Read that file, not the logs.
- Run long jobs in the background; never poll with sleep loops.
- Writers work in their own git worktree (`$WT`). Reviewers get read-only access.
- Pick the model from `~/lonca-local/routing.md` if it exists, else `~/lonca/routing.md`. Writer and reviewer must be different families.
- An empty or missing result file means the run failed: retry once, then report it. Never treat it as success.

## Lanes: anything that writes code
`lane <repo> <branch> <agent> <brief> <result> [base]` (`~/lonca/bin/lane`; base default = the remote's default branch, e.g. a repo whose PRs target `test`). It makes the worktree under `~/.herdr/worktrees`, runs the agent as a herdr-core (`hc`) terminal the owner sees in the Herdr app (started from a lead inside the app, it opens as a tab in the lead's space), starts the agent with full permissions and the guard shims, and the agent writes its report to `<result>`. Wait for that file. Closing a lane's tab in the Herdr app kills the lane.

Lane agents:
- `claude:<role>` — Claude Code with a role from `agents/` (implementer, reviewer, verifier, security-auditor).
- `codex:<model>[:<effort>]` — Codex, interactive so the app shows its status; effort default xhigh.
- `omp:<provider/model>` — oh-my-pi, any provider it knows; `omp:github-copilot/<model>` keeps its helper models on Copilot too.
- `opencode:<provider/model>` — opencode (`mini --standalone` with the `lonca-lane` agent).
- `copilot:<model>` — GitHub Copilot CLI (`~/.herdr/worktrees` is in its trusted folders).
- `agy:<model>` — Antigravity CLI.
- `pi:<provider/model>` — pi.
- `grok:<model>` — Grok CLI.

Read-only questions, code reading, research: `lane --read <repo-dir> <short-name> omp:<provider/model> <brief> <result>` — no worktree, read/grep/glob plus omp's MCP servers (deja, Kanzo), its answer is the report and DONE comes by itself. A review, audit or test check that needs commands: a normal lane on a fresh copy of the PR branch (`lane <repo-dir> review/<lane> <agent> <brief> <result> <pr-branch>`); the brief says "do not edit, commit or push". Several parts of one sweep = several lanes. Close finished lanes with `env -u CLAUDECODE hc kill <name>` after reading the report. omp work never runs as a hidden background command: the owner watches it in Herdr.

Never start or restart the hc core from an agent shell (it would inherit your session variables, incl. your messaging token, into every terminal); `lane` strips them first.

## Raw commands: short Claude/Codex read-only work only
Review or second opinion, outside hc. Always prefix them with `PATH=$HOME/lonca/shims:$PATH` (guards gh/git/pkill when permissions are bypassed).

### Claude Code
```bash
# Resolve the role in the checkout where the command runs.
role=$(lonca-project --claude-agent reviewer "$PWD") || exit 1
claude -p --agent "$role" --permission-mode bypassPermissions < brief.md > $RUN/$L.md   # roles: implementer, reviewer, verifier, security-auditor
# plain model, no role
claude -p --model <model> --effort medium < brief.md > $RUN/$L.md
```
Use the resolved role with `--agent`. Plugin-enabled repositories use `lonca:<role>`; marked repositories using the legacy install use `<role>`. Headless runs need `bypassPermissions` (nobody can answer a prompt); the deny rules and pre-push hook still apply in that mode. Inside Claude Code use the Agent tool with the same subagent names.

### Codex
```bash
# reviewer (read-only)
codex exec -C $WT -s read-only --disable apps -m <model> -c model_reasoning_effort=high -c "$DJ" --ephemeral -o $RUN/$L.review.md - < review-brief.md
codex exec review -c "$DJ" --base <base>      # built-in diff review, run inside $WT
```
`DJ="mcp_servers.deja.env.DEJA_POLICY_FILE=\"$DEJA_POLICY_FILE\""`: Codex starts MCP servers with a minimal environment, so it gets the project's deja scope this way (every other CLI inherits `DEJA_POLICY_FILE` from you).
Codex writers run as `codex:` lanes; with full permissions they commit their own lane branch, and the shims and pre-push hook still block merge, push to the default branch, force-push and the other hard limits.
Read-only Codex can't run tools that write caches (`uvx`, `npm`): it falls back to `python -m pytest` etc. Test results come from the `verifier`; the Codex reviewer reads and reasons.

omp's hard limits are enforced by the `lonca-guard` extension (`~/lonca/config/omp-guard`) and `~/.omp/agent/RULES.md`.

Plan-specific notes (which cheap models, provider limits, what was tested): `examples/dispatch-notes.example.md`; keep your own in `~/lonca-local/`.

## Never
- Full-permission flags only together with the guard shims in PATH.
- No max effort and no fast mode.
- Don't send client code to a provider its project memory does not allow.
