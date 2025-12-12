import asyncio
import argparse

from src.graphs.story_research_graph import StoryResearchGraph


def main():
    parser = argparse.ArgumentParser(description='Story Research Graph CLI')
    parser.add_argument('--subject', type=str, required=True, help='Subject folder name (e.g., shadowglen)')
    args = parser.parse_args()

    print(f"\n=== Story Research Graph ===")
    print(f"Subject: {args.subject}")
    print(f"Input: output/{args.subject}/quest-chain.md")
    print(f"Output: output/{args.subject}/research.json")
    print(f"============================\n")

    graph = StoryResearchGraph(args.subject)
    result = asyncio.run(graph.run())

    if result:
        print(f"\n=== Research Complete ===")
        print(f"Chain: {result.chain_title}")
        print(f"Setting: {result.setting.zone}")
        print(f"Quests: {len(result.quests)}")
        for quest in result.quests:
            print(f"  - {quest.title}")
    else:
        print(f"\n[!] Research failed")


if __name__ == "__main__":
    main()
