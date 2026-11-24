#!/bin/sh
# Self-check: sh ~/lonca/shims/check.sh
S=$(dirname "$(readlink -f "$0")"); fail=0
# A regression should fail the test without forwarding a mutating test case to a real CLI.
stubs=$(mktemp -d)
trap 'rm -f "$stubs/git" "$stubs/gh" "$stubs/pkill" && rmdir "$stubs"' EXIT
for n in git gh pkill; do
  echo '#!/bin/sh' > "$stubs/$n"
  echo 'exit 0' >> "$stubs/$n"
  chmod +x "$stubs/$n"
done
t() { want=$1; shift; PATH="$S:$stubs:$PATH" "$@" >/dev/null 2>&1; rc=$?; got=ok; [ $rc -eq 126 ] && got=blocked; [ "$got" = "$want" ] || { echo "FAIL: $* -> $got (want $want)"; fail=1; }; }
export LONCA_LANE=1 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0="$HOME/lonca/git-hooks"
t blocked env GIT_CONFIG_COUNT=0 git status
t blocked env -u GIT_CONFIG_KEY_0 git status
t blocked env GIT_CONFIG_VALUE_0=fixture git status
t blocked env "GIT_CONFIG_PARAMETERS='core.hooksPath'='/nonexistent'" git push origin x
t blocked env "GIT_CONFIG_PARAMETERS='include.path'='fixture'" git status
t ok      env "GIT_CONFIG_PARAMETERS='user.name'='fixture'" git status
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
t blocked git config --local core.hooksPath "$HOME/lonca/git-hooks"
t blocked git config --local --remove-section core
t blocked git config rename-section core other
t blocked git config remove-section CORE
t blocked git config --local -e
t blocked git config edit
t blocked git config --edit
t blocked git config --local include.path fixture
t blocked git config set includeIf.gitdir:fixture.path fixture
t ok      git config --get include.path
t blocked lonca migrate
t blocked lonca init fixture
t blocked lonca remove fixture
t blocked pkill -f nothing-xyz
[ $fail -eq 0 ] && echo "all shim cases pass"; exit $fail
