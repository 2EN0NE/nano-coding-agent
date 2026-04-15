"""Prompt templates for AI governance review tasks."""


def _json_output_instruction() -> str:
    return (
        "Output your assessment in a JSON format wrapped in a markdown code block like this:\n"
        "```json\n"
        "{\n"
        '  "summary": "string - overall assessment",\n'
        '  "issues": [\n'
        "    {\n"
        '      "severity": "blocking|warning|suggestion",\n'
        '      "title": "short issue name",\n'
        '      "detail": "detailed explanation",\n'
        '      "suggestion": "how to improve"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
        "Important: severity must be exactly one of: blocking, warning, suggestion.\n"
        "This is a read-only review. Do not suggest modifying any source code files.\n"
    )


def _short_content_warning() -> str:
    return (
        "If the document content is empty or extremely short, include an issue with:\n"
        '  severity: "warning", title: "文档内容过短"\n'
    )


def build_agents_md_review(agents_md_content: str) -> str:
    """Build a prompt to review AGENTS.md content quality."""
    prompt = (
        "You are an AI coding governance reviewer.\n\n"
        "Task: Evaluate the following AGENTS.md file and assess its quality as a governance document.\n\n"
        "Evaluation dimensions:\n"
        "1. Are the principles actionable (can an AI agent actually follow them)?\n"
        "2. Are there any contradictory principles?\n"
        "3. Are there concrete examples, or is it purely abstract?\n"
        "4. Is the document structure clear (are ###-separated principle blocks reasonable)?\n\n"
        + _json_output_instruction()
        + "\n"
        + _short_content_warning()
        + "\n--- Document begins ---\n"
        + agents_md_content
        + "\n--- Document ends ---\n"
    )
    return prompt


def build_background_md_review(background_md_content: str) -> str:
    """Build a prompt to review BACKGROUND.md semantic completeness."""
    prompt = (
        "You are an AI coding governance reviewer.\n\n"
        "Task: Evaluate the following BACKGROUND.md file for semantic completeness.\n\n"
        "Evaluation dimensions:\n"
        "1. Does it contain a project vision?\n"
        "2. Does it explain core constraints?\n"
        "3. Does it describe business logic?\n"
        "4. Does it include pitfalls or gotchas to avoid?\n"
        "5. Is the content concrete (not just generic platitudes)?\n\n"
        + _json_output_instruction()
        + "\n"
        + _short_content_warning()
        + "\n--- Document begins ---\n"
        + background_md_content
        + "\n--- Document ends ---\n"
    )
    return prompt


def build_agents_abort_review(abort_content: str) -> str:
    """Build a prompt to review AGENTS_ABORT.md / BANNED-AGENT-BEHAVIORS.md effectiveness."""
    prompt = (
        "You are an AI coding governance reviewer.\n\n"
        "Task: Evaluate the following banned-agent-behaviors document for effectiveness.\n\n"
        "Evaluation dimensions:\n"
        "1. Are the prohibitions specific and unambiguous (e.g., 'do not run rm -rf' vs 'do not make mistakes')?\n"
        "2. Does it cover common AI failure modes?\n"
        "3. Are the prohibitions enforceable by an AI (can an AI actually judge and comply)?\n"
        "4. Are there redundant or duplicated prohibitions?\n\n"
        + _json_output_instruction()
        + "\n"
        + _short_content_warning()
        + "\n--- Document begins ---\n"
        + abort_content
        + "\n--- Document ends ---\n"
    )
    return prompt


def build_subdir_agents_review(subdir_agents: list[tuple[str, str]]) -> str:
    """Build a prompt to review subdirectory AGENTS.md relevance."""
    if not subdir_agents:
        return (
            "You are an AI coding governance reviewer.\n\n"
            "Task: Evaluate the relevance of subdirectory AGENTS.md files.\n\n"
            "No subdirectory AGENTS.md files were provided. "
            "State in the summary that there are zero files to review, and return an empty issues list.\n\n"
            + _json_output_instruction()
        )

    file_list = "\n".join(f"- {path}" for path, _ in subdir_agents)
    sections = []
    for path, content in subdir_agents:
        sections.append(f"### File: {path}\n{content}\n")
    all_content = "\n".join(sections)

    prompt = (
        "You are an AI coding governance reviewer.\n\n"
        "Task: Evaluate the relevance of the following subdirectory AGENTS.md files.\n\n"
        "Files to review:\n" + file_list + "\n\n"
        "Evaluation dimensions:\n"
        "1. Is each subdirectory AGENTS.md focused on the specific concerns of that module?\n"
        "2. Is it just a copy-paste of the root AGENTS.md?\n"
        "3. Does the content match the source code types found in that directory?\n\n"
        + _json_output_instruction()
        + "\n"
        + _short_content_warning()
        + "\n--- Documents begin ---\n"
        + all_content
        + "--- Documents end ---\n"
    )
    return prompt
