# Message Queue / Pub-Sub Solutions for Drama Agent Swarm

## Research Date: 2026-02-21

## Context

Mythline v2 Drama Production system requires 8 AI agents collaborating to produce creative content (drama/screenplay). The design specifies:
- Each agent has its own "channel" (inbox)
- Any agent can post to any other agent's channel
- Messages contain structured data (scene plans, narration, dialogue, feedback)
- Message history serves as audit trail of the creative process
- System runs locally on Windows (not cloud-scale)
- Must integrate with Python async
- Architecture decision D11: "Drama Production = agent swarm with message queue"
- Will be wrapped as an **MCP service** (Message Queue MCP)

Reference: `.claude/specs/v2-architecture/design.md` — Drama Production section

---

## Option 1: Redis Streams

### What It Is
Redis Streams is a persistent, append-only log data structure built into Redis. It supports consumer groups (multiple consumers reading from the same stream with load balancing), message acknowledgement, and message history retention.

### Setup on Windows
- **Not natively supported on Windows.** Redis dropped official Windows support.
- Options: WSL2, Docker, or Memurai (commercial Redis-compatible Windows fork).
- Requires running a separate Redis server process.

### Python Integration
- **redis-py** (official): Full async support via `aioredis` integration. Commands: `XADD`, `XREAD`, `XREADGROUP`, `XACK`, `XRANGE`, `XPENDING`.
- **redis-streams** (PyPI): Higher-level abstraction for consumer group management.
- **streamengine**: Async stream processing on top of aioredis with decorator-based API.
- Mature, well-documented, large community.

### Message Persistence / History
- Streams are append-only logs — messages persist until explicitly trimmed.
- `XRANGE` retrieves full message history between any two timestamps.
- Consumer groups track which messages each consumer has read and acknowledged.
- Pending Entries List (PEL) tracks unacknowledged messages — natural audit trail.
- Can set `MAXLEN` to cap stream size or keep everything.

### Suitability for Agent Communication
- **Channel model**: One stream per agent = one inbox. Natural fit.
- **Any-to-any posting**: Any process can `XADD` to any stream. Perfect match.
- **Structured data**: Messages are field-value pairs (key-value maps). Good for structured data.
- **Audit trail**: Full message history queryable by time range. Excellent.
- **Consumer groups**: Overkill for single-consumer channels but available if needed.

### Overhead Assessment
- **External dependency**: Requires running Redis server separately.
- **Windows friction**: WSL2 or Docker required. Adds setup complexity.
- **Resource usage**: Redis is lightweight (~10MB RAM) but still an external process.
- **For 8 agents**: Significant overkill. Redis handles millions of messages/sec; we send dozens per scene.

### MCP Wrappability
- Straightforward. MCP service wraps redis-py async calls. Tools: `post_message(channel, data)`, `read_messages(channel, since)`, `get_history(channel)`.

### Verdict
**Strong technically, but operationally heavy for the use case.** The Windows setup friction (WSL2/Docker) and external process management add significant overhead for what amounts to 8 agents sending dozens of messages. The persistence and audit trail features are excellent, but we're using a sledgehammer for a nail.

---

## Option 2: ZeroMQ (PyZMQ)

### What It Is
ZeroMQ is a brokerless messaging library. No server process — sockets talk directly to each other. Supports PUB/SUB, REQ/REP, PUSH/PULL, DEALER/ROUTER patterns.

### Setup on Windows
- **pip install pyzmq** — that's it. No server, no external process.
- Pure library. Works natively on Windows.
- Zero operational overhead.

### Python Integration
- **PyZMQ**: Official Python binding. Mature, well-maintained.
- Full async support via `zmq.asyncio` module.
- Socket patterns map well to agent communication:
  - PUB/SUB for broadcast
  - DEALER/ROUTER for any-to-any directed messaging
  - PUSH/PULL for task distribution

### Message Persistence / History
- **None built-in.** ZeroMQ is a transport layer, not a storage layer.
- Messages are fire-and-forget. If a consumer is down, messages are lost (depending on socket type and HWM settings).
- Would need to build persistence ourselves (write messages to file/DB alongside sending).

### Suitability for Agent Communication
- **Channel model**: Each agent binds a PULL or ROUTER socket. Other agents connect and push messages. Workable but requires socket management.
- **Any-to-any**: DEALER/ROUTER pattern supports this, but requires managing connections manually.
- **Structured data**: Messages are raw bytes. Need to serialize/deserialize ourselves (JSON, msgpack, etc.).
- **Audit trail**: Must build entirely ourselves.
- **Topology complexity**: 8 agents with any-to-any = 56 potential connections. Socket management becomes non-trivial.

### Overhead Assessment
- **No external dependency** (just a pip install). Lightest operational footprint.
- **But**: Significant development overhead to build persistence, audit trail, and connection management.
- **Performance**: 50us latency, 2.5M msg/sec. Absurdly overpowered for our use case.

### MCP Wrappability
- Possible but awkward. ZeroMQ sockets are long-lived, stateful connections. MCP tools are stateless request/response. Would need a ZeroMQ broker process behind the MCP service, which defeats the "brokerless" advantage.

### Verdict
**Wrong tool for this job.** ZeroMQ excels at high-throughput, low-latency transport between distributed processes. We need persistence, history, and audit trail — exactly what ZeroMQ doesn't provide. Building all of that on top eliminates ZeroMQ's simplicity advantage. The "no broker" benefit becomes irrelevant when we'd need to build one anyway for MCP wrapping.

---

## Option 3: RabbitMQ / Celery

### What It Is
- **RabbitMQ**: Full-featured AMQP message broker. Exchanges, queues, routing, persistence.
- **Celery**: Python task queue framework that uses RabbitMQ (or Redis) as a broker.

### Setup on Windows
- RabbitMQ requires Erlang runtime. Heavy installation.
- Docker option available but still an external process.
- Celery requires a broker (RabbitMQ or Redis) plus a results backend.

### Python Integration
- **Celery**: Well-known, widely used. But designed for task queues, not agent-to-agent communication.
- **aio-pika**: Async RabbitMQ client for Python.
- **Dramatiq**: Lighter Celery alternative, still requires a broker.
- Celery's mental model is "background task execution" not "agent messaging."

### Message Persistence / History
- RabbitMQ supports persistent queues (survive broker restart).
- But messages are consumed and removed from queue. Not a natural audit trail.
- Would need to configure message logging/tracing separately.
- Celery result backend stores task results but not message history.

### Suitability for Agent Communication
- **Channel model**: One queue per agent. Fits, but queues are consumed-once by default.
- **Any-to-any**: Possible via exchanges and routing keys, but complex configuration.
- **Structured data**: Good — supports JSON payloads natively.
- **Audit trail**: Not built-in. Messages disappear after consumption.
- **Conceptual mismatch**: Celery/RabbitMQ thinks in "tasks to execute", not "messages between collaborating peers."

### Overhead Assessment
- **Heaviest option by far.** Erlang runtime + RabbitMQ broker + Python client library.
- For 8 agents sending structured messages, this is extreme overkill.
- Operational complexity (monitoring, management) inappropriate for local dev.

### MCP Wrappability
- Possible. MCP service wraps aio-pika. But the operational burden of running RabbitMQ makes this impractical for the use case.

### Verdict
**Hard no.** RabbitMQ/Celery is enterprise infrastructure for distributed task processing. Running Erlang + RabbitMQ broker for 8 local agents sending a few dozen messages per scene is absurd overkill. The task-queue mental model doesn't match agent collaboration. The message-consumed-once semantics conflict with our audit trail requirement.

---

## Option 4: Python asyncio Queues (In-Process)

### What It Is
`asyncio.Queue` — built into Python standard library. In-memory, in-process, async-safe queues for coroutine communication.

### Setup
- **Zero setup.** Part of Python standard library. No pip install, no external process.
- Available everywhere Python runs.

### Python Integration
- **Native.** `asyncio.Queue` is the canonical way to do async producer-consumer in Python.
- API: `put()`, `get()`, `put_nowait()`, `get_nowait()`, `join()`, `task_done()`.
- Pydantic AI agents already run in async context. Perfect compatibility.

### Message Persistence / History
- **None.** In-memory only. Messages are consumed and gone.
- Process crash = all messages lost.
- Would need to build persistence layer (write to file/SQLite alongside queue operations).

### Suitability for Agent Communication
- **Channel model**: One `asyncio.Queue` per agent. Simple dict lookup: `channels["narrator"].put(message)`.
- **Any-to-any**: Trivial — any coroutine can put to any queue.
- **Structured data**: Python objects directly — no serialization needed. Pass Pydantic models as-is.
- **Audit trail**: Must build ourselves.
- **Single process constraint**: All agents must run in the same Python process. No multi-process.

### Overhead Assessment
- **Zero external overhead.** Lightest possible option.
- **Development overhead**: Need to build message history and persistence.
- **But**: That development is simple — append to a list and/or write to SQLite.

### MCP Wrappability
- **Awkward.** MCP runs as a separate HTTP service (different process). asyncio.Queue is in-process only.
- Would need the MCP service to be in the same process as the agents, or use inter-process communication to bridge.
- **Or**: The MCP service IS the message bus — holds the queues, agents call MCP tools to post/read. This works but means the MCP service is both transport and storage, which is architecturally consistent with how other Mythline MCP services work.

### Verdict
**Strong contender with a catch.** Zero overhead, native Python, perfect async integration. The persistence gap is easily filled (SQLite or JSON file). The real question is the MCP integration model: if the MCP service holds the queues internally (agents interact via MCP tool calls), then the in-process nature is a feature, not a bug. Agents don't hold queues — the MCP service does. Agents post/read via HTTP tool calls.

**This is architecturally the cleanest option** for the Mythline model where MCP = data layer.

---

## Option 5: NATS / NATS JetStream

### What It Is
NATS is a lightweight, high-performance messaging system. Single binary, no dependencies. JetStream adds persistence, replay, and durable consumers on top of core NATS pub/sub.

### Setup on Windows
- **Single binary download.** Unzip and run `nats-server.exe`. No runtime dependencies.
- Lightest external server option. Server uses ~20MB RAM.
- Docker alternative also simple.

### Python Integration
- **nats-py**: Official async Python client. `pip install nats-py`.
- Full async/await support for pub/sub and JetStream.
- Clean API: `await nc.publish(subject, payload)`, `await sub.next_msg()`.
- Less mature Python ecosystem compared to Redis, but actively maintained.

### Message Persistence / History
- **NATS Core**: No persistence. Fire-and-forget pub/sub.
- **JetStream**: Full persistence. Streams store messages, consumers track position.
  - Durable consumers survive disconnections.
  - Message replay from any point in history.
  - Configurable retention (by time, count, or size).
  - Consumer acknowledgement tracking.

### Suitability for Agent Communication
- **Channel model**: Subjects = channels. `agent.narrator`, `agent.dialogist`, etc. Natural fit.
- **Any-to-any**: Any publisher can publish to any subject. Perfect.
- **Structured data**: Payloads are bytes — need JSON serialization. Standard practice.
- **Audit trail**: JetStream retains full message history, replayable. Excellent.
- **Subject hierarchies**: `agent.>` subscribes to all agent channels. Useful for monitoring.

### Overhead Assessment
- **Lightest external server option.** Single binary, ~20MB RAM, no dependencies.
- **But still external.** Another process to start and manage.
- **Performance**: Sub-millisecond latency, millions of msg/sec. Overkill for 8 agents.

### MCP Wrappability
- Clean fit. MCP service wraps nats-py async calls. Tools: `post_message(channel, data)`, `read_messages(channel)`, `get_history(channel, since)`.
- JetStream handles persistence, so MCP service is thin wrapper.

### Verdict
**Best external-server option.** If we decide we need a real message broker, NATS is the right one. Single binary, minimal resources, excellent persistence via JetStream, clean Python async client, subject-based routing matches our channel model perfectly. But the fundamental question remains: do 8 agents in a local creative process need an external message broker at all?

---

## Option 6: Custom MCP-Based Message Queue

### What It Is
Build the message queue directly inside an MCP service. No external broker. The MCP service holds channels in memory, persists to SQLite/JSON, and exposes tools for posting and reading.

### Setup
- **Zero external dependencies.** Part of the Mythline MCP ecosystem.
- Same FastMCP pattern as other Mythline MCP services.
- Start with `python -m src.mcp_servers.mcp_message_queue` or batch file.

### Python Integration
- **Native.** Built with same stack as rest of Mythline (FastMCP, Pydantic, asyncio).
- Agents interact via MCP tool calls — same pattern they use for every other MCP service.
- No new client library to learn.

### Proposed Implementation

```python
from mcp.server.fastmcp import FastMCP
import sqlite3
from datetime import datetime
from pydantic import BaseModel

server = FastMCP(name="Message Queue", port=8004)

class Message(BaseModel):
    id: str
    channel: str        # target agent channel
    sender: str         # sending agent
    msg_type: str       # scene_plan, narration, dialogue, feedback, query, etc.
    payload: dict       # structured data (scene plan, narration text, feedback, etc.)
    timestamp: datetime
    reply_to: str | None = None  # for threading/conversations

# In-memory channels backed by SQLite persistence
# channels = {agent_name: deque of Message}

@server.tool()
async def post_message(channel: str, sender: str, msg_type: str, payload: dict, reply_to: str = None) -> str:
    """Post a message to an agent's channel."""
    # Create message, append to channel deque, persist to SQLite
    pass

@server.tool()
async def read_messages(channel: str, since: str = None, msg_type: str = None) -> list[dict]:
    """Read messages from a channel, optionally filtered by time or type."""
    pass

@server.tool()
async def get_channel_history(channel: str, limit: int = 50) -> list[dict]:
    """Get full message history for audit trail."""
    pass

@server.tool()
async def get_conversation_thread(message_id: str) -> list[dict]:
    """Follow a reply chain to see full conversation."""
    pass

@server.tool()
async def get_all_activity(since: str = None, limit: int = 100) -> list[dict]:
    """Cross-channel activity log for monitoring the creative process."""
    pass
```

### Message Persistence / History
- **SQLite**: Simple, file-based, zero-config. Perfect for local development.
- Every message persisted on write. Full history queryable.
- Audit trail is first-class — the SQLite database IS the creative process record.
- Can add JSON export for human-readable audit dumps.

### Suitability for Agent Communication
- **Channel model**: Dict of channels, one per agent. Exact match to design spec.
- **Any-to-any**: Any agent calls `post_message(channel="narrator", ...)`. Trivial.
- **Structured data**: Pydantic models, serialized to JSON in SQLite. Type-safe.
- **Audit trail**: Built-in from day one. SQLite queries over message history.
- **Reply threading**: `reply_to` field enables conversation chains.
- **Cross-channel monitoring**: `get_all_activity` shows the full creative process timeline.

### Overhead Assessment
- **Zero external dependencies.** SQLite is part of Python stdlib.
- **Consistent with Mythline architecture.** Same MCP pattern as Storage MCP, Web Search MCP, etc.
- **No new concepts.** Agents already know how to call MCP tools.
- **Simple implementation.** ~200-300 lines of code for full functionality.

### MCP Wrappability
- **It IS the MCP service.** No wrapping needed.

### Verdict
**The architecturally correct choice for Mythline.** This is the only option that:
1. Follows the established pattern (MCP = data layer, agents = intelligence)
2. Adds zero external dependencies
3. Provides built-in persistence and audit trail
4. Requires no new client libraries or concepts
5. Keeps agents interacting via MCP tools (uniform interface)
6. Is simple to build (~200-300 lines)

---

## Option 7: Other Python-Native Libraries

### Bubus (by browser-use team)

- **What**: Pydantic-powered async event bus with WAL persistence, FIFO ordering, concurrency control.
- **Pros**: Production-ready, type-safe events, async/sync handlers, loop prevention, Pydantic integration matches our stack.
- **Cons**: WAL persistence is crash-recovery, not long-term audit trail. In-memory event limits (100 default) prevent unbounded growth but also limit history. Designed for event-driven apps, not agent messaging.
- **Fit**: Partial. Would need significant customization for channel-based agent messaging and persistent audit trail.

### Lahja (by Ethereum Foundation)

- **What**: Multi-process async event bus. Non-blocking asyncio IPC.
- **Pros**: Built for inter-process communication, supports asyncio and trio.
- **Cons**: Last release was 2019-2020 era. Likely unmaintained. Ethereum Foundation has moved on. Limited community.
- **Fit**: Poor. Stale project, over-engineered for our single-process use case.

### messagebus (PyPI)

- **What**: Domain-driven design message bus with command/event handlers.
- **Pros**: Clean DDD pattern, async support.
- **Cons**: Designed for CQRS/DDD patterns, not agent-to-agent messaging. No built-in persistence.
- **Fit**: Wrong abstraction. We need agent channels, not command buses.

### PADE (Python Agent DEvelopment)

- **What**: FIPA-compliant multi-agent framework using Twisted.
- **Pros**: Purpose-built for multi-agent systems, FIPA protocol support.
- **Cons**: Uses Twisted (not asyncio), last significant update ~2020, academic project. Heavy framework — would replace Pydantic AI, not complement it.
- **Fit**: Poor. Different async framework, too heavy, would conflict with our Pydantic AI architecture.

---

## Existing Multi-Agent Communication Frameworks

### Google A2A Protocol (Agent2Agent)
- **What**: Industry standard for agent interoperability (v0.3, 150+ orgs). HTTP/gRPC-based, JSON-RPC protocol.
- **Pros**: Well-designed, official Python SDK, Linux Foundation backed.
- **Cons**: Designed for inter-organization agent interoperability, not intra-system agent collaboration. Heavy protocol for 8 agents in the same system. Assumes agents are separate services.
- **Fit**: Over-engineered for our use case. A2A solves "how do agents from different companies talk" — we need "how do 8 agents in my system collaborate."

### LangGraph Multi-Agent Swarm
- **What**: Swarm-style multi-agent orchestration on LangGraph.
- **Cons**: Requires LangChain/LangGraph ecosystem. We use Pydantic AI. Would require framework migration.
- **Fit**: Framework conflict. Not compatible with our stack.

### Agency Swarm
- **What**: Multi-agent framework with directional communication flows.
- **Cons**: Opinionated framework with its own agent model. Would replace Pydantic AI.
- **Fit**: Same problem — would require abandoning our agent framework.

### Swarms Framework
- **What**: Enterprise multi-agent orchestration with custom social algorithms.
- **Cons**: Heavy enterprise framework, replaces the entire agent stack.
- **Fit**: Way too heavy. Solves a different problem at a different scale.

### OpenAI Swarm
- **What**: Lightweight experimental framework for multi-agent handoffs.
- **Cons**: OpenAI-specific, experimental, sequential handoff model (not parallel collaboration).
- **Fit**: Wrong collaboration model. We need parallel agents with message passing, not sequential handoffs.

**Overall finding**: Existing multi-agent frameworks assume you're using THEIR agent model. Since we're committed to Pydantic AI (Decision D1), none of these frameworks can be adopted without replacing our entire agent stack. What we actually need is just the **communication layer** — which is exactly what a custom MCP message queue provides.

---

## Comparison Matrix

| Criteria | Redis Streams | ZeroMQ | RabbitMQ/Celery | asyncio Queue | NATS JetStream | Custom MCP | Bubus |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Setup simplicity** | Poor (WSL/Docker on Windows) | Good (pip only) | Very Poor (Erlang+broker) | Excellent (stdlib) | Good (single binary) | Excellent (part of project) | Good (pip only) |
| **External process needed** | Yes (Redis server) | No | Yes (RabbitMQ) | No | Yes (NATS server) | No (is the MCP process) | No |
| **Python async quality** | Good (redis-py async) | Good (zmq.asyncio) | Fair (aio-pika) | Excellent (native) | Good (nats-py) | Excellent (FastMCP) | Good (native async) |
| **Message persistence** | Excellent (append-only log) | None | Fair (consumed-once) | None | Excellent (JetStream) | Excellent (SQLite) | Poor (WAL only) |
| **Audit trail** | Excellent (XRANGE) | None | None | None | Excellent (replay) | Excellent (SQL queries) | Poor |
| **Channel-per-agent model** | Good (stream per agent) | Fair (socket mgmt) | Fair (queue per agent) | Good (dict of queues) | Excellent (subjects) | Excellent (by design) | Fair (event types) |
| **Any-to-any posting** | Good (XADD anywhere) | Fair (connection mgmt) | Fair (exchange routing) | Good (dict lookup) | Excellent (publish) | Excellent (tool call) | Fair (emit) |
| **Structured data** | Good (field-value maps) | Poor (raw bytes) | Good (JSON) | Excellent (Python objects) | Good (JSON) | Excellent (Pydantic) | Good (Pydantic events) |
| **Matches Mythline arch** | Fair | Poor | Poor | Fair | Fair | Excellent | Fair |
| **Development effort** | Low (client exists) | High (build everything) | Low (client exists) | Medium (build persistence) | Low (client exists) | Medium (build service) | Medium (customize) |
| **Operational overhead** | Medium | None | High | None | Low | None | None |
| **Appropriate scale** | Overkill | Overkill | Massive overkill | Right-sized | Overkill | Right-sized | Right-sized |

---

## Recommendation

### Primary Recommendation: Option 6 — Custom MCP-Based Message Queue

**Reasoning:**

1. **Architectural consistency.** The design document (D11, MCP Design Principles) explicitly states "Message Queue as MCP. Drama agent collaboration runs through MCP, keeping agent communication uniform with the rest of the system." Building a custom MCP service is not a workaround — it IS the design.

2. **Zero new dependencies.** SQLite is stdlib. FastMCP is already in our stack. No new server processes, no new client libraries, no new concepts for agents to learn.

3. **Right-sized.** 8 agents, dozens of messages per scene, local development. We don't need sub-millisecond latency or millions of messages per second. We need: post, read, history. That's ~200-300 lines of Python.

4. **First-class audit trail.** SQLite persistence means every message is queryable from the moment it's sent. `SELECT * FROM messages WHERE channel = 'narrator' ORDER BY timestamp` — the creative process is fully observable and debuggable.

5. **Pydantic integration.** Message schemas are Pydantic models. Type-safe, validated, documented. Matches the agent framework perfectly.

6. **Uniform agent interface.** Every agent already interacts with MCP services via tool calls. The message queue is just another MCP tool: `post_message()`, `read_messages()`, `get_history()`. No new patterns.

### Fallback / Evolution Path

If the custom MCP approach hits limitations later (e.g., multi-process agents, distributed deployment):

- **Upgrade to NATS JetStream.** Single binary, minimal resources, excellent persistence. The MCP service interface stays the same — just swap the internal implementation from SQLite to NATS. Agents never know the difference.

### What NOT to Do

- **Don't use RabbitMQ/Celery.** Enterprise infrastructure for a local creative tool.
- **Don't use ZeroMQ.** Transport-only, no persistence, wrong abstraction.
- **Don't adopt a multi-agent framework.** They all want to replace Pydantic AI. We just need the communication pipe.
- **Don't over-engineer.** 8 agents, local process, creative content. SQLite + asyncio + MCP is the right level.

---

## Sources

- [Redis Streams Documentation](https://redis.io/docs/latest/develop/data-types/streams/)
- [Redis on Windows](https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-windows/)
- [ZeroMQ Python Patterns](https://www.johal.in/zeromq-pyzmq-patterns-python-dealer-router-for-low-latency-messaging-2025/)
- [ZeroMQ Official Site](https://zeromq.org/)
- [NATS.io Official Site](https://nats.io/)
- [NATS Python Client (nats.py)](https://github.com/nats-io/nats.py)
- [JetStream Documentation](https://docs.nats.io/nats-concepts/jetstream)
- [NATS JetStream Persistence](https://oneuptime.com/blog/post/2026-01-26-nats-jetstream-persistence/view)
- [NATS Server Installation](https://docs.nats.io/running-a-nats-service/introduction/installation)
- [Python asyncio.Queue Documentation](https://docs.python.org/3/library/asyncio-queue.html)
- [RabbitMQ vs Celery Comparison](https://www.svix.com/resources/faq/rabbitmq-vs-celery/)
- [Modern Queueing Architectures](https://medium.com/@pranavprakash4777/modern-queueing-architectures-celery-rabbitmq-redis-or-temporal-f93ea7c526ec)
- [Bubus Event Bus (browser-use)](https://github.com/browser-use/bubus)
- [Lahja Event Bus (Ethereum)](https://github.com/ethereum/lahja)
- [Google A2A Protocol](https://a2a-protocol.org/latest/)
- [A2A Protocol Announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [LangGraph Multi-Agent Swarm](https://www.marktechpost.com/2025/05/15/meet-langgraph-multi-agent-swarm-a-python-library-for-creating-swarm-style-multi-agent-systems-using-langgraph/)
- [Agency Swarm](https://github.com/VRSEN/agency-swarm)
- [Swarms Framework](https://github.com/kyegomez/swarms)
- [OpenAI Swarm](https://github.com/openai/swarm)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [redis-py async documentation](https://redis.readthedocs.io/en/v6.1.0/examples/redis-stream-example.html)
- [HN: Go-to message queue in 2025](https://news.ycombinator.com/item?id=43993982)
- [Redis vs ZeroMQ Comparison](https://stackshare.io/stackups/redis-vs-zeromq)
- [PADE Multi-Agent Framework](https://pade.readthedocs.io/en/latest/)
