"""Codex/omp Stop hook: ask once per turn whether something should be saved to ~/ai-memory.

Claude saves memories on its own; Codex tends not to, hence this nudge at the end of a turn.
"""
import json
import os
import sys

if os.environ.get("LONCA") == "0":
    sys.exit(0)

try:
    event = json.load(sys.stdin)
except ValueError:
    event = {}

if event.get("stop_hook_active"):  # already nudged this turn: let it stop
    sys.exit(0)

print(json.dumps({
    "decision": "block",
    "reason": (
        "Memory check, then stop: did this turn reveal something a future session needs "
        "(owner decision, project or server fact, correction, lesson) that is not already in ~/ai-memory? "
        "If yes, save it now following ~/ai-memory/README.md (group folder, one file, index line). "
        "If no, end without another reply."
    ),
}))
