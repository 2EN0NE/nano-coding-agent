#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys


def check_bd_installed():
    try:
        result = subprocess.run(
            ["bd", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_current_branch():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def run_bd_command(args):
    cmd = ["bd", "--json"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print(f"bd command failed: {result.stderr}", file=sys.stderr)
            return None
        return result.stdout
    except Exception as e:
        print(f"Error running bd: {e}", file=sys.stderr)
        return None


def read_task_by_id(task_id):
    output = run_bd_command(["show", task_id])
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw": output}
    return None


def read_tasks_by_branch(branch_name):
    output = run_bd_command(["list", "--all"])
    if not output:
        return []

    try:
        tasks = json.loads(output)
    except json.JSONDecodeError:
        return []

    branch_tasks = []
    for task in tasks:
        tags = task.get("tags", [])
        if any(branch_name in str(tag) for tag in tags):
            branch_tasks.append(task)

    if not branch_tasks:
        open_tasks = [t for t in tasks if t.get("status") in ["open", "in_progress"]]
        return open_tasks[:10]

    return branch_tasks


def read_ready_tasks():
    output = run_bd_command(["ready"])
    if not output:
        return []

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def main():
    parser = argparse.ArgumentParser(description="Read task memory from bd")
    parser.add_argument("--task-id", help="Specific task ID (e.g., bd-a1b2)")
    parser.add_argument("--current-branch", action="store_true", help="Read tasks for current git branch")
    parser.add_argument("--ready", action="store_true", help="List ready tasks (no blockers)")
    args = parser.parse_args()

    if not check_bd_installed():
        print(json.dumps({
            "error": "bd CLI not installed",
            "hint": "Install: curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash"
        }), file=sys.stderr)
        sys.exit(1)

    result = None

    if args.task_id:
        result = read_task_by_id(args.task_id)
    elif args.current_branch:
        branch = get_current_branch()
        if branch:
            result = read_tasks_by_branch(branch)
        else:
            result = {"error": "Not in a git repository"}
    elif args.ready:
        result = read_ready_tasks()
    else:
        result = read_ready_tasks()

    if result is None:
        result = {"error": "No tasks found"}

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
