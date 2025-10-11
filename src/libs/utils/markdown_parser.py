from marko import Markdown
from marko.md_renderer import MarkdownRenderer

def parse_markdown(markdown: str) -> list[str]:
    md = Markdown()
    doc = md.parse(markdown)

    chunks = []
    current_chunk = []

    for element in doc.children:
        if element.get_type() == 'Heading' and element.level == 2:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [element]
        else:
            current_chunk.append(element)

    if current_chunk:
        chunks.append(current_chunk)

    renderer = MarkdownRenderer()

    rendered_chunks = []
    for chunk in chunks:
        chunk_md = ""
        for element in chunk:
            chunk_md += renderer.render(element)
        rendered_chunks.append(chunk_md)

    return rendered_chunks
