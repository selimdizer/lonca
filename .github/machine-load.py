#!/usr/bin/env python3
"""Machine load: one test slot at a time, merge-pr waiting out UNKNOWN mergeability, closed lanes' containers."""
import os, secrets, shutil, subprocess, sys, tempfile, time
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]


def fixture_env(home):
    env = dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               GIT_CONFIG_GLOBAL=str(home / ".gitconfig"), GIT_CONFIG_NOSYSTEM="1")
    env.pop("LONCA_LANE", None)
    return env


def test_slot(home):
    env = fixture_env(home)
    (home / ".config/lonca").mkdir(parents=True)
    (home / ".config/lonca/config.toml").write_text("test_slots = 1\n")   # the default comes from the config
    log = home / "order"
    slot = [str(SRC / "bin/test-slot"), "--"]
    a = subprocess.Popen(slot + ["sh", "-c", f"echo a-start >> {log}; sleep 2; echo a-end >> {log}"],
                         env=dict(env, LONCA_LANE="lane-a"), stderr=subprocess.PIPE, text=True)
    time.sleep(0.5)
    b = subprocess.Popen(slot + ["sh", "-c", f"echo b-start >> {log}; exit 7"], env=env, stderr=subprocess.PIPE, text=True)
    assert a.wait(30) == 0 and b.wait(30) == 7, "exit codes are passed through"
    waited = b.stderr.read()
    assert log.read_text().split() == ["a-start", "a-end", "b-start"], log.read_text()
    assert waited.count("waiting for a test slot") == 1 and "lane-a: sh -c" in waited, waited
    assert not a.stderr.read()
    # -n 2: both run at once
    both = [subprocess.Popen([str(SRC / "bin/test-slot"), "-n", "2", "--", "sleep", "1"], env=env, stderr=subprocess.PIPE)
            for _ in range(2)]
    assert all(p.wait(30) == 0 and not p.stderr.read() for p in both)
    assert subprocess.run([SRC / "bin/test-slot", "-n", "0", "--", "true"], env=env, capture_output=True).returncode
    # --max-wait: no slot in time -> exit 75 without running the command; the config sets the default
    hold = subprocess.Popen(slot + ["sleep", "30"], env=dict(env, LONCA_LANE="lane-h"))
    try:
        time.sleep(0.5)
        for extra, wait, cfg in ((["--max-wait", "2"], 2, ""), ([], 1, "test_slot_max_wait = 1\n")):
            (home / ".config/lonca/config.toml").write_text("test_slots = 1\n" + cfg)
            ran = home / "ran"
            t0 = time.monotonic()
            r = subprocess.run([SRC / "bin/test-slot", *extra, "--", "touch", ran], env=env, capture_output=True, text=True,
                               timeout=20)
            assert r.returncode == 75 and time.monotonic() - t0 < wait + 5 and not ran.exists(), (r.returncode, r.stderr)
            assert f"no test slot after {wait} s; held by: lane-h: sleep 30" in r.stderr, r.stderr
    finally:
        hold.kill(); hold.wait()
    (home / ".config/lonca/config.toml").write_text("test_slots = 1\n")
    # a test-slot inside a held slot runs at once (N=1 would wait for itself forever)
    nested = subprocess.run([SRC / "bin/test-slot", "--", SRC / "bin/test-slot", "--", "sh", "-c", "exit 5"],
                            env=env, capture_output=True, text=True, timeout=10)
    assert nested.returncode == 5 and not nested.stderr, nested.stderr
    # a slot file that is a symlink is refused, its target untouched
    slots = home / ".local/state/lonca/test-slots"
    (slots / "slot-0").unlink()
    victim = home / "victim"
    victim.write_text("keep")
    (slots / "slot-0").symlink_to(victim)
    r = subprocess.run([SRC / "bin/test-slot", "--", "true"], env=env, capture_output=True, text=True, timeout=10)
    assert r.returncode and "symlinks are refused" in r.stderr and victim.read_text() == "keep", r.stderr
    # every instruction names the path that exists in a lane (~/lonca/bin is not on a lane's PATH)
    for doc in ("agents/implementer.md", "agents/verifier.md", "skills/orchestrate/SKILL.md"):
        text = (SRC / doc).read_text()
        assert "test-slot" in text and text.count("test-slot") == text.count("~/lonca/bin/test-slot"), doc
    assert os.access(SRC / "bin/test-slot", os.X_OK)


def merge_pr_unknown(home):
    """merge-pr reads the PR again while GitHub says UNKNOWN, then judges it (stub gh, stub sleep)."""
    env = fixture_env(home)
    (home / "lonca").symlink_to(SRC, target_is_directory=True)
    stubs = home / "bin"
    stubs.mkdir()
    (stubs / "sleep").write_text("#!/bin/sh\nexit 0\n")
    (stubs / "gh").write_text(r'''#!/bin/sh
case "$*" in
  "pr view 7 --json baseRefName,changedFiles") echo '{"baseRefName":"main","changedFiles":1}' ;;
  "api --paginate repos/{owner}/{repo}/pulls/7/files --jq .[]") echo '{"filename":"README.md","additions":1,"deletions":0,"status":"modified"}' ;;
  "repo view --json nameWithOwner -q .nameWithOwner") echo owner/repo ;;
  "pr view 7 --json state,"*)
    n=$(( $(cat "$HOME/reads" 2>/dev/null || echo 0) + 1 )); echo $n > "$HOME/reads"
    m=UNKNOWN; [ $n -gt "$UNKNOWN_READS" ] && m=MERGEABLE
    printf '{"state":"OPEN","isDraft":false,"mergeable":"%s","title":"t","body":"b","statusCheckRollup":[{"name":"ci","conclusion":"FAILURE"}],"headRefOid":"abc1234def","baseRefName":"main","headRefName":"x"}' $m ;;
  *) echo "unexpected gh $*" >&2; exit 1 ;;
esac
''')
    for f in stubs.iterdir():
        f.chmod(0o755)
    repo = home / "repo"
    git = lambda *a: subprocess.run(["git", *a], env=env, check=True, capture_output=True)
    git("init", "-q", "-b", "main", repo)
    git("-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
    git("clone", "-q", "--bare", repo, home / "origin.git")   # merge-tier reads the settings from a fetched origin/main
    git("-C", repo, "remote", "add", "origin", home / "origin.git")
    (repo / ".lonca.toml").write_text('name = "fixture"\n')
    env["PATH"] = f"{stubs}:{env['PATH']}"
    for unknown, reads, why in ((2, 3, "checks not green"), (99, 6, "not mergeable: UNKNOWN")):
        (home / "reads").unlink(missing_ok=True)
        r = subprocess.run([SRC / "bin/merge-pr", "--dry-run", repo, "7", home / "run", "x"],
                           env=dict(env, UNKNOWN_READS=str(unknown)), capture_output=True, text=True)
        assert r.returncode == 1 and why in r.stderr, r.stderr
        assert (home / "reads").read_text().strip() == str(reads)


def docker(*a, **kw):
    return subprocess.run(["docker", *a], capture_output=True, text=True, **kw)


def lane_containers(home):
    """Through the docker shim, a lane's containers carry its name; closing it removes only those, volumes stay."""
    if docker("info").returncode:
        assert not os.environ.get("CI"), "docker is needed in CI"
        print("docker not running: container cleanup not checked")
        return
    tag = "ml-" + secrets.token_hex(4)
    closed, other = tag + "-a", tag + "-b"
    shim = str(SRC / "shims/docker")
    env = fixture_env(home)
    run = lambda lane, *a: subprocess.run([shim, *a], env=dict(env, LONCA_LANE=lane), capture_output=True, text=True, cwd=home)
    names = [closed + "-c", other + "-c", tag + "-free"]
    project = "lonca-lane-" + closed   # the reserved compose project the shim gives a lane
    volume = project + "_data"
    owners = home / "owners"   # someone's own stack whose project name equals the lane's name: never touched
    owners.mkdir()
    try:
        assert not run(closed, "run", "-d", "--name", names[0], "busybox", "sleep", "300").returncode
        assert not run(other, "run", "-d", "--name", names[1], "busybox", "sleep", "300").returncode
        assert not docker("run", "-d", "--name", names[2], "busybox", "sleep", "300").returncode
        (home / "compose.yaml").write_text("services:\n  s:\n    image: busybox\n    command: sleep 300\n"
                                           "    volumes: [data:/data]\nvolumes:\n  data: {}\n")
        up = run(closed, "compose", "up", "-d")
        assert not up.returncode, up.stderr
        (owners / "compose.yaml").write_text("services:\n  s:\n    image: busybox\n    command: sleep 300\n")
        assert not docker("compose", "-p", closed, "up", "-d", cwd=owners).returncode
        sys.path.insert(0, str(SRC / "bin"))
        from lonca_registry import remove_lane_containers
        assert remove_lane_containers({closed}, dry=True) and docker("inspect", names[0]).returncode == 0
        log = remove_lane_containers({closed})
        assert len(log) == 3 and all("closed lane " + closed in line for line in log), log
        assert any("kept volumes: " + volume in line for line in log), log
        left = docker("ps", "-a", "--format", "{{.Names}}").stdout.split()
        assert names[0] not in left and project + "-s-1" not in left, left
        assert names[1] in left and names[2] in left and closed + "-s-1" in left, left
        assert docker("volume", "inspect", volume).returncode == 0, "named volumes stay"
        assert docker("network", "inspect", project + "_default").returncode, "the lane's compose network removed"
        assert docker("network", "inspect", closed + "_default").returncode == 0, "the owner's network stays"
    finally:
        docker("rm", "-f", *names, project + "-s-1", closed + "-s-1")
        docker("volume", "rm", volume)
        docker("network", "rm", project + "_default", closed + "_default")


base = Path(tempfile.mkdtemp())
try:
    for t in (test_slot, merge_pr_unknown, lane_containers):
        home = base / t.__name__
        home.mkdir()
        t(home)
        print("ok", t.__name__)
finally:
    shutil.rmtree(base)
