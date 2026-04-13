import math
import unittest
from unittest.mock import patch

from nano_coding.core.principles import (
    cosineSimilarity,
    extractMarkdownSection,
    extractPrincipleBlocks,
    extractPrincipleBlocksFromDocument,
    hasDuplicate,
    mergePrinciplesIntoDocument,
    normalizeTitle,
    parseDocument,
    PrincipleBlock,
    resolve_principle_tags,
    vectorize,
)


class TestExtractMarkdownSection(unittest.TestCase):
    def test_extracts_section(self):
        content = "# Top\n\n## Foo\nline1\nline2\n\n## Bar\nother"
        self.assertEqual(extractMarkdownSection(content, "Foo"), "## Foo\nline1\nline2")

    def test_missing_section_returns_empty(self):
        content = "# Top\n\n## Bar\nother"
        self.assertEqual(extractMarkdownSection(content, "Foo"), "")

    def test_extracts_until_next_level2(self):
        content = "## A\na\n## B\nb\n## C\nc"
        self.assertEqual(extractMarkdownSection(content, "B"), "## B\nb")


class TestParseDocument(unittest.TestCase):
    def test_preamble_and_sections(self):
        doc = "Preamble line 1\nPreamble line 2\n\n## Section A\nBody A\n\n## Section B\nBody B"
        parsed = parseDocument(doc)
        self.assertEqual(parsed.preamble, "Preamble line 1\nPreamble line 2")
        self.assertEqual(len(parsed.sections), 2)
        self.assertEqual(parsed.sections[0].header, "## Section A")
        self.assertEqual(parsed.sections[0].body, "Body A\n")
        self.assertEqual(parsed.sections[1].header, "## Section B")
        self.assertEqual(parsed.sections[1].body, "Body B")

    def test_no_headers_means_all_preamble(self):
        doc = "Just preamble\nno headers here"
        parsed = parseDocument(doc)
        self.assertEqual(parsed.preamble, "Just preamble\nno headers here")
        self.assertEqual(parsed.sections, [])

    def test_starts_with_header_no_preamble(self):
        doc = "## First\nBody\n## Second\nMore"
        parsed = parseDocument(doc)
        self.assertEqual(parsed.preamble, "")
        self.assertEqual(len(parsed.sections), 2)
        self.assertEqual(parsed.sections[0].header, "## First")
        self.assertEqual(parsed.sections[0].body, "Body")


class TestExtractPrincipleBlocks(unittest.TestCase):
    def test_extracts_multiple_blocks(self):
        content = (
            "### Title One\nBody one line 1\nBody one line 2\n\n### Title Two\nBody two"
        )
        blocks = extractPrincipleBlocks(content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].title, "Title One")
        self.assertEqual(blocks[0].body, "Body one line 1\nBody one line 2")
        self.assertEqual(blocks[1].title, "Title Two")
        self.assertEqual(blocks[1].body, "Body two")

    def test_empty_content(self):
        self.assertEqual(extractPrincipleBlocks(""), [])
        self.assertEqual(extractPrincipleBlocks("just text\nno blocks"), [])

    def test_trailing_lines_included(self):
        content = "### Title\nLine 1\nLine 2"
        blocks = extractPrincipleBlocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].body, "Line 1\nLine 2")


class TestNormalizeTitle(unittest.TestCase):
    def test_strips_support(self):
        self.assertEqual(normalizeTitle("[support] Foo bar"), "Foo bar")

    def test_strips_suggest(self):
        self.assertEqual(normalizeTitle("[suggest]  Use TypeScript"), "Use TypeScript")

    def test_strips_control(self):
        self.assertEqual(normalizeTitle("[control]   Strict mode"), "Strict mode")

    def test_case_sensitive_no_strip(self):
        self.assertEqual(normalizeTitle("[Support] Foo"), "[Support] Foo")

    def test_no_prefix_unchanged(self):
        self.assertEqual(normalizeTitle("Plain title"), "Plain title")

    def test_normalize_title_strips_some_variants(self):
        self.assertEqual(normalizeTitle("[support some] Foo bar"), "Foo bar")
        self.assertEqual(normalizeTitle("[control some]   Baz"), "Baz")
        self.assertEqual(normalizeTitle("[control some] 行为边界"), "行为边界")


class TestResolvePrincipleTags(unittest.TestCase):
    def test_resolve_principle_tags_empty_registry_all_suggest(self):
        incoming = [
            PrincipleBlock(
                title="Old Title",
                body="- 禁止操作：项目需要禁止的操作\n- 安全防线：明确规定",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status",
            return_value={},
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[suggest] Old Title")
        self.assertIn("[suggest] - 禁止操作：项目需要禁止的操作", result[0].body)
        self.assertIn("[suggest] - 安全防线：明确规定", result[0].body)
        self.assertEqual(incoming[0].title, "Old Title")
        self.assertNotIn("[suggest]", incoming[0].body)

    def test_resolve_principle_tags_support_some(self):
        registry = {
            "行为边界": {
                "禁止操作": {"command_paths": ["cmd"], "in_hooks": False},
                "安全防线": {"command_paths": [], "in_hooks": False},
            }
        }
        incoming = [
            PrincipleBlock(
                title="行为边界",
                body="- 禁止操作：项目需要...\n- 安全防线：明确规定...",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status",
            return_value=registry,
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[support some] 行为边界")
        self.assertIn("[support] - 禁止操作：项目需要...", result[0].body)
        self.assertIn("[suggest] - 安全防线：明确规定...", result[0].body)

    def test_resolve_principle_tags_control(self):
        registry = {
            "TDD先行": {
                "先设计测试": {"command_paths": ["cmd"], "in_hooks": True},
                "运行测试": {"command_paths": ["cmd2"], "in_hooks": True},
            }
        }
        incoming = [
            PrincipleBlock(
                title="TDD先行",
                body="- 先设计测试：先设计...\n- 运行测试：代码完成后...",
            )
        ]
        with patch(
            "nano_coding.core.registry.collect_principle_status",
            return_value=registry,
        ):
            result = resolve_principle_tags(incoming, "/fake")

        self.assertEqual(result[0].title, "[control] TDD先行")
        self.assertIn("[control] - 先设计测试：先设计...", result[0].body)
        self.assertIn("[control] - 运行测试：代码完成后...", result[0].body)


class TestVectorize(unittest.TestCase):
    def test_empty_text(self):
        vec = vectorize("", dim=4)
        self.assertEqual(vec, [0.0, 0.0, 0.0, 0.0])

    def test_bit_exact_small_dim(self):
        vec = vectorize("abc", dim=4)
        expected = [-0.5773502691896258, 0.5773502691896258, 0.5773502691896258, 0.0]
        self.assertEqual(len(vec), 4)
        for a, b in zip(vec, expected):
            self.assertAlmostEqual(a, b, places=15)

    def test_cosine_identical_is_one(self):
        v = vectorize("hello world", dim=8)
        self.assertAlmostEqual(cosineSimilarity(v, v), 1.0, places=14)

    def test_cosine_known_pair(self):
        v1 = vectorize("hello world", dim=8)
        v2 = vectorize("goodbye world", dim=8)
        expected = 0.17928429140015908
        self.assertAlmostEqual(cosineSimilarity(v1, v2), expected, places=15)


class TestHasDuplicate(unittest.TestCase):
    def test_exact_title_match(self):
        inc = PrincipleBlock(title="Foo", body="Body")
        existing = [PrincipleBlock(title="Foo", body="Other body")]
        self.assertTrue(hasDuplicate(inc, existing))

    def test_normalized_title_match(self):
        inc = PrincipleBlock(title="[support] Foo", body="Body")
        existing = [PrincipleBlock(title="Foo", body="Other")]
        self.assertTrue(hasDuplicate(inc, existing))

    def test_vector_above_threshold(self):
        body_long = "word " * 10
        inc = PrincipleBlock(title="Alpha", body=body_long)
        existing = [PrincipleBlock(title="Beta", body=body_long)]
        self.assertTrue(hasDuplicate(inc, existing, semanticThreshold=0.88))

    def test_vector_below_threshold(self):
        body_short = "word " * 5
        inc = PrincipleBlock(title="Alpha", body="word " * 10)
        existing = [PrincipleBlock(title="Beta", body=body_short)]
        self.assertFalse(hasDuplicate(inc, existing, semanticThreshold=0.88))

    def test_custom_threshold_boundary(self):
        body_long = "word " * 10
        inc = PrincipleBlock(title="Alpha", body=body_long)
        existing = [PrincipleBlock(title="Beta", body=body_long)]
        self.assertFalse(hasDuplicate(inc, existing, semanticThreshold=0.90))


class TestExtractPrincipleBlocksFromDocument(unittest.TestCase):
    def test_extracts_h2_and_h3(self):
        content = "## H2 Title\nH2 body\n\n### H3 Title\nH3 body"
        blocks = extractPrincipleBlocksFromDocument(content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].title, "H2 Title")
        self.assertEqual(blocks[0].body, "H2 body")
        self.assertEqual(blocks[1].title, "H3 Title")
        self.assertEqual(blocks[1].body, "H3 body")

    def test_ignores_h1(self):
        content = "# H1 Title\nH1 body\n\n### H3 Title\nH3 body"
        blocks = extractPrincipleBlocksFromDocument(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].title, "H3 Title")

    def test_empty_content(self):
        self.assertEqual(extractPrincipleBlocksFromDocument(""), [])


class TestMergePrinciplesIntoDocument(unittest.TestCase):
    def test_idempotency(self):
        doc = "# Existing doc\n\nSome content.\n"
        incoming = [PrincipleBlock(title="Block A", body="Body A")]
        merged1 = mergePrinciplesIntoDocument(doc, incoming)
        merged2 = mergePrinciplesIntoDocument(merged1, incoming)
        self.assertEqual(merged1, merged2)

    def test_prepends_generated_block(self):
        doc = "# Project\n\n## Existing\nBody\n"
        incoming = [PrincipleBlock(title="New Block", body="New body")]
        merged = mergePrinciplesIntoDocument(doc, incoming)
        lines = merged.split("\n")
        start_idx = lines.index("<!-- NANO_CODING_GENERATED_START -->")
        end_idx = lines.index("<!-- NANO_CODING_GENERATED_END -->")
        existing_header_idx = lines.index("# Project")
        self.assertLess(end_idx, existing_header_idx)
        self.assertIn("## 基础原则", merged)
        self.assertIn("New Block", merged)
        self.assertIn("New body", merged)
        self.assertIn("## Existing", merged)

    def test_removes_old_block_before_inserting_new(self):
        old_block = (
            "<!-- NANO_CODING_GENERATED_START -->\n"
            "<!-- 以下内容通过 nano-coding 自动生成与维护，请勿手动修改此区域 -->\n\n"
            "## 基础原则\n\n"
            "### Old Block\n\nOld body\n\n"
            "<!-- NANO_CODING_GENERATED_END -->\n\n"
        )
        doc = old_block + "# Project\n\nContent.\n"
        incoming = [PrincipleBlock(title="New Block", body="New body")]
        merged = mergePrinciplesIntoDocument(doc, incoming)
        self.assertIn("New Block", merged)
        self.assertNotIn("Old Block", merged)
        self.assertIn("# Project", merged)
        count_start = merged.count("<!-- NANO_CODING_GENERATED_START -->")
        self.assertEqual(count_start, 1)

    def test_removes_block_when_no_incoming(self):
        old_block = (
            "<!-- NANO_CODING_GENERATED_START -->\n"
            "<!-- 以下内容通过 nano-coding 自动生成与维护，请勿手动修改此区域 -->\n\n"
            "## 基础原则\n\n"
            "### Block\n\nBody\n\n"
            "<!-- NANO_CODING_GENERATED_END -->\n\n"
        )
        doc = old_block + "# Project\n"
        merged = mergePrinciplesIntoDocument(doc, [])
        self.assertNotIn("NANO_CODING_GENERATED_START", merged)
        self.assertNotIn("## 基础原则", merged)
        self.assertIn("# Project", merged)

    def test_creates_block_in_empty_doc(self):
        incoming = [PrincipleBlock(title="Block A", body="Body A")]
        merged = mergePrinciplesIntoDocument("", incoming)
        self.assertTrue(merged.startswith("<!-- NANO_CODING_GENERATED_START -->"))
        self.assertIn("## 基础原则", merged)
        self.assertIn("Block A", merged)

    def test_skips_duplicate_in_manual_section_by_title(self):
        doc = (
            "# Project\n\n"
            "## 多环境分支策略\n\n"
            "采用四分支环境模型...\n\n"
            "## Existing\nBody\n"
        )
        incoming = [
            PrincipleBlock(title="多环境分支策略", body="采用四分支环境模型...")
        ]
        merged = mergePrinciplesIntoDocument(doc, incoming)
        self.assertNotIn("### 多环境分支策略", merged)
        self.assertIn("## 多环境分支策略", merged)
        self.assertIn("## Existing", merged)

    def test_skips_duplicate_in_manual_section_with_tags(self):
        doc = "# Project\n\n## [suggest] 多环境分支策略\n\n采用四分支环境模型...\n"
        incoming = [
            PrincipleBlock(title="多环境分支策略", body="采用四分支环境模型...")
        ]
        merged = mergePrinciplesIntoDocument(doc, incoming)
        self.assertNotIn("### 多环境分支策略", merged)
        self.assertIn("## [suggest] 多环境分支策略", merged)

    def test_keeps_unique_incoming_blocks(self):
        doc = "# Project\n\n## Existing Manual\n\nExisting body\n"
        incoming = [
            PrincipleBlock(title="New Block", body="New body"),
            PrincipleBlock(title="Existing Manual", body="Different body"),
        ]
        merged = mergePrinciplesIntoDocument(doc, incoming)
        self.assertIn("### New Block", merged)
        self.assertNotIn("### Existing Manual", merged)
        self.assertIn("## Existing Manual", merged)


if __name__ == "__main__":
    unittest.main()
