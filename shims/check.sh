#!/bin/sh
# Self-check: sh ~/lonca/shims/check.sh
S=$(dirname "$(readlink -f "$0")"); fail=0
t() { want=$1; shift; PATH="$S:$PATH" "$@" >/dev/null 2>&1; rc=$?; got=ok; [ $rc -eq 126 ] && got=blocked; [ "$got" = "$want" ] || { echo "FAIL: $* -> $got (want $want)"; fail=1; }; }
t blocked gh pr merge 3 --squash
t blocked gh api repos/a/b/pulls/3/merge -X PUT
t ok      gh --version
t blocked git push --force origin x
t blocked git push origin x --force
t blocked git reset --hard
t blocked git clean -fdx
t blocked git branch -D x
t blocked git push origin +x
t blocked git push origin main
t blocked git push origin HEAD:main
t blocked git push -u origin master
t blocked git push origin --delete x
t blocked git push origin :x
t blocked git -c core.hooksPath=/dev/null push origin x
t blocked git -C . config --local --unset core.hooksPath
t blocked git config --unset-all core.hookspath
t ok      git config --local --get core.hooksPath
t ok      git --version
t ok      git status --short
t blocked lonca remove fixture
t blocked pkill -f nothing-xyz
[ $fail -eq 0 ] && echo "all shim cases pass"; exit $fail
