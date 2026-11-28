# Roadmap

Updated 28 Nov 2026. What the maintainer's own agent work on Lonca does next, in order; that work starts only after it is listed here. Outside contributions go through [CONTRIBUTING.md](CONTRIBUTING.md). Items name their board card (`lonca#N`) where one exists. Open decisions carry their id (`Q-n`) in the owner's questions ledger, which lives on the owner's machine (`lonca questions`) and is not part of the repo.

## Phase 0: decisions (taken 28 Nov 2026)

| id | question | decision |
|---|---|---|
| Q-1 | Split into **Lonca skills** (works alone) and **Lonca runtime** (`lane`, `merge-pr`, guards, Herdr) | yes |
| Q-2 | Claude Code's built-in commands in Lonca projects | nothing turned on or off; Lonca's own skills stay the flow |
| Q-3 | Claude Code Review (managed service) | not added |
| Q-4 | Claude Approvals | not added: `merge-pr` covers it |
| Q-5 | What to adopt from [ozstack](https://github.com/selimozten/ozstack) (MIT) | what helps our skills, credited: standards, brief slots, review loop, PR self-review record, merge ordering, "Done when" endings with a format check (no hard line cap) |
| Q-6 | Board | every user picks one: files stay the source of truth, boards are adapters (Kanzo now, Obsidian next, Notion on request); Excalidraw stays a drawing skill |
| Q-7 | Where this roadmap lives | here; items name their card where one exists, on whichever board the user runs |
| Q-8 | Non-code workflow (video, marketing) | phase 1 skills stop assuming repo/PR/CI; phase 5 waits for 2-3 real jobs |
| Q-9 | Let the owner merge a PR a check refused | an owner-only override, CI included (lonca#552) |

## Phase 1: the skills layer

- **Skills work without Lonca's commands** (lonca#493): a fallback for each command, and a README section on using only the skills.
- **Skill format rule and CI check** (lonca#494): every stage ends on "Done when", a CI check for the format and frontmatter (no hard line cap), and a prompt audit of our own skills; vendored skills stay as they are.
- **Ideas adopted from ozstack** (lonca#495):
  - engineering and signal standards;
  - Focus and risk slots in briefs;
  - review until nothing new is found;
  - a self-review record in the PR;
  - the reviewer reads `REVIEW.md`;
  - credit to ozstack in the README and `skills/VENDOR.md`.
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
- **Owner override and English approval words** (lonca#552): `override <code>` merges a PR a check refused, CI included; the owner's code only, never auto or night mode; each override is recorded with what failed (PR comment, run folder, merge log); `yes <code>` and `start <code>` replace the Turkish examples (also the approval-words part of lonca#333).
- **Merge ordering: independent, chained, blocked** (lonca#495).
- **Open gate items** (lonca#333, lonca#435).
- **Force-with-lease decision** (lonca#358).

## Phase 3: lanes, guards, board

- **User feedback on lanes** (lonca#357):
  - omp helper models come from the lane's own model family;
  - `lane --review`, a read-only mode.
- **Guard gaps** (lonca#445), one deny table (lonca#334), lane reliability (lonca#335).
- **Machine health check timer** (lonca#336).
- **Boards as adapters** (lonca#356): one small contract over the files; Kanzo stays, an Obsidian vault next, Notion when a user asks (cloud: not for client projects).

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
