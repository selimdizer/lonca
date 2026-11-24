---
name: lonca
description: Set up a folder for Lonca, add a project, inspect its active settings, or enable lanes and merge-pr when the user wants them outside a project.
---

Run `lonca status <folder>` and report the project root, enabled agents and any guard warnings. For a status question, stop there.

In a lane, send the setup request and folder to your lead and wait. Leads and owner sessions can run init.

For setup, ask which agents to enable if the user hasn't said. The default is Claude and Codex. Run `lonca init --agents claude,codex <root>` with their selection, then run status again. Report what changed and any conflicts.

For removal, give the owner `lonca remove <root>` to run in their own shell.
