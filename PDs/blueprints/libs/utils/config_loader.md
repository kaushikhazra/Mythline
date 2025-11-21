# Library: config_loader

Load MCP configuration file path for orchestrator agents.

## Overview

**Location:** `src/libs/utils/config_loader.py`

**Use when:** Initializing orchestrator agents that need MCP servers.

## Import

```python
from src.libs.utils.config_loader import load_mcp_config
```

## Function

### load_mcp_config(caller_file) -> str
Returns path to mcp_config.json in agent's config/ directory.

## Expected Structure
```
agent_name/
├── agent.py
└── config/
    └── mcp_config.json
```

## Usage Pattern

```python
class StoryResearcher:
    def __init__(self, session_id: str):
        mcp_config_path = load_mcp_config(__file__)

        self.agent = Agent(
            model=os.getenv('LLM_MODEL'),
            mcp_servers=mcp_config_path
        )
```

## Examples in Codebase
- StoryResearcherAgent (uses web search/crawler)
- StoryCreatorAgent (uses filesystem)
- All orchestrator agents with MCP tools
