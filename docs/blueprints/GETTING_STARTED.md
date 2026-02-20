# Getting Started with Pydantic AI Multi-Agent Systems

**Welcome!** This guide will help you set up a Pydantic AI multi-agent system and create your first agent.

**Time required:** ~30 minutes

**Prerequisites:** Python 3.10+, basic Python knowledge

---

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Install Dependencies](#install-dependencies)
3. [Configure Environment Variables](#configure-environment-variables)
4. [Start MCP Servers](#start-mcp-servers)
5. [Test Your Setup](#test-your-setup)
6. [Create Your First Agent](#create-your-first-agent)
7. [Next Steps](#next-steps)
8. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### 1. Clone or Create Your Project

```bash
# If starting from scratch
mkdir my-agent-system
cd my-agent-system

# If cloning an existing project
git clone <repository-url>
cd <project-directory>
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

**Verify:**
```bash
which python  # Should point to venv/bin/python
python --version  # Should be 3.10+
```

---

## Install Dependencies

### Install Required Packages

```bash
pip install -r requirements.txt
```

**This installs:**
- `pydantic-ai` - AI agent framework
- `langgraph` - Workflow orchestration
- `openai` - OpenAI SDK (used with OpenRouter)
- `qdrant-client` - Vector database
- `fastmcp` - MCP server framework
- `duckduckgo-search` - Web search
- `python-dotenv` - Environment variables
- And more...

**Verify installation:**
```bash
python -c "import pydantic_ai; print('✓ Pydantic AI installed')"
python -c "from langgraph.graph import StateGraph; print('✓ LangGraph installed')"
python -c "from mcp.server.fastmcp import FastMCP; print('✓ FastMCP installed')"
```

---

## Configure Environment Variables

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Get OpenRouter API Key

1. Go to https://openrouter.ai/
2. Sign up or log in
3. Navigate to "Keys" section
4. Create a new API key
5. Copy the key (starts with `sk-or-v1-...`)

### 3. Edit `.env` File

Open `.env` in your editor and add your API key:

```env
# REQUIRED: Add your API key here
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here

# OPTIONAL: These have defaults, but you can customize
LLM_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small

# MCP Server Ports (defaults are fine)
MCP_WEB_SEARCH_PORT=8000
MCP_WEB_CRAWLER_PORT=8001
MCP_FILESYSTEM_PORT=8002
MCP_KNOWLEDGE_BASE_PORT=8003

# Knowledge Base Path (default is fine)
QDRANT_PATH=.mythline/knowledge_base

# Optional: Prevent __pycache__ directories
PYTHONDONTWRITEBYTECODE=1
```

### 4. Verify Configuration

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✓ API Key:', 'SET' if os.getenv('OPENROUTER_API_KEY') else 'MISSING')"
```

**See [ENVIRONMENT.md](ENVIRONMENT.md) for complete environment variable reference.**

---

## Start MCP Servers

MCP servers provide tools to agents. Let's start the essential ones.

### Windows

Open **4 separate terminal windows** (keep them open):

**Terminal 1 - Web Search:**
```bash
start_web_search.bat
```

**Terminal 2 - Web Crawler:**
```bash
start_web_crawler.bat
```

**Terminal 3 - Filesystem:**
```bash
start_filesystem.bat
```

**Terminal 4 - Knowledge Base:**
```bash
start_knowledge_base.bat
```

### Mac/Linux

```bash
# In separate terminals, or use tmux/screen
python -m src.mcp_servers.mcp_web_search.server &
python -m src.mcp_servers.mcp_web_crawler.server &
python -m src.mcp_servers.mcp_filesystem.server &
python -m src.mcp_servers.mcp_knowledge_base.server &
```

### Verify Servers are Running

Each server should output:
```
Starting [Server Name] MCP Server...
Server running on http://localhost:[PORT]
```

**Quick test:**
```bash
curl http://localhost:8000/mcp
# Should return MCP server info, not an error
```

**Note:** Keep these terminal windows open while working with Mythline. Agents need these servers running.

---

## Test Your Setup

### Test 1: Simple Agent Import

```bash
python -c "from src.agents.user_preference_agent import UserPreferenceAgent; print('✓ Agent imports work')"
```

### Test 2: Run Story Research (Interactive)

```bash
python -m src.ui.cli.research_story
```

**You should see:**
```
Session ID: research_<timestamp>

What would you like to research?
>
```

**Try asking:**
```
> Tell me about Shadowglen in World of Warcraft
```

**Expected:** Agent searches the web and provides information about Shadowglen.

**Exit:** Type `quit` or `exit`

### Test 3: Run Story Creation (Non-Interactive)

```bash
python -m src.ui.cli.create_story --subject shadowglen
```

**Expected:** Agent creates a story about Shadowglen using the workflow.

**Note:** This may take 1-2 minutes as it runs through multiple agents.

### If Tests Pass

✓ Your environment is set up correctly!

### If Tests Fail

See [Troubleshooting](#troubleshooting) section below.

---

## Create Your First Agent

Let's create a simple **sentiment analyzer** agent to learn the basics.

### 1. Create Agent Directory

```bash
mkdir -p src/agents/sentiment_agent/prompts
```

### 2. Create `__init__.py`

**File:** `src/agents/sentiment_agent/__init__.py`

```python
from .agent import SentimentAgent

__all__ = ['SentimentAgent']
```

### 3. Create System Prompt

**File:** `src/agents/sentiment_agent/prompts/system_prompt.md`

```markdown
# Persona

You are a sentiment analysis expert.

# Task

Analyze the sentiment of the provided text and classify it as positive, negative, or neutral.

# Instructions

1. Read the text carefully
2. Identify emotional tone and language
3. Consider context and nuance
4. Classify as: positive, negative, or neutral
5. Provide a brief explanation

# Constraints

- Be objective and unbiased
- Consider subtle emotions
- One-word classification + short explanation

# Output

Format:
Sentiment: [positive/negative/neutral]
Explanation: [2-3 sentences]
```

### 4. Create Agent Implementation

**File:** `src/agents/sentiment_agent/agent.py`

```python
import os

from dotenv import load_dotenv

from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt

load_dotenv()

class SentimentAgent:
    AGENT_ID = "sentiment_agent"

    def __init__(self):
        llm_model = os.getenv('LLM_MODEL')
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            system_prompt=system_prompt
        )

    async def run(self, text: str) -> AgentRunResult:
        agent_output = await self.agent.run(text)
        return agent_output
```

**Note:** This is a stateless agent (no session_id, no memory). Perfect for one-off analysis.

### 5. Test Your Agent

**Create test file:** `test_sentiment.py`

```python
import asyncio
from src.agents.sentiment_agent import SentimentAgent

async def main():
    agent = SentimentAgent()

    # Test positive sentiment
    result = await agent.run("I absolutely love this product! Best purchase ever!")
    print("Test 1 (Positive):")
    print(result.output)
    print()

    # Test negative sentiment
    result = await agent.run("This is terrible. Worst experience of my life.")
    print("Test 2 (Negative):")
    print(result.output)
    print()

    # Test neutral sentiment
    result = await agent.run("The meeting is scheduled for 3 PM tomorrow.")
    print("Test 3 (Neutral):")
    print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

**Run test:**
```bash
python test_sentiment.py
```

**Expected output:**
```
Test 1 (Positive):
Sentiment: positive
Explanation: The text expresses strong enthusiasm and satisfaction...

Test 2 (Negative):
Sentiment: negative
Explanation: The text uses extreme negative language...

Test 3 (Neutral):
Sentiment: neutral
Explanation: The text is purely informational with no emotional tone...
```

### 6. Congratulations!

🎉 You've created your first Mythline agent!

**What you learned:**
- Agent directory structure
- System prompt creation
- Stateless agent pattern
- Async agent execution

---

## Next Steps

### Learn More Patterns

**Create a stateful agent** (with memory):
- Read: [pydantic/agents/agent_stateful_subagent.md](pydantic/agents/agent_stateful_subagent.md)
- Example: Create a chatbot that remembers conversation

**Create an orchestrator agent** (with MCP tools):
- Read: [pydantic/agents/agent_orchestrator.md](pydantic/agents/agent_orchestrator.md)
- Example: Create a research agent that uses web search

**Build a workflow** (with graphs):
- Read: [pydantic/graphs/graph_with_agents.md](pydantic/graphs/graph_with_agents.md)
- Example: Multi-step content generation pipeline

### Explore Existing Agents

Study these agents to learn patterns:

**Simple agents:**
- `src/agents/user_preference_agent/` - Stateless extraction
- `src/agents/chunker_agent/` - Text processing

**Stateful agents:**
- `src/agents/narrator_agent/` - Creative writing with memory
- `src/agents/dialog_creator_agent/` - Dialogue generation

**Orchestrator agents:**
- `src/agents/story_research_agent/` - Web research + sub-agents
- `src/agents/story_creator_agent/` - Complex orchestration

**Graphs:**
- `src/graphs/story_creator_graph/` - Multi-agent workflow
- `src/graphs/shot_creator_graph/` - Sequential processing

### Read Documentation

**Core concepts:**
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Where everything lives
- [ENVIRONMENT.md](ENVIRONMENT.md) - Configuration deep-dive
- [INDEX.md](INDEX.md) - Complete blueprint catalog

**Specific features:**
- Agent memory: `libs/agent_memory/`
- Vector search: `libs/knowledge_base/`
- Web tools: `mcps/web/`
- Prompting: `pydantic/prompts/`

### Join the Development

**Contribute:**
- Fix bugs
- Add features
- Improve documentation
- Create new agents

**Follow the guidelines:**
- [../../CLAUDE.md](../../CLAUDE.md) - Development standards
- Use Git-flow branching
- Write self-documenting code
- Keep it simple (KISS)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'pydantic_ai'"

**Problem:** Dependencies not installed

**Solution:**
```bash
pip install -r requirements.txt
```

### "Missing API Key" or "OPENROUTER_API_KEY not set"

**Problem:** Environment not configured

**Solution:**
```bash
# Check if .env exists
ls -la .env

# If missing, copy template
cp .env.example .env

# Edit and add your API key
nano .env  # or your editor

# Verify
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('OPENROUTER_API_KEY'))"
```

### "Connection refused" or "MCP server not responding"

**Problem:** MCP servers not running

**Solution:**
```bash
# Check if servers are running
curl http://localhost:8000/mcp
curl http://localhost:8001/mcp
curl http://localhost:8002/mcp
curl http://localhost:8003/mcp

# If not, start them:
# Windows: Use start_*.bat files
# Mac/Linux:
python -m src.mcp_servers.mcp_web_search.server &
python -m src.mcp_servers.mcp_web_crawler.server &
python -m src.mcp_servers.mcp_filesystem.server &
python -m src.mcp_servers.mcp_knowledge_base.server &
```

### "Port already in use"

**Problem:** Another process using MCP ports

**Solution:**
```bash
# Windows: Find and kill process
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Mac/Linux:
lsof -ti:8000 | xargs kill

# Or change port in .env:
MCP_WEB_SEARCH_PORT=9000
# And update agent config/mcp_config.json to match
```

### Agent tests fail but imports work

**Problem:** Missing required files or configuration

**Solution:**
```bash
# Check agent structure
ls -la src/agents/story_research_agent/
# Should see: __init__.py, agent.py, prompts/, config/

# Check prompt file exists
ls -la src/agents/story_research_agent/prompts/system_prompt.md

# Check MCP config exists (for orchestrators)
ls -la src/agents/story_research_agent/config/mcp_config.json

# Verify MCP servers in config match running servers
cat src/agents/story_research_agent/config/mcp_config.json
```

### "Rate limit exceeded" or "API error"

**Problem:** OpenRouter rate limits or API issues

**Solution:**
```bash
# Check your OpenRouter dashboard
# https://openrouter.ai/

# Try a different model (cheaper/faster)
# Edit .env:
LLM_MODEL=openai/gpt-4o-mini  # Cheapest option

# Add retry logic or wait a moment
```

### Import errors or "cannot find module"

**Problem:** Python path not set correctly

**Solution:**
```bash
# Run from project root
cd /path/to/mythline

# Use python -m syntax for modules
python -m src.ui.cli.research_story  # Good
python src/ui/cli/research_story.py  # May fail

# If still failing, check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Mac/Linux
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows
```

### Still Having Issues?

1. **Check versions:**
   ```bash
   python --version  # 3.10+
   pip list | grep pydantic-ai
   pip list | grep langgraph
   ```

2. **Clean reinstall:**
   ```bash
   pip uninstall -y -r requirements.txt
   pip install -r requirements.txt
   ```

3. **Check project structure:**
   ```bash
   tree src -L 2  # or ls -R src
   # Should match PROJECT_STRUCTURE.md
   ```

4. **Review logs:**
   - MCP server terminals show errors
   - Python tracebacks indicate issues
   - Check for typos in .env

5. **Ask for help:**
   - Include error messages
   - Share relevant code
   - Mention what you've tried

---

## Quick Command Reference

**Environment:**
```bash
cp .env.example .env                    # Create config
source venv/bin/activate                # Activate venv (Mac/Linux)
venv\Scripts\activate                   # Activate venv (Windows)
pip install -r requirements.txt         # Install deps
```

**MCP Servers:**
```bash
start_web_search.bat                    # Windows
python -m src.mcp_servers.mcp_web_search.server  # Mac/Linux
```

**Testing:**
```bash
python -m src.ui.cli.research_story     # Interactive research
python -m src.ui.cli.create_story --subject <topic>  # Create story
python test_sentiment.py                # Test your agent
```

**Development:**
```bash
git flow feature start <name>           # Start feature
git flow feature finish <name>          # Finish feature
```

---

## Summary Checklist

Setup complete when you can check all these:

- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with `OPENROUTER_API_KEY`
- [ ] All 4 MCP servers running
- [ ] `research_story` CLI works
- [ ] `create_story` CLI works
- [ ] First agent created and tested

**Once complete, you're ready to build with Mythline!**

---

## Additional Resources

**Documentation:**
- [INDEX.md](INDEX.md) - Blueprint navigation
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Project layout
- [ENVIRONMENT.md](ENVIRONMENT.md) - Configuration reference
- [../../CLAUDE.md](../../CLAUDE.md) - Development guidelines

**External:**
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenRouter Documentation](https://openrouter.ai/docs)
- [FastMCP Repository](https://github.com/jlowin/fastmcp)

**Examples:**
- All agents in `src/agents/` are reference implementations
- All graphs in `src/graphs/` show workflow patterns
- All MCP servers in `src/mcp_servers/` demonstrate tool creation

---

**Welcome to Mythline! Happy coding! 🚀**
