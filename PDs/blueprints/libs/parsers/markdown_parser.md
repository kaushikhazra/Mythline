# Library: markdown_parser (Advanced)

Advanced markdown chunking with metadata for knowledge base indexing.

## Overview

**Location:** `src/libs/parsers/markdown_parser.py`

**Use when:** Indexing knowledge bases, need metadata with chunks, structured content processing.

## Import

```python
from src.libs.parsers import chunk_markdown_by_headers
```

## Function

### chunk_markdown_by_headers(file_path: str) -> list[dict]
Split markdown by H2+ headers with metadata.

**Returns:**
```python
[
    {
        'text': 'Markdown chunk content...',
        'source_file': 'character_guide.md',
        'section_header': 'Character Creation',
        'chunk_index': 0
    },
    ...
]
```

**Usage:**
```python
chunks = chunk_markdown_by_headers('guides/character_guide.md')

for chunk in chunks:
    embedding = generate_embedding(chunk['text'])
    store_with_metadata(embedding, chunk)
```

## Features

- Handles code blocks (doesn't split inside ```)
- Regex-based H2+ header detection: `^(#{2,})\s+(.+)$`
- First chunk (before any header) labeled "Introduction"
- Preserves full markdown formatting in chunks

## File-Based

Takes file path, not content string:

```python
# Correct
chunks = chunk_markdown_by_headers('path/to/file.md')

# Wrong
chunks = chunk_markdown_by_headers(file_content)
```

## Dependencies

- `re` - Regex for header detection
- `pathlib` - Path handling

## Examples in Codebase

- knowledge_vectordb (indexing markdown files)

## vs utils/markdown_parser

| Feature | parsers/markdown_parser | utils/markdown_parser |
|---------|------------------------|----------------------|
| **Metadata** | Yes | No |
| **Input** | File path | String content |
| **Headers** | H2+ | H2 only |
| **Code blocks** | Handled | Not handled |
| **Use for** | Knowledge indexing | Simple splitting |
