#!/usr/bin/env python3
"""merge-pr end to end with a stub gh and hc on throwaway git repos: lanes are refused, the code is bound to the
project's batch and the base, the base's settings are fetched (fail closed), a crashed lock holder does not block,
an expired night asks, the night cap counts reserved merges, only a worktree at the merged head is removed, and the
tier reads every page of the PR's files and rates a short list high. Fixture checks run with a stub gh and hc."""
import datetime, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
GH = r'''#!/bin/sh
pr=$3; [ "$1" = api ] && pr=$(echo "$*" | sed 's|.*/pulls/\([0-9]*\)/files.*|\1|')
base=$(cat "$HOME/base_$pr" 2>/dev/null || echo main)
case "$*" in
  "repo view --json nameWithOwner -q .nameWithOwner") echo owner/repo ;;
  "repo view --json mergeCommitAllowed,"*) echo merge ;;
  "pr view $pr --json baseRefName,changedFiles")
    n=$(cat "$HOME/changed_$pr" 2>/dev/null || wc -l < "$HOME/files_$pr")
    echo "{\"baseRefName\":\"$base\",\"changedFiles\":$n}" ;;
  "pr view $pr --json state,"*)
    printf '{"state":"OPEN","isDraft":false,"mergeable":"MERGEABLE","title":"t","body":"b","statusCheckRollup":[{"name":"ci","conclusion":"SUCCESS"}],"headRefOid":"%s","baseRefName":"%s","headRefName":"lane-%s"}' "$(cat "$HOME/head_$pr")" "$base" "$pr" ;;
  api*"repos/{owner}/{repo}/pulls/$pr/files"*)   # GitHub sends 100 files per page; later pages only with --paginate
    case " $* " in *" --paginate "*) cat "$HOME/files_$pr" ;; *) head -100 "$HOME/files_$pr" ;; esac ;;
  "pr merge $pr --merge --match-head-commit "*) echo "$pr" >> "$HOME/merged" ;;
  *) echo "unexpected gh $*" >&2; exit 1 ;;
esac
'''
now = lambda: datetime.datetime.now().astimezone().isoformat(timespec="seconds")
DOC = '{"filename":"README.md","additions":1,"deletions":0,"status":"modified"}\n'


def main(home):
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               GIT_CONFIG_GLOBAL=str(home / ".gitconfig"), GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    env.pop("LONCA_LANE", None)
    (home / "lonca").symlink_to(SRC, target_is_directory=True)
    stubs = home / "stubs"
    stubs.mkdir()
    (stubs / "gh").write_text(GH)
    (stubs / "hc").write_text('#!/bin/sh\ncase $1 in ls) cat "$HOME/terminals.json" 2>/dev/null || echo \'{"terminals":[]}\' ;;\n'
                              '  kill) echo "$2" >> "$HOME/killed" ;; esac\n')
    (stubs / "sleep").write_text("#!/bin/sh\nexit 0\n")
    for f in stubs.iterdir():
        f.chmod(0o755)
    env["PATH"] = f"{stubs}:{env['PATH']}"
    git = lambda *a, cwd=None: subprocess.run(["git", *a], env=env, cwd=cwd, check=True, capture_output=True,
                                              text=True).stdout.strip()
    repo, run, A, N = home / "repo", home / "run", home / ".local/state/lonca/approvals", home / ".cache/ai-runs/night"
    log = home / ".local/state/lonca/merge.log"
    git("init", "-q", "-b", "main", repo)
    (repo / ".lonca.toml").write_text('name = "fixture"\n')
    git("add", ".lonca.toml", cwd=repo)
    git("commit", "-q", "-m", "base", cwd=repo)
    git("clone", "-q", "--bare", repo, home / "origin.git")
    git("remote", "add", "origin", home / "origin.git", cwd=repo)
    run.mkdir()

    def pr(n, worktree=True):
        """PR n: branch lane-n with one commit (in a lane worktree when asked), evidence for its head, a docs diff."""
        wt = home / f".herdr/worktrees/lane-{n}"
        if worktree:
            git("worktree", "add", "-q", "-b", f"lane-{n}", wt, cwd=repo)
            (wt / f"f{n}.md").write_text("x\n")
            git("add", ".", cwd=wt)
            git("commit", "-q", "-m", f"pr {n}", cwd=wt)
            head = git("rev-parse", "HEAD", cwd=wt)
        else:
            head = f"{n:07d}" * 6
        (home / f"head_{n}").write_text(head)
        (home / f"files_{n}").write_text(DOC)
        for kind, text in (("verify", "VERDICT: PASS\nHEAD: {h}\nPERF: OK\nHEAD: {h}\n"),
                           ("review", "VERDICT: SHIP\nHEAD: {h}\n"), ("security", "SECURITY: CLEAN\nHEAD: {h}\n")):
            (run / f"x{n}.{kind}.md").write_text(text.format(h=head))
        return head, wt

    def merge(n, *opts, lane_env=None, at=None):
        return subprocess.run([SRC / "bin/merge-pr", *opts, at or repo, str(n), run, f"x{n}"], env=lane_env or env,
                              capture_output=True, text=True, timeout=60)

    merged = lambda: (home / "merged").read_text().split() if (home / "merged").exists() else []

    # A7: a lane never merges
    pr(1, worktree=False)
    r = merge(1, lane_env=dict(env, LONCA_LANE="fixture-x"))
    assert r.returncode == 1 and "refused in lane" in r.stderr, r.stderr

    # A3: every page of the PR's files counts (a high-risk file after the first 100)
    (home / "files_1").write_text(DOC * 120 + '{"filename":".github/workflows/ci.yml","additions":1,"deletions":0,"status":"modified"}\n')
    r = merge(1, "--dry-run")
    assert r.returncode == 0 and "tier high (.github/workflows/ci.yml" in r.stdout, r.stdout + r.stderr
    (home / "files_1").write_text(DOC)
    # the files API stops at 3000: fewer files than the PR has is high, never a guess
    (home / "changed_1").write_text("3001")
    r = merge(1, "--dry-run")
    assert r.returncode == 0 and "tier high" in r.stdout and "1 of the PR's 3001" in r.stdout, r.stdout + r.stderr
    (home / "changed_1").unlink()

    # B2: the base's settings come from a fetched origin/<base>; when that fails, refuse (no looser fallback)
    (home / "base_1").write_text("gone")
    r = merge(1, "--dry-run")
    assert r.returncode == 1 and "cannot fetch origin/gone" in r.stderr, r.stderr
    (home / "base_1").unlink()
    (repo / ".lonca.toml").write_text('name = "fixture"\nauto_merge = "all"\n')   # the local copy is not the base's
    r = merge(1, "--dry-run")
    assert r.returncode == 0 and "approval: ask" in r.stdout, r.stdout + r.stderr
    # ... also when the repo argument is a lane worktree with its own working-tree .lonca.toml
    lwt = home / ".herdr/worktrees/settings"
    git("worktree", "add", "-q", "-b", "settings", lwt, cwd=repo)
    (lwt / ".lonca.toml").write_text('name = "fixture"\nauto_merge = "all"\n')
    r = merge(1, "--dry-run", at=lwt)
    assert r.returncode == 0 and "approval: ask" in r.stdout, r.stdout + r.stderr
    (repo / ".lonca.toml").write_text('name = "fixture"\n')
    # a repo without origin is refused with a clear reason
    git("remote", "rename", "origin", "upstream", cwd=repo)
    r = merge(1, "--dry-run")
    assert r.returncode == 1 and "has no origin remote" in r.stderr, r.stderr
    git("remote", "rename", "upstream", "origin", cwd=repo)

    # A8 + C4: one code per project batch (another project's fresh batch is not reused), listing every PR it covers
    A.mkdir(parents=True)
    (A / ".batch").write_text("111\n")
    (A / ".batch_other").write_text("111\n")
    pr(2, worktree=False)
    r1, r2 = merge(1), merge(2)
    assert r1.returncode == 3 and r2.returncode == 3, r1.stderr + r2.stderr
    code = re.search(r"evet (\w+)", r1.stdout).group(1)
    assert code != "111" and f"evet {code}" in r2.stdout and "any language" in r2.stdout, r2.stdout
    assert "covers: owner_repo_1 owner_repo_2" in r2.stdout, r2.stdout
    # the code is bound to the base the owner saw
    (A / "owner_repo_1").write_text((A / "owner_repo_1").read_text().replace(" main", " release"))
    r = merge(1, "--code", code)
    assert r.returncode == 1 and "base is now main" in r.stderr and not merged(), r.stderr
    assert merge(1).returncode == 3
    # a key file carrying the code but outside the batch the owner saw is refused
    pr(6, worktree=False)
    (A / "owner_repo_6").write_text(f"{code} {(home / 'head_6').read_text()} {int(time.time())} main\n")
    r = merge(6, "--code", code)
    assert r.returncode == 1 and "not in the batch the owner saw" in r.stderr and not merged(), r.stderr

    # B3: a crashed lock holder does not block: the lock goes with its process
    code = re.search(r"evet (\w+)", merge(1).stdout).group(1)
    holder = subprocess.Popen([sys.executable, "-c", f"""import fcntl, time
f = open({str(N / '.merge.flock')!r}, "a"); fcntl.flock(f, fcntl.LOCK_EX); print("held", flush=True); time.sleep(30)"""],
                              stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "held"
    waiting = subprocess.Popen([SRC / "bin/merge-pr", "--code", code, repo, "1", run, "x1"], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)
    assert waiting.poll() is None and not merged(), "merged while another merge held the lock"
    holder.kill(); holder.wait()
    out, err = waiting.communicate(timeout=30)
    assert waiting.returncode == 0 and merged() == ["1"], out + err
    assert not (A / "owner_repo_1").exists()
    # the first --code run closed the batch: a PR asked now gets a new code; LONCA_PROJECT does not pick the batch
    r = merge(6, lane_env=dict(env, LONCA_PROJECT="other"))
    assert r.returncode == 3 and f"evet {code} " not in r.stdout and "covers: owner_repo_6 " in r.stdout, r.stdout
    assert (A / ".batch_fixture").exists() and (A / ".batch_other").read_text() == "111\n"

    # B1: only a lane worktree at the merged head is removed (with its branch); one with an unpushed commit stays
    head3, wt3 = pr(3)
    head4, wt4 = pr(4)
    (wt4 / "local.md").write_text("not pushed\n")
    git("add", ".", cwd=wt4)
    git("commit", "-q", "-m", "local only", cwd=wt4)
    (home / "terminals.json").write_text(json.dumps({"terminals": [
        {"address": "t3", "cwd": str(wt3)}, {"address": "t3sub", "cwd": f"{wt3}/sub"},
        {"address": "t30", "cwd": f"{wt3}0"}, {"address": "t4", "cwd": str(wt4)}]}))
    for n in (3, 4):
        code = re.search(r"evet (\w+)", merge(n).stdout).group(1)
        r = merge(n, "--code", code)
        assert r.returncode == 0, r.stderr
    assert not wt3.exists() and not git("branch", "--list", "lane-3", cwd=repo), "merged lane left behind"
    assert wt4.exists() and git("branch", "--list", "lane-4", cwd=repo), "unpushed commits removed"
    assert "not the merged head" in r.stdout, r.stdout
    # terminals closed only for the removed worktree and below it: not lane-30's, not the kept lane-4's
    assert (home / "killed").read_text().split() == ["t3", "t3sub"], (home / "killed").read_text()

    # B3: an expired night asks the owner instead of refusing
    night = N / "fixture.json"
    night.write_text(json.dumps({"until": "2000-01-01T00:00:00+00:00", "max_merges": "unlimited"}))
    pr(5, worktree=False)
    r = merge(5)
    assert r.returncode == 3 and "evet" in r.stdout and "asking the owner" in r.stderr, r.stdout + r.stderr
    # the night cap counts a merge reserved before a crash; a failed merge gives its place back
    night.write_text(json.dumps({"until": "2999-01-01T00:00:00+00:00", "max_merges": 1}))
    os.utime(night, (time.time() - 10,) * 2)
    with open(log, "a") as f:
        f.write(f"{now()} merging [night:fixture] {repo} #9\n")
    r = merge(5)
    assert r.returncode == 3 and "past its end time or its cap" in r.stderr, r.stdout + r.stderr
    with open(log, "a") as f:
        f.write(f"{now()} merge-failed [night:fixture] {repo} #9\n")
    r = merge(5)
    assert r.returncode == 0 and "night" in r.stdout and merged()[-1] == "5", r.stdout + r.stderr
    assert f"merging [night:fixture] {repo} #5" in log.read_text()


base = Path(tempfile.mkdtemp())
try:
    main(base)
    print("ok merge gate")
finally:
    shutil.rmtree(base)
