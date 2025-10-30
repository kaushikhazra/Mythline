import re
from pathlib import Path


def chunk_markdown_by_headers(file_path: str) -> list[dict]:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    chunks = []
    lines = content.split('\n')
    current_chunk = []
    current_header = None
    chunk_index = 0
    in_code_block = False

    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            current_chunk.append(line)
            continue

        if not in_code_block:
            header_match = re.match(r'^(#{2,})\s+(.+)$', line)

            if header_match:
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append({
                            'text': chunk_text,
                            'source_file': Path(file_path).name,
                            'section_header': current_header or 'Introduction',
                            'chunk_index': chunk_index
                        })
                        chunk_index += 1

                current_header = header_match.group(2)
                current_chunk = [line]
            else:
                current_chunk.append(line)
        else:
            current_chunk.append(line)

    if current_chunk:
        chunk_text = '\n'.join(current_chunk).strip()
        if chunk_text:
            chunks.append({
                'text': chunk_text,
                'source_file': Path(file_path).name,
                'section_header': current_header or 'Introduction',
                'chunk_index': chunk_index
            })

    return chunks
