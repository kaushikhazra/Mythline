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
    Objectives,
    Setting
)
from src.libs.web.playwright_crawl import crawl_content
from src.libs.web.duck_duck_go import search as web_search
from src.libs.cache import get_npc, set_npc, get_location, set_location
from src.agents.research_input_parser_agent import ResearchInputParserAgent
from src.libs.parsers import parse_quest_chain, get_quest_ids_in_order
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

        quest_chain = parse_quest_chain(str(input_path))

        if not quest_chain['quests']:
            content = input_path.read_text(encoding="utf-8")
            agent = ResearchInputParserAgent()
            result = await agent.run(content)
            ctx.state.chain_title = result.chain_title
            ctx.state.quest_urls = result.quest_urls
        else:
            content = input_path.read_text(encoding="utf-8")
            agent = ResearchInputParserAgent()
            result = await agent.run(content)
            ctx.state.chain_title = result.chain_title

            quest_order = get_quest_ids_in_order(quest_chain)
            ctx.state.quest_urls = [quest_chain['quests'][qid] for qid in quest_order]

            ctx.state.quest_ids = {url: qid for qid, url in quest_chain['quests'].items()}

            if quest_chain.get('setting'):
                ctx.state.parsed_setting = quest_chain['setting']

        logger.success(f"Chain: {ctx.state.chain_title}")
        logger.success(f"Found {len(ctx.state.quest_urls)} quests")

        if ctx.state.quest_ids:
            logger.success(f"Quest IDs: {list(ctx.state.quest_ids.values())}")

        if ctx.state.parsed_setting.get('start'):
            logger.success(f"Starting location: {ctx.state.parsed_setting['start']}")

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


def search_location_url(location_name: str) -> tuple[str | None, str | None]:
    cached = get_location(location_name)
    if cached:
        logger.success(f"Location cache hit: {location_name}")
        return cached['url'], cached['content']

    query = f'site:warcraft.wiki.gg {location_name}'
    logger.info(f"Searching: {query}")
    try:
        results = web_search(query)
        if results:
            url = results[0]['href']
            logger.success(f"Found: {url}")
            return url, None
    except Exception as e:
        logger.warning(f"Search error: {e}")
    return None, None


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
        ctx.state._cached_quest_giver = None
        ctx.state._cached_turn_in_npc = None

        if extraction.quest_giver_name:
            cached_npc = get_npc(extraction.quest_giver_name)
            if cached_npc:
                logger.success(f"NPC cache hit: {extraction.quest_giver_name}")
                ctx.state._cached_quest_giver = cached_npc
            else:
                url = search_npc_url(extraction.quest_giver_name)
                if url:
                    npc_urls.append(url)

        if extraction.turn_in_npc_name and extraction.turn_in_npc_name != extraction.quest_giver_name:
            cached_npc = get_npc(extraction.turn_in_npc_name)
            if cached_npc:
                logger.success(f"NPC cache hit: {extraction.turn_in_npc_name}")
                ctx.state._cached_turn_in_npc = cached_npc
            else:
                url = search_npc_url(extraction.turn_in_npc_name)
                if url:
                    npc_urls.append(url)

        location_urls = []
        location_names_to_crawl = []

        if extraction.zone:
            url, cached_content = search_location_url(extraction.zone)
            if url:
                if cached_content:
                    ctx.state.location_contents[url] = cached_content
                else:
                    location_urls.append(url)
                    location_names_to_crawl.append(extraction.zone)

        if extraction.execution_area and extraction.execution_area != extraction.zone:
            url, cached_content = search_location_url(extraction.execution_area)
            if url:
                if cached_content:
                    ctx.state.location_contents[url] = cached_content
                else:
                    location_urls.append(url)
                    location_names_to_crawl.append(extraction.execution_area)

        ctx.state.current_npc_urls = npc_urls
        ctx.state.current_location_urls = location_urls
        ctx.state._location_names_to_crawl = location_names_to_crawl

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


def _extraction_to_npc(npc_data) -> NPC:
    return NPC(
        name=npc_data.name,
        title=npc_data.title,
        personality=npc_data.personality,
        lore=npc_data.lore,
        location=Location(
            area=Area(
                name=npc_data.location_area,
                x=npc_data.location_x,
                y=npc_data.location_y
            ),
            position=npc_data.location_position,
            visual=npc_data.location_visual,
            landmarks=npc_data.location_landmarks
        )
    )


@dataclass
class EnrichNPCData(BaseNode[ResearchSession]):

    async def run(self, ctx: GraphRunContext[ResearchSession]) -> CrawlLocationPages:
        logger.info("EnrichNPCData")

        extraction = ctx.state._current_extraction

        quest_giver_npc = getattr(ctx.state, '_cached_quest_giver', None)
        turn_in_npc = getattr(ctx.state, '_cached_turn_in_npc', None)

        if quest_giver_npc:
            logger.success(f"Using cached quest giver: {quest_giver_npc.name}")
        if turn_in_npc:
            logger.success(f"Using cached turn-in NPC: {turn_in_npc.name}")

        if ctx.state.current_npc_urls:
            agent = NPCExtractorAgent()
            quest_context = {
                "quest_title": extraction.title,
                "story_beat": extraction.story_beat,
                "zone": extraction.zone,
                "execution_area": extraction.execution_area
            }

            for url in ctx.state.current_npc_urls:
                content = ctx.state.npc_contents.get(url, "")
                if not content:
                    continue

                try:
                    npc_data = await agent.run(content, quest_context=quest_context)
                    npc_model = _extraction_to_npc(npc_data)

                    set_npc(npc_model)
                    logger.success(f"Cached NPC: {npc_model.name}")

                    if npc_data.name.lower() in extraction.quest_giver_name.lower() or extraction.quest_giver_name.lower() in npc_data.name.lower():
                        quest_giver_npc = npc_model
                        logger.success(f"Extracted quest giver: {npc_data.name}")

                    if npc_data.name.lower() in extraction.turn_in_npc_name.lower() or extraction.turn_in_npc_name.lower() in npc_data.name.lower():
                        turn_in_npc = npc_model
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

        location_names = getattr(ctx.state, '_location_names_to_crawl', [])

        for i, url in enumerate(ctx.state.current_location_urls):
            if url not in ctx.state.location_contents:
                try:
                    logger.info(f"Crawling location: {url}")
                    content = await crawl_content(url)
                    ctx.state.location_contents[url] = content

                    if i < len(location_names):
                        set_location(location_names[i], url, content)
                        logger.success(f"Cached location: {location_names[i]}")

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

        if quest_giver_npc:
            quest_giver = quest_giver_npc
        else:
            quest_giver = NPC(
                name=extraction.quest_giver_name,
                title="",
                personality="",
                lore="",
                location=Location(
                    area=Area(
                        name=extraction.quest_giver_location_hint,
                        x=extraction.quest_giver_location_x,
                        y=extraction.quest_giver_location_y
                    ),
                    position="",
                    visual="",
                    landmarks=""
                )
            )

        if turn_in_npc:
            turn_in = turn_in_npc
        else:
            turn_in = NPC(
                name=extraction.turn_in_npc_name,
                title="",
                personality="",
                lore="",
                location=Location(
                    area=Area(
                        name=extraction.turn_in_npc_location_hint,
                        x=extraction.turn_in_npc_location_x,
                        y=extraction.turn_in_npc_location_y
                    ),
                    position="",
                    visual="",
                    landmarks=""
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

        current_url = ctx.state.quest_urls[ctx.state.quest_index]
        quest_id = ctx.state.quest_ids.get(current_url, "")

        quest_research = QuestResearch(
            id=quest_id,
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
        logger.success(f"Stored quest [{quest_id}]: {quest_research.title}")

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

        parsed_setting = ctx.state.parsed_setting
        specified_zone = parsed_setting.get('zone')
        starting_location = parsed_setting.get('start')
        journey = parsed_setting.get('journey')

        collected_data = f"Chain: {ctx.state.chain_title}\n\n"

        if specified_zone:
            collected_data += f"Primary Zone: {specified_zone}\n\n"

        for quest in ctx.state.quest_data:
            collected_data += f"Quest: {quest.title}\n"
            collected_data += f"Zone: {quest.quest_giver.location.area}\n"
            collected_data += f"Execution Area: {quest.execution_location.area}\n"
            collected_data += f"Visual: {quest.execution_location.visual}\n\n"

        agent = StorySettingExtractorAgent()
        setting = await agent.run(collected_data)

        if specified_zone:
            setting = Setting(
                zone=specified_zone,
                starting_location=starting_location,
                journey=journey,
                description=setting.description,
                lore_context=setting.lore_context
            )
        else:
            setting = Setting(
                zone=setting.zone,
                starting_location=starting_location,
                journey=journey,
                description=setting.description,
                lore_context=setting.lore_context
            )

        ctx.state.setting = setting
        logger.success(f"Setting extracted: {setting.zone}")
        if starting_location:
            logger.success(f"Starting location: {starting_location}")

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
