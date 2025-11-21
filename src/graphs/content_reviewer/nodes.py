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
from src.libs.knowledge_base.knowledge_vectordb import search_knowledge, index_knowledge
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

            print(f"[+] Creating new session {ctx.state.session_id}")

            max_retries = getattr(ctx.state, 'max_retries', 3)
            quality_threshold = getattr(ctx.state, 'quality_threshold', 0.8)

            session = create_session(
                session_id=ctx.state.session_id,
                content=ctx.state.content,
                max_retries=max_retries,
                quality_threshold=quality_threshold
            )
        else:
            print(f"[+] Loaded existing session {ctx.state.session_id} (retry {session.retry_count})")

        session.increment_retry()

        ctx.state.session = session
        ctx.state.workflow_stage = "session_loaded"

        return GenerateSearchQueries()

@dataclass
class GenerateSearchQueries(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> GetSavedContext:
        print(f"[*] GenerateSearchQueries")
        ctx.state.workflow_stage = "generating_search_queries"

        try:
            print(f"[*] Invoking Search Query Generator Agent...")
            agent = SearchQueryGeneratorAgent()
            queries = await agent.run(ctx.state.content)

            ctx.state.search_queries = queries

            print(f"[+] KB Query: {queries.kb_query}")
            print(f"[+] Web Query: {queries.web_query}")

        except Exception as e:
            ctx.state.error_message = f"Search query generation error: {e}"
            print(f"[!] Error generating search queries: {e}")

        return GetSavedContext()

@dataclass
class GetSavedContext(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> CollectWebData:
        print(f"[*] GetSavedContext")
        ctx.state.workflow_stage = "getting_context"

        try:

            if ctx.state.search_queries:
                kb_query = ctx.state.search_queries.kb_query
                print(f"[*] Using KB query: {kb_query}")
            else:
                kb_query = "review guidelines"
                print(f"[*] Using fallback KB query: {kb_query}")

            results = search_knowledge(kb_query, top_k=5, collection="reviewer_knowledge")

            if results:
                context_parts = []
                for result in results:
                    context_parts.append(f"[{result.get('source_file', 'unknown')}]\n{result.get('text', '')}")
                ctx.state.saved_context = "\n\n".join(context_parts)
                print(f"[+] Found {len(results)} context items")
            else:
                ctx.state.saved_context = "No saved context found"
                print(f"[*] No saved context found")

        except Exception as e:
            ctx.state.saved_context = "No saved context found"
            ctx.state.error_message = f"Context search error: {e}"
            print(f"[!] Error getting context: {e}")

        return CollectWebData()

@dataclass
class CollectWebData(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> PerformAIReview:
        print(f"[*] CollectWebData")
        ctx.state.workflow_stage = "collecting_web_data"

        try:

            if ctx.state.search_queries:
                query = ctx.state.search_queries.web_query
                print(f"[*] Using web query: {query}")
            else:
                query = "content review best practices 2025"
                print(f"[*] Using fallback web query: {query}")

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
            else:
                print(f"[*] No web results found")

        except Exception as e:
            ctx.state.error_message = f"Web search error: {e}"
            print(f"[!] Error collecting web data: {e}")

        return PerformAIReview()

@dataclass
class PerformAIReview(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> UpdateSession:
        print(f"[*] PerformAIReview")
        ctx.state.workflow_stage = "performing_review"

        try:

            prompt_parts = [
                f"# Content to Review\n\n{ctx.state.content}",
            ]

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

            print(f"[*] Invoking Quality Assessor Agent...")
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
            if assessment.issues:
                print(f"[*] Top issues:")
                for issue in assessment.issues[:3]:
                    print(f"    - [{issue.severity}] {issue.category}: {issue.description}")

        except Exception as e:
            ctx.state.quality_score = 0.0
            ctx.state.current_review = {
                "quality_score": 0.0,
                "summary": f"Review failed: {e}",
                "error": str(e)
            }
            ctx.state.error_message = f"AI review error: {e}"
            print(f"[!] Error performing AI review: {e}")

        return UpdateSession()

@dataclass
class UpdateSession(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> CheckCompletion:
        print(f"[*] UpdateSession")
        ctx.state.workflow_stage = "updating_session"

        if ctx.state.session and ctx.state.current_review:
            ctx.state.session.add_attempt(
                score=ctx.state.quality_score,
                review_details=ctx.state.current_review
            )
            print(f"[+] Recorded attempt {ctx.state.session.retry_count}")

        return CheckCompletion()

@dataclass
class CheckCompletion(BaseNode[ReviewState]):

    async def run(
        self, ctx: GraphRunContext[ReviewState]
    ) -> WipeSession | SaveSession:
        print(f"[*] CheckCompletion")
        ctx.state.workflow_stage = "checking_completion"

        session = ctx.state.session
        score = ctx.state.quality_score
        threshold = session.quality_threshold
        retry_count = session.retry_count
        max_retries = session.max_retries

        print(f"[*] Score: {score:.2f}, Threshold: {threshold:.2f}, Retry: {retry_count}/{max_retries}")

        if score >= threshold:
            print(f"[+] Quality threshold met! ({score:.2f} >= {threshold:.2f})")
            session.status = "completed"
            return WipeSession()

        if retry_count >= max_retries:
            print(f"[!] Max retries reached. Completing with current score.")
            session.status = "completed"
            return WipeSession()

        if retry_count < max_retries:
            print(f"[*] Can retry. Saving session for next attempt...")
            session.status = "in_progress"
            return SaveSession()

@dataclass
class WipeSession(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> PopulateResult:
        print(f"[*] WipeSession")
        ctx.state.workflow_stage = "wiping_session"

        wipe_session(ctx.state.session_id)

        return PopulateResult()

@dataclass
class SaveSession(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> PopulateResult:
        print(f"[*] SaveSession")
        ctx.state.workflow_stage = "saving_session"

        if ctx.state.session:
            save_session(ctx.state.session)
            print(f"[+] Session saved for retry")

        return PopulateResult()

@dataclass
class PopulateResult(BaseNode[ReviewState]):

    async def run(self, ctx: GraphRunContext[ReviewState]) -> End[ReviewResult]:
        print(f"[*] PopulateResult")
        ctx.state.workflow_stage = "populating_result"

        session = ctx.state.session

        passed = ctx.state.quality_score >= session.quality_threshold
        max_retries_reached = session.retry_count >= session.max_retries
        needs_human = session.status == "needs_human"
        human_provided = ctx.state.human_invoked
        session_completed = session.status in ["completed", "needs_human"]

        result = ReviewResult(
            session_id=session.session_id,
            retry_count=session.retry_count,
            max_retries=session.max_retries,
            quality_score=ctx.state.quality_score,
            quality_threshold=session.quality_threshold,
            passed=passed,
            max_retries_reached=max_retries_reached,
            needs_human_review=needs_human,
            human_feedback_provided=human_provided,
            session_completed=session_completed,
            review_details=ctx.state.current_review or {},
            saved_context_summary=(
                ctx.state.saved_context[:200] if ctx.state.saved_context else None
            ),
            web_references=[
                {"title": item["title"], "url": item["url"]}
                for item in ctx.state.web_data
            ],
            timestamp=datetime.now().isoformat(),
            attempt_history=session.history
        )

        return End(result)
