# nano_coding/agent/

This directory contains the default assets that `install_agent()` copies into a project's `.nano-coding-agent/` directory during initialization.

## Contents

- `templates/` – Template files (e.g., `AGENTS.md.template`, `config.yaml.template`) that are written to the target project without the `.template` suffix.
- `hooks/` – Hook templates (e.g., `pre-commit.template`) that are installed into the target project's `.nano-coding-agent/hooks/` and `.git/hooks/` directories.
- `skills/` – Built-in skill metadata used when generating local skill definitions for a target project.
