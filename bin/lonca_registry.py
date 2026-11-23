"""Private project registrations and the resources created for their sessions."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

HOME = Path.home().resolve()
STATE = HOME / ".local/state/lonca"
REGISTRY = STATE / "projects"
BIN = Path(__file__).resolve().parent


def in_lane():
    guards = {(BIN.parent / "shims").resolve(), (HOME / "lonca/shims").resolve()}
    return bool(os.environ.get("LONCA_LANE")) or any(Path(p).resolve() in guards for p in os.get_exec_path())


def key(path):
    return hashlib.sha256(os.fsencode(path)).hexdigest()


def identity(path):
    st = path.stat()
    return [st.st_dev, st.st_ino]


def registered():
    result = {}
    for record in REGISTRY.glob("*.json"):
        data = json.loads(record.read_bytes())
        root = Path(data["root"])
        if root.resolve() == root and record.stem == key(root) and any(
            (root / marker).is_file() for marker in (".lonca.toml", "lonca.toml")
        ):
            result[root] = data
    return result


def names(projects):
    result = set()
    for root in projects:
        proc = subprocess.run([BIN / "lonca-project", root], capture_output=True, text=True,
                              env={k: v for k, v in os.environ.items() if k != "LONCA_PROJECT"})
        if proc.returncode == 0:
            result.add(proc.stdout.rstrip("\n").split("\t")[0])
    return result


def save(path, data):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(data, out)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def remember(root, kind, path):
    directory = STATE / "activity" / key(root) / kind
    save(directory / (key(path) + ".json"), {"path": str(path), "identity": identity(path)})


def resources(root, kind):
    for receipt in (STATE / "activity" / key(root) / kind).glob("*.json"):
        try:
            data = json.loads(receipt.read_bytes())
            path = Path(data["path"])
            if path.resolve() == path and receipt.stem == key(path) and data["identity"] == identity(path):
                yield path
        except (OSError, ValueError, KeyError):
            continue


def records(projects):
    for root, project in projects.items():
        for file in resources(root, "lane"):
            rec = json.loads(file.read_bytes())
            repo = Path(rec["repo"])
            entry = project["repos"].get(str(repo), {})
            if not (rec.get("project") == str(root) and entry.get("ready") and
                    file == Path(rec["result"] + ".lane.json") and repo.resolve() == repo and
                    (repo / ".git").is_dir() and identity(repo / ".git") == entry["identity"]):
                continue
            yield file, rec


def lane_worktree(rec):
    repo, wt = Path(rec["repo"]), Path(rec["worktree"])
    if rec.get("base") == "-":
        return False
    branch = rec["branch"]
    expected = HOME / ".herdr/worktrees" / f"{repo.parent.name}-{repo.name}" / branch.replace("/", "-")
    if not wt.is_dir() or wt.resolve() != wt or wt != expected or identity(wt) != rec.get("worktree_id"):
        return False
    git = subprocess.run(["git", "-C", wt, "rev-parse", "--path-format=absolute", "--git-common-dir",
                          "--symbolic-full-name", "HEAD"], capture_output=True, text=True)
    return git.returncode == 0 and git.stdout.splitlines() == [str(repo / ".git"), "refs/heads/" + branch]
