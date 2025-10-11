def read_file(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path: str, content: str) -> bool:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def append_file(path: str, content: str) -> bool:
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content)
    return True
