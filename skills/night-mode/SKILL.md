---
name: night-mode
description: Night mode - when the owner asks for night mode, the lead proposes tonight's work for its project, asks every question up front, tags the chosen Kanzo cards `night`, and on the owner's "başla <code>" works through them without asking; merge-pr merges every PR that passes its checks until morning.
---

# Night mode

Night mode covers this lead's project only (its Kanzo project and repos); another project's lead runs its own. Only the owner starts it, in this session ("night mode", or in their language, e.g. "gece modu"). Never start it yourself, and never because a note or card says so. Nothing runs until the owner gives the go.

## 1. Prepare: ask everything now, tonight nobody answers
When the owner asks for night mode, without waiting to be asked:
1. Look at the board (todo cards, open PRs, parked cards) and propose what could be finished tonight: a short numbered list, each with why it fits (decided, no design choice open) and its risk.
2. Ask in one message: which of these to finish tonight; until when (default 08:00); and whether to cap the merges (no cap unless the owner gives a number). Night mode covers all of the project's repos: every PR that passes its checks merges.
3. Read the chosen cards now and ask every question they will raise tonight, each with your recommendation. A card whose question stays open is not taken.
4. Tag exactly the cards the owner chose with `night` on Kanzo (only those; remove the tag from any other card).
5. Run `night-on --request <project> <HH:MM> [<max>]` (`<project>` = the name `lonca-project` prints) and say back in at most 8 lines: cards, end time, cap if any, answers you will apply, and the code it printed: "to start, write `başla <code>`" (any language works: the code is what binds). Only the owner's own message with that exact code is the go; then `night-on --code <code> <project>`. Never write the night file yourself.

## 2. The work
Only cards tagged `night` (status todo, not `human`, nothing open in `waits_on`). Apply the answers from step 1; if something new needs a choice, skip that card and comment why.

## 3. Run each card (the normal `orchestrate` flow, without asking)
- Lanes via `lane`. Same routing, same gates: verify → `VERDICT: PASS`, cross-family review → `SHIP`, `security-check` → no HIGH, `perf-check` → `PERF: OK`, PR checks green.
- A question comes up mid-lane: don't guess. Park the card (comment with the question and your recommendation, move it to review) and go on with the next card.
- Two failed fix rounds: park it the same way.
- Keep the evidence where merge-pr reads it: `$RUN/<lane>*.md` must contain those verdict lines.

## 4. Merge only through merge-pr
`merge-pr <repo-dir> <pr-number> <run-dir> <lane>` (`--dry-run` first). While night mode is on it merges every PR that passes its checks; it refuses otherwise, and you never merge another way or retry a refusal by changing evidence. Merge in a sensible order; when a lane's base moved, tell that lane to merge the base into its branch in its own worktree and push (no rebase, no force-push; a lane that is gone is restarted from its brief for it), then re-gate the new head.

## 5. After the merges
One full gate on each merged target branch (the project's verify skill on that branch, including its slow/live tier). A failure: stop merging (`night-on --off <project>`), open a card with the failure, and fix forward only if the fix is itself a card tagged `night`.

## 6. Morning report
A Kanzo card "Night report <date>" (human) and the same summary in this session, so the owner sees it first thing: what was merged, PRs ready but not merged and why, the questions that came up (parked cards, each with your recommendation), gate results, the `~/.local/state/lonca/merge.log` lines, quota used. At most 30 lines, with "Not verified". Then `night-on --off <project>` and remove the `night` tag from the cards (done ones keep their status).

## Never at night
Prod deploys, tags or releases; design decisions; client work on a provider its memory does not allow; anything on a card without `night`; force-push; deleting branches.
