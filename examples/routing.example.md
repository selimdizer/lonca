> An example from one setup (2026-11); models and plans will differ. Copy what fits into `~/lonca-local/routing.md`.

# Model routing

Source: Artificial Analysis 2026-11-19 + subscription accounting (quota = model-weighted tokens).
The lead routes mechanically by this table and writes the choice + one-line reason in each brief.
Review is always done by the family that did NOT write the code (Claude ↔ OpenAI).

| Work | Primary | Fallback |
|---|---|---|
| Lead, plan, hard calls | Claude `fable` effort medium (Opus high was tried as lead; Fable plans better per token) | Codex `gpt-6.2-sol` xhigh |
| Plan second opinion (big or architectural) | Codex `gpt-6.2-astra` high | Claude `opus` high |
| Implementation: frontend/UI, user-facing product features, anything the owner will look at | Claude `implementer` (`opus` high) — Opus's visible work is the strongest | Codex `gpt-6.2-sol` xhigh |
| Implementation: backend plumbing, scripts, infra, tests, migrations | Codex `gpt-6.2-sol` xhigh | Claude `implementer` |
| Implementation: very hard or cross-service | Codex `gpt-6.2-astra` high, or Claude `opus` xhigh when it is UI/product | the other one |
| Mechanical (renames, boilerplate, test scaffolding) | Codex `gpt-6.2-sol` medium | omp `opencode-go/deepseek-v4.1-flash` |
| Code reading, codebase questions, research and summaries, first read of PRs/logs (read-only) | omp `opencode-go/deepseek-v4.1-flash` as a read lane (`lane --read`, `dispatch`); a review/check that needs commands is a normal omp lane — opencode-go is a flat monthly plan, use it first | Claude Explore / `sonnet` subagent |
| Review (code by Claude) | Codex `gpt-6.2-astra` high, read-only | Codex `exec review` |
| Review (code by Codex) | Claude subagent `reviewer` (`opus` high) | `fable` high |
| Verification (run tests and app) | Claude subagent `verifier` (`opus` medium) | — |
| Security (auth, SQL, secrets, LLM tools, money) | Claude subagent `security-auditor` (`fable` high) + semgrep/gitleaks | Codex `gpt-6.2-astra` high |
| Research needing judgment or web synthesis | Claude `sonnet` subagent | omp `opencode-go/deepseek-v4.1-flash` read-only |
| Client-critical work (the project's memory names the allowed provider) | only that provider, for every role (e.g. omp `github-copilot/*`) | — |

## Rules
- opencode-go (a flat-rate plan): only small models; big ones use up the limit fast. Measured 2026-11 on read-only questions: `deepseek-v4.1-flash` best (7-20 s, ~43k requests / 5 h); `hy4-flash-free` as good (free, unlimited for a limited time) but free models may train on the data: only for non-client, non-sensitive code; `qwen3.8-flash` slower; `mimo-v2.6-flash` timed out, `longcat-2.5-free` too slow (171 s).
- Which implementation row: by what the change touches; mixed changes go to the row of their riskiest part. Say the row in the brief. When unsure between Opus and Sol, pick Opus.
- Data behind the rows (Artificial Analysis, 2026-11-21, per task): Sol xhigh II 55.7 / TB4 56.1 / FrontierCode 42.8, $0.65, 6 min; Opus high 51.8 / 56.6 / 35.9, $3.46, 9 min (writes 107 tok/s vs 66); Opus xhigh 57.4 / 59.6 / 43.8, $6.05, 16 min; Astra high 60.1 / 60.1 / 47.1, $2.07, 6 min. The owner's experience with Opus counts too; `~/lonca-local/model-log.jsonl` decides after two weeks of real lanes.
- Never Max effort, never fast mode.
- Cap the lead model's share of your weekly Claude quota (e.g. half). Near that limit, the lead role moves to Codex (`gpt-6.2-sol` xhigh) with the same `orchestrate` skill.
- A rate-limit or quota error moves that lane to the other family; note it in the report.
- Small task (one file, under ~30 minutes): one implementer, no plan ceremony. Every delegation costs the lead ~5–7k tokens.
- Monthly: update this table from `~/lonca-local/model-log.jsonl` + fresh Artificial Analysis data; propose the change to the owner, apply after approval.
