import os
import sys
import argparse
import asyncio
import traceback

from src.agents.story_creator_agent.agent import StoryCreatorAgent


parser = argparse.ArgumentParser(description='Story Creator CLI - Non-Interactive Story Generation')
parser.add_argument('--subject', '-s', type=str, required=True, help='Story subject (e.g., "shadowglen")')
parser.add_argument('--player', '-p', type=str, required=True, help='Player character name (e.g., "Sarephine")')

args = parser.parse_args()

research_path = f"output/{args.subject}/research.md"

if not os.path.exists(research_path):
    print(f"Error: Research file not found at {research_path}")
    print(f"Please run story_research_agent first to create research notes.")
    print(f"\nExample:")
    print(f"  start_story_researcher.bat")
    print(f"  User: Research {args.subject}")
    sys.exit(1)

async def main():
    session_id = args.subject

    story_creator = StoryCreatorAgent(session_id=session_id, player_name=args.player)

    print(f"Starting story generation for: {args.subject}")
    print(f"Player character: {args.player}")
    print(f"Session ID: {session_id}")
    print(f"Research file: {research_path}")
    print("-" * 50)
    print()

    try:
        await story_creator.run(subject=args.subject)

        print()
        print("=" * 50)
        print("Story generation complete!")
        print("=" * 50)
        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 50)
        print(f"Error during story generation:")
        print("=" * 50)
        traceback.print_exc()
        print("=" * 50)
        print(f"Session saved. You can resume by running the same command again.")
        print("=" * 50)
        sys.exit(1)

asyncio.run(main())
