#!/bin/sh
# Herdr pane: the lanes Lonca knows (from ~/.cache/ai-runs/**/*.lane.json), refreshed every 5 s; q closes it.
while :; do
  clear
  python3 -I "$HOME/lonca/bin/lanes"
  printf '\nq: close   (refreshes every 5 s)\n'
  k=$(sh -c 'stty -icanon -echo min 0 time 50 2>/dev/null; dd bs=1 count=1 2>/dev/null; stty icanon echo 2>/dev/null')
  [ "$k" = q ] && exit 0
done
