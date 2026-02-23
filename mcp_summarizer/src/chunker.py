"""Chunking engine for splitting content into LLM-sized pieces."""

import re

from src.config import DEFAULT_CHUNK_OVERLAP_TOKENS, DEFAULT_CHUNK_SIZE_TOKENS
from src.tokens import count_tokens, decode, encode

# Primary boundaries: markdown headers and horizontal rules
HEADER_PATTERN = re.compile(r"(?=^#{1,4}\s|\n-{3,}\n)", re.MULTILINE)


def _split_by_paragraphs(text: str) -> list[str]:
    """Split text at paragraph breaks (double newlines).

    Secondary boundary — used when a header-delimited section exceeds
    chunk_size but has natural paragraph breaks within it.
    """
    parts = re.split(r"\n\n+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_semantic(
    content: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split content at markdown structural boundaries.

    Algorithm:
    1. Split content by headers and horizontal rules (primary boundaries).
    2. Track the header stack (most recent header at each level).
    3. Accumulate units into chunks until approaching chunk_size.
    4. If a single unit exceeds chunk_size, try splitting at paragraph
       breaks (secondary boundaries) before falling back to token-based.
    5. Prepend active header context to each chunk for continuity.
    """
    sections = HEADER_PATTERN.split(content)
    sections = [s.strip() for s in sections if s.strip()]

    if not sections:
        return [content] if content.strip() else []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0
    header_context = ""  # Most recent top-level header

    for section in sections:
        section_tokens = count_tokens(section)

        # Track header context for propagation
        header_match = re.match(r"^(#{1,2}\s+.+)", section)
        if header_match:
            header_context = header_match.group(1)

        if section_tokens > chunk_size:
            # Oversized section — finalize current chunk
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0

            # Try paragraph-level splitting first (secondary boundary)
            paragraphs = _split_by_paragraphs(section)
            if len(paragraphs) > 1:
                # Re-accumulate paragraphs into sub-chunks
                sub_parts: list[str] = []
                sub_tokens = 0
                if header_context:
                    sub_parts.append(header_context)
                    sub_tokens = count_tokens(header_context)
                for para in paragraphs:
                    para_tokens = count_tokens(para)
                    if para_tokens > chunk_size:
                        # Single paragraph too large — token-split it
                        if sub_parts:
                            chunks.append("\n\n".join(sub_parts))
                            sub_parts = []
                            sub_tokens = 0
                        chunks.extend(chunk_token_based(para, chunk_size, overlap))
                    elif sub_tokens + para_tokens > chunk_size and sub_parts:
                        chunks.append("\n\n".join(sub_parts))
                        sub_parts = [header_context] if header_context else []
                        sub_tokens = count_tokens(header_context) if header_context else 0
                        sub_parts.append(para)
                        sub_tokens += para_tokens
                    else:
                        sub_parts.append(para)
                        sub_tokens += para_tokens
                if sub_parts:
                    chunks.append("\n\n".join(sub_parts))
            else:
                # No paragraph breaks — fall back to token-based split
                sub_chunks = chunk_token_based(section, chunk_size, overlap)
                if header_context and sub_chunks:
                    sub_chunks[0] = header_context + "\n\n" + sub_chunks[0]
                chunks.extend(sub_chunks)
            continue

        if current_tokens + section_tokens > chunk_size and current_parts:
            # Would exceed limit — finalize current chunk
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_tokens = 0
            # Propagate header context to new chunk
            if header_context:
                current_parts.append(header_context)
                current_tokens = count_tokens(header_context)

        current_parts.append(section)
        current_tokens += section_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


def chunk_token_based(
    content: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """Split content at fixed token boundaries with overlap."""
    tokens = encode(content)

    if len(tokens) <= chunk_size:
        return [content]

    overlap = min(overlap, chunk_size - 1)
    chunks: list[str] = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(decode(tokens[start:end]))
        if end >= len(tokens):
            break
        start = end - overlap

    return chunks


def chunk_content(
    content: str,
    strategy: str = "semantic",
    chunk_size: int = DEFAULT_CHUNK_SIZE_TOKENS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """Chunk content using the specified strategy."""
    if strategy == "token":
        return chunk_token_based(content, chunk_size, overlap)
    return chunk_semantic(content, chunk_size, overlap)
