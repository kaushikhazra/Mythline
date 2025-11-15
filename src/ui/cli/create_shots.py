import os
import sys
import argparse
import asyncio
import traceback

from src.graphs.shot_creator_graph import ShotCreatorGraph


parser = argparse.ArgumentParser(description='Shot Creator CLI - Create Video Shots from Story')
parser.add_argument('--subject', '-s', type=str, required=True, help='Story subject (e.g., "shadowglen")')

args = parser.parse_args()

story_path = f"output/{args.subject}/story.json"

if not os.path.exists(story_path):
    print(f"Error: Story file not found at {story_path}")
    print(f"Please run create_story first to generate the story.")
    print(f"\nExample:")
    print(f"  python -m src.ui.cli.create_story --subject {args.subject} --player YourCharacter")
    sys.exit(1)

async def main():
    shot_creator_graph = ShotCreatorGraph(subject=args.subject)

    print(f"Starting shot creation for: {args.subject}")
    print(f"Story file: {story_path}")
    print("-" * 50)
    print()

    try:
        await shot_creator_graph.run()

        print()
        print("=" * 50)
        print("Shot creation complete!")
        print(f"Shots saved to: output/{args.subject}/shots.json")
        print("=" * 50)
        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 50)
        print(f"Error during shot creation:")
        print("=" * 50)
        traceback.print_exc()
        print("=" * 50)
        sys.exit(1)

asyncio.run(main())
