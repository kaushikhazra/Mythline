# Content Reviewer Pattern

This blueprint provides detailed implementation guidance for the Content Reviewer pattern - a composite design pattern for quality assessment workflows with session-based retry logic and context enrichment.

## Overview

The Content Reviewer pattern implements a systematic approach to content quality assessment that:
- Evaluates content against multiple quality dimensions
- Enriches assessment with internal knowledge and external research
- Supports multiple improvement attempts with caller-controlled timing
- Tracks full attempt history across non-blocking execution calls
- Provides structured, actionable feedback
- Enables optional human escalation for edge cases

## Architecture

### High-Level Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                         Caller                                  │
│  (Controls retry timing, improves content between attempts)     │
└────────────┬────────────────────────────────────────┬───────────┘
             │                                        │
             │ Call 1: Initial assessment            │ Call N: Retry
             ▼                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Content Review Graph                          │
├─────────────────────────────────────────────────────────────────┤
│  1. LoadOrCreateSession    → Initialize/resume session          │
│  2. GenerateSearchQueries  → Create KB/web queries             │
│  3. GetSavedContext        → Retrieve internal guidelines       │
│  4. CollectWebData         → Gather external best practices     │
│  5. PerformAIReview        → Quality assessment                 │
│  6. UpdateSession          → Record attempt                     │
│  7. CheckCompletion        → Evaluate conditions                │
│  8a. SaveSession           → Persist (if retry)                 │
│  8b. WipeSession           → Clean up (if complete)             │
│  9. PopulateResult         → Build result                       │
└─────────────────────────────────────────────────────────────────┘
             │                                        │
             ▼                                        ▼
     ReviewResult                           ReviewResult
  (can_retry=True)                      (session_completed=True)
```

### Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Content Review Graph                        │
│              (Session-Based Orchestrator)                    │
└───────┬──────────────────────────────────────┬──────────────┘
        │                                      │
┌───────▼──────────┐                  ┌────────▼─────────┐
│   AI Agents      │                  │ Session Manager  │
│                  │                  │                  │
│ • Quality        │                  │ • Load/Create    │
│   Assessor       │                  │ • Save/Wipe      │
│                  │                  │ • JSON Storage   │
│ • Search Query   │                  └──────────────────┘
│   Generator      │
└───────┬──────────┘
        │
┌───────▼──────────────────────────────────────────────────────┐
│              Context Enrichment Layer                        │
├──────────────────────────────┬───────────────────────────────┤
│     Internal Knowledge       │      External Research        │
│                              │                               │
│ • Vector Search (Qdrant)     │ • Web Search (DuckDuckGo)    │
│ • Review Guidelines          │ • Best Practices Crawl        │
│ • Human Feedback History     │ • Current Standards           │
└──────────────────────────────┴───────────────────────────────┘
```

## Building Block Composition

This pattern combines these elementary blueprints:

### Core Foundation
- **[graph_session_based.md](../../pydantic/graphs/graph_session_based.md)** - Session persistence and retry logic
- **[graph_stateful.md](../../pydantic/graphs/graph_stateful.md)** - State management across nodes

### Agent Layer
- **[agent_stateless_subagent.md](../../pydantic/agents/agent_stateless_subagent.md)** - Quality assessor and query generator

### Data Layer
- **[knowledge_vectordb.md](../../libs/knowledge_base/knowledge_vectordb.md)** - Internal guidelines storage
- **[web_search.md](../../libs/web/web_search.md)** - External best practices discovery
- **[web_crawler.md](../../libs/web/web_crawler.md)** - Content extraction from URLs

### Persistence Layer
- **[session_manager.md](../../libs/session/session_manager.md)** - Session CRUD operations
- **[session_models.md](../../libs/session/session_models.md)** - Session state models

## Implementation Guide

### Step 1: Define Data Models

#### Graph State (Transient)

**File:** `src/graphs/content_reviewer/models/state_models.py`

```python
from dataclasses import dataclass, field

@dataclass
class ReviewState:
    """Graph state for one execution pass."""
    # Input
    session_id: str
    content: str
    original_prompt: str = ""  # Original creation prompt for requirement validation
    max_retries: int = 3
    quality_threshold: float = 0.8

    # References
    session: ReviewSession = None

    # Working data
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

#### Session State (Persistent)

**File:** `src/graphs/content_reviewer/models/session_models.py`

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ReviewSession:
    """Session state persisted across calls."""
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

    def increment_retry(self):
        self.retry_count += 1
        self.updated_at = datetime.now().isoformat()

    def add_attempt(self, score: float, review_details: dict):
        attempt_record = {
            "attempt": self.retry_count,
            "quality_score": score,
            "timestamp": datetime.now().isoformat(),
            "review_summary": review_details.get("summary", ""),
            "details": review_details
        }
        self.history.append(attempt_record)
        self.last_review = review_details
        self.updated_at = datetime.now().isoformat()

    def should_wipe(self) -> bool:
        return self.status in ["completed", "needs_human"]
```

#### Output Model

**File:** `src/graphs/content_reviewer/models/output_models.py`

```python
from pydantic import BaseModel, Field

class ReviewResult(BaseModel):
    """Result returned to caller with decision support and best attempt tracking."""
    session_id: str
    retry_count: int
    max_retries: int

    quality_score: float
    quality_threshold: float

    passed: bool = Field(description="Quality threshold met")
    max_retries_reached: bool = Field(description="Retry limit hit")
    needs_human_review: bool = Field(description="Human escalation needed")
    human_feedback_provided: bool = Field(description="Human already reviewed")
    session_completed: bool = Field(description="Session wiped, no more retries")

    # Best attempt tracking
    is_best_so_far: bool = Field(description="True if this attempt has highest score")
    best_attempt_number: int = Field(description="Attempt number with highest score")
    best_quality_score: float = Field(description="Highest score achieved")

    review_details: dict = Field(description="Full assessment")
    saved_context_summary: str | None = Field(description="KB context preview")
    web_references: list[dict] = Field(description="Web sources used")
    timestamp: str
    attempt_history: list[dict] = Field(description="All attempts")

    def can_retry(self) -> bool:
        """Helper for caller to check retry eligibility."""
        return not self.session_completed and not self.max_retries_reached

    def should_store_content(self) -> bool:
        """Helper for caller to check if content should be stored."""
        return self.is_best_so_far
```

### Step 2: Implement Session Manager

**File:** `src/graphs/content_reviewer/session_manager.py`

```python
from pathlib import Path
import json
import hashlib
from dataclasses import asdict
from datetime import datetime

from src.graphs.content_reviewer.models.session_models import ReviewSession

SESSION_DIR = Path(".mythline/content_reviewer/sessions")

def create_session(
    session_id: str,
    content: str,
    max_retries: int,
    quality_threshold: float
) -> ReviewSession:
    """Creates new session with configuration."""
    content_hash = compute_content_hash(content)
    return ReviewSession(
        session_id=session_id,
        content_hash=content_hash,
        max_retries=max_retries,
        quality_threshold=quality_threshold
    )

def load_session(session_id: str) -> ReviewSession | None:
    """Loads session from disk."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session_id}.json"

    if not session_file.exists():
        return None

    try:
        data = json.loads(session_file.read_text())
        return ReviewSession(**data)
    except Exception as e:
        print(f"[!] Error loading session {session_id}: {e}")
        return None

def save_session(session: ReviewSession):
    """Persists session to disk."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session.session_id}.json"

    try:
        session_file.write_text(json.dumps(asdict(session), indent=2))
    except Exception as e:
        print(f"[!] Error saving session {session.session_id}: {e}")

def wipe_session(session_id: str):
    """Deletes session file."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session_id}.json"

    try:
        if session_file.exists():
            session_file.unlink()
            print(f"[+] Session {session_id} wiped")
    except Exception as e:
        print(f"[!] Error wiping session {session_id}: {e}")

def compute_content_hash(content: str) -> str:
    """Computes SHA256 hash for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()
```

### Step 3: Implement Agents

#### Quality Assessor Agent

**File:** `src/agents/quality_assessor/agent.py`

```python
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.quality_assessor.models.output_models import QualityAssessment

load_dotenv()

class QualityAssessorAgent:
    AGENT_ID = "quality_assessor"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=QualityAssessment,
            system_prompt=system_prompt
        )

    async def run(self, prompt: str) -> AgentRunResult[QualityAssessment]:
        agent_output = await self.agent.run(prompt)
        return agent_output
```

**File:** `src/agents/quality_assessor/models/output_models.py`

```python
from pydantic import BaseModel, Field

class ReviewIssue(BaseModel):
    category: str = Field(description="clarity, accuracy, structure, tone, grammar")
    severity: str = Field(description="critical, high, medium, low")
    location: str = Field(description="paragraph, section, line number")
    description: str = Field(description="What the issue is")
    suggestion: str = Field(description="How to fix it")
    example: str | None = Field(default=None, description="Corrected version")

class QualityAssessment(BaseModel):
    quality_score: float = Field(description="Overall score 0.0-1.0")
    confidence: float = Field(description="Assessment confidence 0.0-1.0")
    strengths: list[str] = Field(description="Positive aspects")
    weaknesses: list[str] = Field(description="Areas needing improvement")
    issues: list[ReviewIssue] = Field(description="Detailed issues")
    recommendations: list[str] = Field(description="Actionable improvements")
    summary: str = Field(description="2-3 sentence assessment")
    meets_standards: bool = Field(description="Meets basic standards")
```

**File:** `src/agents/quality_assessor/prompts/system_prompt.md`

See [prompt_engineering.md](../../pydantic/prompts/prompt_engineering.md) for prompt design guidance.

Key elements:
- Multi-dimensional evaluation (clarity, accuracy, structure, tone, grammar)
- Structured output with issues and suggestions
- Scoring guidelines (0.9-1.0 excellent, 0.8-0.9 good, etc.)
- Context integration instructions

#### Search Query Generator Agent

**File:** `src/agents/search_query_generator/agent.py`

```python
import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.run import AgentRunResult

from src.libs.utils.prompt_loader import load_system_prompt
from src.agents.search_query_generator.models.output_models import SearchQueries

load_dotenv()

class SearchQueryGeneratorAgent:
    AGENT_ID = "search_query_generator"

    def __init__(self):
        llm_model = f"openrouter:{os.getenv('LLM_MODEL')}"
        system_prompt = load_system_prompt(__file__)

        self.agent = Agent(
            llm_model,
            output_type=SearchQueries,
            system_prompt=system_prompt
        )

    async def run(self, content: str) -> AgentRunResult[SearchQueries]:
        prompt = f"Generate search queries for this content:\n\n{content[:500]}"
        agent_output = await self.agent.run(prompt)
        return agent_output
```

**File:** `src/agents/search_query_generator/models/output_models.py`

```python
from pydantic import BaseModel, Field

class SearchQueries(BaseModel):
    kb_query: str = Field(description="Query for knowledge base search")
    web_query: str = Field(description="Query for web search")
```

### Step 4: Implement Graph Nodes

**File:** `src/graphs/content_reviewer/nodes.py`

```python
from __future__ import annotations
from dataclasses import dataclass
import asyncio
from datetime import datetime

from pydantic_graph import BaseNode, End, GraphRunContext

from src.graphs.content_reviewer.models.state_models import ReviewState
from src.graphs.content_reviewer.models.output_models import ReviewResult
from src.graphs.content_reviewer.session_manager import (
    load_session, save_session, wipe_session, create_session
)
from src.libs.knowledge_base.knowledge_vectordb import search_knowledge
from src.libs.web.duck_duck_go import search as web_search
from src.libs.web.crawl import crawl_content
from src.agents.quality_assessor import QualityAssessorAgent
from src.agents.search_query_generator import SearchQueryGeneratorAgent

@dataclass
class LoadOrCreateSession(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> GenerateSearchQueries:
        print(f"[*] LoadOrCreateSession for {ctx.state.session_id}")

        session = load_session(ctx.state.session_id)

        if session is None:
            print(f"[+] Creating new session")
            session = create_session(
                session_id=ctx.state.session_id,
                content=ctx.state.content,
                max_retries=ctx.state.max_retries,
                quality_threshold=ctx.state.quality_threshold
            )
        else:
            print(f"[+] Loaded existing session (retry {session.retry_count})")

        session.increment_retry()
        ctx.state.session = session
        ctx.state.workflow_stage = "session_loaded"

        return GenerateSearchQueries()

@dataclass
class GenerateSearchQueries(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> GetSavedContext:
        print(f"[*] GenerateSearchQueries")

        try:
            agent = SearchQueryGeneratorAgent()
            result = await agent.run(ctx.state.content)
            ctx.state.search_queries = result.output

            print(f"[+] KB Query: {result.output.kb_query}")
            print(f"[+] Web Query: {result.output.web_query}")
        except Exception as e:
            print(f"[!] Query generation error: {e}")

        return GetSavedContext()

@dataclass
class GetSavedContext(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> CollectWebData:
        print(f"[*] GetSavedContext")

        try:
            kb_query = ctx.state.search_queries.kb_query if ctx.state.search_queries else "review guidelines"
            results = search_knowledge(kb_query, top_k=5, collection="reviewer_knowledge")

            if results:
                context_parts = [f"[{r.get('source_file', 'unknown')}]\n{r.get('text', '')}" for r in results]
                ctx.state.saved_context = "\n\n".join(context_parts)
                print(f"[+] Found {len(results)} context items")
            else:
                ctx.state.saved_context = "No saved context found"
        except Exception as e:
            print(f"[!] Context search error: {e}")
            ctx.state.saved_context = "No saved context found"

        return CollectWebData()

@dataclass
class CollectWebData(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> PerformAIReview:
        print(f"[*] CollectWebData")

        try:
            query = ctx.state.search_queries.web_query if ctx.state.search_queries else "content review best practices 2025"
            search_results = web_search(query)

            if search_results:
                urls_to_crawl = [r['href'] for r in search_results[:3]]
                print(f"[*] Crawling {len(urls_to_crawl)} URLs...")

                crawl_tasks = [crawl_content(url) for url in urls_to_crawl]
                crawled_contents = await asyncio.gather(*crawl_tasks, return_exceptions=True)

                for i, result in enumerate(search_results[:3]):
                    content = crawled_contents[i] if i < len(crawled_contents) else ""
                    if isinstance(content, Exception):
                        content = ""
                    if isinstance(content, str):
                        content = content[:3000]

                    ctx.state.web_data.append({
                        "url": result['href'],
                        "title": result.get('title', ''),
                        "content": content
                    })

                print(f"[+] Collected {len(ctx.state.web_data)} web references")
        except Exception as e:
            print(f"[!] Web search error: {e}")

        return PerformAIReview()

@dataclass
class PerformAIReview(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> UpdateSession:
        print(f"[*] PerformAIReview")

        try:
            prompt_parts = [f"# Content to Review\n\n{ctx.state.content}"]

            # Include original creation prompt for requirement validation
            if ctx.state.original_prompt:
                prompt_parts.append(f"\n# Review For This:\n\n{ctx.state.original_prompt}")

            if ctx.state.saved_context and ctx.state.saved_context != "No saved context found":
                prompt_parts.append(f"\n## Internal Knowledge\n\n{ctx.state.saved_context}")

            if ctx.state.web_data:
                web_context = "\n\n".join([
                    f"### {item['title']}\nURL: {item['url']}\n{item['content'][:3000]}"
                    for item in ctx.state.web_data if item.get('content')
                ])
                if web_context:
                    prompt_parts.append(f"\n## External References\n\n{web_context}")

            prompt = "\n\n".join(prompt_parts)

            agent = QualityAssessorAgent()
            result = await agent.run(prompt)
            assessment = result.output

            ctx.state.current_review = {
                "quality_score": assessment.quality_score,
                "confidence": assessment.confidence,
                "strengths": assessment.strengths,
                "weaknesses": assessment.weaknesses,
                "issues": [
                    {
                        "category": issue.category,
                        "severity": issue.severity,
                        "location": issue.location,
                        "description": issue.description,
                        "suggestion": issue.suggestion,
                        "example": issue.example
                    }
                    for issue in assessment.issues
                ],
                "recommendations": assessment.recommendations,
                "summary": assessment.summary,
                "meets_standards": assessment.meets_standards
            }
            ctx.state.quality_score = assessment.quality_score

            print(f"[+] Quality Score: {assessment.quality_score:.2f}")
            print(f"[+] Confidence: {assessment.confidence:.2f}")
        except Exception as e:
            print(f"[!] AI review error: {e}")
            ctx.state.quality_score = 0.0
            ctx.state.current_review = {"quality_score": 0.0, "summary": f"Review failed: {e}"}

        return UpdateSession()

@dataclass
class UpdateSession(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> CheckCompletion:
        print(f"[*] UpdateSession")

        if ctx.state.session and ctx.state.current_review:
            is_best_so_far = ctx.state.session.add_attempt(
                score=ctx.state.quality_score,
                review_details=ctx.state.current_review
            )

            # Signal to caller if this is the best attempt
            ctx.state.is_best_attempt = is_best_so_far

            print(f"[+] Recorded attempt {ctx.state.session.retry_count}")
            if is_best_so_far:
                print(f"[*] New best score: {ctx.state.quality_score:.2f}")

        return CheckCompletion()

@dataclass
class CheckCompletion(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> WipeSession | SaveSession:
        print(f"[*] CheckCompletion")

        session = ctx.state.session
        score = ctx.state.quality_score
        threshold = session.quality_threshold
        retry_count = session.retry_count
        max_retries = session.max_retries

        print(f"[*] Score: {score:.2f}, Threshold: {threshold:.2f}, Retry: {retry_count}/{max_retries}")

        if score >= threshold:
            print(f"[+] Quality threshold met!")
            session.status = "completed"
            return WipeSession()

        if retry_count >= max_retries:
            print(f"[!] Max retries reached")
            session.status = "completed"
            return WipeSession()

        print(f"[*] Can retry, saving session")
        session.status = "in_progress"
        return SaveSession()

@dataclass
class SaveSession(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> PopulateResult:
        print(f"[*] SaveSession")
        if ctx.state.session:
            save_session(ctx.state.session)
        return PopulateResult()

@dataclass
class WipeSession(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> PopulateResult:
        print(f"[*] WipeSession")
        wipe_session(ctx.state.session_id)
        return PopulateResult()

@dataclass
class PopulateResult(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> End[ReviewResult]:
        print(f"[*] PopulateResult")

        session = ctx.state.session
        passed = ctx.state.quality_score >= session.quality_threshold
        max_retries_reached = session.retry_count >= session.max_retries
        session_completed = session.status in ["completed", "needs_human"]

        result = ReviewResult(
            session_id=session.session_id,
            retry_count=session.retry_count,
            max_retries=session.max_retries,
            quality_score=ctx.state.quality_score,
            quality_threshold=session.quality_threshold,
            passed=passed,
            max_retries_reached=max_retries_reached,
            needs_human_review=False,
            human_feedback_provided=ctx.state.human_invoked,
            session_completed=session_completed,
            is_best_so_far=ctx.state.is_best_attempt,
            best_attempt_number=session.best_attempt_number,
            best_quality_score=session.best_quality_score,
            review_details=ctx.state.current_review or {},
            saved_context_summary=ctx.state.saved_context[:200] if ctx.state.saved_context else None,
            web_references=[{"title": item["title"], "url": item["url"]} for item in ctx.state.web_data],
            timestamp=datetime.now().isoformat(),
            attempt_history=session.history
        )

        return End(result)
```

### Step 5: Implement Graph Class

**File:** `src/graphs/content_reviewer/graph.py`

```python
from pydantic_graph import Graph

from src.graphs.content_reviewer.models.state_models import ReviewState
from src.graphs.content_reviewer.models.output_models import ReviewResult
from src.graphs.content_reviewer.nodes import (
    LoadOrCreateSession,
    GenerateSearchQueries,
    GetSavedContext,
    CollectWebData,
    PerformAIReview,
    UpdateSession,
    CheckCompletion,
    WipeSession,
    SaveSession,
    PopulateResult
)

class ContentReviewGraph:
    def __init__(self):
        self.graph = Graph(nodes=[
            LoadOrCreateSession,
            GenerateSearchQueries,
            GetSavedContext,
            CollectWebData,
            PerformAIReview,
            UpdateSession,
            CheckCompletion,
            WipeSession,
            SaveSession,
            PopulateResult
        ])

    async def review(
        self,
        content: str,
        session_id: str,
        original_prompt: str = "",
        max_retries: int = 3,
        quality_threshold: float = 0.8
    ) -> ReviewResult:
        """Performs one execution pass of content review.

        Non-blocking: Returns after single pass. Caller controls
        retry timing by calling again with same session_id.

        Args:
            content: Content to review
            session_id: Unique session identifier (same for retries)
            original_prompt: Original creation prompt for requirement validation
            max_retries: Maximum retry attempts
            quality_threshold: Required score (0.0-1.0)

        Returns:
            ReviewResult with session status and decision flags
        """
        state = ReviewState(
            session_id=session_id,
            content=content,
            original_prompt=original_prompt,
            max_retries=max_retries,
            quality_threshold=quality_threshold
        )

        result = await self.graph.run(LoadOrCreateSession(), state=state)

        return result.output
```

## Usage Patterns

### Basic Usage

```python
from src.graphs.content_reviewer import ContentReviewGraph

async def review_content():
    graph = ContentReviewGraph()

    # Original creation prompt for context
    creation_prompt = """
    Write a 500-word blog post explaining JWT authentication for beginner developers.
    Include: what JWTs are, how they work, and a simple use case example.
    Tone: Educational but friendly.
    """

    generated_content = "..."  # Content generated from the prompt

    result = await graph.review(
        content=generated_content,
        original_prompt=creation_prompt,  # Pass original requirements
        session_id="review_001",
        max_retries=3,
        quality_threshold=0.8
    )

    if result.passed:
        print(f"✓ Content meets quality standards (score: {result.quality_score:.2f})")
    else:
        print(f"✗ Quality below threshold (score: {result.quality_score:.2f})")
        for issue in result.review_details['issues']:
            print(f"  - {issue['description']}")
```

### Retry Loop with Content Improvement and Best Attempt Tracking

```python
async def review_with_retries():
    graph = ContentReviewGraph()
    session_id = "review_001"

    # Original requirements
    creation_prompt = "Create technical documentation covering all API endpoints..."
    content = load_initial_content()

    # Storage for content versions
    content_versions = {}

    while True:
        result = await graph.review(
            content=content,
            original_prompt=creation_prompt,  # Validate against requirements
            session_id=session_id,
            max_retries=3,
            quality_threshold=0.85
        )

        print(f"Attempt {result.retry_count}: Score {result.quality_score:.2f}")

        # Store content when it's the best so far
        if result.is_best_so_far:
            content_versions[result.retry_count] = content
            print(f"[+] Stored as best version (score: {result.quality_score:.2f})")

        if result.passed:
            print("✓ Quality threshold met")
            break

        if result.session_completed:
            print("✗ Max retries exhausted")

            # Use best version if available
            if result.best_attempt_number != result.retry_count:
                best_content = content_versions.get(result.best_attempt_number)
                print(f"[*] Returning best attempt #{result.best_attempt_number}")
                print(f"[*] Best score: {result.best_quality_score:.2f} vs last: {result.quality_score:.2f}")
                content = best_content  # Use the best version
            break

        print("Improving content based on feedback...")
        content = apply_suggestions(content, result.review_details)

        await asyncio.sleep(2)

    return content, result
```

### Batch Review

```python
async def batch_review(documents: list[str]):
    graph = ContentReviewGraph()
    results = []

    for i, doc in enumerate(documents):
        result = await graph.review(
            content=doc,
            session_id=f"batch_{i}",
            quality_threshold=0.8
        )

        results.append({
            "doc_id": i,
            "score": result.quality_score,
            "passed": result.passed,
            "attempts": result.retry_count
        })

        print(f"Document {i}: {'✓' if result.passed else '✗'} (score: {result.quality_score:.2f})")

    return results
```

## Key Design Decisions

### 1. Non-Blocking Retry Pattern

**Decision:** Each graph execution is start-to-end, no internal loops

**Rationale:**
- Caller controls retry timing (allows content improvement between attempts)
- Enables async/background processing
- Simplifies graph logic
- Better separation of concerns

**Trade-offs:**
- Caller must implement retry loop
- More complex caller code
- Session persistence required

### 2. Requirement Validation via Original Prompt

**Decision:** Pass original creation prompt to reviewer as "Review For This" context

**Rationale:**
- Reviewer knows exactly what was requested
- Can validate content fulfills original requirements
- Prevents generic quality assessment without purpose
- Enables intent alignment checking
- No separate "review criteria" needed

**Benefits:**
- Complete traceability: request → generation → review
- Validates word count, tone, inclusions, structure
- Checks if all required elements are present
- Contextual quality assessment

**Example Prompt Structure:**
```
# Content to Review
[Generated content...]

# Review For This:
Write a 500-word blog post explaining JWT authentication for beginners.
Include: what JWTs are, how they work, and a simple use case.
Tone: Educational but friendly.

# Internal Knowledge
[Review guidelines...]

# External References
[Best practices...]
```

**Trade-offs:**
- Requires caller to provide original prompt
- Prompt must be well-structured for effective validation

### 3. Context Enrichment Before Assessment

**Decision:** Gather KB and web context before quality assessment

**Rationale:**
- Better assessment with current best practices
- Consistent evaluation criteria
- Learning from past feedback
- Adaptable to content types

**Trade-offs:**
- Longer execution time
- External API dependencies
- Potential for irrelevant context

### 4. Dual Completion Conditions

**Decision:** Complete on either threshold met OR max retries

**Rationale:**
- Flexible success criteria
- Prevents infinite loops
- Allows "good enough" acceptance
- Tracks exhaustion separately from success

**Trade-offs:**
- More complex completion logic
- Caller must distinguish pass vs exhaustion

### 5. Structured Feedback

**Decision:** Return detailed issues with severity, location, suggestions

**Rationale:**
- Actionable improvement guidance
- Transparent decision-making
- Supports automated content improvement
- Better user experience

**Trade-offs:**
- Larger result payloads
- More complex agent prompting
- Potential for inconsistent formatting

## Extension Points

### 1. Human-in-the-Loop Integration

**Add After CheckCompletion:**

```python
@dataclass
class InvokeHuman(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> SaveHumanFeedback:
        print(f"[*] InvokeHuman")

        human_feedback = await request_human_review(
            content=ctx.state.content,
            ai_review=ctx.state.current_review,
            attempt_history=ctx.state.session.history
        )

        ctx.state.human_invoked = True
        ctx.state.current_review = human_feedback
        ctx.state.quality_score = human_feedback.get("quality_score", 0.0)

        return SaveHumanFeedback()

@dataclass
class SaveHumanFeedback(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> WipeSession:
        print(f"[*] SaveHumanFeedback")

        from src.libs.knowledge_base.knowledge_vectordb import index_knowledge

        index_knowledge(
            text=json.dumps(ctx.state.current_review),
            metadata={
                "type": "human_feedback",
                "session_id": ctx.state.session_id,
                "quality_score": ctx.state.quality_score,
                "timestamp": datetime.now().isoformat()
            },
            collection="reviewer_knowledge"
        )

        ctx.state.session.status = "needs_human"
        return WipeSession()
```

**Update CheckCompletion:**

```python
if retry_count >= max_retries and score < 0.5:
    print(f"[!] Low quality after max retries, escalating to human")
    session.status = "needs_human"
    return InvokeHuman()
```

### 2. Auto-Improvement Loop

```python
@dataclass
class ImproveContent(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> PerformAIReview:
        print(f"[*] ImproveContent")

        from src.agents.content_improver import ContentImproverAgent

        agent = ContentImproverAgent()
        result = await agent.run(
            content=ctx.state.content,
            review=ctx.state.current_review
        )

        ctx.state.content = result.output.improved_content
        print(f"[+] Content auto-improved")

        return PerformAIReview()
```

**Update CheckCompletion to route to ImproveContent instead of SaveSession**

### 3. Multi-Model Consensus

```python
@dataclass
class PerformAIReview(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> UpdateSession:
        agent1 = QualityAssessorAgent(model="gpt-4o")
        agent2 = QualityAssessorAgent(model="claude-sonnet-4")

        result1, result2 = await asyncio.gather(
            agent1.run(prompt),
            agent2.run(prompt)
        )

        consensus_score = (result1.output.quality_score + result2.output.quality_score) / 2
        ctx.state.quality_score = consensus_score

        print(f"[+] Consensus Score: {consensus_score:.2f}")

        return UpdateSession()
```

### 4. Dynamic Thresholds

```python
@dataclass
class CheckCompletion(BaseNode[ReviewState]):
    async def run(self, ctx: GraphRunContext[ReviewState]) -> WipeSession | SaveSession:
        session = ctx.state.session

        adaptive_threshold = session.quality_threshold - (0.05 * session.retry_count)
        adaptive_threshold = max(0.5, adaptive_threshold)

        print(f"[*] Adaptive threshold: {adaptive_threshold:.2f}")

        if ctx.state.quality_score >= adaptive_threshold:
            session.status = "completed"
            return WipeSession()

        # ... rest of logic
```

## Core Coding Principles

**IMPORTANT:** Before implementing, ensure code follows [Core Coding Principles](../../INDEX.md#core-coding-principles):
1. **Separation of Concerns** - Single responsibility per module/class/node
2. **KISS Principle** - Simple, direct solutions (no over-engineering)
3. **No Comments** - Self-documenting code (add comments only AFTER testing)

---

## Testing Strategy

### Unit Tests

```python
import pytest
from src.graphs.content_reviewer.nodes import CheckCompletion
from src.graphs.content_reviewer.models.state_models import ReviewState
from src.graphs.content_reviewer.models.session_models import ReviewSession

@pytest.mark.asyncio
async def test_check_completion_pass():
    session = ReviewSession("test", "hash", 3, 0.8)
    session.retry_count = 1

    state = ReviewState(session_id="test", content="test")
    state.session = session
    state.quality_score = 0.85

    ctx = GraphRunContext(state=state)
    node = CheckCompletion()
    result = await node.run(ctx)

    assert isinstance(result, WipeSession)
    assert session.status == "completed"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_workflow():
    graph = ContentReviewGraph()

    result = await graph.review(
        content="Test content for quality assessment",
        session_id="integration_test",
        max_retries=2,
        quality_threshold=0.7
    )

    assert result.session_id == "integration_test"
    assert result.retry_count >= 1
    assert result.quality_score >= 0.0
    assert len(result.attempt_history) >= 1
```

## Performance Considerations

### Async Operations

- **Web Search + Crawl:** Use `asyncio.gather()` for parallel URL crawling
- **Multi-Model Assessment:** Parallel agent invocations
- **Knowledge Base:** Ensure vector search is optimized with indexes

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_web_search(query: str):
    return web_search(query)
```

### Timeouts

```python
async def crawl_content_with_timeout(url: str, timeout: int = 10):
    try:
        return await asyncio.wait_for(crawl_content(url), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"[!] Timeout crawling {url}")
        return ""
```

## Troubleshooting

### Session Not Persisting

**Symptoms:** Session resets on each call

**Solutions:**
- Verify `session.increment_retry()` is called in LoadOrCreateSession
- Check `save_session()` is reached and executes
- Confirm session_id is consistent across calls
- Verify file permissions on `.mythline/content_reviewer/sessions/`

### Low Quality Scores

**Symptoms:** Consistently low scores even for good content

**Solutions:**
- Review quality assessor system prompt
- Check if context enrichment is working (KB + web)
- Verify scoring dimensions alignment with content type
- Test agent with known good/bad examples

### Web Search Failures

**Symptoms:** No web_data collected

**Solutions:**
- Check network connectivity
- Verify DuckDuckGo is accessible
- Add fallback to continue without web data
- Implement exponential backoff for rate limiting

## Related Patterns

- **Agent Orchestrator Pattern:** Coordinating multiple specialized agents
- **Context Enrichment Pattern:** Combining internal and external knowledge
- **Quality Loop Pattern:** Iterative improvement with feedback
- **Session-Based Workflow Pattern:** Resumable, multi-attempt processes

## Version History

- **v1.0** - Initial pattern documentation based on content reviewer implementation
