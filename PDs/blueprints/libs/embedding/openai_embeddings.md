# Library: openai_embeddings

Generate OpenAI embeddings for vector search via OpenRouter.

## Overview

**Location:** `src/libs/embedding/openai_embeddings.py`

**Provider:** OpenRouter (centralized API for multiple embedding providers)

**Use when:** Vectorizing text for knowledge bases, semantic search.

## Import

```python
from src.libs.embedding import generate_embedding, get_openai_client, get_embedding_model
```

## Functions

### generate_embedding(text: str) -> list[float]
Generate 1536-dimensional embedding vector.

**Usage:**
```python
embedding = generate_embedding('Text to vectorize')
# Returns: [0.023, -0.015, ..., 0.042]  # 1536 floats
```

### get_openai_client() -> OpenAI
Get singleton OpenAI client.

### get_embedding_model() -> str
Get configured embedding model name.

## Configuration

**Environment variables:**
```env
OPENROUTER_API_KEY=required
EMBEDDING_MODEL=openai/text-embedding-3-small (default, use OpenRouter format: provider/model-name)
```

**Available Models via OpenRouter:**
- `openai/text-embedding-3-small` (1536 dimensions, default)
- `openai/text-embedding-3-large` (3072 dimensions)
- `mistralai/mistral-embed-2312` (1024 dimensions)
- `qwen/qwen3-embedding-8b` (1024 dimensions)

**Vector dimensions:** 1536 (for openai/text-embedding-3-small)

## Singleton Pattern
```python
_openai_client: Optional[OpenAI] = None

def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv('OPENROUTER_API_KEY')
        )
    return _openai_client
```

**Note:** Uses OpenAI SDK with OpenRouter endpoint for unified API access.

## Dependencies
- `openai` - OpenAI Python SDK
- `dotenv` - Environment variable loading

## Examples in Codebase
- knowledge_vectordb (index and search operations)
