#!/bin/sh
# install.sh [--yes] [--timers] [--memory-review] [--sui] [--uninstall]
#   --yes             non-interactive (tools only)
#   --timers          enable project jobs, shared-memory commits and history indexing
#   --memory-review   also enable review of registered projects' recent messages
#   --sui             install Sui version selection and the Move LSP launcher
#   --uninstall       restore registered projects and remove the tools and legacy installation
set -eu
timers=0 review=0 sui=0 uninstall=0
for arg in "$@"; do
  case $arg in
    --yes) ;; --timers) timers=1 ;; --memory-review) review=1 ;; --sui) sui=1 ;; --uninstall) uninstall=1 ;;
    --agent-tmpdir) echo "Project sessions manage their own temporary directories." ;;
    --help|-h) sed -n '2,/^set -eu/p' "$0" | sed '$d; s/^# *//'; exit 0 ;;
    *) echo "unknown option: $arg (see --help)" >&2; exit 2 ;;
  esac
done
src=$(cd "$(dirname "$0")" && pwd -P)
L=$HOME/lonca
links() {
  for c in lonca lane lanes leads lonca-project deja-scope merge-pr merge-tier night-on kanzo-sync; do
    link "$L/bin/$c" "$HOME/.local/bin/$c"
  done
}
link() {
  if [ "$uninstall" = 1 ]; then
    if [ -L "$2" ] && [ "$(readlink "$2")" = "$1" ]; then rm "$2"; fi
  elif [ ! -L "$2" ] && [ ! -e "$2" ]; then
    mkdir -p "$(dirname "$2")"
    ln -s "$1" "$2"
  elif [ "$(readlink "$2" || true)" != "$1" ]; then
    echo "kept existing $2"
  fi
}
sui_links() {
  link "$L/extras/sui/sui-pick" "$HOME/lonca-local/shims/sui"
  link "$L/extras/sui/move-analyzer" "$HOME/.local/bin/lonca-move-analyzer"
}
units=$HOME/.config/systemd/user
if [ "$uninstall" = 1 ]; then
  python3 "$src/bin/lonca-uninstall"
  for unit in "$src"/config/systemd/*; do
    dst=$units/$(basename "$unit")
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$L/config/systemd/$(basename "$unit")" ]; then
      case "$dst" in *.timer) systemctl --user disable --now "$(basename "$dst")" 2>/dev/null || true ;; esac
      rm "$dst"
    fi
  done
  if [ "$(uname)" = Darwin ]; then python3 "$src/bin/launchd-units" uninstall; fi
  links
  sui_links
  if [ -L "$L" ] && [ "$(cd "$L" && pwd -P)" = "$src" ]; then rm "$L"; fi
  echo "Uninstalled Lonca. Memory, private extensions and backups are in your home directory."
  exit 0
fi
if [ ! -e "$L" ]; then ln -s "$src" "$L"; fi
[ "$(cd "$L" && pwd -P)" = "$src" ] || { echo "~/lonca points to another checkout" >&2; exit 1; }
for cmd in git python3; do command -v "$cmd" >/dev/null || { echo "missing: $cmd" >&2; exit 1; }; done
links
if [ "$sui" = 1 ]; then
  sui_links
  echo 'After lonca init, install Move LSP in the project with claude plugin install move-lsp@lonca --scope local'
fi
if [ ! -e "$HOME/ai-memory" ]; then
  cp -R "$L/memory-template" "$HOME/ai-memory"
  git -C "$HOME/ai-memory" init -q
  git -C "$HOME/ai-memory" add -A
  git -C "$HOME/ai-memory" -c user.name=Lonca -c user.email=lonca@localhost commit -qm 'memory: start from the Lonca template'
fi
if [ "$timers" = 1 ]; then
  skip=""
  command -v deja >/dev/null || skip="$skip deja-index"
  command -v hc >/dev/null || skip="$skip lane-watch"
  command -v kanzo >/dev/null || skip="$skip kanzo-sync kanzo-backup monthly-card"
  [ "$review" = 1 ] || skip="$skip memory-review"
  if [ "$(uname)" = Darwin ]; then
    python3 "$L/bin/launchd-units" install $skip
  elif command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
    for timer in "$L"/config/systemd/*.timer; do
      n=$(basename "$timer" .timer)
      case " $skip " in *" $n "*) continue ;; esac
      link "$L/config/systemd/$n.service" "$units/$n.service"
      link "$timer" "$units/$n.timer"
    done
    systemctl --user daemon-reload
    for timer in "$L"/config/systemd/*.timer; do
      n=$(basename "$timer" .timer)
      case " $skip " in *" $n "*) continue ;; esac
      [ "$(readlink "$units/$n.timer" || true)" = "$timer" ] && systemctl --user enable --now "$n.timer"
    done
  else
    echo 'No user timer manager available.' >&2
  fi
fi
echo 'Tools installed. Run lonca init <folder> to use the ~/lonca marketplace and guards in a project.'
