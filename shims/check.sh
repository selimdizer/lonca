#!/bin/sh
# Self-check: sh ~/lonca/shims/check.sh
S=$(dirname "$(readlink -f "$0")"); fail=0
# A regression should fail the test without forwarding a mutating test case to a real CLI.
stubs=$(mktemp -d)
trap 'rm -f "$stubs/git" "$stubs/gh" "$stubs/pkill" "$stubs/docker" && rmdir "$stubs"' EXIT
for n in git gh pkill; do
  echo '#!/bin/sh' > "$stubs/$n"
  echo 'exit 0' >> "$stubs/$n"
  chmod +x "$stubs/$n"
done
printf '#!/bin/sh\necho "${COMPOSE_PROJECT_NAME:--}" "$@"\n' > "$stubs/docker"; chmod +x "$stubs/docker"
t() { want=$1; shift; PATH="$S:$stubs:$PATH" "$@" >/dev/null 2>&1; rc=$?; got=ok; [ $rc -eq 126 ] && got=blocked; [ "$got" = "$want" ] || { echo "FAIL: $* -> $got (want $want)"; fail=1; }; }
export LONCA_LANE=1 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath GIT_CONFIG_VALUE_0="$HOME/lonca/git-hooks"
t blocked env GIT_CONFIG_COUNT=0 git status
t blocked env -u GIT_CONFIG_KEY_0 git status
t blocked env GIT_CONFIG_VALUE_0=fixture git status
t blocked env "GIT_CONFIG_PARAMETERS='core.hooksPath'='/nonexistent'" git push origin x
t blocked env "GIT_CONFIG_PARAMETERS='include.path'='fixture'" git status
t ok      env "GIT_CONFIG_PARAMETERS='user.name'='fixture'" git status
t blocked env -u LONCA_LANE "GIT_CONFIG_PARAMETERS='core.hooksPath'='/nonexistent'" git push origin x
t blocked git commit -m x --no-verify
t blocked git commit --no-veri -m x
t blocked git -C . commit -n -m x
t blocked git commit -anm x
t blocked git merge feature --no-verify
t blocked git push origin x --no-verify
t ok      git commit -m -n
t ok      git commit -uno -m x
t ok      git commit -am "add notes"
t ok      git log -n 3
t ok      git commit -m x -- -n
t ok      git merge --no-verify-signatures feature
t ok      git pull --no-verify-signatures origin x
t blocked git pull --no-verify origin x
t blocked git -c alias.ci=commit ci --no-verify
t blocked git --config-env=alias.ci=FIXTURE ci -m x
t blocked env "GIT_CONFIG_PARAMETERS='alias.ci'='commit --no-verify'" git ci -m x
t blocked git config alias.x "commit --no-verify"
t blocked git config --global alias.x commit
t ok      git config --get alias.x
t blocked git --attr-source HEAD commit --no-verify -m x
t blocked git --attr-source=HEAD commit -n -m x
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
t blocked lonca questions answer Q-1 fixture
t blocked lonca questions drop Q-1 fixture
t blocked pkill -f nothing-xyz
# docker in a lane: run/create get the lane's label, compose gets the lane as its project; outside lanes nothing changes
d() { want=$1; shift; got=$(PATH="$S:$stubs:$PATH" "$@" 2>&1); [ "$got" = "$want" ] || { echo "FAIL: $* -> '$got' (want '$want')"; fail=1; }; }
d "- run --label lonca.lane=ml-x --rm -e A=1 busybox true" env LONCA_LANE=ml-x docker run --rm -e A=1 busybox true
d "- --context c container create --label lonca.lane=ml-x busybox" env LONCA_LANE=ml-x docker --context c container create busybox
d "- -H unix:///x run --label lonca.lane=ml-x busybox run" env LONCA_LANE=ml-x docker -H unix:///x run busybox run
d "- ps -a --filter name=run" env LONCA_LANE=ml-x docker ps -a --filter name=run
d "lonca-lane-ml-x compose up -d" env LONCA_LANE=ml-x docker compose up -d
d "mine compose up -d" env LONCA_LANE=ml-x COMPOSE_PROJECT_NAME=mine docker compose up -d
d "- run busybox" env LONCA_LANE=1 docker run busybox
d "- run busybox" env -u LONCA_LANE docker run busybox
d "- compose up" env -u LONCA_LANE docker compose up
[ $fail -eq 0 ] && echo "all shim cases pass"; exit $fail
