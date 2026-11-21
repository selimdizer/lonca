# Monthly maintenance
project: maintenance
- Skills: compare ~/lonca/skills/VENDOR.md with upstream; propose updates to the owner.
- Memory: propose stale, duplicated or unused notes in ~/ai-memory to delete or merge (nothing is deleted without the owner's OK).
- routing.md: propose changes from ~/lonca-local/model-log.jsonl and current benchmark data.
- Tools: kanzo, deja, herdr, omp, codex, claude versions; summarise their release notes.
- Past sessions: ~/lonca/bin/history-mine --days 31, then give the output to a Sonnet subagent with ~/lonca/config/history-candidates.prompt.md; show the owner the candidate decisions and save only the approved ones.
