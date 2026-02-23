#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any

from hooks import BaseHook, HookResult, hook


AUDIT_RULES = {
    "python": "python-security",
    "typescript": "ts-security",
    "go": "go-security",
    "rust": "rust-security",
}


def get_rules_for_type(project_type: str) -> str:
    return AUDIT_RULES.get(project_type, "auto")


def run_semgrep(rules: str, level: str = "security") -> Dict[str, Any]:
    cmd = ["semgrep", "--config", rules, "--json", "--quiet"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return json.loads(result.stdout) if result.stdout else {"results": []}
    except Exception as e:
        return {"results": [], "error": str(e)}


def filter_blocking(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    blocking = []
    for r in results.get("results", []):
        if r.get("extra", {}).get("severity") in ["ERROR", "WARNING"]:
            blocking.append(r)
    return blocking


@hook(enabled=True, timeout=60)
class GuardianHook(BaseHook):
    name = "guardian"
    description = "Security scanner using semgrep"
    
    def setup_parser(self, parser: argparse.ArgumentParser):
        parser.add_argument("--level", choices=["security", "full"], default="security")
        parser.add_argument("--project-type", default="python")
    
    def run(self, context: Dict[str, Any]) -> HookResult:
        level = self.config.get("level", "security")
        project_type = self.config.get("project_type", "python")
        
        rules = get_rules_for_type(project_type)
        results = run_semgrep(rules, level)
        
        if "error" in results:
            return HookResult(
                name=self.name,
                success=False,
                blocking=[f"Semgrep error: {results['error']}"]
            )
        
        blocking = filter_blocking(results)
        
        if blocking:
            messages = [
                f"{issue.get('check_id')}: {issue.get('extra', {}).get('message')}"
                for issue in blocking
            ]
            return HookResult(
                name=self.name,
                success=False,
                blocking=messages
            )
        
        return HookResult(name=self.name, success=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Guardian Hook")
    parser.add_argument("--level", choices=["security", "full"], default="security")
    parser.add_argument("--project-type", default="python")
    args = parser.parse_args()
    
    hook_instance = GuardianHook({"level": args.level, "project_type": args.project_type})
    result = hook_instance.run({})
    
    if not result.success:
        print(f"Guardian found {len(result.blocking)} blocking issues:", file=sys.stderr)
        for issue in result.blocking:
            print(f"  - {issue}", file=sys.stderr)
        sys.exit(1)
    
    print("Guardian scan passed")
    sys.exit(0)
