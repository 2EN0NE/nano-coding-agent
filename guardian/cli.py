import argparse
import os
import shutil
import stat
import sys
from pathlib import Path

from guardian.core.principles import (
    PrincipleBlock,
    extractPrincipleBlocks,
    mergePrinciplesIntoDocument,
)
from guardian.core.scanner import (
    get_staged_files,
    run_audit_scan,
    run_security_scan,
)
from guardian.core.validator import validate_project


def install(target_dir: str) -> None:
    target = Path(target_dir).resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        print(f"[ERROR] {target} is not a git repository (.git directory missing)")
        sys.exit(1)

    source_hook = Path(__file__).resolve().parent / "hooks" / "pre-commit"
    dest_hook = git_dir / "hooks" / "pre-commit"
    dest_hook.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(source_hook), str(dest_hook))
    dest_hook.chmod(dest_hook.stat().st_mode | stat.S_IXUSR)

    principles_dir = target / "principles"
    principles_dir.mkdir(parents=True, exist_ok=True)

    source_principles = (
        Path(__file__).resolve().parent.parent / "principles" / "core.md"
    )
    dest_principles = principles_dir / "core.md"
    if not dest_principles.exists():
        shutil.copy(str(source_principles), str(dest_principles))

    print(f"Installed guardian hook to {dest_hook}")
    print(f"Ensured principles directory at {principles_dir}")
    print(f"Installed principles file at {dest_principles}")


def validate(target_dir: str) -> None:
    result = validate_project(target_dir)
    for issue in result.get("blocking", []):
        print(f"[BLOCKING] {issue}")
    for issue in result.get("warnings", []):
        print(f"[WARNING] {issue}")
    sys.exit(0 if result["success"] else 1)


def merge(principles_path: str, target_path: str) -> None:
    principles_file = Path(principles_path)
    target_file = Path(target_path)

    if not principles_file.exists():
        print(f"[ERROR] Principles file not found: {principles_path}")
        sys.exit(1)
    if not target_file.exists():
        print(f"[ERROR] Target file not found: {target_path}")
        sys.exit(1)

    principles_content = principles_file.read_text(encoding="utf-8")
    target_content = target_file.read_text(encoding="utf-8")

    incoming_blocks = extractPrincipleBlocks(principles_content)
    merged = mergePrinciplesIntoDocument(target_content, incoming_blocks)

    target_file.write_text(merged, encoding="utf-8")
    print(f"Merged {len(incoming_blocks)} principle blocks into {target_path}")


def scan(path: str, level: str) -> None:
    original_dir = os.getcwd()
    if path != ".":
        os.chdir(path)

    try:
        security = run_security_scan()
        audit = run_audit_scan(files=get_staged_files(), level=level)

        for issue in security.get("blocking", []):
            print(f"[SECURITY BLOCKING] {issue}")
        for issue in security.get("warnings", []):
            print(f"[SECURITY WARNING] {issue}")
        for issue in security.get("suggestions", []):
            print(f"[SECURITY SUGGESTION] {issue}")

        for issue in audit.get("blocking", []):
            print(f"[AUDIT BLOCKING] {issue}")
        for issue in audit.get("warnings", []):
            print(f"[AUDIT WARNING] {issue}")
        for issue in audit.get("suggestions", []):
            print(f"[AUDIT SUGGESTION] {issue}")

        sys.exit(1 if security.get("blocking") else 0)
    finally:
        os.chdir(original_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="guardian", description="Guardian CLI for project validation and scanning"
    )
    subparsers = parser.add_subparsers(dest="command")

    install_parser = subparsers.add_parser(
        "install", help="Install guardian hooks into a target directory"
    )
    install_parser.add_argument("target_dir", help="Target directory to install into")

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a project directory"
    )
    validate_parser.add_argument("target_dir", help="Project directory to validate")

    merge_parser = subparsers.add_parser(
        "merge", help="Merge principles into AGENTS.md"
    )
    merge_parser.add_argument(
        "--principles", required=True, help="Path to principles markdown file"
    )
    merge_parser.add_argument(
        "--target", required=True, help="Path to target AGENTS.md"
    )

    scan_parser = subparsers.add_parser("scan", help="Run security and audit scans")
    scan_parser.add_argument(
        "--path", default=".", help="Directory to scan (default: current directory)"
    )
    scan_parser.add_argument(
        "--level", default="standard", help="Audit level (default: standard)"
    )

    args = parser.parse_args()

    if args.command == "install":
        install(args.target_dir)
    elif args.command == "validate":
        validate(args.target_dir)
    elif args.command == "merge":
        merge(args.principles, args.target)
    elif args.command == "scan":
        scan(args.path, args.level)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
