# MCP Knowledge Base Server Blueprint

This blueprint provides a comprehensive MCP server for searching and listing indexed knowledge base content using vector search.

## Overview

The Knowledge Base MCP server provides tools for semantic search across vectorized knowledge bases and listing indexed content. It uses vector embeddings for intelligent information retrieval from markdown documentation files.

## Structure

```
src/mcp_servers/mcp_knowledge_base/
├── __init__.py
└── server.py

start_knowledge_base.bat (at project root)
```

## Implementation

### `server.py`

```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.knowledge_base.knowledge_vectordb import search_knowledge, list_all_chunks, get_all_knowledge_collections

load_dotenv()

port = int(os.getenv('MCP_KNOWLEDGE_BASE_PORT', 8003))
server = FastMCP(name="Knowledge Base MCP", port=port)


@server.tool()
def search_guide_knowledge(query: str, top_k: int = 3) -> str:
    """Searches all knowledge bases for relevant information.

    Args:
        query (str): The search query (natural language)
        top_k (int): Number of results to return (default: 3)

    Returns:
        str: Formatted search results with relevant sections from all knowledge bases
    """
    print(f"Searching knowledge bases for: {query}")

    all_collections = get_all_knowledge_collections()

    if not all_collections:
        return "Error: No knowledge bases found. Please run 'manage_knowledge_base.bat load <directory>' first."

    results = search_knowledge(query, top_k)

    if not results:
        return f"No relevant information found for: {query}"

    output = f"Found {len(results)} relevant section(s) across {len(all_collections)} knowledge base(s):\n\n"

    for i, result in enumerate(results, 1):
        output += f"--- Result {i} (Score: {result['score']:.3f}) ---\n"
        output += f"Collection: {result['collection']}\n"
        output += f"Source: {result['source_file']}\n"
        output += f"Section: {result['section_header']}\n\n"
        output += f"{result['text']}\n\n"

    print(f"{output}")

    return output


@server.tool()
def list_indexed_content(knowledge_dir: str = "guides") -> str:
    """Lists all indexed content in a specific knowledge base.

    Args:
        knowledge_dir (str): The knowledge directory to list (default: "guides")

    Returns:
        str: Summary of all indexed chunks in the specified knowledge base
    """
    print(f"Listing indexed content from: {knowledge_dir}")

    from src.libs.knowledge_base.knowledge_vectordb import collection_exists

    if not collection_exists(knowledge_dir):
        return f"Error: Knowledge base '{knowledge_dir}' not initialized. Please run 'manage_knowledge_base.bat load {knowledge_dir}' first."

    chunks = list_all_chunks(knowledge_dir)

    if not chunks:
        return f"No content indexed in '{knowledge_dir}' knowledge base."

    output = f"Total indexed chunks in '{knowledge_dir}': {len(chunks)}\n\n"

    for chunk in chunks:
        output += f"[{chunk['id']}] {chunk['source_file']} - {chunk['section_header']}\n"
        output += f"    {chunk['text_preview']}\n\n"

    print(f"{output}")

    return output


if __name__=='__main__':
    server.run(transport='streamable-http')
```

### `__init__.py`

```python
from .server import server

__all__ = ['server']
```

### `start_knowledge_base.bat` (at project root)

```batch
@echo off
echo Starting Knowledge Base MCP Server...
python -m src.mcp_servers.mcp_knowledge_base.server
```

This file should be placed at the root of the project for easy access.

## Configuration

### Environment Variables

Add to `.env`:

```
MCP_KNOWLEDGE_BASE_PORT=8003
```

### Agent Configuration

Add to agent's `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "url": "http://localhost:8003/mcp"
    }
  }
}
```

## Available Tools

### search_guide_knowledge(query: str, top_k: int = 3) -> str

Performs semantic search across all indexed knowledge bases using vector similarity.

**Parameters:**
- `query`: Natural language search query
- `top_k`: Number of results to return (default: 3)

**Returns:**
- Formatted string with search results including:
  - Similarity score
  - Collection name
  - Source file
  - Section header
  - Relevant text content

**Features:**
- Searches across all knowledge collections
- Returns results ranked by semantic similarity
- Includes context from source documents
- Handles cases with no knowledge bases

The agent uses this tool automatically when instructed to search knowledge.

### list_indexed_content(knowledge_dir: str = "guides") -> str

Lists all indexed chunks in a specific knowledge base.

**Parameters:**
- `knowledge_dir`: Directory name of the knowledge base (default: "guides")

**Returns:**
- Summary of all indexed chunks with:
  - Chunk ID
  - Source file
  - Section header
  - Text preview

**Features:**
- Lists all content in specified collection
- Provides overview of indexed documents
- Shows section-level granularity
- Validates collection exists

The agent uses this tool automatically when instructed to list knowledge base content.

## Usage in Agents

### Agent Integration

Load the MCP server in the agent's `__init__` method:

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers
from src.libs.utils.config_loader import load_mcp_config

class ResearchAgent:
    AGENT_ID = "research_agent"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )
```

### Using the Tools

The knowledge base tools are automatically available to the agent. Instruct the agent about these capabilities in the system prompt.

**System Prompt Example:**
```markdown
You have access to the following knowledge base tools:
- search_guide_knowledge: Search all knowledge bases using natural language queries
- list_indexed_content: List all indexed content in a specific knowledge base

Use search_guide_knowledge when you need to find information from documentation.
Use list_indexed_content to see what content is available in a knowledge base.
```

The agent will automatically use these tools when researching topics covered in the knowledge bases.

## Dependencies

### Required Libraries

```python
from src.libs.knowledge_base.knowledge_vectordb import (
    search_knowledge,
    list_all_chunks,
    get_all_knowledge_collections,
    collection_exists
)
```

### Knowledge Base Library

The knowledge base library provides:
- Vector search functionality
- Collection management
- Chunk listing and retrieval
- Embedding generation

## Knowledge Base Management

### Loading Knowledge

Before using the knowledge base MCP server, knowledge must be loaded:

```bash
manage_knowledge_base.bat load guides
```

This processes markdown files in the `guides/` directory and creates vector embeddings.

### Supported Formats

- Markdown files (.md)
- Hierarchical section structure
- Metadata preservation

### Indexing Strategy

- Documents split into sections
- Each section vectorized separately
- Preserves source file and header context
- Enables fine-grained retrieval

## Best Practices

### Query Formulation

**Good Queries:**
- "How to create a new agent in Pydantic AI"
- "What is the agent memory system"
- "Best practices for system prompts"

**Less Effective:**
- Single word queries
- Very generic terms
- Queries outside knowledge domain

### Result Count Selection

```python
# For focused answers
search_guide_knowledge("specific topic", top_k=3)

# For comprehensive research
search_guide_knowledge("broad topic", top_k=10)
```

### Collection Naming

Use descriptive directory names:
- `guides/` - Development guides
- `docs/` - API documentation
- `references/` - Reference materials

## Customization Options

### Adjusting Search Results

```python
@server.tool()
def search_guide_knowledge(query: str, top_k: int = 3, min_score: float = 0.5) -> str:
    """Search with minimum score threshold."""
    results = search_knowledge(query, top_k)

    filtered_results = [r for r in results if r['score'] >= min_score]

    if not filtered_results:
        return f"No results found with score >= {min_score}"

    # Format results...
```

### Custom Formatting

```python
@server.tool()
def search_guide_knowledge_json(query: str, top_k: int = 3) -> dict:
    """Returns results as JSON instead of formatted string."""
    results = search_knowledge(query, top_k)

    return {
        "query": query,
        "count": len(results),
        "results": results
    }
```

### Collection Filtering

```python
@server.tool()
def search_specific_collection(query: str, collection: str, top_k: int = 3) -> str:
    """Searches only in a specific collection."""
    from src.libs.knowledge_base.knowledge_vectordb import search_knowledge_in_collection

    results = search_knowledge_in_collection(query, collection, top_k)

    # Format results...
```

## Advanced Features

### Multi-Collection Search

The server automatically searches across all loaded collections:

```python
all_collections = get_all_knowledge_collections()
# Returns: ['guides', 'docs', 'references']

results = search_knowledge(query, top_k)
# Searches all collections and returns ranked results
```

### Metadata Access

Search results include rich metadata:

```python
result = {
    'score': 0.856,
    'collection': 'guides',
    'source_file': 'agent_guide.md',
    'section_header': '## Creating Agents',
    'text': 'Full section text...',
    'id': 'chunk_123'
}
```

### Content Listing

View all indexed content in a collection:

```python
chunks = list_all_chunks('guides')
# Returns list of all chunks with previews
```

## Testing

### Start Server

```bash
python -m src.mcp_servers.mcp_knowledge_base.server
```

Or:

```bash
start_knowledge_base.bat
```

### Verify Knowledge Base

```bash
manage_knowledge_base.bat status
```

### Test Search

```python
from src.mcp_servers.mcp_knowledge_base.server import search_guide_knowledge

result = search_guide_knowledge("agent creation")
print(result)
```

### Verify Agent Integration

Test that agents can:
1. Search knowledge bases
2. Retrieve relevant sections
3. List indexed content
4. Handle empty results

## Common Use Cases

### Documentation Search

**System Prompt:**
```markdown
When users ask about Pydantic AI features or development patterns, use search_guide_knowledge to find relevant information from the documentation.
```

### Code Examples

**System Prompt:**
```markdown
For code examples, search the knowledge base for relevant patterns and best practices before suggesting solutions.
```

### Best Practices Lookup

**System Prompt:**
```markdown
When asked about best practices, use search_guide_knowledge to find established patterns in the guides.
```

### Knowledge Discovery

**System Prompt:**
```markdown
To understand what information is available, use list_indexed_content to browse the knowledge base contents.
```

## Performance Considerations

### Vector Search Speed

- Fast for small to medium collections (< 10,000 chunks)
- Results returned in milliseconds
- Scales with number of indexed chunks

### Memory Usage

- Embeddings cached in memory
- ChromaDB handles persistence
- Minimal overhead per query

### Indexing Time

- Initial indexing takes time
- Incremental updates supported
- Re-indexing required for changes

## Troubleshooting

### No Knowledge Bases Found

**Error:** `No knowledge bases found`

**Solution:**
```bash
manage_knowledge_base.bat load guides
```

### Collection Not Initialized

**Error:** `Knowledge base 'name' not initialized`

**Solution:**
```bash
manage_knowledge_base.bat load name
```

### No Results Found

- Check if content is indexed
- Try broader queries
- Verify query is relevant to indexed content

### Poor Result Quality

- Increase `top_k` for more results
- Refine query to be more specific
- Check that relevant content is indexed

## Knowledge Base Structure

### Expected Directory Layout

```
guides/
├── agent_guide.md
├── memory_guide.md
├── mcp_guide.md
└── prompt_guide.md
```

### Document Format

Markdown files with clear section headers:

```markdown
# Document Title

## Section 1

Content here...

## Section 2

Content here...
```

### Indexing Process

1. Parse markdown files
2. Split by section headers
3. Generate embeddings for each section
4. Store in vector database
5. Preserve metadata

## Integration Examples

### Research Agent

```python
class ResearchAgent:
    def __init__(self, session_id: str):
        # Load knowledge base MCP
        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            system_prompt="""
            You are a research assistant with access to comprehensive guides.

            Use search_guide_knowledge to find relevant information before answering questions.
            Always cite sources from the search results.
            """,
            toolsets=servers
        )
```

### Support Agent

```python
class SupportAgent:
    def __init__(self, session_id: str):
        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            system_prompt="""
            You help users with technical questions.

            When users ask questions:
            1. Search knowledge base for relevant information
            2. Synthesize answer from search results
            3. Provide references to documentation
            """,
            toolsets=servers
        )
```

## Related Blueprints

- `mcp_base.md` - Base MCP server structure
- `web/mcp_web_search.md` - Web-based information retrieval
- `filesystem/mcp_filesystem.md` - File operations for knowledge management
