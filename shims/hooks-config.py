#!/usr/bin/env python3
"""Exit 1 for a protected Git configuration write. Compare argv, including scope and value."""
import sys

args = sys.argv[1:]
lower = [arg.lower() for arg in args]
key = "core.hookspath"
if any(arg.startswith((key + "=", "-c" + key + "=", "--config-env=" + key + "=")) for arg in lower):
    sys.exit(1)
if "config" not in args:
    sys.exit(0)
idx = args.index("config")
config = lower[idx + 1:]
# Section operations select core itself rather than spelling out the key.
section_args = [item for arg in config for item in arg.split("=", 1)]
if "core" in section_args and any(
    len(arg) > 2 and any(flag.startswith(arg) for flag in ("--remove-section", "--rename-section"))
    or arg in ("remove-section", "rename-section") for arg in section_args
):
    sys.exit(1)
if key not in config:
    sys.exit(0)
# The key must be the last argument of a read. All other ways of writing it fail closed.
read_flags = {"--local", "--global", "--system", "--worktree", "--includes", "--no-includes",
              "--show-origin", "--show-scope", "--get", "--get-all", "get", "--all", "--name-only"}
sys.exit(0 if config[-1:] == [key] and all(arg in read_flags for arg in config[:-1]) else 1)
