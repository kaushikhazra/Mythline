from __future__ import annotations
import asyncio
from dataclasses import dataclass
from pathlib import Path

from pydantic_graph import BaseNode, End, GraphRunContext

from src.graphs.story_research_graph.models.state_models import ResearchSession
from src.graphs.story_research_graph.models.research_models import (
    Area,
    ResearchBrief,
    QuestResearch,
    NPC,
    Location,
    ExecutionLocation,
    Objectives
)
from src.libs.web.crawl import crawl_content
from src.libs.web.duck_duck_go import search as web_search
from src.agents.research_input_parser_agent import ResearchInputParserAgent
from src.agents.quest_extractor_agent import QuestExtractorAgent
from src.agents.npc_extractor_agent import NPCExtractorAgent
from src.agents.location_extractor_agent import LocationExtractorAgent
from src.agents.story_setting_extractor_agent import StorySettingExtractorAgent
from src.libs.logger import logger


@dataclass
class ParseInput(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> InitializeLoop | End[str]:
        logger.info(f"ParseInput for subject: {ctx.state.subject}")

        input_path = Path(f"output/{ctx.state.subject}/quest-chain.md")

        if not input_path.exists():
            return End(f"Input file not found: {input_path}")

        content = input_path.read_text(encoding="utf-8")

        agent = ResearchInputParserAgent()
        result = await agent.run(content)

        ctx.state.chain_title = result.chain_title
        ctx.state.quest_urls = result.quest_urls

        logger.success(f"Chain: {result.chain_title}")
        logger.success(f"Found {len(result.quest_urls)} quests")

        return InitializeLoop()


@dataclass
class InitializeLoop(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> CheckHasMoreQuests:
        logger.info("InitializeLoop")
        ctx.state.quest_index = 0
        return CheckHasMoreQuests()


@dataclass
class CheckHasMoreQuests(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> CrawlQuestPage | ExtractSetting:
        if ctx.state.quest_index < len(ctx.state.quest_urls):
            logger.info(f"Processing quest {ctx.state.quest_index + 1}/{len(ctx.state.quest_urls)}")
            return CrawlQuestPage()
        else:
            logger.info("All quests processed, extracting setting")
            return ExtractSetting()


@dataclass
class CrawlQuestPage(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> ExtractQuestData:
        url = ctx.state.quest_urls[ctx.state.quest_index]
        logger.info(f"Crawling quest: {url}")

        try:
            content = await crawl_content(url)
            ctx.state.current_quest_content = content
            ctx.state.quest_contents[url] = content
            logger.success(f"Crawled {len(content)} characters")
        except Exception as e:
            logger.warning(f"Error crawling quest: {e}")
            ctx.state.current_quest_content = ""

        return ExtractQuestData()


def search_npc_url(npc_name: str) -> str | None:
    query = f'site:warcraft.wiki.gg "{npc_name}"'
    logger.info(f"Searching: {query}")
    try:
        results = web_search(query)
        if results:
            url = results[0]['href']
            logger.success(f"Found: {url}")
            return url
    except Exception as e:
        logger.warning(f"Search error: {e}")
    return None


def search_location_url(location_name: str) -> str | None:
    query = f'site:warcraft.wiki.gg {location_name}'
    logger.info(f"Searching: {query}")
    try:
        results = web_search(query)
        if results:
            url = results[0]['href']
            logger.success(f"Found: {url}")
            return url
    except Exception as e:
        logger.warning(f"Search error: {e}")
    return None


@dataclass
class ExtractQuestData(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> CrawlNPCPages:
        logger.info("ExtractQuestData")

        agent = QuestExtractorAgent()
        extraction = await agent.run(ctx.state.current_quest_content)

        logger.success(f"Quest: {extraction.title}")
        logger.success(f"Quest Giver: {extraction.quest_giver_name}")
        logger.success(f"Turn-in NPC: {extraction.turn_in_npc_name}")
        logger.success(f"Zone: {extraction.zone}")
        logger.success(f"Execution Area: {extraction.execution_area}")

        npc_urls = []
        if extraction.quest_giver_name:
            url = search_npc_url(extraction.quest_giver_name)
            if url:
                npc_urls.append(url)
        if extraction.turn_in_npc_name and extraction.turn_in_npc_name != extraction.quest_giver_name:
            url = search_npc_url(extraction.turn_in_npc_name)
            if url:
                npc_urls.append(url)

        location_urls = []
        if extraction.zone:
            url = search_location_url(extraction.zone)
            if url:
                location_urls.append(url)
        if extraction.execution_area and extraction.execution_area != extraction.zone:
            url = search_location_url(extraction.execution_area)
            if url:
                location_urls.append(url)

        ctx.state.current_npc_urls = npc_urls
        ctx.state.current_location_urls = location_urls

        ctx.state._current_extraction = extraction

        logger.success(f"NPCs to crawl: {len(npc_urls)}")
        logger.success(f"Locations to crawl: {len(location_urls)}")

        return CrawlNPCPages()


@dataclass
class CrawlNPCPages(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> EnrichNPCData:
        logger.info("CrawlNPCPages")

        for url in ctx.state.current_npc_urls:
            if url not in ctx.state.npc_contents:
                try:
                    logger.info(f"Crawling NPC: {url}")
                    content = await crawl_content(url)
                    ctx.state.npc_contents[url] = content
                    logger.info("Breathing for 5 seconds")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.warning(f"Error crawling NPC {url}: {e}")
                    ctx.state.npc_contents[url] = ""

        return EnrichNPCData()


@dataclass
class EnrichNPCData(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> CrawlLocationPages:
        logger.info("EnrichNPCData")

        extraction = ctx.state._current_extraction
        agent = NPCExtractorAgent()

        quest_context = {
            "quest_title": extraction.title,
            "story_beat": extraction.story_beat,
            "zone": extraction.zone,
            "execution_area": extraction.execution_area
        }

        quest_giver_npc = None
        turn_in_npc = None

        for url in ctx.state.current_npc_urls:
            content = ctx.state.npc_contents.get(url, "")
            if not content:
                continue

            try:
                npc_data = await agent.run(content, quest_context=quest_context)

                if npc_data.name.lower() in extraction.quest_giver_name.lower() or extraction.quest_giver_name.lower() in npc_data.name.lower():
                    quest_giver_npc = npc_data
                    logger.success(f"Extracted quest giver: {npc_data.name}")

                if npc_data.name.lower() in extraction.turn_in_npc_name.lower() or extraction.turn_in_npc_name.lower() in npc_data.name.lower():
                    turn_in_npc = npc_data
                    logger.success(f"Extracted turn-in NPC: {npc_data.name}")
            except Exception as e:
                logger.warning(f"Error extracting NPC: {e}")

        ctx.state._quest_giver_npc = quest_giver_npc
        ctx.state._turn_in_npc = turn_in_npc

        return CrawlLocationPages()


@dataclass
class CrawlLocationPages(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> EnrichLocationData:
        logger.info("CrawlLocationPages")

        for url in ctx.state.current_location_urls:
            if url not in ctx.state.location_contents:
                try:
                    logger.info(f"Crawling location: {url}")
                    content = await crawl_content(url)
                    ctx.state.location_contents[url] = content
                    logger.info("Breathing for 5 seconds")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.warning(f"Error crawling location {url}: {e}")
                    ctx.state.location_contents[url] = ""

        return EnrichLocationData()


@dataclass
class EnrichLocationData(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> StoreQuestResearch:
        logger.info("EnrichLocationData")

        extraction = ctx.state._current_extraction
        agent = LocationExtractorAgent()

        execution_location = None

        for url in ctx.state.current_location_urls:
            content = ctx.state.location_contents.get(url, "")
            if not content:
                continue

            try:
                loc_data = await agent.run(content)

                if extraction.execution_area.lower() in loc_data.area.lower() or loc_data.area.lower() in extraction.execution_area.lower():
                    execution_location = loc_data
                    logger.success(f"Extracted execution location: {loc_data.area}")
                    break
            except Exception as e:
                logger.warning(f"Error extracting location: {e}")

        ctx.state._execution_location = execution_location

        return StoreQuestResearch()


@dataclass
class StoreQuestResearch(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> IncrementIndex:
        logger.info("StoreQuestResearch")

        extraction = ctx.state._current_extraction
        quest_giver_npc = getattr(ctx.state, '_quest_giver_npc', None)
        turn_in_npc = getattr(ctx.state, '_turn_in_npc', None)
        execution_location = getattr(ctx.state, '_execution_location', None)

        quest_giver = NPC(
            name=extraction.quest_giver_name,
            title=quest_giver_npc.title if quest_giver_npc else "",
            personality=quest_giver_npc.personality if quest_giver_npc else "",
            lore=quest_giver_npc.lore if quest_giver_npc else "",
            location=Location(
                area=Area(
                    name=quest_giver_npc.location_area if quest_giver_npc else extraction.quest_giver_location_hint,
                    x=quest_giver_npc.location_x if quest_giver_npc else extraction.quest_giver_location_x,
                    y=quest_giver_npc.location_y if quest_giver_npc else extraction.quest_giver_location_y
                ),
                position=quest_giver_npc.location_position if quest_giver_npc else "",
                visual=quest_giver_npc.location_visual if quest_giver_npc else "",
                landmarks=quest_giver_npc.location_landmarks if quest_giver_npc else ""
            )
        )

        turn_in = NPC(
            name=extraction.turn_in_npc_name,
            title=turn_in_npc.title if turn_in_npc else "",
            personality=turn_in_npc.personality if turn_in_npc else "",
            lore=turn_in_npc.lore if turn_in_npc else "",
            location=Location(
                area=Area(
                    name=turn_in_npc.location_area if turn_in_npc else extraction.turn_in_npc_location_hint,
                    x=turn_in_npc.location_x if turn_in_npc else extraction.turn_in_npc_location_x,
                    y=turn_in_npc.location_y if turn_in_npc else extraction.turn_in_npc_location_y
                ),
                position=turn_in_npc.location_position if turn_in_npc else "",
                visual=turn_in_npc.location_visual if turn_in_npc else "",
                landmarks=turn_in_npc.location_landmarks if turn_in_npc else ""
            )
        )

        exec_loc = ExecutionLocation(
            area=Area(
                name=execution_location.area if execution_location else extraction.execution_area,
                x=execution_location.area_x if execution_location else None,
                y=execution_location.area_y if execution_location else None
            ),
            visual=execution_location.visual if execution_location else "",
            landmarks=execution_location.landmarks if execution_location else "",
            enemies=execution_location.enemies if execution_location else extraction.enemies
        )

        quest_research = QuestResearch(
            title=extraction.title,
            story_beat=extraction.story_beat,
            objectives=Objectives(
                summary=extraction.objectives_summary,
                details=extraction.objectives_details
            ),
            quest_giver=quest_giver,
            turn_in_npc=turn_in,
            execution_location=exec_loc,
            story_text=extraction.story_text,
            completion_text=extraction.completion_text
        )

        ctx.state.quest_data.append(quest_research)
        logger.success(f"Stored quest: {quest_research.title}")

        return IncrementIndex()


@dataclass
class IncrementIndex(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> CheckHasMoreQuests:
        ctx.state.quest_index += 1
        return CheckHasMoreQuests()


@dataclass
class ExtractSetting(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> SynthesizeBrief:
        logger.info("ExtractSetting")

        collected_data = f"Chain: {ctx.state.chain_title}\n\n"

        for quest in ctx.state.quest_data:
            collected_data += f"Quest: {quest.title}\n"
            collected_data += f"Zone: {quest.quest_giver.location.area}\n"
            collected_data += f"Execution Area: {quest.execution_location.area}\n"
            collected_data += f"Visual: {quest.execution_location.visual}\n\n"

        agent = StorySettingExtractorAgent()
        setting = await agent.run(collected_data)

        ctx.state.setting = setting
        logger.success(f"Setting extracted: {setting.zone}")

        return SynthesizeBrief()


@dataclass
class SynthesizeBrief(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> SaveJSON:
        logger.info("SynthesizeBrief")

        research_brief = ResearchBrief(
            chain_title=ctx.state.chain_title,
            setting=ctx.state.setting,
            quests=ctx.state.quest_data
        )

        ctx.state.research_brief = research_brief
        logger.success(f"Brief synthesized: {research_brief.chain_title}")

        return SaveJSON()


@dataclass
class SaveJSON(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> End[str]:
        logger.info("SaveJSON")

        output_path = Path(f"output/{ctx.state.subject}/research.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        json_content = ctx.state.research_brief.model_dump_json(indent=2)
        output_path.write_text(json_content, encoding="utf-8")

        logger.success(f"Saved to {output_path}")

        return End(f"Research complete: {output_path}")
