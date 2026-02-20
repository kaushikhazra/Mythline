# Pydantic AI - State of the Framework (February 2026)

Research Date: 2026-02-21

## 1. Latest Version and Features

### Version History
- **v1.0.0** released September 4, 2025 (after 9 months of development)
- **v1.62.0** released February 19, 2026 (latest as of this research)
- 15 million downloads achieved by v1 launch
- Minimum Python version: 3.10+ (Python 3.9 dropped in v1.0)

### V1 Stability Commitment
API stability guaranteed -- no breaking changes until V2. Security fixes for V1 will continue for 6+ months after V2 launches.

### Major Features Added Post-V1

| Feature | Status |
|---------|--------|
| MCP Client (Streamable HTTP, SSE, Stdio) | Stable |
| Agent2Agent (A2A) protocol | Stable |
| AG-UI protocol (CopilotKit) | Stable |
| Durable Execution (Temporal) | Stable (out of beta) |
| Human-in-the-Loop tool approval | Stable |
| pydantic-graph (FSM) | Stable |
| History Processors | Stable |
| MCP Sampling | Stable |
| MCP Elicitation | Stable |
| Deep Agents (pydantic-deep) | Community package |
| Prompt caching | Planned |
| Embeddings support | Planned |
| Context-Free Grammar output | Planned |

### Model Provider Support
Virtually every major provider: OpenAI, Anthropic, Gemini, DeepSeek, Grok, Cohere, Mistral, Perplexity, Azure AI Foundry, Amazon Bedrock, Google Vertex AI, OpenRouter, and more.

---

## 2. Multi-Agent Patterns

Pydantic AI defines **five complexity levels** for multi-agent applications:

### Level 1: Single Agent Workflows
Standard single-agent with tools. No multi-agent coordination.

### Level 2: Agent Delegation
One agent calls another via a tool function. The parent agent retains control after the delegate completes.

```python
@parent_agent.tool
async def delegate_task(ctx: RunContext[None]) -> list[str]:
    result = await delegate_agent.run(
        prompt,
        usage=ctx.usage,   # aggregate token counts
        deps=ctx.deps,     # share dependencies
    )
    return result.output
```

Key points:
- Agents are stateless and can be global singletons
- `ctx.usage` aggregates token counts across delegates
- `ctx.deps` shares dependencies (DB connections, HTTP clients)
- `UsageLimits` prevents runaway costs (request limits, token limits, tool-call limits)
- Different models can be used per agent

### Level 3: Programmatic Hand-Off
Application code decides which agent runs next. Agents do NOT need to share dependencies. Message history can be passed between agents for context continuity.

Pattern: Agent A runs -> application logic inspects result -> Agent B runs with previous message history.

### Level 4: Graph-Based Control Flow
Uses pydantic-graph for complex state machine orchestration. A Supervisor agent node dispatches to Worker agent nodes via graph edges.

### Level 5: Deep Agents
Autonomous agents combining:
- Task planning with progress tracking
- File system operations
- Sub-agent delegation
- Sandboxed code execution
- Conversation summarization
- Human approval workflows
- Durable execution across failures

Community package `pydantic-deep` (by Vstorm) composes multiple PydanticAI capabilities into a `create_deep_agent()` call.

### What Pydantic AI Does NOT Have Natively
- No agent "swarm" abstraction (like OpenAI Swarm)
- No built-in message bus between agents
- No native agent registry or discovery
- No automatic agent routing -- you build this with tools or graphs
- Multi-agent is compositional, not declarative

---

## 3. MCP Support

### Architecture
Pydantic AI agents act as **MCP clients** connecting to MCP servers. Three integration approaches:

#### Approach 1: Direct MCP Server Connection
```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP

# Stdio transport (subprocess)
server_stdio = MCPServerStdio('python', args=['mcp_server.py'])

# Streamable HTTP transport
server_http = MCPServerStreamableHTTP('http://localhost:8000/mcp')

agent = Agent('openai:gpt-4o', toolsets=[server_stdio, server_http])
```

#### Approach 2: FastMCP Toolset
```python
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

toolset = FastMCPToolset(server)
agent = Agent('openai:gpt-4o', toolsets=[toolset])
```
Works with any MCP server, not just FastMCP-built ones.

#### Approach 3: Provider-Native MCP
Some model providers connect to MCP servers directly using `MCPServerTool` (built-in tool).

### Transport Mechanisms
1. **MCPServerStreamableHTTP** -- HTTP with streaming (recommended)
2. **MCPServerSSE** -- HTTP with Server-Sent Events (deprecated, use StreamableHTTP)
3. **MCPServerStdio** -- Subprocess over stdin/stdout

Note: `MCPServerHTTP` is deprecated; `MCPServerSSE` replaces it.

### Key MCP Features

**Tool Prefix**: Avoid naming conflicts across servers:
```python
weather = MCPServerStreamableHTTP(url, tool_prefix='weather')
calc = MCPServerStreamableHTTP(url, tool_prefix='calc')
```

**MCP Sampling**: MCP servers can request LLM calls through the client:
```python
agent.set_mcp_sampling_model()
```

**MCP Elicitation**: Servers can request structured user input during execution via `elicitation_callback`.

**Resource Access**: `list_resources()`, `list_resource_templates()`, `read_resource(uri)`

**Config Loading**: Load servers from JSON with env var expansion:
```python
from pydantic_ai.mcp import load_mcp_servers
servers = load_mcp_servers('mcp_config.json')
```

### Agents AS MCP Servers
Agents can also operate inside MCP servers, reversing the typical client-server relationship.

### Impact on Mythline
Mythline currently uses FastMCP servers with custom stdio/HTTP transport. The new `toolsets` parameter and `MCPServerStreamableHTTP` would replace the manual MCP configuration pattern. The `tool_prefix` feature would solve potential tool naming conflicts.

---

## 4. Agent Graphs (pydantic-graph)

### Overview
pydantic-graph is a separate but tightly integrated library for building async finite state machines. It is generic, type-centric, and uses Python dataclasses for nodes.

The Pydantic AI team's guidance: "If agents are a hammer, multi-agent workflows are a sledgehammer, then graphs are a nail gun." Graphs should only be used when genuinely necessary.

### Core Components

**GraphRunContext**: Execution context holding state and dependencies (like RunContext for agents).

**BaseNode**: Dataclass-based execution units with async `run()` methods. Return type annotations define edges.

**Graph**: Container composed of node classes. Runs synchronously or asynchronously.

**End**: Return value indicating graph termination.

### State Management
State flows through nodes, accumulating changes:
- `SimpleStatePersistence` -- latest snapshot only (default)
- `FullStatePersistence` -- all snapshots
- `FileStatePersistence` -- JSON file persistence

Persistence enables interrupted/resumed execution for human-in-the-loop and durable workflows.

### Execution Patterns
- `Graph.run()` / `Graph.run_sync()` -- basic execution
- `Graph.iter()` -- async iteration with `async for` over nodes
- `GraphRun.next(node)` -- manual stepping
- `Graph.iter_from_persistence()` -- resume from stored state

### Visualization
Generates Mermaid state diagrams:
```python
graph.mermaid_code()     # Returns diagram code
graph.mermaid_image()    # Generates PNG
graph.mermaid_save()     # Saves to file
```

### How It Compares to Mythline's Approach
Mythline uses custom graph implementations (shot_creator_graph, story_creator_graph). pydantic-graph provides a more standardized, type-safe alternative with built-in persistence and visualization.

---

## 5. Memory / Context Management

### Built-In: Message History
Pydantic AI provides message history management but NOT a built-in persistent memory system.

**Passing history between runs:**
```python
result1 = agent.run_sync('Tell me a joke.')
result2 = agent.run_sync('Explain?', message_history=result1.new_messages())
```

**Serialization for persistence:**
```python
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

history = result.all_messages()
serialized = to_jsonable_python(history)
restored = ModelMessagesTypeAdapter.validate_python(serialized)
```

Messages are model-agnostic -- you can switch models between runs.

### History Processors (Context Window Management)
The `history_processors` parameter allows intercepting and modifying message history before each model request:

```python
def keep_recent(messages: list[ModelMessage]) -> list[ModelMessage]:
    return messages[-5:] if len(messages) > 5 else messages

agent = Agent('openai:gpt-4o', history_processors=[keep_recent])
```

**Advanced -- token-aware filtering:**
```python
def context_processor(ctx: RunContext[None], messages: list[ModelMessage]):
    if ctx.usage.total_tokens > 1000:
        return messages[-3:]
    return messages
```

**Advanced -- LLM-based summarization:**
Use a cheaper model to summarize older messages while preserving technical context.

### What Pydantic AI Does NOT Provide
- No built-in persistent memory store (like Mythline's context_memory/long_term_memory)
- No vector-based memory retrieval
- No cross-session memory management
- No memory consolidation or forgetting

### Community Memory Patterns
- MongoDB-backed memory layers
- Separate "memory_agent" that analyzes conversations and produces profile/memory updates
- Structured memory systems combining profiles + episodic memories + experience

### Impact on Mythline
Mythline's custom context_memory and long_term_memory system is ahead of what Pydantic AI provides natively. The `history_processors` feature could replace some of Mythline's manual message history management, but the persistent memory architecture would still need to be custom.

---

## 6. Additional Notable Features

### Agent2Agent (A2A) Protocol
Google's open standard for cross-framework agent communication. Pydantic AI supports both consuming and exposing A2A endpoints.

**Expose agent as A2A server:**
```python
agent = Agent('openai:gpt-4o', instructions='Be fun!')
app = agent.to_a2a()  # Creates ASGI app
```

**FastA2A**: Framework-agnostic A2A implementation by Pydantic. Provides Storage, Broker, and Worker abstractions.

**Context management**: `context_id` maintains conversation threads across multiple tasks.

### AG-UI Protocol
CopilotKit's standard for frontend-agent communication. Natively supported in Pydantic AI.

Features:
- Streaming events (SSE) from agent to frontend
- Frontend tools (UI can provide tools to the agent)
- Shared state synchronization
- Custom events
- Human-in-the-loop checkpoints

### Durable Execution
Three supported backends:
1. **Temporal** -- production-ready, replay-based recovery
2. **DBOS** -- database-backed durability
3. **Prefect** -- workflow orchestration integration

Agents preserve progress across API failures, crashes, and restarts.

### Human-in-the-Loop
Tool calls can be flagged for approval before execution. Configurable based on:
- Tool call arguments
- Conversation history
- User preferences

### Observability
Pydantic Logfire integration using OpenTelemetry standards:
- Per-agent token usage and costs
- Tool execution tracing
- Delegation decision visibility
- Multi-agent flow tracing

---

## 7. Community Ecosystem

### pydantic-deep / pydantic-deepagents (Vstorm)
Batteries-included framework on top of Pydantic AI:
- `create_deep_agent()` -- single function to create autonomous agents
- Plan mode with planning subagent
- Filesystem operations
- Sub-agent delegation
- Cost tracking with budget enforcement
- Human-in-the-loop

### Common Architecture Patterns in the Wild
1. **Triage/Router Agent** -- receives queries, delegates to specialized agents via tools
2. **Orchestrator-Worker** -- supervisor dispatches to worker agents via graph edges
3. **Pipeline** -- sequential agent execution with programmatic hand-off
4. **Event-driven** -- real-time agents with streaming responses (FastAPI + PydanticAI)

### Framework Comparisons (Community Sentiment)
- vs **LangGraph**: Pydantic AI is simpler, more Pythonic, better typed. LangGraph has more built-in orchestration.
- vs **CrewAI**: Pydantic AI is lower-level but more flexible. CrewAI is more opinionated about multi-agent.
- vs **OpenAI Agents SDK**: Pydantic AI is model-agnostic. OpenAI SDK is locked to OpenAI models.

---

## 8. Relevance to Mythline

### What Mythline Could Adopt

| Feature | Current Mythline | Pydantic AI Native | Migration Effort |
|---------|-----------------|-------------------|-----------------|
| MCP Integration | Custom FastMCP + config | `toolsets` parameter | Medium |
| Agent Tools | `@agent.tool` decorator | Same pattern | None |
| Message History | Custom JSON persistence | `ModelMessagesTypeAdapter` | Low |
| Context Window Mgmt | Manual | `history_processors` | Low |
| Multi-Agent | Custom delegation | Same pattern (tools) | None |
| Graph Workflows | Custom graph classes | pydantic-graph | High |
| Memory System | Custom context+LTM | Not built-in | N/A (keep custom) |
| Observability | None | Logfire/OpenTelemetry | Medium |
| A2A Protocol | N/A | `agent.to_a2a()` | New capability |
| AG-UI | Custom WebSocket/SSE | AG-UI protocol | High |
| Durable Execution | N/A | Temporal/DBOS/Prefect | New capability |

### Key Observation
Mythline does not currently have `pydantic-ai` installed as a package. The CLAUDE.md references "Pydantic AI" as the framework, but the actual pip packages installed are `pydantic` (validator), `pydantic-settings`, and `pydantic_core`. The agent system appears to be a custom implementation inspired by Pydantic AI patterns rather than using the framework directly.

If Mythline were to adopt pydantic-ai proper, the most impactful features would be:
1. **MCP toolsets** -- cleaner MCP server integration
2. **History processors** -- automated context window management
3. **Durable execution** -- crash recovery for long story generation
4. **A2A protocol** -- if agents need to be exposed as services

---

## Sources

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Pydantic AI GitHub](https://github.com/pydantic/pydantic-ai)
- [Pydantic AI v1 Announcement](https://pydantic.dev/articles/pydantic-ai-v1)
- [Multi-Agent Patterns](https://ai.pydantic.dev/multi-agent-applications/)
- [MCP Overview](https://ai.pydantic.dev/mcp/overview/)
- [MCP Client](https://ai.pydantic.dev/mcp/client/)
- [pydantic-graph Documentation](https://ai.pydantic.dev/graph/)
- [Message History](https://ai.pydantic.dev/message-history/)
- [Agent2Agent (A2A)](https://ai.pydantic.dev/a2a/)
- [AG-UI Integration](https://ai.pydantic.dev/ui/ag-ui/)
- [Durable Execution](https://ai.pydantic.dev/durable_execution/overview/)
- [FastA2A GitHub](https://github.com/pydantic/fasta2a)
- [pydantic-deep GitHub](https://github.com/vstorm-co/pydantic-deep)
- [Pydantic AI Upgrade Guide](https://ai.pydantic.dev/changelog/)
- [PyPI - pydantic-ai](https://pypi.org/project/pydantic-ai/)
- [Toolsets Documentation](https://ai.pydantic.dev/toolsets/)
