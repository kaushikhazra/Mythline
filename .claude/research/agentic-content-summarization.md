# Agentic Content Summarization for Large Research Pipelines

**Date**: 2026-02-23
**Context**: World Lore Researcher — context window overflow at extraction step
**Status**: Research complete, pending design decision

---

## The Problem

The World Lore Researcher's 9-step pipeline crawls web pages across 5 research topics (steps 1-5), accumulates the raw content, then sends it all to a single LLM call for structured extraction (step 6). During manual testing, the accumulated content reached ~198k tokens — far exceeding gpt-4o-mini's 128k context window.

### How Content Accumulates

```
Step 1 (zone_overview):       agent crawls 2-4 pages → full page content captured
Step 2 (npc_research):        agent crawls 2-4 pages → appended to raw_content
Step 3 (faction_research):    agent crawls 2-3 pages → appended
Step 4 (lore_research):       agent crawls 2-4 pages → appended
Step 5 (narrative_items):     agent crawls 2-3 pages → appended
                              ─────────────────────────────────
                              Total: 10-18 full web pages (~150k-250k tokens)
                              ↓
Step 6 (extract_all):         ALL content → single LLM prompt → 💥 128k limit
```

The pipeline already caps extraction to `MAX_RAW_CONTENT_BLOCKS = 10` blocks, and truncates content shown to the research agent (`CRAWL_CONTENT_TRUNCATE_CHARS = 5000`). But the full crawled content is what gets passed to extraction — and 10 full web pages easily exceed any reasonable context window.

### Why Truncation Won't Work

Naive truncation loses information. A wiki page about Elwynn Forest might have NPC details at the bottom, faction info in a sidebar, and lore buried in subsections. Cutting at a character limit discards structured data that the extraction step needs.

---

## Solution: Agentic Summarization (Map-Reduce)

The proven approach for summarizing content that exceeds any single LLM's context window:

### Map-Reduce Pattern

```
                        RAW CONTENT (198k tokens)
                              │
                    ┌─────────┼─────────┐
                    │         │         │
               Chunk 1    Chunk 2    Chunk N     ← MAP: split into chunks
                    │         │         │
               Summary 1  Summary 2  Summary N   ← Each chunk summarized independently
                    │         │         │
                    └─────────┼─────────┘
                              │
                      Merged Summary              ← REDUCE: combine summaries
                        (~20k tokens)
                              │
                     Step 6: extract_all           ← Fits in context window
```

Each chunk is summarized with awareness of the extraction task — the summarizer knows what fields to preserve (NPCs, factions, lore events, etc.) so domain-relevant details are retained while boilerplate, navigation text, and repetitive content are discarded.

### Variant: Hierarchical Summarization (RAPTOR-style)

For very large content, summaries themselves can be recursively summarized:

```
Level 0:  [chunk1] [chunk2] [chunk3] [chunk4] [chunk5] [chunk6]
              ↓        ↓        ↓        ↓        ↓        ↓
Level 1:  [sum1]   [sum2]   [sum3]   [sum4]   [sum5]   [sum6]
              ↓              ↓              ↓              ↓
Level 2:    [merged_1_2]  [merged_3_4]  [merged_5_6]
                   ↓              ↓
Level 3:      [final_summary]
```

This is overkill for our current scale (~200k tokens fits in 2-3 map rounds) but worth knowing for future domains with larger corpora.

---

## MCP Ecosystem Assessment

### Existing MCP Servers (None Fit)

| Server | Stars | Approach | Why It Doesn't Fit |
|--------|-------|----------|--------------------|
| **Braffolk/mcp-summarization-functions** | 38 | Single LLM call, caches full content | No chunking — same context limit problem |
| **0xshellming/mcp-summarizer** | 155 | Sends to Gemini 1.5 Pro (1M tokens) | Single-provider lock-in, no map-reduce |
| **Dicklesworthstone/ultimate_mcp_server** | 139 | Smart chunking + parallel multi-model | Kitchen-sink server (dozens of unrelated tools) |
| **puran-water/knowledge-base-mcp** | 4 | RAPTOR-style tree summarization | Full RAG system, not a standalone tool |
| **banyan-god/mcp-compact** | 1 | MCP proxy that compresses tool output | Compression proxy, not extraction-aware |
| **samteezy/mcp-context-proxy** | 5 | Transparent proxy with smart compression | Same — compression, not domain-aware summary |

**Gap**: No MCP server implements domain-aware, map-reduce summarization as a standalone tool. The pattern is well-known (LangChain implements it as a chain, RAPTOR uses hierarchical trees), but nobody has packaged it as an MCP service.

### Key Insight: The `ultimate_mcp_server` Approach

Dicklesworthstone's `ultimate_mcp_server` has the most sophisticated chunking:
- Three chunking methods: token-based, semantic boundary detection, structural analysis
- Configurable overlap between chunks
- Parallel processing across multiple LLM providers
- But it's a monolith with dozens of unrelated tools (browser automation, OCR, Excel, etc.)

The chunking + parallel summarization pattern is exactly what we need — just not as part of a 139-tool monolith.

---

## Design Options

### Option A: Build a Dedicated Summarization MCP Server

A new `mcp_summarizer/` service in the Mythline repo (follows our existing MCP pattern).

**Tools exposed**:
- `summarize(content, strategy, focus_areas, max_output_tokens)` — chunk → summarize → merge
- `summarize_for_extraction(content, schema_hint)` — domain-aware: preserves fields matching a schema

**Pros**:
- Reusable across all researcher agents (Quest, Character, Dynamics, etc.)
- Clean separation — researchers don't need to know about chunking
- Open-source opportunity (no standalone map-reduce MCP server exists)
- Follows Mythline convention: MCP = data/utility layer, agents = intelligence

**Cons**:
- New service to build, test, Dockerize
- Adds a hop: researcher → summarizer MCP → LLM → back
- Need to choose chunking strategy (token-based vs. semantic)

### Option B: Inline Summarization in the Pipeline

Add a "summarize" step between steps 5 and 6 in the existing pipeline. The researcher agent itself chunks and summarizes before extraction.

**Pros**:
- No new service
- Simpler deployment
- Agent can use its own LLM/MCP connections

**Cons**:
- Tightly coupled to the researcher — other agents can't reuse it
- Bloats the pipeline with non-research logic
- Harder to test in isolation

### Option C: Summarize Per-Step Instead of All-at-Once

Change steps 1-5 to summarize each topic's content immediately after crawling, before accumulating. Step 6 then receives 5 summaries (~5k tokens each) instead of 10+ raw pages.

**Pros**:
- Simplest change — modify `_accumulate_research()` or add a per-step summarization call
- No new service needed
- Content is summarized with topic awareness (the research agent already knows the focus)
- Natural fit: the research agent already sees truncated content (5k chars), just formalize that

**Cons**:
- Summarization happens inside the research agent's LLM call budget
- Each step's summary loses cross-topic context (NPC mentioned in lore step won't be in NPC summary)
- Still tightly coupled, not reusable

### Option D: Hybrid — Per-Step Summary + MCP Service

Summarize per-step in the pipeline (Option C) for immediate use, but also build the MCP service (Option A) for the broader ecosystem. The MCP service becomes the standard tool for any agent hitting context limits.

---

## Chunking Strategy Research

### Token-Based Chunking (Simple)

Split content at fixed token boundaries (e.g., 8k tokens per chunk with 500 token overlap).

- **Pros**: Predictable, simple, guaranteed to fit any model
- **Cons**: May split mid-sentence or mid-paragraph, losing semantic coherence
- **Best for**: Unstructured text, chat logs

### Semantic Boundary Chunking (Better)

Split at natural boundaries: paragraph breaks, section headers, horizontal rules.

- **Pros**: Preserves semantic units, respects document structure
- **Cons**: Chunks may be uneven in size, some may still exceed limits
- **Best for**: Wiki pages, articles, documentation (our primary content)

### Structural Chunking (Best for Web Content)

Parse HTML/markdown structure: split by `<h2>`, `<h3>`, `<section>` boundaries. Each chunk is a self-contained section.

- **Pros**: Highest quality splits, preserves information hierarchy
- **Cons**: Requires content to be well-structured (most wiki pages are)
- **Best for**: Our use case — crawled wiki/reference pages with clear structure

### Recommended Approach for Mythline

**Semantic boundary chunking** as default, with **structural chunking** for markdown content (which is what crawl4ai outputs). Token-based as fallback for unstructured content.

---

## LLM Choice for Summarization

The summarization LLM doesn't need to be the same as the research or extraction LLM. Summarization is a simpler task — a cheaper, faster model works well.

| Model | Context | Speed | Cost | Notes |
|-------|---------|-------|------|-------|
| gpt-4o-mini | 128k | Fast | Cheap | Good for per-chunk summarization |
| gemini-2.0-flash | 1M | Fast | Very cheap | Could handle most content in one call |
| claude-3.5-haiku | 200k | Fast | Cheap | Good balance of quality and cost |

**Consideration**: Using a 1M-context model (Gemini Flash) as the summarizer could skip chunking entirely for most content. But that creates a single-provider dependency and doesn't solve the architectural problem for truly large corpora.

---

## Recommendation

**Option C (per-step summarization) as the immediate fix**, with **Option A (MCP service) as the proper long-term solution**.

### Immediate Fix (Per-Step Summarization)

1. After each research step crawls content, summarize the raw content blocks using the research agent's existing LLM connection
2. Store the **summary** in `research_raw_content` instead of the full page text
3. Keep the full content available for the agent's own reasoning (it already sees 5k chars via truncation)
4. Step 6 (extract_all) receives 5 topic-focused summaries (~5k tokens each) instead of 10+ raw pages

This is a ~30-line change in `_accumulate_research()` or `_make_research_step()`.

### Long-Term Solution (Summarization MCP Server)

Build `mcp_summarizer/` following the existing MCP blueprint:
- Map-reduce summarization with configurable chunking strategy
- Domain-aware mode (pass schema hints for extraction-targeted summaries)
- Multi-provider LLM support via OpenRouter
- Open-source as a standalone MCP server

This becomes the standard content compression tool for all Mythline agents — any agent that crawls content and needs to fit it into a context window.

---

## Open Questions

1. **Should summaries be cached?** If the same page is crawled by multiple steps (e.g., a wiki page has both NPC and faction info), should we summarize once and reuse?
2. **What compression ratio to target?** A 50k-token page summarized to 5k tokens is 10:1 compression. Is that enough to preserve extraction-relevant details?
3. **Should the extraction step change too?** Instead of one monolithic extraction call, could we extract per-topic (NPC extraction from NPC summary, faction extraction from faction summary)?
4. **Quality validation**: How do we verify the summary didn't drop critical information? Compare extraction results between full-content (on a model with enough context) vs. summarized content?

---

## References

- [LangChain Map-Reduce Summarization](https://python.langchain.com/docs/tutorials/summarization/)
- [RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval](https://arxiv.org/abs/2401.18059)
- [Braffolk/mcp-summarization-functions](https://github.com/Braffolk/mcp-summarization-functions)
- [Dicklesworthstone/ultimate_mcp_server](https://github.com/Dicklesworthstone/ultimate_mcp_server)
- [0xshellming/mcp-summarizer](https://github.com/0xshellming/mcp-summarizer)
- [puran-water/knowledge-base-mcp](https://github.com/puran-water/knowledge-base-mcp)
