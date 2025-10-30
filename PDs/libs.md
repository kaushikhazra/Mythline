# Library Template And Shared Libraries

## Library file structure
```python
# imports at the top

# logic divided into methods
```

## Agent Memory Handler Library
### `\libs\agent_memory\context_memory.py`
```python
from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python
import json
from pathlib import Path


CONTEXT_DIR = ".mythline"


def save_context(agent_id, session_id, messages: list[ModelMessage]):
    json_data = to_jsonable_python(messages)

    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory/{session_id}.json")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w') as f:
        json.dump(json_data, f, indent=2)


def load_context(agent_id, session_id) -> list[ModelMessage]:
    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory/{session_id}.json")

    if not file_path.exists():
        return []

    with open(file_path, 'r') as f:
        json_data = json.load(f)

    return ModelMessagesTypeAdapter.validate_python(json_data)


def get_latest_session(agent_id: str) -> str | None:
    context_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory")

    if not context_path.exists():
        return None

    json_files = sorted(context_path.glob("*.json"), key=lambda p: p.stem, reverse=True)

    if not json_files:
        return None

    return json_files[0].stem

```

## Web Crawler Library
### `\libs\web\crawl.py`
```python
from crawl4ai import AsyncWebCrawler

async def crawl_content(url: str) -> str:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        return result.markdown
```

## Web Search Library
### `\libs\web\duck_duck_go.py`
```python
from ddgs import DDGS

def search(query: str) -> list:
    results = None
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=5)
    return results
```

## File Operations Library
### `\libs\filesystem\file_operations.py`
```python
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
```

## Directory Operations Library
### `\libs\filesystem\directory_operations.py`
```python
import os

def list_directory(path: str) -> list:
    return os.listdir(path)

def create_directory(path: str) -> bool:
    os.makedirs(path, exist_ok=True)
    return True

def file_exists(path: str) -> bool:
    return os.path.exists(path)
```

## Prompt Loader Library
### `\libs\utils\prompt_loader.py`
```python
import os


def load_agent_prompt(caller_file, prompt_name="system_prompt.md"):
    """
    Load a prompt file from the agent's prompts directory.

    Args:
        caller_file: The __file__ variable from the calling agent script
        prompt_name: Name of the prompt file (default: "system_prompt.md")

    Returns:
        str: Content of the prompt file
    """
    agent_dir = os.path.dirname(os.path.abspath(caller_file))
    prompt_path = os.path.join(agent_dir, "prompts", prompt_name)

    with open(prompt_path, "r") as file:
        return file.read()
```

## Config Loader Library
### `\libs\utils\config_loader.py`
```python
import os


def load_mcp_config(caller_file):
    """
    Load the MCP config file path from the agent's config folder.

    Args:
        caller_file: The __file__ variable from the calling agent script

    Returns:
        str: Full path to mcp_config.json in agent's config folder
    """
    agent_dir = os.path.dirname(os.path.abspath(caller_file))
    config_path = os.path.join(agent_dir, "config", "mcp_config.json")
    return config_path
```

## Output Writer Library
### `\libs\utils\output_writer.py`
```python
def write_output(content, filename="output.md"):
    with open(filename, "w", encoding='utf-8') as file:
        file.write(content)
```

## Argument Parser Library
### `\libs\utils\argument_parser.py`
```python
import argparse
from datetime import datetime
from src.libs.agent_memory.context_memory import get_latest_session


def get_session(agent_id: str) -> str:
    parser = argparse.ArgumentParser(description='Story Creator CLI')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--session', type=str, help='Load specific session by ID')
    group.add_argument('--resume', action='store_true', help='Resume most recent session')

    args = parser.parse_args()

    if args.resume:
        session_id = get_latest_session(agent_id)
        if not session_id:
            print("No previous sessions found. Creating new session.")
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    elif args.session:
        session_id = args.session
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    return session_id
```
