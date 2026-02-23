# Hooks Framework

A flexible git hook framework for running various validation and auditing agents during the commit workflow.

## Structure

```
hooks/
├── __init__.py          # Base Hook interface and registry
├── runner.py             # Hook dispatcher
├── hooks.yaml           # Hook configuration
├── implementations/     # Hook implementations
│   ├── __init__.py
│   ├── audit.py         # Code review agent
│   └── guardian.py      # Security scanner
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r hooks/requirements.txt
```

### 2. Enable Git Hooks

```bash
# Copy the pre-commit hook
cp .husky/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
```

### 3. Configure Hooks

Edit `hooks/hooks.yaml` to enable/disable hooks and adjust settings.

## Available Hooks

### Guardian (Security Scanner)

Scans code for security vulnerabilities using semgrep.

Configuration:
- `level`: security | full
- `project_type`: python | typescript | go | rust | auto

### Audit (Code Review Agent)

Performs code review for logic errors, bugs, and quality issues.

Configuration:
- `mode`: shadow | full
- `level`: lax | standard | strict
- `exclude`: List of file patterns to skip

## Adding New Hooks

1. Create a new file in `hooks/implementations/`
2. Implement a class inheriting from `BaseHook`
3. Use the `@hook` decorator to register it:

```python
from hooks import BaseHook, HookResult, hook

@hook(enabled=True, timeout=60)
class MyHook(BaseHook):
    name = "my_hook"
    description = "My custom hook"
    
    def run(self, context):
        # Your logic here
        return HookResult(name=self.name, success=True)
```

4. Add the hook to `hooks.yaml`:

```yaml
hooks:
  my_hook:
    enabled: true
    timeout: 60
```

5. Add to git hook execution order:

```yaml
git:
  pre_commit:
    - guardian
    - audit
    - my_hook  # Add here
```

## Running Hooks Manually

```bash
# Run all pre-commit hooks
python hooks/runner.py --hook-type pre_commit

# Run commit-msg hooks
python hooks/runner.py --hook-type commit_msg

# List available hooks
python hooks/runner.py --list
```

## Configuration

All configuration is in `hooks.yaml`:

- `git.enabled`: Which git hooks are active
- `git.pre_commit`: Hooks to run before commit
- `git.commit_msg`: Hooks to run on commit message
- `hooks.<hook_name>`: Individual hook settings
- `settings`: Global runner settings

## Settings

- `fail_fast`: Stop on first blocking issue
- `show_all_results`: Show suggestions even if blocking issues found
- `color`: Enable colored output
- `quiet`: Only show errors
