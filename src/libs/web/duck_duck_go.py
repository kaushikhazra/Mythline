from ddgs import DDGS

def search(query: str) -> list:
    results = None
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
    return results
