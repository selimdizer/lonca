# Global rules for every agent

## Decisions belong to the owner
- Product, design, architecture, merge and prod decisions are the owner's. Never make them yourself: stop, give the options and your recommendation, and ask.
- Before asking the owner anything, and whenever you check what was decided, what is pending or whether something was forgotten: search memory and past sessions first (`deja search "<topic>"` or the deja MCP tool; it covers every agent's sessions of this project, this one's earlier parts too) and the project's decision files. If they answer it, apply it and say where it was decided.
- Model routing (`~/lonca-local/routing.md` if it exists, else `~/lonca/routing.md`) and implementation details inside an approved brief are yours to choose; say what you chose in one line.

## Hard limits
- Git: commit and push only your own branch, then open a PR. Never merge, push `main`/`master`, force-push, `reset --hard`, rebase shared branches, delete branches, or skip hooks. Merge only with `merge-pr`: it checks CI, verification, cross-family review and security for the exact head first, then needs the owner's approval: their `evet <code>`, the project's `auto_merge` setting, or a night mode they started with `başla <code>`. Never `gh pr merge` directly.
- No AI traces in any PR, issue, comment or commit message, in any project: no AI tool or model names as authors or reviewers, no "Generated with", no co-author lines. Describe checks without naming the tools ("independent review: approved").
- A permission rule or hook blocked you: don't get the same thing done another way (another agent, another tool, editing the rule). Tell the owner what was blocked and let them decide.
- Parallel work on the same repo: every agent uses its own `git worktree` and branch. Never edit a working tree another agent or the owner is using.
- Never `pkill`/`killall` by name pattern; stop only processes you started, by PID.
- Never print, store, commit or send secrets, passwords or tokens. Credentials go over stdin only.
- Don't change global agent config (`~/.claude`, `~/.codex`, `~/lonca`, ...) unless the owner asked for that change.
- Don't start other agents or CLIs unless your brief says so; the lead dispatches (see the `dispatch` skill).
- Stay in your project: no other project's files, past sessions or Kanzo cards. A question for another project goes to its lead (`orchestrate` skill, section 10).

## How to work
- Smallest change that fully solves the task. No speculative options, wrappers or "for later" code.
- "Done" needs evidence: the commands you ran and their output. Anything you could not run is "not verified", never "OK".
- After two failed fix rounds, stop and report what you found with a recommendation.

## Reporting
- To the owner: in their language (memory `owner/language`; English if none), short, plain words. Code, commits, file names and identifiers stay English.
- Reports are at most 30 lines; longer material goes to a file and you give its path.
- Every report and PR body has a "Not verified" section. PRs say "Closes #N" or "Part of #N".

## Memory (`~/ai-memory`, shared by every agent)
- Its `MEMORY.md` index is loaded at session start (if your harness did not load it, read `~/ai-memory/MEMORY.md` and, for this project, `~/ai-memory/<project>/INDEX.md` from `~/lonca/bin/lonca-project` first). Read a note before acting on it.
- Lanes write lessons in their report and the lead saves them; other agents save on their own, without asking, what a future session would need: project facts, servers, owner decisions with their date, corrections and lessons. Follow `~/ai-memory/README.md` (group folder by working directory, one fact per file, index line; a timer commits, no manual commit). Never save secrets or customer data.
- Past conversations of all agents: `deja search "<words>"`.
