# Contributing

Thanks for helping. Lonca is small on purpose: shell and Python scripts, Markdown skills, no build step.

- **Bugs and ideas:** open an issue (the template asks what you ran and what happened).
- **PRs:** one change per PR, with what you tested. Keep scripts POSIX `sh` (or Python ≥ 3.11, standard library only).
- **Before you push:** `sh -n` every shell script you touched, `python3 -m py_compile` every Python one, and run
  `./install.sh --yes` then `./install.sh --uninstall` in a throwaway `HOME` if you changed the installer:
  `env -i HOME=$(mktemp -d) PATH=/usr/bin:/bin sh ./install.sh --yes`.
- **Skills and rules** (`AGENTS.md`, `skills/*/SKILL.md`) are read by agents: write short, plain, testable instructions.
  Vendored skills (`skills/VENDOR.md`) are changed upstream, not here.
- **No personal data** in examples: use `acme/shop`, `~/Work/<project>` and the like.

By contributing you agree that your work is released under the MIT licence (`LICENSE`).
