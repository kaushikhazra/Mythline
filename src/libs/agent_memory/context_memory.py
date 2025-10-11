from pydantic_ai import ModelMessage, ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python
import json
from pathlib import Path


CONTEXT_DIR = ".mythline"


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
