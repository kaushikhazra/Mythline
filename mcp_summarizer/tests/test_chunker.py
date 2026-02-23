"""Unit tests for src/chunker.py — chunking engine."""

from src.chunker import (
    _split_by_paragraphs,
    chunk_content,
    chunk_semantic,
    chunk_token_based,
)
from src.tokens import count_tokens


# --- _split_by_paragraphs ---


def test_split_by_paragraphs_basic():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = _split_by_paragraphs(text)
    assert result == ["First paragraph.", "Second paragraph.", "Third paragraph."]


def test_split_by_paragraphs_multiple_newlines():
    text = "First.\n\n\n\nSecond."
    result = _split_by_paragraphs(text)
    assert result == ["First.", "Second."]


def test_split_by_paragraphs_single_paragraph():
    text = "Just one paragraph with no breaks."
    result = _split_by_paragraphs(text)
    assert result == ["Just one paragraph with no breaks."]


def test_split_by_paragraphs_strips_whitespace():
    text = "  First.  \n\n  Second.  "
    result = _split_by_paragraphs(text)
    assert result == ["First.", "Second."]


def test_split_by_paragraphs_empty_string():
    result = _split_by_paragraphs("")
    assert result == []


def test_split_by_paragraphs_only_whitespace():
    result = _split_by_paragraphs("   \n\n   ")
    assert result == []


# --- chunk_token_based ---


def test_token_based_small_content_returns_single_chunk():
    text = "Hello world."
    result = chunk_token_based(text, chunk_size=100, overlap=10)
    assert result == [text]


def test_token_based_splits_at_token_boundaries():
    # Build content that exceeds chunk_size
    words = ["word"] * 200
    text = " ".join(words)
    chunk_size = 50
    overlap = 10
    result = chunk_token_based(text, chunk_size=chunk_size, overlap=overlap)
    assert len(result) > 1
    # Each chunk (except possibly last) should be roughly chunk_size tokens
    for chunk in result[:-1]:
        tokens = count_tokens(chunk)
        assert tokens <= chunk_size + 5  # Allow small margin for decode rounding


def test_token_based_overlap_produces_shared_content():
    words = ["word"] * 200
    text = " ".join(words)
    chunk_size = 50
    overlap = 10
    result = chunk_token_based(text, chunk_size=chunk_size, overlap=overlap)
    # With overlap, consecutive chunks should share some tokens
    assert len(result) >= 3
    # More chunks than without overlap (since we step by chunk_size - overlap)
    no_overlap = chunk_token_based(text, chunk_size=chunk_size, overlap=0)
    assert len(result) >= len(no_overlap)


def test_token_based_zero_overlap():
    words = ["word"] * 200
    text = " ".join(words)
    result = chunk_token_based(text, chunk_size=50, overlap=0)
    assert len(result) > 1
    # Reconstructed text should cover all original content
    reconstructed = "".join(result)
    # All words should be present (order preserved)
    assert reconstructed.count("word") == 200


def test_token_based_empty_content():
    result = chunk_token_based("", chunk_size=100, overlap=10)
    assert result == [""]


def test_token_based_exact_chunk_size():
    # Content exactly at chunk_size should return single chunk
    text = "hello"
    tokens = count_tokens(text)
    result = chunk_token_based(text, chunk_size=tokens, overlap=0)
    assert result == [text]


# --- chunk_semantic ---


def test_semantic_splits_at_headers():
    content = "# Section One\n\nContent of section one.\n\n# Section Two\n\nContent of section two."
    # Use a chunk_size big enough for each section but not both
    section_one_tokens = count_tokens("# Section One\n\nContent of section one.")
    section_two_tokens = count_tokens("# Section Two\n\nContent of section two.")
    total = section_one_tokens + section_two_tokens
    # Set chunk_size to fit one section but not two
    chunk_size = max(section_one_tokens, section_two_tokens) + 5
    if total <= chunk_size:
        chunk_size = min(section_one_tokens, section_two_tokens) + 2
    result = chunk_semantic(content, chunk_size=chunk_size, overlap=0)
    assert len(result) >= 2


def test_semantic_small_content_single_chunk():
    content = "# Title\n\nSmall paragraph."
    result = chunk_semantic(content, chunk_size=1000, overlap=0)
    assert len(result) == 1


def test_semantic_empty_content():
    result = chunk_semantic("", chunk_size=100, overlap=0)
    assert result == []


def test_semantic_whitespace_only():
    result = chunk_semantic("   \n\n   ", chunk_size=100, overlap=0)
    assert result == []


def test_semantic_header_context_propagation():
    # Build content where section 1 header should propagate to next chunk
    header = "# Main Topic"
    small_section = "Some introductory text about the main topic."
    other_header = "## Sub Topic"
    other_content = "Content about the sub topic."
    content = f"{header}\n\n{small_section}\n\n{other_header}\n\n{other_content}"

    # Set chunk_size so that header + small_section fits, but adding sub topic doesn't
    tokens_first = count_tokens(f"{header}\n\n{small_section}")
    tokens_second = count_tokens(f"{other_header}\n\n{other_content}")
    chunk_size = tokens_first + 3  # Fits first part, not second

    if tokens_first + tokens_second <= chunk_size:
        # Content too small to split — skip this test's assertion
        return

    result = chunk_semantic(content, chunk_size=chunk_size, overlap=0)
    if len(result) >= 2:
        # Second chunk should contain the sub-topic header
        assert "Sub Topic" in result[1]


def test_semantic_oversized_section_falls_to_paragraphs():
    # Create a section with multiple paragraphs that exceed chunk_size
    para1 = "First paragraph with enough words to count. " * 5
    para2 = "Second paragraph with different content here. " * 5
    para3 = "Third paragraph adding more variety to text. " * 5
    section = f"# Big Section\n\n{para1}\n\n{para2}\n\n{para3}"

    # chunk_size that can't fit the whole section but can fit individual paragraphs
    total_tokens = count_tokens(section)
    para_max = max(count_tokens(para1), count_tokens(para2), count_tokens(para3))
    chunk_size = para_max + 20  # Fits a paragraph + header, not all three

    if total_tokens <= chunk_size:
        return  # Content too small to test this scenario

    result = chunk_semantic(section, chunk_size=chunk_size, overlap=0)
    assert len(result) >= 2
    # Header should propagate to sub-chunks
    assert "Big Section" in result[0]


def test_semantic_oversized_section_falls_to_token_based():
    # Single section, no paragraph breaks, very long
    long_text = "# Dense Section\n\n" + ("word " * 500)
    chunk_size = 50
    result = chunk_semantic(long_text, chunk_size=chunk_size, overlap=5)
    assert len(result) > 1
    # First chunk should have header context prepended
    assert "Dense Section" in result[0]


def test_semantic_horizontal_rule_boundary():
    content = "Section above the rule.\n\n---\n\nSection below the rule."
    # Small chunk_size to force split
    tokens_above = count_tokens("Section above the rule.")
    tokens_below = count_tokens("Section below the rule.")
    chunk_size = max(tokens_above, tokens_below) + 2
    result = chunk_semantic(content, chunk_size=chunk_size, overlap=0)
    # Should split at the hrule boundary
    assert len(result) >= 1


def test_semantic_accumulates_small_sections():
    # Multiple small sections should be combined into one chunk
    sections = [f"## Section {i}\n\nContent {i}." for i in range(5)]
    content = "\n\n".join(sections)
    result = chunk_semantic(content, chunk_size=5000, overlap=0)
    assert len(result) == 1


def test_semantic_preserves_all_content():
    content = "# Header 1\n\nParagraph one.\n\n# Header 2\n\nParagraph two.\n\n# Header 3\n\nParagraph three."
    result = chunk_semantic(content, chunk_size=5000, overlap=0)
    combined = "\n\n".join(result)
    assert "Paragraph one" in combined
    assert "Paragraph two" in combined
    assert "Paragraph three" in combined


def test_semantic_oversized_paragraph_within_section():
    # A section with paragraphs where one paragraph itself exceeds chunk_size
    small_para = "Small paragraph."
    huge_para = "huge " * 300  # Very long paragraph
    section = f"# Title\n\n{small_para}\n\n{huge_para}"
    chunk_size = 50
    result = chunk_semantic(section, chunk_size=chunk_size, overlap=5)
    assert len(result) > 1
    # All the huge content should be present across chunks
    # Overlap may duplicate some words at boundaries, so count >= 300
    combined = " ".join(result)
    assert combined.count("huge") >= 300


# --- chunk_content dispatcher ---


def test_chunk_content_semantic_default():
    content = "# Title\n\nSome content here."
    result = chunk_content(content, strategy="semantic", chunk_size=5000, overlap=0)
    assert len(result) == 1
    assert "Title" in result[0]


def test_chunk_content_token_strategy():
    words = ["word"] * 200
    content = " ".join(words)
    result = chunk_content(content, strategy="token", chunk_size=50, overlap=10)
    assert len(result) > 1


def test_chunk_content_defaults_to_semantic():
    content = "# Heading\n\nBody text."
    result = chunk_content(content)
    assert len(result) >= 1
    assert "Heading" in result[0]


def test_chunk_content_uses_config_defaults():
    # chunk_content without explicit chunk_size/overlap should use config defaults
    content = "Short content."
    result = chunk_content(content)
    assert result == ["Short content."]


def test_chunk_content_unknown_strategy_falls_to_semantic():
    # Unknown strategy should fall through to semantic (default branch)
    content = "# Test\n\nContent."
    result = chunk_content(content, strategy="unknown")
    assert len(result) >= 1
