import argparse
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from src.libs.agent_memory.context_memory import get_latest_session


@dataclass
class CLIArgs:
    session_id: str
    input_file: Optional[str] = None
    output_file: Optional[str] = None
    verbose: bool = False


def get_arguments(
    agent_id: str,
    description: str = "CLI Application",
    require_input: bool = False,
    require_output: bool = False
) -> CLIArgs:

    parser = argparse.ArgumentParser(description=description)

    session_group = parser.add_mutually_exclusive_group()
    session_group.add_argument(
        '--session', '-s',
        type=str,
        help='Load specific session by ID'
    )
    session_group.add_argument(
        '--resume', '-r',
        action='store_true',
        help='Resume most recent session'
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        required=require_input,
        help='Input file path'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        required=require_output,
        help='Output file path'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

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

    return CLIArgs(
        session_id=session_id,
        input_file=args.input,
        output_file=args.output,
        verbose=args.verbose
    )
