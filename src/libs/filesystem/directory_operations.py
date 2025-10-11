import os

def list_directory(path: str) -> list:
    return os.listdir(path)

def create_directory(path: str) -> bool:
    os.makedirs(path, exist_ok=True)
    return True

def file_exists(path: str) -> bool:
    return os.path.exists(path)
