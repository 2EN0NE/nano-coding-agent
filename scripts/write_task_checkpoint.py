#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime


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


def run_bd_command(args):
    cmd = ["bd"] + args
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


def create_checkpoint_message(summary, next_steps, branch=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = f"""## Checkpoint - {timestamp}

### Summary
{summary}

### Next Steps
{next_steps}
"""
    if branch:
        body += f"\n**Branch:** {branch}"
    return body


def create_message(summary, next_steps, parent_id=None):
    body = create_checkpoint_message(summary, next_steps)

    args = ["message", "create"]
    if parent_id:
        args.extend(["--thread", parent_id])
    args.extend(["-m", body])

    output = run_bd_command(args)
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw": output}
    return None


def update_task_summary(task_id, summary, next_steps):
    body = f"{summary}\n\n---\n\n**Next Steps:** {next_steps}"
    output = run_bd_command(["update", task_id, "-m", body])
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return {"raw": output}
    return None


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


def main():
    parser = argparse.ArgumentParser(description="Write checkpoint to bd")
    parser.add_argument("--summary", required=True, help="Current progress summary")
    parser.add_argument("--next-steps", required=True, help="Next steps to continue")
    parser.add_argument("--task-id", help="Update specific task ID (e.g., bd-a1b2)")
    parser.add_argument("--message", action="store_true", help="Create as message instead of updating task")
    args = parser.parse_args()

    if not check_bd_installed():
        print(json.dumps({
            "error": "bd CLI not installed",
            "hint": "Install: curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash"
        }), file=sys.stderr)
        sys.exit(1)

    branch = get_current_branch()

    if args.task_id:
        result = update_task_summary(args.task_id, args.summary, args.next_steps)
    elif args.message:
        result = create_message(args.summary, args.next_steps)
    else:
        result = create_message(args.summary, args.next_steps)

    if result is None:
        result = {"error": "Failed to create checkpoint"}

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
