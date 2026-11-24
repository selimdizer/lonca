"""Private project registrations and the resources created for their sessions."""
import hashlib
import json
import os
import secrets
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
    receipt = {"path": str(path), "identity": identity(path)}
    if kind == "temp":
        # A deleted directory's inode may be reused by an unrelated replacement.
        receipt["token"] = secrets.token_hex(16)
        with (path / ".lonca-temp-owner").open("x") as marker:
            marker.write(receipt["token"])
    save(directory / (key(path) + ".json"), receipt)


def forget_activity(root):
    directory = STATE / "activity" / key(root)
    if directory.resolve() != directory:
        raise ValueError(f"refusing symlink: {directory}")
    for kind in ("lane", "temp", "watch", "backup"):
        subdir = directory / kind
        if not subdir.is_dir() or subdir.is_symlink():
            continue
        for file in subdir.glob("*.json"):
            if len(file.stem) == 64 and all(c in "0123456789abcdef" for c in file.stem) and not file.is_symlink():
                file.unlink()
        if not any(subdir.iterdir()):
            subdir.rmdir()
    if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()


def forget_resource(root, kind, path):
    (STATE / "activity" / key(root) / kind / (key(path) + ".json")).unlink(missing_ok=True)


def resources(root, kind):
    for receipt in (STATE / "activity" / key(root) / kind).glob("*.json"):
        try:
            data = json.loads(receipt.read_bytes())
            path = Path(data["path"])
            if path.resolve() == path and receipt.stem == key(path) and data["identity"] == identity(path):
                if kind == "temp":
                    marker = path / ".lonca-temp-owner"
                    if marker.is_symlink() or not marker.is_file() or marker.read_text() != data["token"]:
                        continue
                yield path
        except (OSError, ValueError, KeyError):
            continue


def records(projects):
    for root, project in projects.items():
        name = None
        for file in resources(root, "lane"):
            try:
                rec = json.loads(file.read_bytes())
                # Fields every record reader uses; anything else is not a lane record.
                if not all(isinstance(rec[k], str) for k in ("name", "worktree", "result", "repo", "project", "temp")):
                    continue
                repo = Path(rec["repo"])
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if rec["project"] != str(root) and rec.get("base") == "-" and file == Path(rec["result"] + ".lane.json"):
                # A read lane on a temp copy whose marker carries this project's name counts as this project's.
                name = names([root]) if name is None else name
                copy = Path(rec["project"])
                if copy.resolve() == copy and repo.resolve() == repo and repo.is_relative_to(copy) and names([copy]) == name:
                    yield file, {**rec, "project": str(root)}
                continue
            entry = project["repos"].get(str(repo), {})
            if not (rec["project"] == str(root) and entry.get("ready") and
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
