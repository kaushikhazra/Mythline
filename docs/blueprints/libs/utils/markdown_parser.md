# Library: markdown_parser (Legacy)

Simple H2-based markdown chunking.

## Overview

**Location:** `src/libs/utils/markdown_parser.py`

**Status:** Legacy - Consider using `parsers/markdown_parser` for new code

**Use when:** Simple markdown splitting without metadata needed.

## Import

```python
from src.libs.utils.markdown_parser import parse_markdown
```

## Function

### parse_markdown(markdown: str) -> list[str]
Splits markdown by H2 (##) headers.

**Usage:**
```python
story_md = read_file('story.md')
chunks = parse_markdown(story_md)

for chunk in chunks:
    process(chunk)
```

## Dependencies
- `marko` - Markdown parser library

## Note
For new code with metadata needs, use `src.libs.parsers.chunk_markdown_by_headers` instead.

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Examples in Codebase
- generate_shots CLI (legacy usage)
