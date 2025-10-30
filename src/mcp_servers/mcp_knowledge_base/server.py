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
