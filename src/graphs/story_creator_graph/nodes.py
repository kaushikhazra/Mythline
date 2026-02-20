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
    TodoItem
)
from src.agents.story_creator_agent.models.story_models import (
    Story,
    StorySegment,
    Narration,
    DialogueLines
)
from src.agents.story_planner_agent.agent import StoryPlannerAgent
from src.agents.narrator_agent.agent import NarratorAgent
from src.agents.dialog_creator_agent.agent import DialogCreatorAgent
from src.agents.story_reviewer_agent import StoryReviewerAgent
from src.libs.filesystem.file_operations import read_file, write_file, file_exists
from src.libs.filesystem.directory_operations import create_directory
from src.libs.knowledge_base import index_story

MAX_REVIEW_RETRIES = 3
QUALITY_THRESHOLD = 0.75


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
    regenerate_plan: bool = False

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateTODO | GetNextTODO | End[str]:
        subject = ctx.state.subject
        research_file = f"output/{subject}/research.json"
        todo_cache_file = f"output/{subject}/todo.json"

        print(colored(f"\n[*] Reading research notes for {subject}...", "cyan"))

        if not file_exists(research_file):
            error_msg = f"Research file not found for subject: {subject}. Run the research graph first."
            print(colored(f"[!] {error_msg}", "red"))
            return End(error_msg)

        research_json = read_file(research_file)
        research_data = json.loads(research_json)

        ctx.state.research_data = research_data
        ctx.state.research_content = self._format_research_summary(research_data)
        print(colored(f"[+] Research loaded ({len(research_data.get('quests', []))} quests)", "green"))

        if not self.regenerate_plan and file_exists(todo_cache_file):
            print(colored(f"[*] Loading cached todo list from {todo_cache_file}...", "cyan"))
            try:
                cached_todos_json = read_file(todo_cache_file)
                cached_todos_data = json.loads(cached_todos_json)
                ctx.state.todo_list = [Todo.model_validate(todo_data) for todo_data in cached_todos_data]

                completed_count = sum(1 for todo in ctx.state.todo_list if todo.status == "done")
                print(colored(f"[+] Loaded {len(ctx.state.todo_list)} todos ({completed_count} completed)", "green"))

                ctx.state.current_todo_index = completed_count
                return GetNextTODO()
            except Exception as e:
                print(colored(f"[!] Failed to load cached todos: {e}", "yellow"))
                print(colored(f"[*] Regenerating plan...", "cyan"))

        return CreateTODO()

    def _format_research_summary(self, research_data: dict) -> str:
        setting = research_data.get('setting', {})
        quests = research_data.get('quests', [])
        quest_titles = [q.get('title', 'Unknown') for q in quests]
        return f"Chain: {research_data.get('chain_title', 'Unknown')} | Zone: {setting.get('zone', 'Unknown')} | Quests: {', '.join(quest_titles)}"

    def _get_settings_segment(self, research_data: dict, segment_type: str, previous_scene_ending: str = None) -> dict:
        setting = research_data.get('setting', {})
        roleplay = research_data.get('roleplay', {})
        roleplay_key = segment_type.title()
        roleplay_text = roleplay.get(roleplay_key)

        segment = {
            "segment_type": segment_type,
            "chain_title": research_data.get('chain_title', ''),
            "zone": setting.get('zone', ''),
            "starting_location": setting.get('starting_location', ''),
            "journey": setting.get('journey', ''),
            "description": setting.get('description', ''),
            "lore_context": setting.get('lore_context', '')
        }

        if roleplay_text:
            segment["roleplay"] = roleplay_text

        if previous_scene_ending:
            segment["previous_scene_ending"] = previous_scene_ending

        return segment

    def _get_quest_segment(self, research_data: dict, quest_index: int, previous_scene_ending: str = None) -> dict:
        quest = research_data.get('quests', [])[quest_index]
        quest_giver = quest.get('quest_giver', {})
        turn_in_npc = quest.get('turn_in_npc', {})
        exec_loc = quest.get('execution_location', {})
        roleplay = research_data.get('roleplay', {})
        quest_id = quest.get('id', '')

        def extract_location(loc: dict) -> dict:
            area = loc.get('area', {})
            area_name = area.get('name', '') if isinstance(area, dict) else str(area)
            return {
                "area_name": area_name,
                "position": loc.get('position', ''),
                "landmarks": loc.get('landmarks', '')
            }

        segment = {
            "segment_type": "quest",
            "id": quest_id,
            "title": quest.get('title', ''),
            "story_beat": quest.get('story_beat', ''),
            "objectives": quest.get('objectives', {}),
            "quest_giver": {
                "name": quest_giver.get('name', ''),
                "title": quest_giver.get('title', ''),
                "personality": quest_giver.get('personality', ''),
                "lore": quest_giver.get('lore', ''),
                "location": extract_location(quest_giver.get('location', {}))
            },
            "turn_in_npc": {
                "name": turn_in_npc.get('name', ''),
                "title": turn_in_npc.get('title', ''),
                "personality": turn_in_npc.get('personality', ''),
                "lore": turn_in_npc.get('lore', ''),
                "location": extract_location(turn_in_npc.get('location', {}))
            },
            "execution_location": {
                "area_name": exec_loc.get('area', {}).get('name', '') if isinstance(exec_loc.get('area'), dict) else str(exec_loc.get('area', '')),
                "enemies": exec_loc.get('enemies', ''),
                "landmarks": exec_loc.get('landmarks', '')
            },
            "story_text": quest.get('story_text', ''),
            "completion_text": quest.get('completion_text', '')
        }

        quest_roleplay = {}
        if roleplay.get(f'{quest_id}.accept'):
            quest_roleplay['accept'] = roleplay[f'{quest_id}.accept']
        if roleplay.get(f'{quest_id}.exec'):
            quest_roleplay['exec'] = roleplay[f'{quest_id}.exec']
        if roleplay.get(f'{quest_id}.complete'):
            quest_roleplay['complete'] = roleplay[f'{quest_id}.complete']

        if quest_roleplay:
            segment["roleplay"] = quest_roleplay

        if previous_scene_ending:
            segment["previous_scene_ending"] = previous_scene_ending

        return segment


@dataclass
class CreateTODO(BaseNode[StorySession]):

    def __post_init__(self):
        self.planner_agent = None
        self.research_node = GetStoryResearch()

    async def run(self, ctx: GraphRunContext[StorySession]) -> GetNextTODO | End:
        if self.planner_agent is None:
            self.planner_agent = StoryPlannerAgent(session_id=ctx.state.session_id)

        print(colored("\n[*] Generating story plan from segments...", "cyan"))
        save_progress(ctx.state.subject, "in_progress", "Generating story plan", 0, 0)

        research_data = ctx.state.research_data
        todos = []

        print(colored("[*] Processing introduction segment...", "cyan"))
        save_progress(ctx.state.subject, "planning", "Planning Introduction", 0, 0, {"phase": "planning", "segment": "Introduction"})
        intro_segment = self.research_node._get_settings_segment(research_data, "introduction")
        intro_todos = await self.planner_agent.run(intro_segment, ctx.state.player)
        todos.extend(intro_todos)
        print(colored(f"[+] Introduction: {len(intro_todos)} todos", "green"))

        execution_order = research_data.get('execution_order', [])
        quests = research_data.get('quests', [])
        quest_by_id = {q.get('id'): q for q in quests}
        quest_index_by_id = {q.get('id'): i for i, q in enumerate(quests)}

        last_scene_ending = None
        if execution_order:
            quest_todos, last_scene_ending = await self._generate_todos_by_flow(
                ctx, execution_order, quests, quest_by_id, quest_index_by_id
            )
            todos.extend(quest_todos)
        else:
            quest_todos, last_scene_ending = await self._generate_todos_sequential(ctx, quests)
            todos.extend(quest_todos)

        print(colored("[*] Processing conclusion segment...", "cyan"))
        save_progress(ctx.state.subject, "planning", "Planning Conclusion", 0, 0, {"phase": "planning", "segment": "Conclusion"})
        conclusion_segment = self.research_node._get_settings_segment(research_data, "conclusion", last_scene_ending)
        conclusion_todos = await self.planner_agent.run(conclusion_segment, ctx.state.player)
        todos.extend(conclusion_todos)
        print(colored(f"[+] Conclusion: {len(conclusion_todos)} todos", "green"))

        ctx.state.todo_list = todos

        print(colored(f"[+] Plan created with {len(ctx.state.todo_list)} todos", "green"))
        save_progress(ctx.state.subject, "in_progress", f"Plan created with {len(ctx.state.todo_list)} todos", 0, len(ctx.state.todo_list))

        todo_cache_file = f"output/{ctx.state.subject}/todo.json"
        print(colored(f"[*] Saving todo list to {todo_cache_file}...", "cyan"))
        try:
            todos_data = [todo.model_dump() for todo in ctx.state.todo_list]
            write_file(todo_cache_file, json.dumps(todos_data, indent=2))
            print(colored(f"[+] Todo list cached successfully", "green"))
        except Exception as e:
            print(colored(f"[!] Failed to cache todos: {e}", "yellow"))

        return GetNextTODO()

    async def _generate_todos_by_flow(self, ctx, execution_order, quests, quest_by_id, quest_index_by_id):
        todos = []
        research_data = ctx.state.research_data
        roleplay = research_data.get('roleplay', {})
        total_quests = len(quests)

        accept_order = []
        complete_order = []
        for seg in execution_order:
            phase = seg.get('phase') if isinstance(seg, dict) else seg.phase
            nodes = seg.get('nodes') if isinstance(seg, dict) else seg.nodes
            if phase == 'accept':
                accept_order.extend([n.split('.')[0] for n in nodes])
            elif phase == 'complete':
                complete_order.extend([n.split('.')[0] for n in nodes])

        previous_accept_quest = None
        previous_scene_ending = roleplay.get('Introduction')

        for seg in execution_order:
            phase = seg.get('phase') if isinstance(seg, dict) else seg.phase
            nodes = seg.get('nodes') if isinstance(seg, dict) else seg.nodes
            is_parallel = seg.get('is_parallel') if isinstance(seg, dict) else seg.is_parallel

            batch_previous_scene = previous_scene_ending if phase == 'accept' else None

            for node in sorted(nodes):
                quest_id = node.split('.')[0]
                quest = quest_by_id.get(quest_id)
                if not quest:
                    continue

                quest_index = quest_index_by_id.get(quest_id, 0)
                quest_title = quest.get('title', f'Quest {quest_id}')
                quest_segment = self.research_node._get_quest_segment(research_data, quest_index, batch_previous_scene)

                quest_segment['quest_position'] = accept_order.index(quest_id) + 1 if quest_id in accept_order else quest_index + 1
                quest_segment['total_quests'] = total_quests
                quest_segment['is_first_quest'] = (accept_order[0] == quest_id) if accept_order else (quest_index == 0)
                quest_segment['is_final_quest'] = (complete_order[-1] == quest_id) if complete_order else (quest_index == total_quests - 1)
                quest_segment['target_phase'] = phase

                if phase == 'accept':
                    if previous_accept_quest:
                        prev_quest = quest_by_id.get(previous_accept_quest)
                        if prev_quest:
                            prev_quest_giver = prev_quest.get('quest_giver', {}).get('name', '')
                            current_quest_giver = quest.get('quest_giver', {}).get('name', '')
                            prev_turn_in_npc = prev_quest.get('turn_in_npc', {}).get('name', '')
                            quest_segment['previous_quest'] = {
                                'title': prev_quest.get('title'),
                                'completion_text': prev_quest.get('completion_text', '')[:500]
                            }
                            quest_segment['same_npc_as_previous'] = (prev_quest_giver == current_quest_giver)
                            quest_segment['skip_introduction'] = (prev_turn_in_npc == current_quest_giver)
                    previous_accept_quest = quest_id

                    next_accept_idx = accept_order.index(quest_id) + 1 if quest_id in accept_order else -1
                    if next_accept_idx > 0 and next_accept_idx < len(accept_order):
                        next_quest_id = accept_order[next_accept_idx]
                        next_quest = quest_by_id.get(next_quest_id)
                        if next_quest:
                            quest_segment['next_quest'] = {
                                'title': next_quest.get('title'),
                                'story_beat': next_quest.get('story_beat', '')[:200]
                            }

                print(colored(f"[*] Processing {quest_title} ({phase})...", "cyan"))
                save_progress(ctx.state.subject, "planning", f"Planning {quest_title} ({phase})", 0, 0, {"phase": "planning", "segment": quest_title, "quest_phase": phase})
                phase_todos = await self.planner_agent.run(quest_segment, ctx.state.player)
                todos.extend(phase_todos)
                print(colored(f"[+] {quest_title} ({phase}): {len(phase_todos)} todos", "green"))

                current_roleplay_key = f"{quest_id}.{phase}"
                if roleplay.get(current_roleplay_key):
                    previous_scene_ending = roleplay[current_roleplay_key]

        return todos, previous_scene_ending

    async def _generate_todos_sequential(self, ctx, quests):
        todos = []
        research_data = ctx.state.research_data
        roleplay = research_data.get('roleplay', {})
        previous_scene_ending = roleplay.get('Introduction')

        for i, quest in enumerate(quests):
            quest_id = quest.get('id', '')
            quest_title = quest.get('title', f'Quest {i+1}')
            print(colored(f"[*] Processing quest segment: {quest_title}...", "cyan"))
            save_progress(ctx.state.subject, "planning", f"Planning {quest_title}", 0, 0, {"phase": "planning", "segment": quest_title})
            quest_segment = self.research_node._get_quest_segment(research_data, i, previous_scene_ending)

            quest_segment['quest_position'] = i + 1
            quest_segment['total_quests'] = len(quests)
            quest_segment['is_first_quest'] = (i == 0)
            quest_segment['is_final_quest'] = (i == len(quests) - 1)

            if i > 0:
                prev_quest = quests[i - 1]
                prev_quest_giver = prev_quest.get('quest_giver', {}).get('name', '')
                current_quest_giver = quest.get('quest_giver', {}).get('name', '')
                prev_turn_in_npc = prev_quest.get('turn_in_npc', {}).get('name', '')
                quest_segment['previous_quest'] = {
                    'title': prev_quest.get('title'),
                    'completion_text': prev_quest.get('completion_text', '')[:500]
                }
                quest_segment['same_npc_as_previous'] = (prev_quest_giver == current_quest_giver)
                quest_segment['skip_introduction'] = (prev_turn_in_npc == current_quest_giver)

            if i < len(quests) - 1:
                next_quest = quests[i + 1]
                quest_segment['next_quest'] = {
                    'title': next_quest.get('title'),
                    'story_beat': next_quest.get('story_beat', '')[:200]
                }

            quest_todos = await self.planner_agent.run(quest_segment, ctx.state.player)
            todos.extend(quest_todos)
            print(colored(f"[+] {quest_title}: {len(quest_todos)} todos", "green"))

            for phase in ['accept', 'exec', 'complete']:
                roleplay_key = f"{quest_id}.{phase}"
                if roleplay.get(roleplay_key):
                    previous_scene_ending = roleplay[roleplay_key]

        return todos, previous_scene_ending


@dataclass
class GetNextTODO(BaseNode[StorySession]):

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateStorySegment | IndexStoryToKB:
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
                {"segment_type": current_todo.item.type, "sub_type": current_todo.item.sub_type, "quest_name": current_todo.item.quest_name}
            )

            return CreateStorySegment()
        else:
            print(colored("\n[+] Story generation complete!", "green"))
            save_progress(ctx.state.subject, "complete", "Story generation complete", len(ctx.state.todo_list), len(ctx.state.todo_list))
            return IndexStoryToKB()


@dataclass
class CreateStorySegment(BaseNode[StorySession]):

    def __post_init__(self):
        self.narrator_agent = None
        self.dialog_creator_agent = None
        self.reviewer_agent = None

    async def run(self, ctx: GraphRunContext[StorySession]) -> WriteToFile:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]
        segment = current_todo.item

        prompt = self._build_prompt(segment, ctx.state)
        is_dialogue = segment.sub_type in ["quest_dialogue", "quest_conclusion"]
        content_type = "dialogue" if is_dialogue else "narration"

        best_output = None
        best_score = 0.0

        for attempt in range(1, MAX_REVIEW_RETRIES + 1):
            if is_dialogue:
                output = await self._generate_dialogue(prompt, ctx.state.session_id)
            else:
                output = await self._generate_narration(prompt, ctx.state.session_id)

            review = await self._review_content(output, content_type, segment, ctx.state)

            if review.quality_score > best_score:
                best_score = review.quality_score
                best_output = output

            if review.passed:
                print(colored(f"[+] Review passed (score: {review.quality_score:.2f})", "green"))
                segment.output = output
                current_todo.status = "done"
                return WriteToFile()

            print(colored(f"[!] Review failed (attempt {attempt}/{MAX_REVIEW_RETRIES}, score: {review.quality_score:.2f})", "yellow"))
            if review.suggestions:
                print(colored(f"    Feedback: {review.suggestions[0]}", "yellow"))

            if attempt < MAX_REVIEW_RETRIES:
                feedback = "\n".join(review.suggestions) if review.suggestions else review.summary
                prompt = self._build_prompt_with_feedback(segment, ctx.state, feedback)

        print(colored(f"[!] Max retries reached, using best attempt (score: {best_score:.2f})", "yellow"))
        segment.output = best_output
        current_todo.status = "done"
        return WriteToFile()

    async def _generate_narration(self, prompt: str, session_id: str) -> Narration:
        if self.narrator_agent is None:
            self.narrator_agent = NarratorAgent(session_id=session_id)

        print(colored(f"[*] Generating narration using NarratorAgent...", "cyan"))
        self.narrator_agent.messages = []
        result = await self.narrator_agent.run(prompt)
        return result.output

    async def _generate_dialogue(self, prompt: str, session_id: str) -> DialogueLines:
        if self.dialog_creator_agent is None:
            self.dialog_creator_agent = DialogCreatorAgent(session_id=session_id)

        print(colored(f"[*] Generating dialogue using DialogCreatorAgent...", "cyan"))
        self.dialog_creator_agent.messages = []
        result = await self.dialog_creator_agent.run(prompt)
        return result.output

    async def _review_content(self, output, content_type: str, segment: TodoItem, state: StorySession):
        if self.reviewer_agent is None:
            self.reviewer_agent = StoryReviewerAgent()

        if content_type == "dialogue":
            content_str = "\n".join([f"{line.actor}: {line.line}" for line in output.lines])
        else:
            content_str = output.text

        print(colored(f"[*] Reviewing {content_type}...", "cyan"))
        result = await self.reviewer_agent.run(
            content=content_str,
            content_type=content_type,
            research_context=state.research_content[:5000],
            segment_prompt=segment.prompt,
            player_name=state.player
        )
        return result.output

    def _build_prompt(self, segment: TodoItem, state: StorySession) -> str:
        player = state.player
        prompt = segment.prompt.replace("{player}", player)
        return prompt

    def _build_prompt_with_feedback(self, segment: TodoItem, state: StorySession, feedback: str) -> str:
        base_prompt = self._build_prompt(segment, state)
        return f"{base_prompt}\n\n## Reviewer Feedback (Please Address)\n\n{feedback}"


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
            display_name = subject.replace('_', ' ').title()
            if display_name.lower().startswith('the '):
                display_name = display_name[4:]
            story = Story(title=f"The {display_name} Chronicles", subject=subject)

        story = self._add_segment_to_story(story, segment)

        story_json = story.model_dump_json(indent=2)
        write_file(file_path, story_json)
        print(colored(f"[+] Story saved to {file_path}", "green"))

        todo_cache_file = f"output/{subject}/todo.json"
        try:
            todos_data = [todo.model_dump() for todo in ctx.state.todo_list]
            write_file(todo_cache_file, json.dumps(todos_data, indent=2))
        except Exception as e:
            print(colored(f"[!] Failed to update todo cache: {e}", "yellow"))

        ctx.state.current_todo_index += 1

        return GetNextTODO()

    def _add_segment_to_story(self, story: Story, segment: TodoItem) -> Story:
        if segment.type == "introduction":
            story.introduction = segment.output  # type: ignore

        elif segment.type == "conclusion":
            story.conclusion = segment.output  # type: ignore

        elif segment.type == "quest":
            section = self._map_sub_type_to_section(segment.sub_type)
            phase = segment.phase or self._infer_phase_from_sub_type(segment.sub_type)

            story_segment = StorySegment(
                quest_ids=segment.quest_ids,
                phase=phase,
                section=section
            )

            if isinstance(segment.output, Narration):
                story_segment.text = segment.output.text
                story_segment.word_count = segment.output.word_count
            elif isinstance(segment.output, DialogueLines):
                story_segment.lines = segment.output.lines

            story.segments.append(story_segment)

        return story

    def _map_sub_type_to_section(self, sub_type: str | None) -> str:
        mapping = {
            "quest_introduction": "intro",
            "quest_dialogue": "dialogue",
            "quest_execution": "narration",
            "quest_conclusion": "dialogue"
        }
        return mapping.get(sub_type or "", "intro")

    def _infer_phase_from_sub_type(self, sub_type: str | None) -> str:
        mapping = {
            "quest_introduction": "accept",
            "quest_dialogue": "accept",
            "quest_execution": "exec",
            "quest_conclusion": "complete"
        }
        return mapping.get(sub_type or "", "accept")


@dataclass
class IndexStoryToKB(BaseNode[StorySession]):

    async def run(self, ctx: GraphRunContext[StorySession]) -> End[None]:
        subject = ctx.state.subject
        story_path = f"output/{subject}/story.json"

        print(colored(f"\n[*] Indexing story to knowledge base...", "cyan"))

        try:
            chunks_indexed = index_story(story_path)
            print(colored(f"[+] Story indexed: {chunks_indexed} chunks added to knowledge base", "green"))
        except Exception as e:
            print(colored(f"[!] Failed to index story: {e}", "yellow"))

        return End(None)
