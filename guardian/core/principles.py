from __future__ import annotations

import math
import re
from dataclasses import dataclass


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

    return ParsedDocument(preamble="\n".join(preamble_lines).rstrip("\n"), sections=sections)


def extractPrincipleBlocks(content: str) -> list[PrincipleBlock]:
    blocks: list[PrincipleBlock] = []
    lines = content.split("\n")
    current_title = ""
    current_body: list[str] = []

    for line in lines:
        if line.startswith("### "):
            if current_title:
                blocks.append(
                    PrincipleBlock(title=current_title, body="\n".join(current_body).strip())
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
    return re.sub(r"^\[(suggest|support|control)\]\s*", "", title).strip()


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


def mergePrinciplesIntoDocument(doc: str, incoming: list[PrincipleBlock]) -> str:
    parsed = parseDocument(doc)

    all_existing_blocks: list[PrincipleBlock] = []
    existing_basics_section: DocumentSection | None = None

    for section in parsed.sections:
        if section.header.strip() == "## 基础原则":
            if existing_basics_section is None:
                existing_basics_section = section
        else:
            blocks = extractPrincipleBlocks(section.body)
            all_existing_blocks.extend(blocks)

    if existing_basics_section is not None:
        basics_blocks = extractPrincipleBlocks(existing_basics_section.body)
        all_existing_blocks.extend(basics_blocks)

    missing: list[PrincipleBlock] = []
    for inc in incoming:
        if not hasDuplicate(inc, all_existing_blocks):
            missing.append(inc)

    retained_sections = [
        s for s in parsed.sections if s.header.strip() != "## 基础原则"
    ]

    if not missing:
        if existing_basics_section is not None:
            retained_sections.append(existing_basics_section)
        parts: list[str] = []
        if parsed.preamble.strip():
            parts.append(parsed.preamble.rstrip())
        for s in retained_sections:
            body = s.body.strip()
            if body:
                parts.append(f"{s.header.strip()}\n\n{body}")
            else:
                parts.append(s.header.strip())
        return "\n\n".join(parts).lstrip() + "\n"

    basics_header = "## 基础原则"
    basics_intro = "以下原则由 nano-coding-agent 生成，作为项目通用补充规范。"
    blocks_body = "\n\n".join(
        f"---\n\n### {b.title}\n\n{b.body}" for b in missing
    )
    basics_body = f"{basics_intro}\n\n{blocks_body}"

    retained_sections.append(
        DocumentSection(header=basics_header, body=basics_body)
    )

    parts: list[str] = []
    if parsed.preamble.strip():
        parts.append(parsed.preamble.rstrip())
    for s in retained_sections:
        body = s.body.strip()
        if body:
            parts.append(f"{s.header.strip()}\n\n{body}")
        else:
            parts.append(s.header.strip())

    return "\n\n".join(parts).lstrip() + "\n"
