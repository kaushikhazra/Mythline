import os

def file_exists(path: str) -> bool:
    return os.path.isfile(path)

def read_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except UnicodeDecodeError:
        return f"Error: Unable to decode file as UTF-8: {path}"
    except Exception as e:
        return f"Error reading file {path}: {str(e)}"

def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to file: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except OSError as e:
        return f"Error: Unable to write to file {path}: {str(e)}"
    except Exception as e:
        return f"Error writing file {path}: {str(e)}"

def append_file(path: str, content: str) -> str:
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully appended to file: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except OSError as e:
        return f"Error: Unable to append to file {path}: {str(e)}"
    except Exception as e:
        return f"Error appending to file {path}: {str(e)}"

def rename_file(old_path: str, new_path: str) -> str:
    try:
        os.rename(old_path, new_path)
        return f"Successfully renamed {old_path} to {new_path}"
    except FileNotFoundError:
        return f"Error: File not found: {old_path}"
    except PermissionError:
        return f"Error: Permission denied"
    except OSError as e:
        return f"Error: Unable to rename file: {str(e)}"
    except Exception as e:
        return f"Error renaming file: {str(e)}"

def delete_file(path: str) -> str:
    try:
        os.remove(path)
        return f"Successfully deleted file: {path}"
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except OSError as e:
        return f"Error: Unable to delete file {path}: {str(e)}"
    except Exception as e:
        return f"Error deleting file {path}: {str(e)}"
