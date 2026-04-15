from __future__ import annotations
import enum
import json
import re
from dataclasses import dataclass, field


class Severity(enum.Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    SUGGESTION = "suggestion"


@dataclass
class ReviewIssue:
    severity: Severity
    title: str
    detail: str
    suggestion: str


@dataclass
class ReviewResult:
    review_type: str
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    raw_response: str = ""


def severity_from_string(value: str) -> Severity:
    try:
        return Severity[value.upper()]
    except KeyError:
        return Severity.SUGGESTION


def parse_llm_response(review_type: str, raw: str) -> ReviewResult:
    code_block_pattern = re.compile(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        re.IGNORECASE,
    )
    match = code_block_pattern.search(raw)
    extracted_text = match.group(1).strip() if match else raw.strip()

    try:
        data = json.loads(extracted_text)
        if not isinstance(data, dict):
            raise ValueError("Parsed JSON is not a dictionary")

        summary = data.get("summary", "")
        if not isinstance(summary, str):
            summary = str(summary)

        issues: list[ReviewIssue] = []
        for item in data.get("issues", []):
            if not isinstance(item, dict):
                continue
            severity_str = item.get("severity", "suggestion")
            if not isinstance(severity_str, str):
                severity_str = str(severity_str)
            severity = severity_from_string(severity_str)
            title = item.get("title", "Untitled issue")
            if not isinstance(title, str):
                title = str(title)
            detail = item.get("detail", "")
            if not isinstance(detail, str):
                detail = str(detail)
            suggestion = item.get("suggestion", "")
            if not isinstance(suggestion, str):
                suggestion = str(suggestion)
            issues.append(
                ReviewIssue(
                    severity=severity,
                    title=title,
                    detail=detail,
                    suggestion=suggestion,
                )
            )

        return ReviewResult(
            review_type=review_type,
            summary=summary,
            issues=issues,
            raw_response=raw,
        )
    except Exception:
        fallback_summary = "Failed to parse structured response from LLM."
        fallback_issues = [
            ReviewIssue(
                severity=Severity.SUGGESTION,
                title="Parse error",
                detail=f"Raw response excerpt: {raw[:500]}",
                suggestion="Please review the raw response manually.",
            )
        ]
        return ReviewResult(
            review_type=review_type,
            summary=fallback_summary,
            issues=fallback_issues,
            raw_response=raw,
        )
