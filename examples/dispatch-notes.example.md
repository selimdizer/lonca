> An example from one setup (2026-11); models and plans will differ. Put your own notes in `~/lonca-local/` or your memory's `setup/` group.

# Dispatch notes from one setup

## Plans and providers
- opencode-go (a flat monthly plan): only small models; big ones use up the limit fast. `deepseek-v4.1-flash` first (cheap read lanes and first-pass reviews); `hy4-flash-free` (free) only for non-client, non-sensitive code, since free models may train on the data.
- z.ai: `zai/glm-5.3-flash` for cheap mechanical work through omp.
- omp with no `--model`: Opus 5.5 via Copilot, thinking medium (`config/omp-config.yml`).

## Copilot-only client work
- `lane` runs `omp:github-copilot/<model>` with `--smol github-copilot/claude-sonnet-5.5 --slow github-copilot/claude-opus-5.5`, so omp's helpers stay on Copilot too (its default helpers are DeepSeek/GLM).

## Example commands
```sh
lane --read <repo-dir> <short-name> omp:opencode-go/deepseek-v4.1-flash $RUN/<name>.brief.md $RUN/<name>.md
lane <repo-dir> review/<lane> omp:opencode-go/deepseek-v4.1-flash $RUN/<lane>.review-brief.md $RUN/<lane>.review.md <pr-branch>
codex exec -C $WT --dangerously-bypass-approvals-and-sandbox --disable apps -m gpt-6.2-sol -c model_reasoning_effort=xhigh --ephemeral -o $RUN/$L.md - < brief.md
codex exec -C $WT -s read-only --disable apps -m gpt-6.2-astra -c model_reasoning_effort=high --ephemeral -o $RUN/$L.review.md - < review-brief.md
```

## Tested
- 2026-11-20: Claude headless with `bypassPermissions` still applies the deny rules and the pre-push hook.
- 2026-11-20: omp on github-copilot (claude-opus-5.5, claude-sonnet-5.5), opencode-go (deepseek-v4.1-flash), zai (glm-5.3); kanzo + chrome-devtools MCP work.
- 2026-11-21: a read lane on deepseek-v4.1-flash answered with file:line in 14 s, wrote the report, DONE arrived.
