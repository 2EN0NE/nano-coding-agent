import math
import unittest

from guardian.core.principles import (
    cosineSimilarity,
    extractMarkdownSection,
    extractPrincipleBlocks,
    hasDuplicate,
    mergePrinciplesIntoDocument,
    normalizeTitle,
    parseDocument,
    PrincipleBlock,
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
        content = "### Title One\nBody one line 1\nBody one line 2\n\n### Title Two\nBody two"
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


class TestMergePrinciplesIntoDocument(unittest.TestCase):
    def test_idempotency(self):
        doc = "## 基础原则\n\nIntro\n\n### Block A\n\nBody A\n"
        incoming = [PrincipleBlock(title="Block A", body="Body A")]
        merged1 = mergePrinciplesIntoDocument(doc, incoming)
        merged2 = mergePrinciplesIntoDocument(merged1, incoming)
        self.assertEqual(merged1, merged2)

    def test_duplicate_basics_uses_first(self):
        doc = (
            "Preamble\n\n"
            "## 基础原则\n"
            "Intro one\n"
            "### Block A\n"
            "Body A\n\n"
            "## 基础原则\n"
            "Intro two\n"
            "### Block B\n"
            "Body B\n\n"
            "## Other\n"
            "Other body\n"
        )
        merged = mergePrinciplesIntoDocument(doc, [])
        self.assertIn("Intro one", merged)
        self.assertIn("Block A", merged)
        self.assertNotIn("Intro two", merged)
        self.assertNotIn("Block B", merged)
        self.assertIn("## Other", merged)

    def test_creates_new_basics_when_missing(self):
        doc = "## Other\n\nOther body\n"
        incoming = [PrincipleBlock(title="New Block", body="New body")]
        merged = mergePrinciplesIntoDocument(doc, incoming)
        self.assertIn("## 基础原则", merged)
        self.assertIn("New Block", merged)
        self.assertIn("New body", merged)
        self.assertIn("## Other", merged)

    def test_preserves_existing_basics_when_no_missing(self):
        doc = "## 基础原则\n\nIntro\n\n### Block A\n\nBody A\n"
        merged = mergePrinciplesIntoDocument(doc, [])
        self.assertIn("## 基础原则", merged)
        self.assertIn("Intro", merged)
        self.assertIn("Block A", merged)


if __name__ == "__main__":
    unittest.main()
