import json
from pathlib import Path
from datetime import datetime


CONTEXT_DIR = ".mythline"


def save_long_term_memory(agent_id: str, preference: str):
    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/long_term_memory/memory.json")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    existing_preferences = []
    if file_path.exists():
        with open(file_path, 'r') as f:
            existing_preferences = json.load(f)

    new_preference = {
        "preference": preference,
        "timestamp": datetime.now().isoformat()
    }
    existing_preferences.append(new_preference)

    with open(file_path, 'w') as f:
        json.dump(existing_preferences, f, indent=2)


def load_long_term_memory(agent_id: str) -> list[dict]:
    file_path = Path(f"{CONTEXT_DIR}/{agent_id}/long_term_memory/memory.json")

    if not file_path.exists():
        return []

    with open(file_path, 'r') as f:
        return json.load(f)
