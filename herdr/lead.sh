#!/bin/sh
# Herdr action: open a tab in this workspace running the lead, in the focused pane's folder.
set -eu
H=${HERDR_BIN_PATH:-herdr}
cwd=$(printf '%s' "${HERDR_PLUGIN_CONTEXT_JSON:-{\}}" | python3 -I -c 'import json,sys; c=json.load(sys.stdin); print(c.get("focused_pane_cwd") or "")')
[ -n "$cwd" ] || cwd=$HOME
set -- --cwd "$cwd" --label lead --focus
[ -n "${HERDR_WORKSPACE_ID:-}" ] && set -- "$@" --workspace "$HERDR_WORKSPACE_ID"
pane=$("$H" tab create "$@" | python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(d["result"]["root_pane"]["pane_id"])')
[ -n "$pane" ] || { echo "lonca: could not read the new tab's pane id" >&2; exit 1; }
# deja limited to this folder's project from the lead's first second (deja-scope prints nothing outside a project)
f=$("$HOME/lonca/bin/deja-scope" "$cwd" 2>/dev/null || true)
"$H" pane run "$pane" ${f:+env DEJA_POLICY_FILE="$f"} ${LONCA_LEAD_CMD:-claude --agent lead}
