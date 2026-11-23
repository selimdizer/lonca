#!/usr/bin/env python3
"""Live local smoke test for omp's extension-package MCP discovery. No model turn."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

SRC = Path(__file__).resolve().parents[1]
SERVER = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
for line in sys.stdin:
    msg = json.loads(line)
    if "id" not in msg:
        continue
    method = msg["method"]
    result = {}
    if method == "initialize":
        result = {"protocolVersion": msg["params"]["protocolVersion"], "capabilities": {"tools": {}},
                  "serverInfo": {"name": Path(sys.argv[0]).name, "version": "1"}}
    if method == "tools/list":
        Path(os.environ["HOME"], Path(sys.argv[0]).name + ".seen").write_text(os.environ.get("DEJA_POLICY_FILE", ""))
        result = {"tools": []}
    print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
"""


def main():
    exe = shutil.which("omp")
    if not exe:
        raise SystemExit("requires omp")
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        repo = home / "project"
        repo.mkdir()
        for server in ("kanzo", "deja"):
            path = home / server
            path.write_text(SERVER)
            path.chmod(0o755)
        policy = home / "project-policy.json"
        policy.write_text('{"ignore":["*"]}')
        env = dict(HOME=tmp, PATH=tmp + ":/usr/local/bin:/usr/bin:/bin", TMPDIR=tmp, TERM="dumb",
                   XDG_RUNTIME_DIR=tmp, XDG_CONFIG_HOME=str(home / ".config"), DEJA_POLICY_FILE=str(policy),
                   OMP_MCP_STARTUP_TIMEOUT_MS="3000", OMP_MCP_TIMEOUT_MS="3000")
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen([exe, "--mode", "rpc", "--no-session", "--offline", "--no-lsp",
                                     "--extension", SRC / "config/omp-lane"], cwd=repo, env=env,
                                    stdin=subprocess.PIPE, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 18
                while time.monotonic() < deadline and proc.poll() is None:
                    if all((home / (s + ".seen")).exists() for s in ("kanzo", "deja")):
                        break
                    time.sleep(0.1)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if not all((home / (s + ".seen")).exists() for s in ("kanzo", "deja")):
                log.seek(0)
                raise SystemExit("MCP discovery failed: " + log.read(2500).decode(errors="replace"))
        assert (home / "deja.seen").read_text() == str(policy)
        assert not list(repo.iterdir())
        print("omp discovered both lane MCP servers with the project policy")


if __name__ == "__main__":
    main()
