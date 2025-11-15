# Library: knowledge_vectordb

Complete vector database system for knowledge retrieval with Qdrant.

## Overview

**Location:** `src/libs/knowledge_base/knowledge_vectordb.py`

**Storage:** `.mythline/knowledge_base/` (Qdrant database)

**Use when:** Building knowledge bases, semantic search, RAG systems, documentation retrieval.

## Import

```python
from src.libs.knowledge_base import (
    index_knowledge, search_knowledge,
    create_collection, clear_collection,
    collection_exists, list_all_chunks
)
```

## Core Functions

### index_knowledge(knowledge_dir: str, fresh: bool = False) -> int
Index markdown files from directory into vector database.

**Returns:** Number of chunks indexed

**Usage:**
```python
num_chunks = index_knowledge('guides')
# Indexes all .md files in guides/ directory
```

### search_knowledge(query: str, top_k: int = 3) -> list[dict]
Semantic search across all collections.

**Returns:**
```python
[
    {
        'text': str,
        'source_file': str,
        'section_header': str,
        'score': float,
        'collection': str
    },
    ...
]
```

**Usage:**
```python
results = search_knowledge('How to create characters?', top_k=3)
for result in results:
    print(f"{result['source_file']}: {result['text']}")
```

## Collection Management

### create_collection(knowledge_dir: str)
Initialize collection for knowledge directory.

### clear_collection(knowledge_dir: str)
Delete collection and all data.

### collection_exists(knowledge_dir: str) -> bool
Check if collection exists.

### list_all_chunks(knowledge_dir: str) -> list[dict]
List all indexed chunks in collection.

## Collection Naming

- Directory: `guides/` → Collection: `guides_knowledge`
- Directory: `lore/` → Collection: `lore_knowledge`

## Index Workflow

```python
# 1. Create collection
create_collection('guides')

# 2. Parse markdown files
chunks = chunk_markdown_by_headers(md_file)

# 3. Generate embeddings
embedding = generate_embedding(chunk['text'])

# 4. Store in Qdrant
# (handled internally by index_knowledge)
```

## Configuration

**Environment:**
```env
QDRANT_PATH=.mythline/knowledge_base (default)
```

**Vector params:**
```python
size: 1536              # OpenAI embedding dimension
distance: Distance.COSINE  # Similarity metric
```

## Dependencies

**External:**
- `qdrant_client` - Vector database
- `dotenv` - Environment variables

**Internal:**
- `src.libs.embedding.generate_embedding`
- `src.libs.parsers.chunk_markdown_by_headers`

## Examples in Codebase

- manage_knowledge_base CLI (all operations)
- MCP knowledge server (search functionality)

## Common Patterns

**Index knowledge base:**
```python
num_chunks = index_knowledge('guides')
print(f"Indexed {num_chunks} chunks")
```

**Search and display:**
```python
results = search_knowledge('query', top_k=5)
for r in results:
    print(f"[{r['score']:.3f}] {r['source_file']}")
    print(f"{r['text']}\n")
```

**Rebuild collection:**
```python
clear_collection('guides')
index_knowledge('guides', fresh=True)
```

## Context Manager Pattern

```python
from src.libs.knowledge_base.knowledge_vectordb import qdrant_client

with qdrant_client() as client:
    results = client.search(...)
```
