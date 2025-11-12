import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.filesystem.file_operations import read_file, write_file, append_file, rename_file, delete_file
from src.libs.filesystem.directory_operations import list_directory, create_directory, file_exists

load_dotenv()

port = int(os.getenv('MCP_FILESYSTEM_PORT', 8002))
server = FastMCP(name="Filesystem MCP", port=port)

@server.tool()
def read(path: str) -> str:
    """Reads the content of a file.

    Args:
        path (str): The file path to read from

    Returns:
        str: The content of the file
    """
    print(f"Reading file: {path}")
    return read_file(path)

@server.tool()
def write(path: str, content: str) -> str:
    """Writes content to a file, overwriting existing content.

    Args:
        path (str): The file path to write to
        content (str): The content to write

    Returns:
        str: Success or error message
    """
    print(f"Writing to file: {path}")
    return write_file(path, content)

@server.tool()
def append(path: str, content: str) -> str:
    """Appends content to the end of a file.

    Args:
        path (str): The file path to append to
        content (str): The content to append

    Returns:
        str: Success or error message
    """
    print(f"Appending to file: {path}")
    return append_file(path, content)

@server.tool()
def list_dir(path: str) -> list:
    """Lists all files and directories in a directory.

    Args:
        path (str): The directory path to list

    Returns:
        list: List of file and directory names
    """
    print(f"Listing directory: {path}")
    return list_directory(path)

@server.tool()
def create_dir(path: str) -> str:
    """Creates a directory, including parent directories if needed.

    Args:
        path (str): The directory path to create

    Returns:
        str: Success or error message
    """
    print(f"Creating directory: {path}")
    return create_directory(path)

@server.tool()
def exists(path: str) -> str:
    """Checks if a file or directory exists.

    Args:
        path (str): The file or directory path to check

    Returns:
        str: Existence status or error message
    """
    print(f"Checking existence: {path}")
    return file_exists(path)

@server.tool()
def rename(old_path: str, new_path: str) -> str:
    """Renames or moves a file or directory.

    Args:
        old_path (str): The current file or directory path
        new_path (str): The new file or directory path

    Returns:
        str: Success or error message
    """
    print(f"Renaming: {old_path} -> {new_path}")
    return rename_file(old_path, new_path)

@server.tool()
def delete(path: str) -> str:
    """Deletes a file.

    Args:
        path (str): The file path to delete

    Returns:
        str: Success or error message
    """
    print(f"Deleting file: {path}")
    return delete_file(path)

if __name__=='__main__':
    server.run(transport='streamable-http')
