"""Tests for nano_coding.core.config_loader."""

import json
from pathlib import Path

from nano_coding.core.config_loader import (
    get_default_config,
    load_config,
    merge_configs,
    resolve_config,
)


class TestLoadConfig:
    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        assert load_config(missing) == {}

    def test_returns_parsed_json(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text('{"key": "value"}')
        assert load_config(path) == {"key": "value"}

    def test_returns_empty_and_warns_on_invalid_json(
        self, tmp_path: Path, capsys
    ) -> None:
        path = tmp_path / "bad.json"
        path.write_text("not json")
        result = load_config(path)
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert str(path) in captured.err

    def test_returns_empty_and_warns_on_non_dict_json(
        self, tmp_path: Path, capsys
    ) -> None:
        path = tmp_path / "list.json"
        path.write_text("[1, 2, 3]")
        result = load_config(path)
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err


class TestGetDefaultConfig:
    def test_returns_empty_dict(self) -> None:
        assert get_default_config() == {}


class TestMergeConfigs:
    def test_simple_override(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        assert merge_configs(base, override) == {"a": 1, "b": 3, "c": 4}

    def test_nested_dict_merge(self) -> None:
        base = {"scan": {"enabled": False, "depth": 3}}
        override = {"scan": {"enabled": True}}
        assert merge_configs(base, override) == {"scan": {"enabled": True, "depth": 3}}

    def test_list_union_deduplicates(self) -> None:
        base = {"tags": ["a", "b"]}
        override = {"tags": ["b", "c"]}
        assert merge_configs(base, override) == {"tags": ["a", "b", "c"]}

    def test_override_replaces_non_dict_non_list(self) -> None:
        base = {"value": "old"}
        override = {"value": "new"}
        assert merge_configs(base, override) == {"value": "new"}

    def test_deeply_nested_merge(self) -> None:
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"c": 3}}}
        assert merge_configs(base, override) == {"a": {"b": {"c": 3, "d": 2}}}

    def test_list_in_nested_dict(self) -> None:
        base = {"scan": {"exts": [".py"]}}
        override = {"scan": {"exts": [".js", ".py"]}}
        assert merge_configs(base, override) == {"scan": {"exts": [".py", ".js"]}}


class TestResolveConfig:
    def test_returns_default_when_no_configs_exist(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert resolve_config(tmp_path) == {}

    def test_merges_user_and_project_config(self, tmp_path: Path, monkeypatch) -> None:
        user_dir = tmp_path / "user_home" / ".nano-coding-agent"
        user_dir.mkdir(parents=True)
        user_config = user_dir / "config.json"
        user_config.write_text(json.dumps({"scan": {"timeout": 30}}))
        monkeypatch.setattr(
            "nano_coding.core.config_loader.USER_CONFIG_PATH", user_config
        )

        project_dir = tmp_path / "project"
        git_dir = project_dir / ".git"
        git_dir.mkdir(parents=True)
        agent_dir = project_dir / ".nano-coding-agent"
        agent_dir.mkdir()
        project_config = agent_dir / "config.json"
        project_config.write_text(json.dumps({"scan": {"enabled": True}}))

        result = resolve_config(project_dir)
        assert result == {"scan": {"timeout": 30, "enabled": True}}

    def test_project_overrides_user(self, tmp_path: Path, monkeypatch) -> None:
        user_dir = tmp_path / "user_home" / ".nano-coding-agent"
        user_dir.mkdir(parents=True)
        user_config = user_dir / "config.json"
        user_config.write_text(json.dumps({"mode": "user"}))
        monkeypatch.setattr(
            "nano_coding.core.config_loader.USER_CONFIG_PATH", user_config
        )

        project_dir = tmp_path / "project"
        git_dir = project_dir / ".git"
        git_dir.mkdir(parents=True)
        agent_dir = project_dir / ".nano-coding-agent"
        agent_dir.mkdir()
        project_config = agent_dir / "config.json"
        project_config.write_text(json.dumps({"mode": "project"}))

        result = resolve_config(project_dir)
        assert result["mode"] == "project"

    def test_uses_cwd_when_start_dir_none(self, tmp_path: Path, monkeypatch) -> None:
        project_dir = tmp_path / "project"
        git_dir = project_dir / ".git"
        git_dir.mkdir(parents=True)
        agent_dir = project_dir / ".nano-coding-agent"
        agent_dir.mkdir()
        project_config = agent_dir / "config.json"
        project_config.write_text(json.dumps({"from": "cwd"}))

        monkeypatch.chdir(project_dir)
        result = resolve_config()
        assert result == {"from": "cwd"}

    def test_returns_default_when_project_config_invalid(
        self, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        project_dir = tmp_path / "project"
        git_dir = project_dir / ".git"
        git_dir.mkdir(parents=True)
        agent_dir = project_dir / ".nano-coding-agent"
        agent_dir.mkdir()
        project_config = agent_dir / "config.json"
        project_config.write_text("bad json")

        result = resolve_config(project_dir)
        assert result == {}
        captured = capsys.readouterr()
        assert "Warning" in captured.err
