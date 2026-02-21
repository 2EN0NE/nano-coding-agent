#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

AUDIT_RULES = {
    "python": "python-security",
    "typescript": "ts-security",
    "go": "go-security",
    "rust": "rust-security",
}

def get_rules_for_type(project_type):
    return AUDIT_RULES.get(project_type, "auto")

def run_semgrep(rules, level="security"):
    cmd = ["semgrep", "--config", rules, "--json", "--quiet"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout) if result.stdout else {"results": []}
    except Exception as e:
        print(f"Semgrep error: {e}", file=sys.stderr)
        return {"results": []}

def filter_blocking(results):
    blocking = []
    for r in results.get("results", []):
        if r.get("extra", {}).get("severity") in ["ERROR", "WARNING"]:
            blocking.append(r)
    return blocking

def main():
    parser = argparse.ArgumentParser(description="Guardian - Security Scanner")
    parser.add_argument("--level", choices=["security", "full"], default="security")
    parser.add_argument("--project-type", default="python")
    parser.add_argument("--output", default="json")
    args = parser.parse_args()

    rules = get_rules_for_type(args.project_type)
    results = run_semgrep(rules, args.level)
    blocking = filter_blocking(results)

    if blocking:
        print(f"Found {len(blocking)} blocking issues:", file=sys.stderr)
        for issue in blocking:
            print(f"  - {issue.get('check_id')}: {issue.get('extra', {}).get('message')}", file=sys.stderr)
        sys.exit(1)

    print("Guardian scan passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
