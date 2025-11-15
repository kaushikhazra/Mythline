import os
import sys
import argparse
import asyncio
import traceback

from src.graphs.audio_generator_graph import AudioGeneratorGraph


parser = argparse.ArgumentParser(description='Audio Generator CLI - Create Audio from Shots')
parser.add_argument('--subject', '-s', type=str, required=True, help='Story subject (e.g., "shadowglen")')

args = parser.parse_args()

shots_path = f"output/{args.subject}/shots.json"

if not os.path.exists(shots_path):
    print(f"Error: Shots file not found at {shots_path}")
    print(f"Please run create_shots first to generate the shots.")
    print(f"\nExample:")
    print(f"  python -m src.ui.cli.create_shots --subject {args.subject}")
    sys.exit(1)

async def main():
    audio_generator_graph = AudioGeneratorGraph(subject=args.subject)

    print(f"Starting audio generation for: {args.subject}")
    print(f"Shots file: {shots_path}")
    print("-" * 50)
    print()

    try:
        await audio_generator_graph.run()

        print()
        print("=" * 50)
        print("Audio generation complete!")
        print(f"Audio files saved to: output/{args.subject}/audio/")
        print("=" * 50)
        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 50)
        print(f"Error during audio generation:")
        print("=" * 50)
        traceback.print_exc()
        print("=" * 50)
        sys.exit(1)

asyncio.run(main())
