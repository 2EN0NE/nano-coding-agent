import copy
import functools
import importlib
import os
import pkgutil
from typing import Any

import nano_coding.skills

_REGISTRY: dict[str, dict[str, list[str]]] = {}


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
            existing = set(_REGISTRY[principle][practice_name])
            for cp in command_paths:
                if cp not in existing:
                    _REGISTRY[principle][practice_name].append(cp)
                    existing.add(cp)

        return wrapper

    return decorator


def scan_registry() -> dict[str, dict[str, list[str]]]:
    for _, name, _ in pkgutil.iter_modules(nano_coding.skills.__path__):
        importlib.import_module(f"nano_coding.skills.{name}")
    return copy.deepcopy(_REGISTRY)


def collect_principle_status(
    target_dir: str | None,
) -> dict[str, dict[str, dict[str, Any]]]:
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
        for practice_name, command_paths in practices.items():
            command_str = " ".join(command_paths)
            result[principle][practice_name] = {
                "command_paths": command_paths,
                "in_hooks": command_str in hooks_text,
            }

    return result
