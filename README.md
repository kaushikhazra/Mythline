# Mythline

An AI-powered storytelling system that creates rich, immersive World of Warcraft narratives using autonomous agents and specialized sub-agents.

## Overview

Mythline is a multi-agent system built with [Pydantic AI](https://ai.pydantic.dev/) that researches WoW lore and generates engaging stories complete with narration, dialogue, and visual scene descriptions. The system uses a modular architecture with specialized agents that work together to create coherent, contextually-aware narratives.

## Features

- **Story Creation**: Automated WoW story generation with quest research, narration, and dialogue
- **Shot Creation**: Visual scene descriptions for cinematic storytelling
- **Contextual Memory**: Session-based context memory for coherent multi-part stories
- **Long-term Memory**: User preference tracking across sessions
- **Web Research**: Automated lore research using web search and crawling
- **File Operations**: Automated story output to markdown and PDF formats

## Architecture

### Agents

**story_creator_agent**
- Main orchestrator for story creation
- Researches WoW lore using MCP web tools
- Delegates narration and dialogue to sub-agents
- Tracks user preferences in long-term memory

**narrator_agent**
- Creates third-person narrations
- Maintains context across story segments
- Ensures word count compliance

**dialog_creator_agent**
- Generates engaging character dialogues
- Maintains consistent character voices
- Ensures all actors have speaking parts

**user_preference_agent**
- Stateless preference analyzer
- Extracts memorable user preferences
- Feeds into long-term memory system

**shot_creator_agent**
- Creates visual scene descriptions
- Supports cinematic storytelling

### MCP Servers

**mcp_web_search**
- DuckDuckGo search integration
- Crawls top results for comprehensive research

**mcp_web_crawler**
- Web page content extraction
- Markdown conversion for LLM consumption

**mcp_filesystem**
- File read/write operations
- Directory management
- File existence checking

### Memory System

**Context Memory**
- Session-based conversation history
- Persisted per agent per session
- Enables coherent multi-turn interactions

**Long-term Memory**
- Cross-session preference storage
- Agent-specific memory namespaces
- Automatic preference extraction

## Installation

### Prerequisites

- Python 3.8+
- OpenAI API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/kaushikhazra/Mythline.git
cd Mythline
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .evn.example .env
```

Edit `.env` and add:
```
OPENAI_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o
```

4. Configure MCP server ports (optional):
```
MCP_WEB_SEARCH_PORT=8000
MCP_WEB_CRAWLER_PORT=8001
MCP_FILESYSTEM_PORT=8002
```

## Usage

### Start MCP Servers

Start all required MCP servers before running agents:

```bash
start_web_search_mcp.bat
start_web_crawler_mcp.bat
start_filesystem_mcp.bat
```

Or manually:
```bash
python -m src.mcp_servers.mcp_web_search.server
python -m src.mcp_servers.mcp_web_crawler.server
python -m src.mcp_servers.mcp_filesystem.server
```

### Run Story Creator Agent

Start the interactive CLI:
```bash
start_story_creator_agent.bat
```

Or manually:
```bash
python src/ui/cli/cli.py
```

### CLI Arguments

**Create new session:**
```bash
python src/ui/cli/cli.py
```

**Resume last session:**
```bash
python src/ui/cli/cli.py --resume
```

**Load specific session:**
```bash
python src/ui/cli/cli.py --session 20231015_143022
```

### Example Interaction

```
Session: 20231015_143022

🙍 User: Create a story about Velunasa starting her journey in Shadowglen

🤖 Agent: I'll research Shadowglen and create an engaging introduction
for Velunasa's journey...

[Agent researches lore, delegates to sub-agents, and generates story]
```

## Project Structure

```
Mythline/
├── src/
│   ├── agents/
│   │   ├── story_creator_agent/
│   │   ├── narrator_agent/
│   │   ├── dialog_creator_agent/
│   │   ├── user_preference_agent/
│   │   └── shot_creator_agent/
│   ├── mcp_servers/
│   │   ├── mcp_web_search/
│   │   ├── mcp_web_crawler/
│   │   └── mcp_filesystem/
│   ├── libs/
│   │   ├── agent_memory/
│   │   ├── filesystem/
│   │   ├── web/
│   │   └── utils/
│   └── ui/
│       └── cli/
├── output/
├── PDs/
│   └── pydantic_ai_coding_guide.md
├── requirements.txt
└── README.md
```

## Development

### Git Workflow

This project follows **Git-flow**:

- `main` - Production releases
- `develop` - Active development
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `release/*` - Release preparation
- `hotfix/*` - Production hotfixes

### Start a Feature

```bash
git flow feature start feature-name
```

### Finish a Feature

```bash
git flow feature finish feature-name
```

### Coding Standards

Follow the guidelines in `PDs/pydantic_ai_coding_guide.md`:
- KISS philosophy
- No inline imports
- OOP where appropriate
- No unnecessary logging
- No code comments (self-documenting code)

## Contributing

1. Fork the repository
2. Create a feature branch using git-flow
3. Follow coding standards
4. Submit a pull request to `develop`

## License

[Add your license here]

## Acknowledgments

- Built with [Pydantic AI](https://ai.pydantic.dev/)
- Powered by OpenAI GPT models
- World of Warcraft lore from [warcraft.wiki.gg](https://warcraft.wiki.gg/)
