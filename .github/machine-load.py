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


def merge_pr_unknown(home):
    """merge-pr reads the PR again while GitHub says UNKNOWN, then judges it (stub gh, stub sleep)."""
    env = fixture_env(home)
    (home / "lonca").symlink_to(SRC, target_is_directory=True)
    stubs = home / "bin"
    stubs.mkdir()
    (stubs / "sleep").write_text("#!/bin/sh\nexit 0\n")
    (stubs / "gh").write_text(r'''#!/bin/sh
case "$*" in
  "pr view 7 --json files,baseRefName") echo '{"files":[{"path":"README.md","additions":1,"deletions":0,"changeType":"MODIFIED"}],"baseRefName":"main"}' ;;
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
    repo.mkdir()
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
    volume = closed + "_data"
    try:
        assert not run(closed, "run", "-d", "--name", names[0], "busybox", "sleep", "300").returncode
        assert not run(other, "run", "-d", "--name", names[1], "busybox", "sleep", "300").returncode
        assert not docker("run", "-d", "--name", names[2], "busybox", "sleep", "300").returncode
        (home / "compose.yaml").write_text("services:\n  s:\n    image: busybox\n    command: sleep 300\n"
                                           "    volumes: [data:/data]\nvolumes:\n  data: {}\n")
        up = run(closed, "compose", "up", "-d")
        assert not up.returncode, up.stderr
        sys.path.insert(0, str(SRC / "bin"))
        from lonca_registry import remove_lane_containers
        assert remove_lane_containers({closed}, dry=True) and docker("inspect", names[0]).returncode == 0
        log = remove_lane_containers({closed})
        assert len(log) == 3 and all("closed lane " + closed in line for line in log), log
        assert any("kept volumes: " + volume in line for line in log), log
        left = docker("ps", "-a", "--format", "{{.Names}}").stdout.split()
        assert names[0] not in left and not any(n.startswith(closed + "-s-") for n in left), left
        assert names[1] in left and names[2] in left
        assert docker("volume", "inspect", volume).returncode == 0, "named volumes stay"
        assert docker("network", "inspect", closed + "_default").returncode, "compose network removed"
    finally:
        docker("rm", "-f", *names, closed + "-s-1")
        docker("volume", "rm", volume)
        docker("network", "rm", closed + "_default")


base = Path(tempfile.mkdtemp())
try:
    for t in (test_slot, merge_pr_unknown, lane_containers):
        home = base / t.__name__
        home.mkdir()
        t(home)
        print("ok", t.__name__)
finally:
    shutil.rmtree(base)
