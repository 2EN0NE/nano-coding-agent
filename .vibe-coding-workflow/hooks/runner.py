#!/usr/bin/env python3
import sys
from pathlib import Path

_workflow_root = Path(__file__).resolve().parent.parent
if str(_workflow_root) not in sys.path:
    sys.path.insert(0, str(_workflow_root))

import argparse
import os
import subprocess
from typing import Dict, List, Any, Optional

import yaml

from hooks import HookRegistry, BaseHook, HookResult


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = Path(__file__).parent / "hooks.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        return {"hooks": {}, "settings": {}, "git": {}}
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_git_context() -> Dict[str, Any]:
    context = {"changed_files": [], "git_info": {}}
    
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            timeout=30
        )
        context["changed_files"] = [f for f in result.stdout.strip().split("\n") if f]
        
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10
        )
        context["git_info"]["commit"] = result.stdout.strip() or "initial"
        
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=10
        )
        context["git_info"]["branch"] = result.stdout.strip() or "unknown"
        
    except Exception:
        pass
    
    return context


def import_hook_modules():
    from hooks.implementations import audit, guardian


def run_hook(hook_name: str, config: Dict[str, Any], context: Dict[str, Any]) -> HookResult:
    hook_instance = HookRegistry.create_instance(hook_name, config)
    
    if hook_instance is None:
        return HookResult(
            name=hook_name,
            success=False,
            blocking=[f"Hook '{hook_name}' not found"]
        )
    
    return hook_instance.run(context)


def run_hooks(hook_type: str, config: Dict[str, Any], context: Dict[str, Any]) -> List[HookResult]:
    results = []
    settings = config.get("settings", {})
    git_config = config.get("git", {})
    
    hooks_to_run = git_config.get(hook_type, [])
    
    import_hook_modules()
    
    for hook_name in hooks_to_run:
        hook_config = config.get("hooks", {}).get(hook_name, {})
        
        if not hook_config.get("enabled", True):
            print(f"Skipping disabled hook: {hook_name}")
            continue
        
        print(f"Running {hook_name}...")
        
        result = run_hook(hook_name, hook_config, context)
        results.append(result)
        
        if settings.get("fail_fast", True) and result.has_blocking():
            print(f"Blocking issues found in {hook_name}, stopping.")
            break
    
    return results


def print_results(results: List[HookResult], settings: Dict[str, Any]):
    has_blocking = any(r.has_blocking() for r in results)
    
    for result in results:
        if result.has_blocking():
            print(f"\n{result.name}: FAILED")
            for issue in result.blocking:
                print(f"  [BLOCKING] {issue}")
        elif result.warnings and not settings.get("quiet", False):
            print(f"\n{result.name}: OK (with warnings)")
            for w in result.warnings:
                print(f"  [WARNING] {w}")
        else:
            print(f"{result.name}: OK")
        
        if result.suggestions and settings.get("show_all_results", False):
            for s in result.suggestions:
                print(f"  [SUGGESTION] {s}")
    
    return not has_blocking


def main():
    parser = argparse.ArgumentParser(description="Hook Runner")
    parser.add_argument("--hook-type", default="pre_commit", choices=["pre_commit", "commit_msg"])
    parser.add_argument("--config", help="Path to hooks.yaml")
    parser.add_argument("--list", action="store_true", help="List available hooks")
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    import_hook_modules()
    
    if args.list:
        print("Available hooks:")
        for name, hook_class in HookRegistry.list_hooks().items():
            print(f"  - {name}: {hook_class.description}")
        return 0
    
    context = get_git_context()
    results = run_hooks(args.hook_type, config, context)
    
    if not results:
        print("No hooks ran")
        return 0
    
    success = print_results(results, config.get("settings", {}))
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
