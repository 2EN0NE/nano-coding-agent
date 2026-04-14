from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass


NANO_CODING_START = "<!-- NANO_CODING_GENERATED_START -->"
NANO_CODING_COMMENT = (
    "<!-- 以下内容通过 nano-coding 自动生成与维护，请勿手动修改此区域 -->"
)
NANO_CODING_END = "<!-- NANO_CODING_GENERATED_END -->"


@dataclass
class PrincipleBlock:
    title: str
    body: str


@dataclass
class DocumentSection:
    header: str
    body: str


@dataclass
class ParsedDocument:
    preamble: str
    sections: list[DocumentSection]


def extractMarkdownSection(content: str, heading: str) -> str:
    lines = content.split("\n")
    start_re = re.compile(rf"^##\s+{re.escape(heading)}\s*$")
    start = -1
    for i, line in enumerate(lines):
        if start_re.match(line):
            start = i
            break
    if start == -1:
        return ""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if re.match(r"^##\s", lines[i]):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def parseDocument(content: str) -> ParsedDocument:
    lines = content.split("\n")
    sections: list[DocumentSection] = []
    preamble_lines: list[str] = []
    current_header: str | None = None
    current_body_lines: list[str] = []
    found_first_header = False

    for line in lines:
        if re.match(r"^##\s", line):
            if found_first_header:
                sections.append(
                    DocumentSection(
                        header=current_header,
                        body="\n".join(current_body_lines),
                    )
                )
            else:
                preamble_lines = list(current_body_lines)
                found_first_header = True
            current_header = line
            current_body_lines = []
        else:
            current_body_lines.append(line)

    if current_header is not None:
        sections.append(
            DocumentSection(
                header=current_header,
                body="\n".join(current_body_lines),
            )
        )
    else:
        preamble_lines = list(current_body_lines)

    return ParsedDocument(
        preamble="\n".join(preamble_lines).rstrip("\n"), sections=sections
    )


def extractPrincipleBlocks(content: str) -> list[PrincipleBlock]:
    blocks: list[PrincipleBlock] = []
    lines = content.split("\n")
    current_title = ""
    current_body: list[str] = []

    for line in lines:
        if line.startswith("### "):
            if current_title:
                blocks.append(
                    PrincipleBlock(
                        title=current_title, body="\n".join(current_body).strip()
                    )
                )
            current_title = line[4:].strip()
            current_body = []
        else:
            current_body.append(line)

    if current_title:
        blocks.append(
            PrincipleBlock(title=current_title, body="\n".join(current_body).strip())
        )

    return blocks


def normalizeTitle(title: str) -> str:
    return re.sub(r"^\[(suggest|support|control)( some)?\]\s*", "", title).strip()


def resolve_principle_tags(
    incoming: list[PrincipleBlock], target_dir: str | None
) -> list[PrincipleBlock]:
    from nano_coding.core.registry import collect_principle_status

    status = collect_principle_status(target_dir)
    result: list[PrincipleBlock] = []

    for block in incoming:
        new_block = copy.deepcopy(block)
        principle_name = normalizeTitle(block.title).strip()
        principle_status = status.get(principle_name, {})

        if not principle_status:
            principle_tag = "[suggest]"
        else:
            all_in_hooks = all(
                p.get("in_hooks", False) for p in principle_status.values()
            )
            all_have_commands = all(
                len(p.get("command_paths", [])) > 0 for p in principle_status.values()
            )
            some_in_hooks = any(
                p.get("in_hooks", False) for p in principle_status.values()
            )
            some_have_commands = any(
                len(p.get("command_paths", [])) > 0 for p in principle_status.values()
            )

            if all_in_hooks:
                principle_tag = "[control]"
            elif all_have_commands and some_in_hooks:
                principle_tag = "[control some]"
            elif some_have_commands and not all_have_commands:
                principle_tag = "[support some]"
            elif all_have_commands and not some_in_hooks:
                principle_tag = "[support]"
            else:
                principle_tag = "[suggest]"

        new_block.title = f"{principle_tag} {principle_name}"

        body_lines = new_block.body.split("\n")
        new_body_lines: list[str] = []
        for line in body_lines:
            stripped = line.strip()
            if stripped.startswith("- "):
                content = stripped[2:].strip()
                colon_idx = -1
                if ":" in content:
                    colon_idx = content.index(":")
                if "：" in content:
                    idx = content.index("：")
                    if colon_idx == -1 or idx < colon_idx:
                        colon_idx = idx
                if colon_idx != -1:
                    practice_name = content[:colon_idx].strip()
                else:
                    practice_name = content

                practice_info = principle_status.get(practice_name, {})
                if not practice_info:
                    practice_tag = "[suggest]"
                elif practice_info.get("in_hooks", False):
                    practice_tag = "[control]"
                elif len(practice_info.get("command_paths", [])) > 0:
                    practice_tag = "[support]"
                else:
                    practice_tag = "[suggest]"

                indent = line[: len(line) - len(line.lstrip())]
                new_line = f"{indent}{practice_tag} {stripped}"
                new_body_lines.append(new_line)
            else:
                new_body_lines.append(line)

        new_block.body = "\n".join(new_body_lines)
        result.append(new_block)

    return result


def _djb2(s: str) -> int:
    h = 5381
    for ch in s:
        h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
    return h & 0xFFFFFFFF


def _xorshift32(x: int) -> int:
    x &= 0xFFFFFFFF
    x ^= (x << 13) & 0xFFFFFFFF
    x ^= (x >> 17) & 0xFFFFFFFF
    x ^= (x << 5) & 0xFFFFFFFF
    return x & 0xFFFFFFFF


def vectorize(text: str, dim: int = 256) -> list[float]:
    vec = [0.0] * dim
    normalized = "".join(text.split()).lower()
    for i in range(len(normalized) - 1):
        bigram = normalized[i : i + 2]
        h = _djb2(bigram)
        for d in range(dim):
            h = _xorshift32(h)
            if (h & 1) == 1:
                vec[d] += 1.0
            else:
                vec[d] -= 1.0

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosineSimilarity(a: list[float], b: list[float]) -> float:
    dot = 0.0
    for i in range(len(a)):
        dot += a[i] * b[i]
    return dot


def _vectorizeBlock(block: PrincipleBlock) -> list[float]:
    weighted_text = f"{block.title}\n{block.title}\n{block.title}\n{block.body}"
    return vectorize(weighted_text, 256)


def hasDuplicate(
    incoming: PrincipleBlock,
    existingBlocks: list[PrincipleBlock],
    semanticThreshold: float = 0.88,
) -> bool:
    inc_title = normalizeTitle(incoming.title)

    for ex in existingBlocks:
        if normalizeTitle(ex.title) == inc_title:
            return True

    inc_vec = _vectorizeBlock(incoming)
    for ex in existingBlocks:
        sim = cosineSimilarity(inc_vec, _vectorizeBlock(ex))
        if sim >= semanticThreshold:
            return True

    return False


def _removeNanoCodingBlock(content: str) -> str:
    lines = content.split("\n")
    result: list[str] = []
    inside_block = False
    for line in lines:
        if line.strip() == NANO_CODING_START:
            inside_block = True
            continue
        if line.strip() == NANO_CODING_END:
            inside_block = False
            continue
        if not inside_block:
            result.append(line)
    return "\n".join(result)


def extractPrincipleBlocksFromDocument(content: str) -> list[PrincipleBlock]:
    blocks: list[PrincipleBlock] = []
    lines = content.split("\n")
    current_title = ""
    current_body: list[str] = []

    for line in lines:
        if re.match(r"^#{2,3}\s+", line):
            if current_title:
                blocks.append(
                    PrincipleBlock(
                        title=current_title,
                        body="\n".join(current_body).strip(),
                    )
                )
            current_title = re.sub(r"^#{2,3}\s+", "", line).strip()
            current_body = []
        else:
            current_body.append(line)

    if current_title:
        blocks.append(
            PrincipleBlock(title=current_title, body="\n".join(current_body).strip())
        )

    return blocks


def extractPrincipleBlocksFromDocumentWithRanges(
    content: str,
) -> list[tuple[PrincipleBlock, int, int]]:
    """Extract principle blocks with their (start_line, end_line) ranges."""
    lines = content.split("\n")
    blocks: list[tuple[PrincipleBlock, int, int]] = []
    current_title = ""
    current_body: list[str] = []
    start_idx = -1

    for i, line in enumerate(lines):
        if re.match(r"^#{2,3}\s+", line):
            if current_title:
                blocks.append(
                    (
                        PrincipleBlock(
                            title=current_title,
                            body="\n".join(current_body).strip(),
                        ),
                        start_idx,
                        i,
                    )
                )
            current_title = re.sub(r"^#{2,3}\s+", "", line).strip()
            current_body = []
            start_idx = i
        else:
            current_body.append(line)

    if current_title:
        blocks.append(
            (
                PrincipleBlock(
                    title=current_title, body="\n".join(current_body).strip()
                ),
                start_idx,
                len(lines),
            )
        )

    return blocks


@dataclass
class MergeResult:
    merged_doc: str
    warnings: list[str]


def mergePrinciplesIntoDocument(
    doc: str, incoming: list[PrincipleBlock], semantic_threshold: float = 0.88
) -> MergeResult:
    cleaned = _removeNanoCodingBlock(doc).strip()
    lines = cleaned.split("\n") if cleaned else []
    existing_with_ranges = extractPrincipleBlocksFromDocumentWithRanges(cleaned)

    warnings: list[str] = []
    blocks_to_remove: set[int] = set()
    incoming_to_add: list[PrincipleBlock] = []

    for inc in incoming:
        inc_title_norm = normalizeTitle(inc.title)
        exact_match_indices = [
            idx
            for idx, (ex, _start, _end) in enumerate(existing_with_ranges)
            if normalizeTitle(ex.title) == inc_title_norm
        ]

        if exact_match_indices:
            for idx in exact_match_indices:
                blocks_to_remove.add(idx)
            incoming_to_add.append(inc)
            continue

        inc_vec = _vectorizeBlock(inc)
        semantic_match_found = False
        for idx, (ex, _start, _end) in enumerate(existing_with_ranges):
            if idx in blocks_to_remove:
                continue
            sim = cosineSimilarity(inc_vec, _vectorizeBlock(ex))
            if sim >= semantic_threshold:
                semantic_match_found = True
                warnings.append(
                    f"[WARN] AGENTS.md 中已存在与原则「{inc.title}」语义相近但标题不同的内容"
                    f"「{ex.title}」，建议参考原则「{inc.title}」修改该部分，因为这些验证"
                    f"有对应保护技能可以让 Agent 直接执行。"
                )
                break

        if not semantic_match_found:
            incoming_to_add.append(inc)

    remove_ranges: list[tuple[int, int]] = []
    for idx in blocks_to_remove:
        _ex, start, end = existing_with_ranges[idx]
        remove_ranges.append((start, end))

    remove_ranges.sort()
    merged_ranges: list[tuple[int, int]] = []
    for start, end in remove_ranges:
        if merged_ranges and start <= merged_ranges[-1][1]:
            merged_ranges[-1] = (
                merged_ranges[-1][0],
                max(merged_ranges[-1][1], end),
            )
        else:
            merged_ranges.append((start, end))

    remaining_lines: list[str] = []
    last_end = 0
    for start, end in merged_ranges:
        remaining_lines.extend(lines[last_end:start])
        last_end = end
    remaining_lines.extend(lines[last_end:])

    new_cleaned = "\n".join(remaining_lines).strip()

    if not incoming_to_add:
        return MergeResult(
            merged_doc=new_cleaned + "\n" if new_cleaned else "",
            warnings=warnings,
        )

    blocks_body = "\n\n".join(
        f"---\n\n### {b.title}\n\n{b.body}" for b in incoming_to_add
    )
    generated_section = (
        f"{NANO_CODING_START}\n"
        f"{NANO_CODING_COMMENT}\n\n"
        f"## 基础原则\n\n"
        f"{blocks_body}\n\n"
        f"{NANO_CODING_END}"
    )

    if new_cleaned:
        return MergeResult(
            merged_doc=generated_section + "\n\n" + new_cleaned + "\n",
            warnings=warnings,
        )
    return MergeResult(
        merged_doc=generated_section + "\n",
        warnings=warnings,
    )
