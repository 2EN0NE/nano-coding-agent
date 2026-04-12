# Project Background & Context

## 1. Vision

Guardian is a resident agent that enforces AI-coding discipline through lightweight, local tooling. It turns `AGENTS.md` from a static document into an active contract by providing:
- CLI commands for validation, scanning, and principle merging
- Git hooks that block commits violating project rules
- Zero heavy runtime dependencies

## 2. Constraints

- **Minimal dependencies**: Runtime logic uses only the Python standard library plus PyYAML
- **Self-hosting**: This repository is validated by `guardian validate`
- **Safety first**: API Keys and Secrets must never be committed
- **Atomic commits**: One logical change per commit, green tests after each

## 3. High-Level Logic

### Guardian Workflow
```
git commit → pre-commit hook →
  ├─ guardian scan  (security + audit scan)
  └─ guardian validate (AGENTS.md + project rules)
```

### CLI Lifecycle
```
guardian install  → copy hook + bootstrap principles/
guardian validate → check AGENTS.md, forbidden dirs, file length, tests
guardian merge    → deduplicated principle injection into AGENTS.md
guardian scan     → Semgrep security + heuristic audit scan
```

## 4. Anti-Patterns

- **Do not skip validation**: Run `guardian validate` before considering a change complete
- **Do not bury issues in commit messages**: They will surface during review
- **Do not delete failing tests to pass**: Fix the code or the test, never the signal
- **Do not hardcode configuration**: Favor env vars or config files
