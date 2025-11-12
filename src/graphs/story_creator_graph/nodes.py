from __future__ import annotations
import os
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from termcolor import colored

from pydantic_graph import BaseNode, End, GraphRunContext

from src.agents.story_creator_agent.models.state_models import (
    StorySession,
    Todo,
    StorySegment
)
from src.agents.story_creator_agent.models.story_models import (
    Story,
    Quest,
    QuestSection,
    Narration,
    DialogueLines
)
from src.agents.story_planner_agent.agent import StoryPlannerAgent
from src.agents.narrator_agent.agent import NarratorAgent
from src.agents.dialog_creator_agent.agent import DialogCreatorAgent
from src.agents.reviewer_agent.agent import ReviewerAgent
from src.libs.filesystem.file_operations import read_file, write_file, file_exists
from src.libs.filesystem.directory_operations import create_directory


def save_progress(subject: str, status: str, message: str, current: int = 0, total: int = 0, details: dict = None):
    progress_dir = Path(".mythline/story_jobs")
    progress_dir.mkdir(parents=True, exist_ok=True)

    progress_file = progress_dir / f"{subject}.json"
    progress_file.write_text(json.dumps({
        "status": status,
        "message": message,
        "current": current,
        "total": total,
        "details": details or {},
        "timestamp": time.time()
    }))


@dataclass
class GetStoryResearch(BaseNode[StorySession]):
    research_content: Optional[str] = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateTODO | End[str]:
        subject = ctx.state.subject
        research_file = f"output/{subject}/research.md"

        print(colored(f"\n[*] Reading research notes for {subject}...", "cyan"))

        if not file_exists(research_file):
            error_msg = f"Research file not found for subject: {subject}"
            print(colored(f"[!] {error_msg}", "red"))
            return End(error_msg)

        research_content = read_file(research_file)
        print(colored(f"[+] Research loaded", "green"))

        return CreateTODO(research_content=research_content)


@dataclass
class CreateTODO(BaseNode[StorySession]):
    research_content: str

    def __post_init__(self):
        self.planner_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> GetNextTODO | End:
        if self.planner_agent is None:
            self.planner_agent = StoryPlannerAgent(session_id=ctx.state.session_id)

        print(colored("\n[*] Generating story plan...", "cyan"))
        save_progress(ctx.state.subject, "in_progress", "Generating story plan", 0, 0)

        todo_list = await self.planner_agent.run(self.research_content, ctx.state.player)
        ctx.state.todo_list = todo_list

        print(colored(f"[+] Plan created with {len(ctx.state.todo_list)} todos", "green"))
        save_progress(ctx.state.subject, "in_progress", f"Plan created with {len(ctx.state.todo_list)} todos", 0, len(ctx.state.todo_list))

        # for todo in todo_list:
        #     print(colored(f"[+] {todo.item.type}","grey"))
        #     print(colored(f"    {todo.item.quest_name}","grey"))
        #     print(colored(f"    {todo.item.description}","grey"))
        #     print(colored(f"    {todo.item.prompt[:100]}...","grey"))

        return GetNextTODO()
        # return End(None)


@dataclass
class GetNextTODO(BaseNode[StorySession]):

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateStorySegment | End[None]:
        if ctx.state.current_todo_index < len(ctx.state.todo_list):
            current_todo = ctx.state.todo_list[ctx.state.current_todo_index]
            current_todo.status = "in_progress"

            description_preview = current_todo.item.description[:50] + "..." if len(current_todo.item.description) > 50 else current_todo.item.description
            quest_info = f" [{current_todo.item.quest_name}]" if current_todo.item.quest_name else ""
            sub_type_info = f"/{current_todo.item.sub_type}" if current_todo.item.sub_type else ""
            todo_index = f"{ctx.state.current_todo_index + 1}/{len(ctx.state.todo_list)}"
            message = f"\n[*] Processing todo {todo_index}: {current_todo.item.type}{sub_type_info}{quest_info} - {description_preview}"
            print(colored(message, "cyan"))

            save_progress(
                ctx.state.subject,
                "in_progress",
                f"Processing {current_todo.item.type}{sub_type_info}{quest_info}",
                ctx.state.current_todo_index + 1,
                len(ctx.state.todo_list),
                {"segment_type": current_todo.item.type, "quest_name": current_todo.item.quest_name}
            )

            return CreateStorySegment()
        else:
            print(colored("\n[+] Story generation complete!", "green"))
            save_progress(ctx.state.subject, "complete", "Story generation complete", len(ctx.state.todo_list), len(ctx.state.todo_list))
            return End(None)


@dataclass
class CreateStorySegment(BaseNode[StorySession]):

    def __post_init__(self):
        self.narrator_agent = None
        self.dialog_creator_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> ReviewOutput:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]
        segment = current_todo.item

        prompt = self._build_prompt(segment, ctx.state, current_todo.review_comments)

        if segment.sub_type in ["quest_dialogue", "quest_conclusion"]:
            if self.dialog_creator_agent is None:
                self.dialog_creator_agent = DialogCreatorAgent(session_id=ctx.state.session_id)

            print(colored(f"[*] Generating dialogue using DialogCreatorAgent...", "cyan"))
            self.dialog_creator_agent.messages = []
            result = await self.dialog_creator_agent.run(prompt)
            segment.output = result.output
        else:
            if self.narrator_agent is None:
                self.narrator_agent = NarratorAgent(session_id=ctx.state.session_id)

            print(colored(f"[*] Generating narration using NarratorAgent...", "cyan"))
            self.narrator_agent.messages = []
            result = await self.narrator_agent.run(prompt)
            segment.output = result.output

        print(colored(f"[+] Content generated successfully", "green"))
        return ReviewOutput()

    def _build_prompt(self, segment: StorySegment, state: StorySession, review_comments: Optional[str]) -> str:
        player = state.player
        prompt = segment.prompt.replace("{player}", player)

        if review_comments:
            print(colored(f"[*] Addressing review comments", "grey"))
            prompt += f"\n\nPREVIOUS REVIEW FEEDBACK:\n{review_comments}\n\nIMPORTANT: Preserve all elements listed as correct. Only change what's listed in REQUIRED CHANGES."

        return prompt


@dataclass
class ReviewOutput(BaseNode[StorySession]):

    def __post_init__(self):
        self.reviewer_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateStorySegment | WriteToFile:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]
        segment = current_todo.item

        if self.reviewer_agent is None:
            self.reviewer_agent = ReviewerAgent(session_id=ctx.state.session_id)

        print(colored(f"[*] Reviewing content quality...", "cyan"))
        self.reviewer_agent.messages = []

        prompt = self._build_review_prompt(segment, ctx.state.player)

        review = await self.reviewer_agent.run(prompt)

        if review.need_improvement and review.score < 0.8:
            current_todo.retry_count += 1

            if current_todo.retry_count >= 10:
                print(colored(f"[!] Warning: Max retries (10) reached with score {review.score}. Accepting content anyway.", "yellow"))
                current_todo.status = "done"
                return WriteToFile()

            print(colored(f"[!] Review suggests improvement (score: {review.score}, attempt {current_todo.retry_count}/10)", "yellow"))
            print(colored(f"[*] Feedback: {review.review_comments}", "yellow"))

            current_todo.review_comments = review.review_comments

            print(colored(f"[*] Retrying...", "cyan"))
            return CreateStorySegment()
        else:
            print(colored(f"[+] Content validated successfully (score: {review.score})", "green"))
            current_todo.status = "done"
            return WriteToFile()

    def _build_review_prompt(self, segment: StorySegment, player: str) -> str:
        output = segment.output

        if isinstance(output, Narration):
            segment_type = segment.type
            segment_subtype = segment.sub_type

            if segment_type == "introduction":
                return f"""Review story introduction narration for suspense and atmosphere.

Player character name: {player}
Introduction text: "{output.text}"

Check:
1. Must use third-person perspective (not "you/your")
2. Should use player name "{player}" when referring to player
3. CRITICAL: Must NOT reveal quest details, objectives, or specific NPCs
4. CRITICAL: Must focus on atmosphere, mood, and sensory details
5. Should build curiosity and anticipation without exposition
6. Should show the present moment, not future actions
7. "She/her/he/him" pronouns are acceptable for flow and immersion

Score lower for: quest spoilers, objective reveals, telling instead of showing, or stating future actions."""

            elif segment_subtype == "quest_introduction":
                return f"""Review quest introduction narration for scene-setting without spoilers.

Player character name: {player}
Quest prompt context: {segment.prompt}
Quest introduction text: "{output.text}"

Check:
1. Must use third-person perspective (not "you/your")
2. Should use player name "{player}" when referring to player
3. CRITICAL: Must NOT state quest objectives (those come from dialogue)
4. CRITICAL: Should describe scene, NPCs, and atmosphere only
5. If prompt specifies NPC location (e.g., "inside main building", "near Aldrassil"), verify narration uses this exact location
6. Should build anticipation for the dialogue that follows
7. Should show what the character observes, not what they will do
8. Should flow smoothly from previous quest context if applicable
9. "She/her/he/him" pronouns are acceptable for flow and immersion

Score lower for: objective reveals, future action statements, abrupt transitions, or incorrect NPC locations (e.g., "near well" when prompt says "main building")."""

            elif segment_subtype == "quest_execution":
                return f"""Review quest execution narration for class-appropriate combat and third-person perspective.

Player character name: {player}
Quest: {segment.quest_name}
Narration text: "{output.text}"

Check:
1. Must use third-person perspective (not "you/your")
2. Should use player name "{player}" when referring to player
3. CRITICAL: Use search_guide_knowledge to look up {player}'s class
4. CRITICAL: Verify combat actions and abilities match the player's class:
   - Fire Mage: Should use ranged fire spells (Fireball, Fire Blast, Flamestrike), NOT melee combat
   - Warrior: Should use melee weapons (sword, shield, charges), NOT spells
   - Hunter: Should use ranged weapons (bow, gun) with pet companion, NOT pure melee
   - Priest: Should use healing/shadow magic, support role
   - Balance Druid: Should use nature magic, shapeshifting, ranged spells
   - Warlock: Should use demonic magic, curses, demonic minions
   - Shaman: Should use elemental magic, totems, lightning/earth spells
5. "She/her/he/him" pronouns are acceptable for flow and immersion
6. Should maintain immersive fantasy narrative tone

Score lower for: class-inappropriate combat (e.g., mage using melee), wrong abilities for class, or second-person perspective."""

            else:
                return f"""Review narration for proper third-person perspective.

Player character name: {player}
Narration text: "{output.text}"

Check:
1. Must use third-person perspective (not "you/your")
2. Should use player name "{player}" when referring to player
3. "She/her/he/him" pronouns are acceptable for flow and immersion
4. Should maintain immersive fantasy narrative tone
5. Identify any second-person usage that needs correction"""

        elif isinstance(output, DialogueLines):
            segment_subtype = segment.sub_type
            actors = [line.actor for line in output.lines]
            npc_actors = [actor for actor in actors if actor != player]
            unique_npc_actors = list(set(npc_actors))

            if len(unique_npc_actors) > 1:
                return f"""Review NPC location compatibility for multi-NPC dialogue.

Player character name: {player}
NPCs in dialogue: {', '.join(unique_npc_actors)}
Quest prompt context: {segment.prompt}
Dialogue lines: {[line.line for line in output.lines]}

Validation Steps:
1. Use web_search to verify each NPC's canonical spawn location (zone and coordinates) from warcraft.wiki.gg
2. Check if all NPCs spawn in the same location (same building/area, nearby coordinates)
3. Apply decision criteria below

PASS CRITERIA (dialogue is acceptable):
- All NPCs spawn in the same location (e.g., all in Fairbreeze Village main building)
- OR dialogue explicitly explains why an NPC traveled from their canonical location to meet the other(s), AND there is lore support for this meeting

FAIL CRITERIA (dialogue must be split into separate scenes):
- NPCs spawn in DIFFERENT locations (different zones OR far apart in same zone)
- AND this appears to be a QUEST CHAIN where NPC A directs the player to find NPC B at a different location
- Quest chains require separate dialogue scenes - player bridges the locations, not the NPCs meeting each other

WoW Quest Chain Mechanics:
In World of Warcraft, quest chains have NPCs at different locations who don't physically meet. The player carries the quest between them. Example: If Ardeyn at Fairbreeze Village gives quest to find Larianna at Goldenbough Pass, these should be TWO separate dialogue scenes (Ardeyn speaks alone, player travels, then Larianna speaks alone). Do NOT stage them in the same conversation.

If quest chain detected with NPCs at different locations, required fix: "Split this into separate dialogue scenes: Scene 1 with [NPC A] at [location A], Scene 2 with [NPC B] at [location B]"

Note: {player} is the player character, not an NPC - do not check co-location for the player."""

            elif segment_subtype == "quest_dialogue":
                npc = unique_npc_actors[0] if unique_npc_actors else actors[0]
                return f"""Review quest acceptance dialogue for WoW format and location accuracy.

Player character name: {player}
Quest NPC: {npc}
Quest prompt context: {segment.prompt}
Dialogue lines: {[line.line for line in output.lines]}

Check:
1. CRITICAL: Each NPC line must start with speaker tag "NPC Full Name:" (e.g., "Magistrix Landra Dawnstrider:")
2. CRITICAL: First NPC line must include location from prompt (e.g., "NPC Name at Location:")
3. NPC must explicitly state quest objective (what to collect/do and where)
4. Player response confirms acceptance and may restate objective
5. Dialogue fits WoW quest acceptance style (2-4 lines total)
6. If prompt specifies NPC location, verify exact location is included in first line
7. Use web_search on warcraft.wiki.gg if needed to verify location accuracy"""

            elif segment_subtype == "quest_conclusion":
                npc = unique_npc_actors[0] if unique_npc_actors else actors[0]
                return f"""Review quest completion for format and content.

Player character name: {player}
Quest NPC: {npc}
Quest prompt context: {segment.prompt}
Completion content: {[line.line for line in output.lines]}

Check:
1. CRITICAL: Determine if prompt requests dialogue or narration format
2. If DIALOGUE format: Each NPC line starts with "NPC Name:", location in first line
3. If NARRATION format: Uses {{player}} token, third-person description of scene, 60-100 words
4. Completion acknowledges quest success organically
5. May include reward mention, NPC reaction, or narrative hook to next quest
6. Tone appropriate for quest conclusion (gratitude, concern, urgency for next step)
7. Content matches format requested in prompt"""

            else:
                npc = unique_npc_actors[0] if unique_npc_actors else actors[0]
                return f"""Review dialogue for WoW quest pattern and location accuracy.

Player character name: {player}
Quest NPC: {npc}
Quest prompt context: {segment.prompt}
Dialogue: {[line.line for line in output.lines]}

Check:
1. Does dialogue fit WoW quest style?
2. Is NPC appropriate for this quest type?
3. Are dialogue lines clear and engaging?
4. If the prompt specifies NPC location (e.g., "inside main building", "near Aldrassil"), verify this location is accurate
5. Use web_search on warcraft.wiki.gg if needed to verify NPC spawn location matches the prompt"""
        else:
            return f"""Review the below content and score the content between 0 to 1, then provide a review comment if needed:
{output}"""


@dataclass
class WriteToFile(BaseNode[StorySession]):

    async def run(self, ctx: GraphRunContext[StorySession]) -> GetNextTODO:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]
        segment = current_todo.item
        subject = ctx.state.subject

        segment_type = f"{segment.type}" if not segment.quest_name else f"{segment.sub_type} for '{segment.quest_name}'"
        print(colored(f"[*] Writing {segment_type} to file...", "cyan"))

        dir_path = f"output/{subject}"
        file_path = f"{dir_path}/story.json"

        create_directory(dir_path)

        if file_exists(file_path):
            existing_content = read_file(file_path)
            story = Story.model_validate_json(existing_content)
        else:
            print(colored(f"[+] Creating {file_path}", "grey"))
            story = Story(title=f"The {subject.title()} Chronicles", subject=subject)

        story = self._add_segment_to_story(story, segment)

        story_json = story.model_dump_json(indent=2)
        write_file(file_path, story_json)
        print(colored(f"[+] Story saved to {file_path}", "green"))

        ctx.state.current_todo_index += 1

        return GetNextTODO()

    def _add_segment_to_story(self, story: Story, segment: StorySegment) -> Story:
        if segment.type == "introduction":
            story.introduction = segment.output # type: ignore

        elif segment.type == "conclusion":
            story.conclusion = segment.output # type: ignore

        elif segment.sub_type == "quest_introduction":
            quest = Quest(title=segment.quest_name, sections=QuestSection())  # type: ignore
            quest.sections.introduction = segment.output # type: ignore
            story.quests.append(quest)

        elif segment.sub_type == "quest_dialogue":
            for quest in story.quests:
                if quest.title == segment.quest_name:
                    quest.sections.dialogue = segment.output # type: ignore
                    break
            else:
                raise ValueError(f"Quest not found: {segment.quest_name}")

        elif segment.sub_type == "quest_execution":
            for quest in story.quests:
                if quest.title == segment.quest_name:
                    quest.sections.execution = segment.output # type: ignore
                    break
            else:
                raise ValueError(f"Quest not found: {segment.quest_name}")

        elif segment.sub_type == "quest_conclusion":
            for quest in story.quests:
                if quest.title == segment.quest_name:
                    quest.sections.completion = segment.output # type: ignore
                    break
            else:
                raise ValueError(f"Quest not found: {segment.quest_name}")

        return story
