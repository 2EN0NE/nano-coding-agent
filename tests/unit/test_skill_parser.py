import tempfile
from pathlib import Path

import pytest

from nano_coding.core.skill_parser import load_skill_from_file, parse_skill_md


class TestParseSkillMd:
    def test_valid_skill_md(self) -> None:
        content = "---\nname: test\ndescription: A test skill\n---\nHello"
        result = parse_skill_md(content)
        assert result["name"] == "test"
        assert result["description"] == "A test skill"
        assert result["type"] == "markdown"
        assert result["body"] == "Hello"

    def test_type_defaults_to_markdown(self) -> None:
        content = "---\nname: foo\n---\nBody here"
        result = parse_skill_md(content)
        assert result["type"] == "markdown"
        assert result["body"] == "Body here"

    def test_type_override_preserved(self) -> None:
        content = "---\nname: foo\ntype: custom\n---\nBody here"
        result = parse_skill_md(content)
        assert result["type"] == "custom"

    def test_missing_separator_raises(self) -> None:
        content = "name: test\n\nHello"
        with pytest.raises(ValueError, match="Missing '---' frontmatter separator"):
            parse_skill_md(content)

    def test_partial_fields_allowed(self) -> None:
        content = "---\ndescription: Only desc\n---\nBody"
        result = parse_skill_md(content)
        assert "name" not in result
        assert result["description"] == "Only desc"
        assert result["body"] == "Body"
        assert result["type"] == "markdown"

    def test_empty_frontmatter(self) -> None:
        content = "---\n---\nBody"
        result = parse_skill_md(content)
        assert result["body"] == "Body"
        assert result["type"] == "markdown"

    def test_multiline_body(self) -> None:
        content = "---\nname: test\n---\nLine 1\nLine 2\nLine 3"
        result = parse_skill_md(content)
        assert result["body"] == "Line 1\nLine 2\nLine 3"


class TestLoadSkillFromFile:
    def test_load_from_file(self) -> None:
        content = "---\nname: file_test\n---\nFile body"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill.md"
            path.write_text(content, encoding="utf-8")
            result = load_skill_from_file(path)
        assert result["name"] == "file_test"
        assert result["body"] == "File body"
