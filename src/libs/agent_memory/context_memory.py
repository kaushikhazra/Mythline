import json

from dotenv import load_dotenv
from pathlib import Path
from termcolor import colored

from pydantic_core import to_jsonable_python

from pydantic_ai import (
    Agent, 
    RunContext, 
    ModelMessage, 
    ModelMessagesTypeAdapter
)

load_dotenv()

CONTEXT_DIR = ".mythline"

SUMMARIZER_AGENT = Agent(
    'openai:gpt-4o-mini'
)


def save_context(agent_id, session_id, messages: list[ModelMessage]):
    json_data = to_jsonable_python(messages)

    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory/{session_id}.json")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w') as f:
        json.dump(json_data, f, indent=2)


def load_context(agent_id, session_id) -> list[ModelMessage]:
    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory/{session_id}.json")

    if not file_path.exists():
        return []

    with open(file_path, 'r') as f:
        json_data = json.load(f)

    return ModelMessagesTypeAdapter.validate_python(json_data)


def get_latest_session(agent_id: str) -> str | None:
    context_path = Path(f"{CONTEXT_DIR}/{agent_id}/context_memory")

    if not context_path.exists():
        return None

    json_files = sorted(context_path.glob("*.json"), key=lambda p: p.stem, reverse=True)

    if not json_files:
        return None

    return json_files[0].stem

async def summarize_context(ctx: RunContext[None], messages: list[ModelMessage]) -> list[ModelMessage]:
    if len(messages) > 50:
        print(colored(f'\n⚙ summarizing history...', 'grey'))

        messages_no_tools : list[ModelMessage] = []
        for message in messages:
            has_no_tool_parts = all(
                part.part_kind not in ['tool-return','tool-call', 'retry-prompt']
                for part in message.parts
            )

            if has_no_tool_parts:
                messages_no_tools.append(message)
        
        print(colored(f'\nTool call history removed {len(messages) - len(messages_no_tools)}', 'grey'))

        message_to_summarize = messages_no_tools[2:-30]
        summarized_message = []
        if len(message_to_summarize) > 1:
            summary_message = await SUMMARIZER_AGENT.run(
                """Summarize this conversation, 
                omitting small talk and unrelated topics.""", 
                message_history=message_to_summarize
            )
            summarized_message = summary_message.new_messages()
            print(colored(summary_message.output, 'grey'))                                         

        print(colored(f'...done', 'grey'))

        messages_to_keep = -20 if len(messages_no_tools) > 20 else -1 * len(messages_no_tools)
        print(colored(f'\nKeeping messages {messages_to_keep}', 'grey'))

        return messages[:1] \
            + summarized_message\
            + messages_no_tools[messages_to_keep:]
    
    return messages
