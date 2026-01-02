# Mythline

An AI-powered storytelling system that creates rich, immersive World of Warcraft narratives using autonomous agents and specialized sub-agents.

## Overview

Mythline is a multi-agent system built with [Pydantic AI](https://ai.pydantic.dev/) that researches WoW lore and generates engaging stories complete with narration, dialogue, and visual scene descriptions. The system uses a modular architecture with specialized agents that work together to create coherent, contextually-aware narratives.

## Features

- **Story Creation**: Automated WoW story generation with quest research, narration, and dialogue
- **Shot Creation**: Visual scene descriptions for cinematic storytelling
- **Voice Navigation**: Hands-free shot navigation with voice commands and OBS integration
- **YouTube Upload**: Direct video upload to YouTube with full metadata support
- **Contextual Memory**: Session-based context memory for coherent multi-part stories
- **Long-term Memory**: User preference tracking across sessions
- **Web Research**: Automated lore research using web search and crawling
- **File Operations**: Automated story output to markdown and PDF formats

## Architecture

### Agents

**Orchestrator Agents**

**story_research_agent**
- Research orchestrator for WoW lore gathering
- Researches WoW lore using MCP web tools
- Creates and maintains research notes
- Tracks user preferences in long-term memory

**story_creator_agent**
- Story orchestrator for narrative generation
- Transforms research notes into engaging stories
- Delegates narration and dialogue to sub-agents
- Structures stories with proper sections

**shot_creator_agent**
- Creates visual scene descriptions
- Supports cinematic storytelling

**video_director_agent**
- Orchestrates video production workflow
- Coordinates shot creation and review

**Sub-Agents (Stateful)**

**narrator_agent**
- Creates third-person narrations
- Maintains context across story segments
- Ensures word count compliance

**dialog_creator_agent**
- Generates engaging character dialogues
- Maintains consistent character voices
- Ensures all actors have speaking parts

**story_planner_agent**
- Plans story structure and flow
- Creates story outlines

**shot_reviewer_agent**
- Reviews and validates shot descriptions
- Ensures visual consistency

**story_reviewer_agent**
- Reviews generated stories for quality
- Validates narrative coherence

**Sub-Agents (Stateless)**

**user_preference_agent**
- Stateless preference analyzer
- Extracts memorable user preferences
- Feeds into long-term memory system

**chunker_agent**
- Splits content into manageable chunks
- Supports processing pipelines

**location_extractor_agent**
- Extracts location information from lore
- Identifies key settings

**npc_extractor_agent**
- Extracts NPC information from research
- Identifies characters and their roles

**quest_extractor_agent**
- Extracts quest information from lore
- Identifies objectives and storylines

**research_input_parser_agent**
- Parses user research input
- Structures research requests

**search_query_generator**
- Generates optimized search queries
- Improves research efficiency

**story_setting_extractor_agent**
- Extracts setting details from stories
- Identifies atmosphere and environment

**quality_assessor**
- Assesses content quality
- Provides quality metrics

**youtube_metadata_agent**
- Generates YouTube metadata (titles, descriptions, tags)
- SEO optimization for video uploads

**llm_tester_agent**
- Tests LLM responses
- Validates model behavior

### MCP Servers

**mcp_web_search (port 8000)**
- DuckDuckGo search integration
- Crawls top results for comprehensive research

**mcp_web_crawler (port 8001)**
- Web page content extraction
- Markdown conversion for LLM consumption

**mcp_filesystem (port 8002)**
- File read/write operations
- Directory management
- File existence checking

**mcp_knowledge_base (port 8003)**
- Vector-based knowledge storage
- Semantic search capabilities
- Qdrant-powered embeddings

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
- OpenRouter API key

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
cp .env.example .env
```

Edit `.env` and add:
```
OPENROUTER_API_KEY=your_api_key_here
LLM_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small
```

4. Configure MCP server ports (optional):
```
MCP_WEB_SEARCH_PORT=8000
MCP_WEB_CRAWLER_PORT=8001
MCP_FILESYSTEM_PORT=8002
MCP_KNOWLEDGE_BASE_PORT=8003
```

5. Setup YouTube Upload (optional):
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a project and enable YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop application)
   - Download and save as `client_secrets.json` in project root
   - First upload will open browser for OAuth consent

## Usage

### Start MCP Servers

Start all required MCP servers before running agents:

```bash
start_web_search_mcp.bat
start_web_crawler_mcp.bat
start_filesystem_mcp.bat
start_knowledge_base_mcp.bat
```

Or manually:
```bash
python -m src.mcp_servers.mcp_web_search.server
python -m src.mcp_servers.mcp_web_crawler.server
python -m src.mcp_servers.mcp_filesystem.server
python -m src.mcp_servers.mcp_knowledge_base.server
```

### Run Story Research Agent

Start the interactive CLI:
```bash
start_story_researcher.bat
```

Or manually:
```bash
python -m src.ui.cli.research_story
```

### Run Story Creator Agent

**Note:** Story creator requires research notes to exist first. Run story_research_agent before using this.

Non-interactive story generation:
```bash
start_story_creator.bat --subject shadowglen
```

Or manually:
```bash
python -m src.ui.cli.create_story --subject shadowglen
```

The agent will:
1. Validate research notes exist at `output/shadowglen/research.md`
2. Autonomously generate complete story
3. Save to `output/shadowglen/story.json`
4. Use subject as session ID for resumable generation

### CLI Arguments

**Story Research Agent (Interactive):**
```bash
# Create new session
python -m src.ui.cli.research_story

# Resume last session
python -m src.ui.cli.research_story --resume

# Load specific session
python -m src.ui.cli.research_story --session 20231015_143022
```

**Story Creator Agent (Non-Interactive):**
```bash
# Generate story for a subject
python -m src.ui.cli.create_story --subject shadowglen

# Short form
python -m src.ui.cli.create_story -s shadowglen
```

**Voice Navigator:**
```bash
# Navigate shots with voice commands
python -m src.ui.cli.voice_navigator --subject shadowglen

# Commands: "next", "previous", "repeat", "pause", "resume", "go to shot 5"
# Recording: "start recording", "pause recording", "stop recording"
```

**YouTube Uploader:**
```bash
# Upload with auto-generated metadata from story
python -m src.ui.cli.upload_youtube --subject last_stand

# Upload with custom privacy setting
python -m src.ui.cli.upload_youtube --subject last_stand -p public

# Utility commands
python -m src.ui.cli.upload_youtube --list-categories
python -m src.ui.cli.upload_youtube --list-playlists
python -m src.ui.cli.upload_youtube --logout
```

**Additional CLI Tools:**
```bash
# Shot generation
python -m src.ui.cli.create_shots --subject shadowglen
python -m src.ui.cli.generate_shots --subject shadowglen

# Direct shot creation
python -m src.ui.cli.direct_shots --subject shadowglen

# Shot director (interactive)
python -m src.ui.cli.shot_director --subject shadowglen

# Audio creation
python -m src.ui.cli.create_audio --subject shadowglen

# Knowledge base management
python -m src.ui.cli.manage_knowledge_base

# Research with graph visualization
python -m src.ui.cli.research_story_graph

# LLM testing
python -m src.ui.cli.test_llm
```

### Example Workflow

**Step 1: Research (Interactive)**
```
start_story_researcher.bat

Session: 20231015_143022

🙍 User: Research Shadowglen starting zone for night elves

🤖 Agent: I'll research Shadowglen and gather lore information...
[Agent creates output/shadowglen/research.md]
```

**Step 2: Story Creation (Non-Interactive)**
```
start_story_creator.bat --subject shadowglen

Starting story generation for: shadowglen
Session ID: shadowglen
Research file: output/shadowglen/research.md
--------------------------------------------------

⚙ Reading research notes for: shadowglen
✓ Research notes loaded from output/shadowglen/research.md
⚙ Saving story for: shadowglen
✓ Story saved successfully to output/shadowglen/story.json

==================================================
Story generation complete!
Story title: The Awakening of Shadowglen
Quest count: 3
Output file: output/shadowglen/story.json
==================================================
```

## Project Structure

```
Mythline/
├── src/
│   ├── agents/
│   │   ├── chunker_agent/
│   │   ├── dialog_creator_agent/
│   │   ├── llm_tester_agent/
│   │   ├── location_extractor_agent/
│   │   ├── narrator_agent/
│   │   ├── npc_extractor_agent/
│   │   ├── quality_assessor/
│   │   ├── quest_extractor_agent/
│   │   ├── research_input_parser_agent/
│   │   ├── search_query_generator/
│   │   ├── shot_creator_agent/
│   │   ├── shot_reviewer_agent/
│   │   ├── story_creator_agent/
│   │   ├── story_planner_agent/
│   │   ├── story_research_agent/
│   │   ├── story_reviewer_agent/
│   │   ├── story_setting_extractor_agent/
│   │   ├── user_preference_agent/
│   │   ├── video_director_agent/
│   │   └── youtube_metadata_agent/
│   ├── mcp_servers/
│   │   ├── mcp_web_search/
│   │   ├── mcp_web_crawler/
│   │   ├── mcp_filesystem/
│   │   └── mcp_knowledge_base/
│   ├── libs/
│   │   ├── agent_memory/
│   │   ├── audio/
│   │   ├── embedding/
│   │   ├── filesystem/
│   │   ├── knowledge_base/
│   │   ├── logger/
│   │   ├── obs/
│   │   ├── parsers/
│   │   ├── voice/
│   │   ├── web/
│   │   ├── youtube/
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
- Powered by OpenRouter (unified API for multiple LLM providers)
- World of Warcraft lore from [warcraft.wiki.gg](https://warcraft.wiki.gg/)
