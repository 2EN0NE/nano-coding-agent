# AI Coding Guardian

Resident principle guardian for AI-assisted coding projects. Enforces `AGENTS.md` discipline through lightweight CLI tooling and Git hooks.

## Install

```bash
pip install .
```

## Commands

### `guardian install <project>`
Install the pre-commit hook and bootstrap a `principles/` directory into a Git repository.

```bash
guardian install .
```

### `guardian validate <project>`
Validate that a project satisfies baseline governance rules:
- `AGENTS.md` exists and contains `## 基础原则`
- No forbidden root directories
- Source files do not exceed 1000 lines
- Tests are present

### `guardian merge --principles <file> --target <AGENTS.md>`
Merge principle blocks from a source markdown file into an existing `AGENTS.md`, deduplicating by semantic similarity.

```bash
guardian merge --principles principles/core.md --target AGENTS.md
```

### `guardian scan --path <project>`
Run security and audit scans over the project. Reports blocking issues, warnings, and suggestions.

```bash
guardian scan --path .
```

## Philosophy

- **Minimalist**: Zero heavy dependencies; runtime uses only the Python standard library plus PyYAML
- **Agent-first**: Tools operate on `AGENTS.md` as the single source of truth
- **Self-governing**: This repository is validated by `guardian validate`

## License

MIT
