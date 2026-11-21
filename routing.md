# Model routing

Your own routing goes in `~/lonca-local/routing.md`; agents read that file instead of this one when it exists. This is the generic template; a filled-in example is `examples/routing.example.md`.

The lead routes by this table and writes the choice + a one-line reason in each brief. "Family" means a model vendor (e.g. Claude, OpenAI); A is the lead's family, B the other one you have.

| Work | Model | Why |
|---|---|---|
| Lead, plan, hard calls | your strongest model of family A, medium effort | planning quality decides every lane; medium effort keeps it affordable |
| Plan second opinion (big or architectural plans) | your strongest model of family B, high effort | another family catches blind spots the lead shares with its own family |
| Implementation: frontend, UI, user-facing product work | the strongest model for visible work, high effort | what the owner looks at needs the best taste and polish |
| Implementation: backend plumbing, scripts, infra, tests, migrations | a strong, cheaper coding model, high effort | correctness matters more than taste; cost per lane adds up |
| Mechanical (renames, boilerplate, test scaffolding) | a cheap model of either family, medium effort | the task is fully specified; a big model wastes quota |
| Code reading, research, summaries, first read of PRs/logs (read-only) | a cheap or flat-rate model as a read lane (`lane --read`) | reading is high volume and low risk |
| Review | a strong model of the family that did NOT write the code, read-only | a model rarely spots its own family's mistakes |
| Verification (run tests and app) | Claude subagent `verifier` or any strong model with shell access | needs to run things and report evidence, not to write code |
| Security (auth, SQL, secrets, LLM tools, money) | your strongest model, high effort (`security-auditor`) + local scanners | a missed finding costs more than the tokens |
| Client work (the project's memory names the allowed provider) | only that provider, for every role | the client's code may only go there |

## Rules
- Review is always done by the family that did not write the code.
- Which implementation row: by what the change touches; mixed changes go to the row of their riskiest part. Say the row in the brief.
- Never max effort, never fast mode.
- A rate-limit or quota error moves that lane to the other family; note it in the report.
- Small task (one file, under ~30 minutes): one implementer, no plan ceremony. Every delegation costs the lead tokens.
- Monthly: update the table from `~/lonca-local/model-log.jsonl` (and fresh benchmark data if you use it); propose the change to the owner, apply after approval.
