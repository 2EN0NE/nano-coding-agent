#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def read_file(path: Path) -> str:
    if not path.exists():
        return f"\n\n> Warning: {path} not found\n\n"
    return path.read_text()


def generate_agents_md():
    script_dir = Path(__file__).resolve().parent
    workflow_dir = script_dir.parent
    root = workflow_dir.parent
    
    tmpl_path = root / "AGENTS.md.tmpl"
    output_path = root / "AGENTS.md"
    
    if not tmpl_path.exists():
        print(f"Template not found: {tmpl_path}")
        return False
    
    tmpl = tmpl_path.read_text()
    
    docs_dir = root / "docs"
    
    core_path = docs_dir / "agents-core.md"
    scaffold_path = docs_dir / "agents-scaffold-specific.md"
    
    core_content = read_file(core_path)
    scaffold_content = read_file(scaffold_path)
    
    result = tmpl.replace('{% include "docs/agents-core.md" %}', core_content)
    result = result.replace('{% include "docs/agents-scaffold-specific.md" %}', scaffold_content)
    
    output_path.write_text(result)
    print(f"Generated: {output_path}")
    return True


if __name__ == "__main__":
    success = generate_agents_md()
    sys.exit(0 if success else 1)
