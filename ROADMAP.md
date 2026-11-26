# Roadmap

What Lonca works on next, in order. Work outside this list starts only after it is added here. Items name their board card (`lonca#N`) where one exists. Open decisions are in the owner's questions ledger (`lonca questions`, ids `Q-n`).

## Urgent

- **Checkers leave background shells running** (lonca#492):
  - verifier, security-auditor and reviewer run commands in the foreground and report only after their shells have exited;
  - the lead stops what a finished check left behind;
  - `test-slot` gets a wait limit.

## Phase 0: decisions

| id | question | recommended |
|---|---|---|
| Q-1 | Split into **Lonca skills** (works alone) and **Lonca runtime** (`lane`, `merge-pr`, guards, Herdr) | yes |
| Q-2 | Claude Code's built-in commands in Lonca projects | `/code-review high` as an extra local review (not cross-family); `ultra` on request; `/ship` and `/steward` off; `/simplify` allowed |
| Q-3 | Claude Code Review (managed service) | per project on request, with a spend cap; `merge-pr` reads its check as extra input |
| Q-4 | Claude Approvals | no: `merge-pr` covers it, and private repos need a paid GitHub plan for the required check |
| Q-5 | What to adopt from ozstack | format rule and check, standards, brief slots, review loop, PR self-review record, merge ordering |
| Q-6 | Board: Kanzo, Notion, Excalidraw | research first; files stay the source of truth |
| Q-7 | Where this roadmap lives | here, plus one card per item (this file is the proposal) |
| Q-8 | Build a non-code workflow (video, marketing) now? | not yet: phase 1 skills avoid assuming repo/PR/CI; phase 5 waits for real examples |

## Phase 1: the skills layer

- **Skills work without Lonca's commands** (lonca#493): a fallback for each command, and a README section on using only the skills.
- **Skill format rule and CI check** (lonca#494): a prompt audit of our own skills; vendored skills stay as they are.
- **Ideas adopted from ozstack** (lonca#495):
  - engineering and signal standards;
  - Focus and risk slots in briefs;
  - review until nothing new is found;
  - the reviewer reads `REVIEW.md`.
- **Short rules from user feedback** (lonca#357):
  - removing an API field is a blocking finding;
  - stage files by path;
  - never rename an open PR's branch;
  - one PR per card;
  - a WSL2 note.

## Phase 2: the merge gate

- **User feedback** (lonca#357):
  - refuse on CHANGES_REQUESTED or unresolved review threads;
  - a `protected_branches` setting;
  - mobile and Firebase files count as high risk.
- **Merge ordering: independent, chained, blocked** (lonca#495).
- **Open gate items** (lonca#333, lonca#435).
- **Force-with-lease decision** (lonca#358).

## Phase 3: lanes, guards, board

- **User feedback on lanes** (lonca#357):
  - omp helper models come from the lane's own model family;
  - `lane --review`, a read-only mode.
- **Guard gaps** (lonca#445), one deny table (lonca#334), lane reliability (lonca#335).
- **Machine health check timer** (lonca#336).
- **Board as an optional adapter** (lonca#356): compare Kanzo, Notion and Excalidraw.

## Phase 3b: Excalidraw

- **A diagram skill with a live canvas** for system design, notes and presentations (lonca#496).

## Phase 4: later

- A deploy skill.
- Required skills by path.
- Conventional commits.
- Doctor and docs fixes (lonca#332).
- ozstack's audit skills (`arch-audit`, `state-machine-audit`, `prune-slop`).

## Phase 5: non-code work

- **Video, marketing and content jobs** (lonca#497): job folders instead of worktrees, checks against the brief, acceptance instead of merge.

## Dated

- **28 Nov:** lead and security-auditor models back to the default (lonca#411).
