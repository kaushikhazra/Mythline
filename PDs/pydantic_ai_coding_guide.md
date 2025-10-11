## Agent Folder Structure
```bash
/project_root
    .env
    .evn.example
    mcp_config.json
    system_prompt.md
    /src
        __init__.py
        /ui
            __init__.py
            cli.py
        /agent
            __init__.py
            agent.py
        /mcp_servers
            __init__.py
            /mcp_{server_name}
                __init__.py
                server.py
        /libs
            __init__.py
            /xyx
                __init__.py
                xyz.py
```

## `.evn.example`
```conf
OPENAI_API_KEY=
LLM_MODEL=gpt-5-nano
```

## `mcp_config.json`
```json
{
  "mcpServers": {
    "server-name": {
      "url": "http://localhost:port_numer/mcp"
    }
  }
}
```

## `system_prompt.md`
```markdown
## Persona
You are a|an {Persona}

## Task
Your task is to {the task}

## Instructions
Follow the below instructions to perform your task
- Instruction 1
- Instruction 2
...
- Instruction n

## Constraints
- Avoid {what to avoid}
- Important {what is important}
...
- {Any other constraint}

## Output
{specify output format based on the requirement}

```

## `cli.py`
```python
# Imports at the top

# Argument parsing using arg parser

# Invoke the agent to produce output
```

## Example CLI With Session Loading
### `\ui\cli.py`
```python
from src.agents.story_creator_agent.agent import StoryCreator
from src.libs.utils.argument_parser import get_session


session_id = get_session(StoryCreator.AGENT_ID)
print(f"Session: {session_id}\n")
story_creator = StoryCreator(session_id)

while True:
    prompt = input("🙍 User‍: ")

    if prompt == "exit":
        break

    response = story_creator.run(prompt)
    print(f"\n🤖 Agent: {response.output} \n\n")
```


## `agent.py` 

### Code Sample for Simple Agent
```python
import os
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

llm_model = f"openai:{os.getenv('LLM_MODEL')}"
system_prompt=None

with open("system_prompt.md", "r") as file:
    system_prompt = file.read()
    print(f"System Prompt:\n{system_prompt}\n")

agent = Agent(  
    llm_model,
    system_prompt=system_prompt,
)

while (True):
    prompt = input("User: ")

    if (prompt == "exit"):
        break

    agent_output = agent.run_sync(prompt)
    print(f"Agent:{agent_output.output}\n")
```

### Code Sample for Simple Agent With Memory
```python
import os
from pydantic_ai import Agent
from dotenv import load_dotenv

load_dotenv()

llm_model = f"openai:{os.getenv('LLM_MODEL')}"
system_prompt=None

with open("system_prompt.md", "r") as file:
    system_prompt = file.read()
    print(f"System Prompt:\n{system_prompt}\n")

agent = Agent(  
    llm_model,
    system_prompt=system_prompt
)


messages = None
while (True):
    prompt = input("User: ")

    if (prompt == "exit"):
        break

    agent_output = agent.run_sync(prompt, message_history=messages)
    messages = agent_output.all_messages()
    print(f"Agent: {agent_output.output}\n")
```

### Code Sample for Agent with Tool Call
```python
import os
from datetime import datetime as dt
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

load_dotenv()

llm_model = f"openai:{os.getenv('LLM_MODEL')}"
system_prompt=None

with open("system_prompt.md", "r") as file:
    system_prompt = file.read()
    print(f"System Prompt:\n{system_prompt}\n")

agent = Agent(  
    llm_model,
    system_prompt=system_prompt
)

@agent.tool_plain
async def current_time() -> str:
    """
    Provides current time of the user
    """
    print("Current time requested")
    return str(dt.now())

messages = None
while (True):
    prompt = input("User: ")

    if (prompt == "exit"):
        break

    agent_output = agent.run_sync(prompt, message_history=messages)
    messages = agent_output.all_messages()
    print(f"Agent: {agent_output.output}\n")
```

### Code Sample for Configurable MCP
```python
import os
from datetime import datetime as dt
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_servers

load_dotenv()

llm_model = f"openai:{os.getenv('LLM_MODEL')}"
system_prompt=None

with open("system_prompt.md", "r") as file:
    system_prompt = file.read()
    print(f"System Prompt:\n{system_prompt}\n")


servers = load_mcp_servers('mcp_config.json')

agent = Agent(  
    llm_model,
    system_prompt=system_prompt,
    toolsets=servers
)

messages = None
while (True):
    prompt = input("User: ")

    if (prompt == "exit"):
        break

    agent_output = agent.run_sync(prompt, message_history=messages)
    messages = agent_output.all_messages()
    print(f"Agent: {agent_output.output}\n")
```

### Code Sample for Object Oriented Agent
```python
from dotenv import load_dotenv

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult

load_dotenv()

class {AgentName}:

    def __init__(self):
        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_agent_prompt(__file__)
        servers = load_mcp_servers(load_mcp_config(__file__))

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )

    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        return agent_output

```

### Code Sample to Persist message (Context Persistence)
```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import load_mcp_servers
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_agent_prompt
from src.libs.utils.config_loader import load_mcp_config
from src.libs.agent_memory.context_memory import save_context, load_context

load_dotenv()

class {AgentName}:
    AGENT_ID = "story_creator"

    def __init__(self, session_id: str):
        self.session_id = session_id

        llm_model = f"openai:{os.getenv('LLM_MODEL')}"
        system_prompt = load_agent_prompt(__file__)

        servers = load_mcp_servers(load_mcp_config(__file__))


        self.messages = load_context(self.AGENT_ID, session_id)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt,
            toolsets=servers
        )
    
    def run(self, prompt: str) -> AgentRunResult:
        agent_output = self.agent.run_sync(prompt, message_history=self.messages)
        self.messages = agent_output.all_messages()
        save_context(self.AGENT_ID, self.session_id, self.messages)
        return agent_output
```

## `server.py`
```python
from mcp.server.fastmcp import FastMCP
from datetime import datetime as dt

server = FastMCP()

@server.tool()
async def the_tool(ctx: RunContext[required_type], arg1: required_type, ..., argn: required_type] ) -> return_type:
    """ What the tool does
    Args:
        arg1 (type): Description of the argument
        ...
        argn (type): Description of the argument
    Return:
        (type): Description of the return type
    
    """
    # the logic goes here

if __name__=='__main__':
    server.run(transport='streamable-http')
```

## Web Search MCP Server
### `\mcp_servers\mcp_web_search`
```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.web.duck_duck_go import search
from src.libs.web.crawl import crawl_content

load_dotenv()

port = int(os.getenv('MCP_WEB_SEARCH_PORT', 8000))
server = FastMCP(name="Web Search MCP", port=port)

@server.tool()
async def web_search(query: str) -> str:
    """Searches the web using DuckDuckGo and crawls the top results to fetch their content.
    Args:
        query (str): The search query to look for
    Return:
        (str): Combined content from the top search results
    """

    print(f"Searching for : {query}")

    content = ""
    search_results = search(query)
    for result in search_results:
        page_content = await crawl_content(result['href'])
        content += f"{result['href']} \n\n {page_content[:3000]} \n\n"

    print(content[:300],"...")

    return content

if __name__=='__main__':
    server.run(transport='streamable-http')
```

## Web Crawler MCP Server
### `\mcp_servers\mcp_web_crawler`
```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.web.crawl import crawl_content

load_dotenv()

port = int(os.getenv('MCP_WEB_CRAWLER_PORT', 8001))
server = FastMCP(name="Web Crawler MCP", port=port)

@server.tool()
async def crawl(url: str) -> str:
    """Crawls content from a given URL and returns it as markdown.
    Args:
        url (str): The URL to crawl content from
    Return:
        (str): The crawled content in markdown format
    """

    print(f"Crawling content from: {url}")

    content = await crawl_content(url)

    print(f"Crawled {len(content)} characters from {url}")

    return content

if __name__=='__main__':
    server.run(transport='streamable-http')
```

## Filesystem MCP Server
### `\mcp_servers\mcp_filesystem`
```python
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.libs.filesystem.file_operations import read_file, write_file, append_file
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
def write(path: str, content: str) -> bool:
    """Writes content to a file, overwriting existing content.

    Args:
        path (str): The file path to write to
        content (str): The content to write

    Returns:
        bool: True if successful
    """
    print(f"Writing to file: {path}")
    return write_file(path, content)

@server.tool()
def append(path: str, content: str) -> bool:
    """Appends content to the end of a file.

    Args:
        path (str): The file path to append to
        content (str): The content to append

    Returns:
        bool: True if successful
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
def create_dir(path: str) -> bool:
    """Creates a directory, including parent directories if needed.

    Args:
        path (str): The directory path to create

    Returns:
        bool: True if successful
    """
    print(f"Creating directory: {path}")
    return create_directory(path)

@server.tool()
def exists(path: str) -> bool:
    """Checks if a file or directory exists.

    Args:
        path (str): The file or directory path to check

    Returns:
        bool: True if exists, False otherwise
    """
    print(f"Checking existence: {path}")
    return file_exists(path)

if __name__=='__main__':
    server.run(transport='streamable-http')
```

## `xyz.py` The library modules
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



## Coding Style
- All imports should be at the top. Do NOT use inline imports
- Use Object Oriented Programming where necessary
- Use KISS philosophy.
- Avoid any extra validation and verification.
- Avoid adding any log statement.
- Follow the indentation as described in the sample codes.
- Follow the naming convention as used in the sample codes.
- The above structure is the sum of all. Pick and choose what is necessary for the project. 
- Avoid using version in `requirement.txt` so that latest can be used all the time.
- String indentation style
    ```python
    # Single string
    str = "Some value"

    # Multiline string
    str="""
        This is line 1
        this is line 2
    """
    ```