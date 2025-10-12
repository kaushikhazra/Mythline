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


def get_io_files() -> tuple[str, str]:
    parser = argparse.ArgumentParser(description='File input/output processing')
    parser.add_argument('--input', type=str, required=True, help='Input file path')
    parser.add_argument('--output', type=str, required=True, help='Output file path')

    args = parser.parse_args()

    return args.input, args.output


def get_verbose() -> bool:
    parser = argparse.ArgumentParser(description='Verbose output control')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    return args.verbose


def get_io_files_with_verbose() -> tuple[str, str, bool]:
    parser = argparse.ArgumentParser(description='File input/output processing with verbose control')
    parser.add_argument('--input', type=str, required=True, help='Input file path')
    parser.add_argument('--output', type=str, required=True, help='Output file path')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    return args.input, args.output, args.verbose
