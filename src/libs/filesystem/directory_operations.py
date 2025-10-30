import os
import csv
import io
from datetime import datetime

def list_directory(path: str) -> str:
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['name', 'path', 'is_dir', 'is_file', 'is_symlink', 'size', 'modified_time', 'created_time'])
        for entry in os.scandir(path):
            stat = entry.stat()

            created_time = datetime\
                .fromtimestamp(stat.st_birthtime
                               if hasattr(stat, 'st_birthtime')
                               else stat.st_ctime).isoformat()

            writer.writerow([
                entry.name,
                entry.path,
                entry.is_dir(),
                entry.is_file(),
                entry.is_symlink(),
                stat.st_size,
                datetime.fromtimestamp(stat.st_mtime).isoformat(),
                created_time
            ])
        return output.getvalue()
    except FileNotFoundError:
        return f"Error: Directory not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except NotADirectoryError:
        return f"Error: Not a directory: {path}"
    except Exception as e:
        return f"Error listing directory {path}: {str(e)}"

def create_directory(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
        return f"Successfully created directory: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except OSError as e:
        return f"Error: Unable to create directory {path}: {str(e)}"
    except Exception as e:
        return f"Error creating directory {path}: {str(e)}"

def file_exists(path: str) -> str:
    try:
        exists = os.path.exists(path)
        if exists:
            return f"Path exists: {path}"
        else:
            return f"Path does not exist: {path}"
    except Exception as e:
        return f"Error checking path {path}: {str(e)}"
