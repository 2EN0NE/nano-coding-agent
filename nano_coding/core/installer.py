import os
import shutil
import stat
import sys
from pathlib import Path


def install_hooks_and_principles(target_dir: str) -> None:
    target = Path(target_dir).resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        print(f"[ERROR] {target} is not a git repository (.git directory missing)")
        sys.exit(1)

    source_hook = Path(__file__).resolve().parent.parent / "hooks" / "pre-commit"
    dest_hook = git_dir / "hooks" / "pre-commit"
    dest_hook.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(source_hook), str(dest_hook))
    dest_hook.chmod(dest_hook.stat().st_mode | stat.S_IXUSR)

    principles_dir = target / "principles"
    principles_dir.mkdir(parents=True, exist_ok=True)

    source_principles = (
        Path(__file__).resolve().parent.parent.parent / "principles" / "core.md"
    )
    dest_principles = principles_dir / "core.md"
    if not dest_principles.exists():
        shutil.copy(str(source_principles), str(dest_principles))

    print(f"Installed nano-coding hook to {dest_hook}")
    print(f"Ensured principles directory at {principles_dir}")
    print(f"Installed principles file at {dest_principles}")
