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
    regenerate_plan: bool = False

    async def run(self, ctx: GraphRunContext[StorySession]) -> CreateTODO | GetNextTODO | End[str]:
        subject = ctx.state.subject
        research_file = f"output/{subject}/research.md"
        todo_cache_file = f"output/{subject}/todo.json"

        print(colored(f"\n[*] Reading research notes for {subject}...", "cyan"))

        if not file_exists(research_file):
            error_msg = f"Research file not found for subject: {subject}"
            print(colored(f"[!] {error_msg}", "red"))
            return End(error_msg)

        research_content = read_file(research_file)
        print(colored(f"[+] Research loaded", "green"))

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

        todo_cache_file = f"output/{ctx.state.subject}/todo.json"
        print(colored(f"[*] Saving todo list to {todo_cache_file}...", "cyan"))
        try:
            todos_data = [todo.model_dump() for todo in ctx.state.todo_list]
            write_file(todo_cache_file, json.dumps(todos_data, indent=2))
            print(colored(f"[+] Todo list cached successfully", "green"))
        except Exception as e:
            print(colored(f"[!] Failed to cache todos: {e}", "yellow"))

        return GetNextTODO()


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

    async def run(self, ctx: GraphRunContext[StorySession]) -> WriteToFile:
        current_todo = ctx.state.todo_list[ctx.state.current_todo_index]
        segment = current_todo.item

        prompt = self._build_prompt(segment, ctx.state)

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
        current_todo.status = "done"
        return WriteToFile()

    def _build_prompt(self, segment: StorySegment, state: StorySession) -> str:
        player = state.player
        prompt = segment.prompt.replace("{player}", player)
        return prompt


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

        todo_cache_file = f"output/{subject}/todo.json"
        try:
            todos_data = [todo.model_dump() for todo in ctx.state.todo_list]
            write_file(todo_cache_file, json.dumps(todos_data, indent=2))
        except Exception as e:
            print(colored(f"[!] Failed to update todo cache: {e}", "yellow"))

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
