import sys
import tempfile
from pathlib import Path

import click

from nano_coding.core.local_skill_loader import (
    discover_local_skills,
    load_python_skill,
    resolve_skill,
)


class TestDiscoverLocalSkills:
    def test_empty_when_skills_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            assert discover_local_skills(agent_dir) == []

    def test_discovers_skill_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            skill_dir = agent_dir / "skills" / "hello"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: hello\nentrypoint: main:cli\n---\nHello skill",
                encoding="utf-8",
            )
            result = discover_local_skills(agent_dir)
            assert len(result) == 1
            assert result[0]["name"] == "hello"
            assert result[0]["skill_dir"] == skill_dir
            assert result[0]["metadata"]["name"] == "hello"
            assert result[0]["metadata"]["entrypoint"] == "main:cli"
            assert result[0]["has_python_module"] is False

    def test_has_python_module_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            skill_dir = agent_dir / "skills" / "py_skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: py\n---\nBody", encoding="utf-8"
            )
            (skill_dir / "main.py").write_text("# python", encoding="utf-8")
            result = discover_local_skills(agent_dir)
            assert len(result) == 1
            assert result[0]["has_python_module"] is True

    def test_skips_non_directory_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            skills_dir = agent_dir / "skills"
            skills_dir.mkdir(parents=True)
            (skills_dir / "not_a_dir.txt").write_text("hello", encoding="utf-8")
            assert discover_local_skills(agent_dir) == []

    def test_sorts_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            for name in ("zeta", "alpha"):
                skill_dir = agent_dir / "skills" / name
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    f"---\nname: {name}\n---\nBody", encoding="utf-8"
                )
            result = discover_local_skills(agent_dir)
            assert [s["name"] for s in result] == ["alpha", "zeta"]


class TestLoadPythonSkill:
    def test_invalid_entrypoint_no_colon(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            assert load_python_skill(Path(tmpdir), "nocolon") is None

    def test_invalid_entrypoint_empty_parts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            assert load_python_skill(Path(tmpdir), ":func") is None
            assert load_python_skill(Path(tmpdir), "mod:") is None

    def test_missing_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            assert load_python_skill(Path(tmpdir), "missing:cli") is None

    def test_loads_click_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "main.py").write_text(
                "import click\n\n@click.command()\ndef hello():\n    pass\n\ncli = hello\n",
                encoding="utf-8",
            )
            cmd = load_python_skill(skill_dir, "main:cli")
            assert cmd is not None
            assert isinstance(cmd, click.Command)
            assert cmd.name == "hello"

    def test_loads_click_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "cli.py").write_text(
                "import click\ncli = click.Group()\n", encoding="utf-8"
            )
            cmd = load_python_skill(skill_dir, "cli:cli")
            assert cmd is not None
            assert isinstance(cmd, click.Group)

    def test_non_command_object_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "main.py").write_text("cli = 42\n", encoding="utf-8")
            assert load_python_skill(skill_dir, "main:cli") is None

    def test_missing_function_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "main.py").write_text("x = 1\n", encoding="utf-8")
            assert load_python_skill(skill_dir, "main:missing") is None

    def test_sys_path_restored(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            (skill_dir / "main.py").write_text(
                "import click\ncli = click.command()(lambda: None)\n", encoding="utf-8"
            )
            original = list(sys.path)
            load_python_skill(skill_dir, "main:cli")
            assert sys.path == original

    def test_nested_module_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            sub = skill_dir / "sub"
            sub.mkdir()
            (sub / "mod.py").write_text(
                "import click\ncli = click.command()(lambda: None)\n", encoding="utf-8"
            )
            cmd = load_python_skill(skill_dir, "sub.mod:cli")
            assert cmd is not None
            assert isinstance(cmd, click.Command)

    def test_package_init_py(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            pkg = skill_dir / "pkg"
            pkg.mkdir()
            (pkg / "__init__.py").write_text(
                "import click\ncli = click.command()(lambda: None)\n", encoding="utf-8"
            )
            cmd = load_python_skill(skill_dir, "pkg:cli")
            assert cmd is not None
            assert isinstance(cmd, click.Command)


class TestResolveSkill:
    def test_resolve_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            skill_dir = agent_dir / "skills" / "myskill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: myskill\nentrypoint: main:cli\n---\nBody", encoding="utf-8"
            )
            (skill_dir / "main.py").write_text(
                "import click\ncli = click.command()(lambda: None)\n", encoding="utf-8"
            )
            cmd = resolve_skill("myskill", agent_dir)
            assert cmd is not None
            assert isinstance(cmd, click.Command)

    def test_resolve_missing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            assert resolve_skill("noskill", agent_dir) is None

    def test_resolve_no_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            skill_dir = agent_dir / "skills" / "noentry"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: noentry\n---\nBody", encoding="utf-8"
            )
            (skill_dir / "main.py").write_text("cli = None\n", encoding="utf-8")
            assert resolve_skill("noentry", agent_dir) is None

    def test_resolve_no_python_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / ".nano-coding-agent"
            skill_dir = agent_dir / "skills" / "nopy"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: nopy\nentrypoint: main:cli\n---\nBody", encoding="utf-8"
            )
            assert resolve_skill("nopy", agent_dir) is None
