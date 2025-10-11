import argparse
from datetime import datetime
from src.libs.agent_memory.context_memory import get_latest_session


def get_session(agent_id: str) -> str:
    parser = argparse.ArgumentParser(description='Story Creator CLI')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--session', type=str, help='Load specific session by ID')
    group.add_argument('--resume', action='store_true', help='Resume most recent session')

    args = parser.parse_args()

    if args.resume:
        session_id = get_latest_session(agent_id)
        if not session_id:
            print("No previous sessions found. Creating new session.")
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    elif args.session:
        session_id = args.session
    else:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    return session_id
