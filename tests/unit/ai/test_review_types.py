from nano_coding.core.ai.review_types import (
    Severity,
    parse_llm_response,
    severity_from_string,
)


def test_parse_llm_response_standard_json_code_block():
    raw = """```json
{
  "summary": "Looks good overall.",
  "issues": [
    {
      "severity": "warning",
      "title": "Missing docstring",
      "detail": "Function foo lacks a docstring.",
      "suggestion": "Add a descriptive docstring."
    }
  ]
}
```"""
    result = parse_llm_response("code_review", raw)
    assert result.review_type == "code_review"
    assert result.summary == "Looks good overall."
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == Severity.WARNING
    assert issue.title == "Missing docstring"
    assert issue.detail == "Function foo lacks a docstring."
    assert issue.suggestion == "Add a descriptive docstring."
    assert result.raw_response == raw


def test_parse_llm_response_no_language_tag_code_block():
    raw = """```
{
  "summary": "No lang tag.",
  "issues": [
    {
      "severity": "blocking",
      "title": "Security issue",
      "detail": "Hardcoded password.",
      "suggestion": "Use environment variables."
    }
  ]
}
```"""
    result = parse_llm_response("security_review", raw)
    assert result.review_type == "security_review"
    assert result.summary == "No lang tag."
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == Severity.BLOCKING
    assert issue.title == "Security issue"
    assert result.raw_response == raw


def test_parse_llm_response_plain_json_string():
    raw = '{"summary": "Plain JSON.", "issues": []}'
    result = parse_llm_response("plain_review", raw)
    assert result.review_type == "plain_review"
    assert result.summary == "Plain JSON."
    assert result.issues == []
    assert result.raw_response == raw


def test_parse_llm_response_unparseable_text_fallback():
    raw = "This is not JSON at all."
    result = parse_llm_response("bad_review", raw)
    assert result.review_type == "bad_review"
    assert result.summary == "Failed to parse structured response from LLM."
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity == Severity.SUGGESTION
    assert issue.title == "Parse error"
    assert "This is not JSON at all." in issue.detail
    assert issue.suggestion == "Please review the raw response manually."
    assert result.raw_response == raw


def test_parse_llm_response_mixed_case_severity():
    raw = """```json
{
  "summary": "Mixed case severities.",
  "issues": [
    {"severity": "BLOCKING", "title": "T1"},
    {"severity": "Warning", "title": "T2"},
    {"severity": "suggestion", "title": "T3"},
    {"severity": "unknown", "title": "T4"}
  ]
}
```"""
    result = parse_llm_response("case_review", raw)
    assert result.summary == "Mixed case severities."
    assert len(result.issues) == 4
    assert result.issues[0].severity == Severity.BLOCKING
    assert result.issues[1].severity == Severity.WARNING
    assert result.issues[2].severity == Severity.SUGGESTION
    assert result.issues[3].severity == Severity.SUGGESTION


def test_severity_from_string_case_insensitive():
    assert severity_from_string("blocking") == Severity.BLOCKING
    assert severity_from_string("BLOCKING") == Severity.BLOCKING
    assert severity_from_string("Warning") == Severity.WARNING
    assert severity_from_string("SUGGESTION") == Severity.SUGGESTION
    assert severity_from_string("unknown") == Severity.SUGGESTION
