# Content Reviewer Pattern - Module Structure

This document outlines the file organization and structure for implementing the Content Reviewer pattern.

## Overview

The Content Reviewer pattern is organized into three main component areas:
1. **Graph Workflow** - Orchestrates the review process
2. **Agents** - Perform specialized tasks (assessment, query generation)
3. **Session Management** - Handles state persistence

## Directory Structure

```
src/
├── graphs/
│   └── content_reviewer/
│       ├── __init__.py
│       ├── graph.py
│       ├── nodes.py
│       ├── session_manager.py
│       └── models/
│           ├── __init__.py
│           ├── state_models.py
│           ├── session_models.py
│           └── output_models.py
│
├── agents/
│   ├── quality_assessor/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── prompts/
│   │   │   └── system_prompt.md
│   │   └── models/
│   │       ├── __init__.py
│   │       └── output_models.py
│   │
│   └── search_query_generator/
│       ├── __init__.py
│       ├── agent.py
│       ├── prompts/
│       │   └── system_prompt.md
│       └── models/
│           ├── __init__.py
│           └── output_models.py
│
└── libs/
    ├── web/
    │   ├── __init__.py
    │   ├── duck_duck_go.py
    │   └── crawl.py
    │
    ├── knowledge_base/
    │   ├── __init__.py
    │   └── knowledge_vectordb.py
    │
    └── utils/
        ├── __init__.py
        └── prompt_loader.py
```

## Component Breakdown

### Graph Workflow (`src/graphs/content_reviewer/`)

#### `__init__.py`
```python
from src.graphs.content_reviewer.graph import ContentReviewGraph

__all__ = ["ContentReviewGraph"]
```

#### `graph.py`
**Purpose:** Main graph class that orchestrates the workflow

**Responsibilities:**
- Initialize graph with all nodes
- Provide public `review()` method
- Handle state initialization
- Return results to caller

**Pattern Reference:** [graph_session_based.md](../../pydantic/graphs/graph_session_based.md)

**Key Elements:**
- Graph class with node list
- Async `review()` method with session parameters
- State initialization from input parameters
- Result extraction from graph output

#### `nodes.py`
**Purpose:** All workflow nodes for the review process

**Node List:**
1. `LoadOrCreateSession` - Session initialization
2. `GenerateSearchQueries` - AI-powered query generation
3. `GetSavedContext` - Knowledge base retrieval
4. `CollectWebData` - Web search and crawling
5. `PerformAIReview` - Quality assessment
6. `UpdateSession` - Record attempt in history
7. `CheckCompletion` - Decision logic for retry vs complete
8. `SaveSession` - Persist session for retry
9. `WipeSession` - Delete session on completion
10. `PopulateResult` - Build final result

**Pattern Reference:** [graph_session_based.md](../../pydantic/graphs/graph_session_based.md)

**Key Elements:**
- Each node is a `@dataclass` extending `BaseNode[ReviewState]`
- Async `run()` method with `GraphRunContext`
- State read/write via `ctx.state`
- Return next node or `End[Result]`

#### `session_manager.py`
**Purpose:** Session CRUD operations

**Functions:**
- `create_session()` - Create new session
- `load_session()` - Load from disk
- `save_session()` - Persist to disk
- `wipe_session()` - Delete from disk
- `compute_content_hash()` - SHA256 hash for change detection

**Pattern Reference:** [session_manager.md](../../libs/session/session_manager.md)

**Storage Location:** `.mythline/content_reviewer/sessions/{session_id}.json`

#### `models/state_models.py`
**Purpose:** Graph state (transient, per-execution)

**State Class:**
```python
@dataclass
class ReviewState:
    # Input
    session_id: str
    content: str
    original_prompt: str = ""  # Original creation prompt for requirement validation
    max_retries: int = 3
    quality_threshold: float = 0.8

    # References
    session: ReviewSession = None

    # Working data (not persisted)
    search_queries: SearchQueries = None
    saved_context: str = ""
    web_data: list[dict] = field(default_factory=list)
    current_review: dict = None
    quality_score: float = 0.0

    # Tracking
    workflow_stage: str = ""
    error_message: str = ""
    human_invoked: bool = False
```

**Pattern Reference:** [graph_stateful.md](../../pydantic/graphs/graph_stateful.md)

#### `models/session_models.py`
**Purpose:** Session state (persistent, across executions)

**Session Class:**
```python
@dataclass
class ReviewSession:
    session_id: str
    content_hash: str
    max_retries: int
    quality_threshold: float

    retry_count: int = 0
    status: str = "in_progress"
    last_review: dict | None = None
    history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def increment_retry(self): ...
    def add_attempt(self, score, details): ...
    def should_wipe(self) -> bool: ...
```

**Pattern Reference:** [session_models.md](../../libs/session/session_models.md)

#### `models/output_models.py`
**Purpose:** Result models returned to caller

**Result Class:**
```python
from pydantic import BaseModel, Field

class ReviewResult(BaseModel):
    session_id: str
    retry_count: int
    max_retries: int

    quality_score: float
    quality_threshold: float

    passed: bool
    max_retries_reached: bool
    needs_human_review: bool
    human_feedback_provided: bool
    session_completed: bool

    review_details: dict
    saved_context_summary: str | None
    web_references: list[dict]
    timestamp: str
    attempt_history: list[dict]

    def can_retry(self) -> bool:
        return not self.session_completed and not self.max_retries_reached
```

### Agents (`src/agents/`)

#### Quality Assessor Agent (`quality_assessor/`)

**Purpose:** Evaluates content quality across multiple dimensions

**File Structure:**
```
quality_assessor/
├── __init__.py              # Export QualityAssessorAgent
├── agent.py                 # Agent implementation
├── prompts/
│   └── system_prompt.md     # Assessment instructions
└── models/
    ├── __init__.py
    └── output_models.py     # QualityAssessment, ReviewIssue
```

**Pattern Reference:** [agent_stateless_subagent.md](../../pydantic/agents/agent_stateless_subagent.md)

**Key Output Model:**
```python
class QualityAssessment(BaseModel):
    quality_score: float           # Overall 0.0-1.0
    confidence: float              # Agent confidence 0.0-1.0
    strengths: list[str]
    weaknesses: list[str]
    issues: list[ReviewIssue]
    recommendations: list[str]
    summary: str
    meets_standards: bool
```

#### Search Query Generator Agent (`search_query_generator/`)

**Purpose:** Generates optimized search queries for KB and web

**File Structure:**
```
search_query_generator/
├── __init__.py
├── agent.py
├── prompts/
│   └── system_prompt.md
└── models/
    ├── __init__.py
    └── output_models.py     # SearchQueries
```

**Pattern Reference:** [agent_stateless_subagent.md](../../pydantic/agents/agent_stateless_subagent.md)

**Key Output Model:**
```python
class SearchQueries(BaseModel):
    kb_query: str              # For knowledge base search
    web_query: str             # For web search
```

### Libraries (`src/libs/`)

#### Web Integration (`libs/web/`)

**`duck_duck_go.py`**
- **Function:** `search(query: str) -> list[dict]`
- **Returns:** List of search results with `href`, `title`, `body`
- **Pattern Reference:** [web_search.md](../../libs/web/web_search.md)

**`crawl.py`**
- **Function:** `async crawl_content(url: str) -> str`
- **Returns:** Markdown content extracted from URL
- **Pattern Reference:** [web_crawler.md](../../libs/web/web_crawler.md)

#### Knowledge Base (`libs/knowledge_base/`)

**`knowledge_vectordb.py`**
- **Function:** `search_knowledge(query, top_k, collection) -> list[dict]`
- **Returns:** List of relevant documents from vector DB
- **Function:** `index_knowledge(text, metadata, collection)`
- **Purpose:** Add documents to knowledge base
- **Pattern Reference:** [knowledge_vectordb.md](../../libs/knowledge_base/knowledge_vectordb.md)

#### Utilities (`libs/utils/`)

**`prompt_loader.py`**
- **Function:** `load_system_prompt(file_path: str) -> str`
- **Returns:** System prompt from `prompts/system_prompt.md`
- **Pattern Reference:** [prompt_loader.md](../../libs/utils/prompt_loader.md)

## Data Flow

### Input → Graph → Output

```
Caller Input:
  content: str
  session_id: str
  original_prompt: str
  max_retries: int
  quality_threshold: float

        ↓

Graph State (ReviewState):
  session_id, content, original_prompt, config
  session: ReviewSession (loaded/created)
  search_queries: SearchQueries (generated)
  saved_context: str (from KB)
  web_data: list[dict] (from web)
  current_review: dict (from agent)
  quality_score: float (from agent)

        ↓

Session (ReviewSession):
  session_id, config
  retry_count, status
  history: list[attempt records]
  timestamps

        ↓

Caller Output (ReviewResult):
  session_id, retry_count
  quality_score, threshold
  passed, max_retries_reached
  session_completed, can_retry
  review_details, attempt_history
```

## Node Interaction Map

```
LoadOrCreateSession
  ├─ Loads: session_manager.load_session()
  ├─ Creates: session_manager.create_session()
  └─ Updates: ctx.state.session

        ↓

GenerateSearchQueries
  ├─ Calls: SearchQueryGeneratorAgent.run()
  └─ Updates: ctx.state.search_queries

        ↓

GetSavedContext
  ├─ Calls: knowledge_vectordb.search_knowledge()
  └─ Updates: ctx.state.saved_context

        ↓

CollectWebData
  ├─ Calls: duck_duck_go.search()
  ├─ Calls: crawl.crawl_content() (parallel)
  └─ Updates: ctx.state.web_data

        ↓

PerformAIReview
  ├─ Reads: ctx.state.content, saved_context, web_data
  ├─ Calls: QualityAssessorAgent.run()
  └─ Updates: ctx.state.current_review, quality_score

        ↓

UpdateSession
  ├─ Reads: ctx.state.quality_score, current_review
  └─ Calls: ctx.state.session.add_attempt()

        ↓

CheckCompletion
  ├─ Reads: ctx.state.session (status, retry_count)
  ├─ Evaluates: score vs threshold, retry vs max
  └─ Routes: WipeSession OR SaveSession

        ↓

SaveSession / WipeSession
  ├─ Calls: session_manager.save_session()
  └─ Calls: session_manager.wipe_session()

        ↓

PopulateResult
  ├─ Reads: All state data
  └─ Returns: ReviewResult
```

## File Responsibilities Summary

| File | Primary Responsibility | Key Functions/Classes |
|------|------------------------|----------------------|
| `graph.py` | Orchestrate workflow | `ContentReviewGraph.review()` |
| `nodes.py` | Workflow steps | 10 node classes |
| `session_manager.py` | Session persistence | `create/load/save/wipe_session()` |
| `state_models.py` | Transient state | `ReviewState` |
| `session_models.py` | Persistent state | `ReviewSession` |
| `output_models.py` | Results | `ReviewResult` |
| `quality_assessor/agent.py` | Quality evaluation | `QualityAssessorAgent.run()` |
| `quality_assessor/output_models.py` | Assessment structure | `QualityAssessment`, `ReviewIssue` |
| `search_query_generator/agent.py` | Query generation | `SearchQueryGeneratorAgent.run()` |
| `search_query_generator/output_models.py` | Query structure | `SearchQueries` |
| `duck_duck_go.py` | Web search | `search()` |
| `crawl.py` | Content extraction | `crawl_content()` |
| `knowledge_vectordb.py` | Vector DB ops | `search_knowledge()`, `index_knowledge()` |
| `prompt_loader.py` | Prompt loading | `load_system_prompt()` |

## Extension Points

### Adding New Nodes

**Location:** `src/graphs/content_reviewer/nodes.py`

```python
@dataclass
class MyNewNode(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> NextNode:
        # Your logic here
        return NextNode()
```

**Update:** `graph.py` to include new node in graph initialization

### Adding New Agents

**Location:** `src/agents/my_agent/`

**Structure:**
```
my_agent/
├── __init__.py
├── agent.py
├── prompts/
│   └── system_prompt.md
└── models/
    └── output_models.py
```

**Integration:** Call from node in `nodes.py`

### Customizing Session Model

**Location:** `src/graphs/content_reviewer/models/session_models.py`

**Add fields:** Extend `ReviewSession` dataclass with additional tracking

**Update:** `session_manager.py` if serialization changes needed

### Adding Metadata

**Location:** `src/graphs/content_reviewer/models/state_models.py`

**Add fields:** Extend `ReviewState` for additional working data

**Usage:** Available in all nodes via `ctx.state`

## Implementation Checklist

When implementing this pattern:

- [ ] Create `src/graphs/content_reviewer/` directory
- [ ] Implement `graph.py` with `ContentReviewGraph` class
- [ ] Implement all 10 nodes in `nodes.py`
- [ ] Create `session_manager.py` with CRUD functions
- [ ] Define `ReviewState` in `state_models.py`
- [ ] Define `ReviewSession` in `session_models.py`
- [ ] Define `ReviewResult` in `output_models.py`
- [ ] Create `quality_assessor/` agent
- [ ] Create `search_query_generator/` agent
- [ ] Implement/verify web libraries (`duck_duck_go.py`, `crawl.py`)
- [ ] Implement/verify knowledge base (`knowledge_vectordb.py`)
- [ ] Add system prompts for both agents
- [ ] Create session directory (`.mythline/content_reviewer/sessions/`)
- [ ] Write tests for nodes, agents, and full workflow
- [ ] Add error handling and logging
- [ ] Document custom configurations

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class/node
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Related Documentation

- **[INDEX.md](./INDEX.md)** - Pattern overview and quick navigation
- **[content_reviewer_pattern.md](./content_reviewer_pattern.md)** - Detailed implementation guide
- **[graph_session_based.md](../../pydantic/graphs/graph_session_based.md)** - Session-based graph patterns
- **[agent_stateless_subagent.md](../../pydantic/agents/agent_stateless_subagent.md)** - Stateless agent patterns
