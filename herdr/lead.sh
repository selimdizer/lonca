#!/bin/sh
# Herdr action: open a tab in this workspace running the lead, in the focused pane's folder.
set -eu
H=${HERDR_BIN_PATH:-herdr}
cwd=$(printf '%s' "${HERDR_PLUGIN_CONTEXT_JSON:-{\}}" | python3 -I -c 'import json,sys; c=json.load(sys.stdin); print(c.get("focused_pane_cwd") or "")')
[ -n "$cwd" ] || cwd=$HOME
if role=$("$HOME/lonca/bin/lonca-project" --claude-agent lead "$cwd"); then
  f=$("$HOME/lonca/bin/deja-scope" "$cwd")
else
  role=
fi
set -- --cwd "$cwd" --label lead --focus
[ -n "${HERDR_WORKSPACE_ID:-}" ] && set -- "$@" --workspace "$HERDR_WORKSPACE_ID"
pane=$("$H" tab create "$@" | python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(d["result"]["root_pane"]["pane_id"])')
[ -n "$pane" ] || { echo "lonca: could not read the new tab's pane id" >&2; exit 1; }
if [ -n "$role" ]; then
  "$H" pane run "$pane" env DEJA_POLICY_FILE="$f" ${LONCA_LEAD_CMD:-claude --agent $role}
else
  # This one session receives a startup notice. Ordinary sessions need no global hook.
  settings='{"hooks":{"SessionStart":[{"matcher":"startup","hooks":[{"type":"command","command":"\"$HOME/lonca/bin/lonca\" outside-session"}]}]}}'
  "$H" pane run "$pane" ${LONCA_LEAD_CMD:-claude} --settings "$settings" \
    --append-system-prompt "When asked to set this folder up for Lonca, follow $HOME/lonca/skills/lonca/SKILL.md."
fi
