import nano_coding.core.ai.prompts as prompts


def test_build_agents_md_review_returns_non_empty_string():
    result = prompts.build_agents_md_review("# AGENTS.md\nBe good.")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_agents_md_review_contains_json_and_issues():
    result = prompts.build_agents_md_review("# AGENTS.md\nBe good.")
    assert "```json" in result
    assert "issues" in result


def test_build_background_md_review_returns_non_empty_string():
    result = prompts.build_background_md_review("# BACKGROUND.md\nProject vision.")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_background_md_review_contains_json_and_issues():
    result = prompts.build_background_md_review("# BACKGROUND.md\nProject vision.")
    assert "```json" in result
    assert "issues" in result


def test_build_agents_abort_review_returns_non_empty_string():
    result = prompts.build_agents_abort_review("# BANNED\nDo not rm -rf /")
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_agents_abort_review_contains_json_and_issues():
    result = prompts.build_agents_abort_review("# BANNED\nDo not rm -rf /")
    assert "```json" in result
    assert "issues" in result


def test_build_subdir_agents_review_with_files():
    subdirs = [("src/api/AGENTS.md", "# API rules\nUse REST.")]
    result = prompts.build_subdir_agents_review(subdirs)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "```json" in result
    assert "issues" in result
    assert "src/api/AGENTS.md" in result


def test_build_subdir_agents_review_empty_list():
    result = prompts.build_subdir_agents_review([])
    assert isinstance(result, str)
    assert len(result) > 0
    assert "```json" in result
    assert "zero files" in result or "empty issues list" in result
