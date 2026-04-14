import tempfile
from pathlib import Path

import pytest

from nano_coding.core.skill_generator import (
    generate_all_skills,
    generate_skill_md,
    write_skills_to_agent_dir,
)
from nano_coding.skills.guard import install


class TestGenerateSkillMd:
    def test_returns_string_with_frontmatter_and_body(self) -> None:
        result = generate_skill_md(install)
        assert isinstance(result, str)
        assert result.startswith("---")
        assert "name: install" in result
        assert "type: python" in result
        assert "description:" in result

    def test_includes_help_as_description(self) -> None:
        result = generate_skill_md(install)
        assert "description:" in result

    def test_includes_parameters(self) -> None:
        result = generate_skill_md(install)
        assert "## Parameters" in result
        assert "<target_dir>" in result

    def test_raises_type_error_for_non_command(self) -> None:
        with pytest.raises(TypeError, match="Expected click.Command"):
            generate_skill_md("not-a-command")

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError, match="Expected click.Command"):
            generate_skill_md(None)


class TestGenerateAllSkills:
    def test_returns_dict_with_guard_commands(self) -> None:
        skills = generate_all_skills()
        assert isinstance(skills, dict)
        assert "install" in skills
        assert "validate" in skills
        assert "update" in skills
        assert "scan" in skills

    def test_returns_dict_with_principle_review(self) -> None:
        skills = generate_all_skills()
        assert "principle-review" in skills

    def test_each_value_is_valid_skill_md(self) -> None:
        skills = generate_all_skills()
        for name, content in skills.items():
            assert content.startswith("---")
            assert f"name: {name}" in content
            assert "type: python" in content


class TestWriteSkillsToAgentDir:
    def test_writes_skills_to_directory(self) -> None:
        skills = generate_all_skills()
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir)
            write_skills_to_agent_dir(agent_dir)
            for name in skills:
                skill_file = agent_dir / "skills" / name / "SKILL.md"
                assert skill_file.exists()
                assert f"name: {name}" in skill_file.read_text(encoding="utf-8")

    def test_skips_existing_files_when_force_is_false(self) -> None:
        skills = generate_all_skills()
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir)
            write_skills_to_agent_dir(agent_dir)
            original_contents = {
                name: (agent_dir / "skills" / name / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                for name in skills
            }
            # Overwrite one file
            skill_file = agent_dir / "skills" / "install" / "SKILL.md"
            skill_file.write_text("modified", encoding="utf-8")
            skill_file = agent_dir / "skills" / "install" / "SKILL.md"
            skill_file.write_text("modified", encoding="utf-8")
            write_skills_to_agent_dir(agent_dir, force=False)
            assert skill_file.read_text(encoding="utf-8") == "modified"
            for name in skills:
                if name == "install":
                    continue
                other_file = agent_dir / "skills" / name / "SKILL.md"
                assert other_file.read_text(encoding="utf-8") == original_contents[name]

    def test_overwrites_existing_files_when_force_is_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir)
            write_skills_to_agent_dir(agent_dir)
            skill_file = agent_dir / "skills" / "install" / "SKILL.md"
            skill_file.write_text("modified", encoding="utf-8")
            write_skills_to_agent_dir(agent_dir, force=True)
            assert "name: install" in skill_file.read_text(encoding="utf-8")
            assert skill_file.read_text(encoding="utf-8") != "modified"
