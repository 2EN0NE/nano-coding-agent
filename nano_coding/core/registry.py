import copy
import functools
from typing import Any, Optional

# Store as principle -> practice_name -> list of command path lists
# This allows multiple commands under the same practice
# (e.g., "禁止操作" can have both install and validate)
_REGISTRY: dict[str, dict[str, list[list[str]]]] = {}


def register_practice(principle: str, practices: dict[str, list[str]]):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        if principle not in _REGISTRY:
            _REGISTRY[principle] = {}

        for practice_name, command_paths in practices.items():
            if practice_name not in _REGISTRY[principle]:
                _REGISTRY[principle][practice_name] = []
            if command_paths not in _REGISTRY[principle][practice_name]:
                _REGISTRY[principle][practice_name].append(command_paths)

        return wrapper

    return decorator


# Whitelist of explicitly allowed skill module names.
# This prevents arbitrary code execution from injected files in skills/.
_SKILL_MODULE_NAMES = ["guard", "principle_review"]


def scan_registry() -> dict[str, dict[str, list[str]]]:
    # Explicit static imports avoid both circular imports and
    # semgrep false positives on dynamic import_module usage.
    import nano_coding.skills.guard  # noqa: F401
    import nano_coding.skills.principle_review  # noqa: F401

    return copy.deepcopy(_REGISTRY)


def collect_principle_status(
    target_dir: Optional[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    import os

    registry = scan_registry()
    hooks_text = ""

    if target_dir is not None:
        hooks_dir = os.path.join(target_dir, ".git", "hooks")
        if os.path.isdir(hooks_dir):
            for filename in sorted(os.listdir(hooks_dir)):
                filepath = os.path.join(hooks_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            hooks_text += f.read() + "\n"
                    except Exception:
                        pass

    result: dict[str, dict[str, dict[str, Any]]] = {}
    for principle, practices in registry.items():
        result[principle] = {}
        for practice_name, command_paths_list in practices.items():
            any_in_hooks = any(p in hooks_text for cp in command_paths_list for p in cp)
            result[principle][practice_name] = {
                "command_paths": command_paths_list[0] if command_paths_list else [],
                "in_hooks": any_in_hooks,
            }

    return result
