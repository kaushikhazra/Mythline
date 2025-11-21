import json
import hashlib
from pathlib import Path
from dataclasses import asdict

from src.graphs.content_reviewer.models.session_models import ReviewSession

SESSION_DIR = Path(".mythline/content_reviewer/sessions")

def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def load_session(session_id: str) -> ReviewSession | None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session_id}.json"

    if not session_file.exists():
        return None

    try:
        data = json.loads(session_file.read_text())
        return ReviewSession(**data)
    except Exception as e:
        print(f"[!] Error loading session {session_id}: {e}")
        return None

def save_session(session: ReviewSession):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session.session_id}.json"

    try:
        session_file.write_text(json.dumps(asdict(session), indent=2))
    except Exception as e:
        print(f"[!] Error saving session {session.session_id}: {e}")

def wipe_session(session_id: str):
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    session_file = SESSION_DIR / f"{session_id}.json"

    try:
        if session_file.exists():
            session_file.unlink()
            print(f"[+] Session {session_id} wiped")
    except Exception as e:
        print(f"[!] Error wiping session {session_id}: {e}")

def create_session(
    session_id: str,
    content: str,
    max_retries: int,
    quality_threshold: float
) -> ReviewSession:
    content_hash = compute_content_hash(content)
    return ReviewSession(
        session_id=session_id,
        content_hash=content_hash,
        max_retries=max_retries,
        quality_threshold=quality_threshold
    )
