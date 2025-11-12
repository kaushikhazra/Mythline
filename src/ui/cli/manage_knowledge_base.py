import argparse
from termcolor import colored

from src.libs.knowledge_base.knowledge_vectordb import (
    index_knowledge,
    search_knowledge,
    list_all_chunks,
    clear_collection,
    collection_exists
)


def load_command(args):
    print(colored(f"Loading knowledge from '{args.knowledge_dir}' into knowledge base...", "cyan"))

    if collection_exists(args.knowledge_dir):
        print(colored("Warning: Collection already exists. Use 'rebuild' to regenerate.", "yellow"))
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    try:
        num_chunks = index_knowledge(args.knowledge_dir)
        print(colored(f"Successfully indexed {num_chunks} chunks from '{args.knowledge_dir}'", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def rebuild_command(args):
    print(colored(f"Rebuilding knowledge base for '{args.knowledge_dir}'...", "cyan"))

    try:
        clear_collection(args.knowledge_dir)
        print(colored("Cleared existing collection", "yellow"))

        num_chunks = index_knowledge(args.knowledge_dir, fresh=True)
        print(colored(f"Successfully reindexed {num_chunks} chunks from '{args.knowledge_dir}'", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def search_command(args):
    print(colored(f"Searching all knowledge bases for: {args.query}", "cyan"))

    from src.libs.knowledge_base.knowledge_vectordb import get_all_knowledge_collections

    all_collections = get_all_knowledge_collections()

    if not all_collections:
        print(colored("Error: No knowledge bases found. Run 'load <directory>' first.", "red"))
        return

    try:
        results = search_knowledge(args.query, args.top_k)

        if not results:
            print(colored("No results found.", "yellow"))
            return

        print(colored(f"\nFound {len(results)} result(s) across {len(all_collections)} knowledge base(s):\n", "green"))

        for i, result in enumerate(results, 1):
            print(colored(f"--- Result {i} (Score: {result['score']:.3f}) ---", "cyan"))
            print(f"Collection: {result['collection']}")
            print(f"Source: {result['source_file']}")
            print(f"Section: {result['section_header']}\n")
            print(result['text'])
            print()

    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def list_command(args):
    print(colored(f"Listing indexed content from '{args.knowledge_dir}'...", "cyan"))

    if not collection_exists(args.knowledge_dir):
        print(colored(f"Error: Knowledge base '{args.knowledge_dir}' not initialized. Run 'load {args.knowledge_dir}' first.", "red"))
        return

    try:
        chunks = list_all_chunks(args.knowledge_dir)

        if not chunks:
            print(colored("No content indexed.", "yellow"))
            return

        print(colored(f"\nTotal chunks in '{args.knowledge_dir}': {len(chunks)}\n", "green"))

        for chunk in chunks:
            print(colored(f"[{chunk['id']}] {chunk['source_file']} - {chunk['section_header']}", "cyan"))
            print(f"    {chunk['text_preview']}\n")

    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def clear_command(args):
    print(colored(f"Clearing knowledge base '{args.knowledge_dir}'...", "yellow"))

    response = input(f"Are you sure? This will delete all indexed content from '{args.knowledge_dir}'. (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return

    try:
        clear_collection(args.knowledge_dir)
        print(colored(f"Knowledge base '{args.knowledge_dir}' cleared successfully", "green"))
    except Exception as e:
        print(colored(f"Error: {str(e)}", "red"))


def main():
    parser = argparse.ArgumentParser(description="Manage knowledge bases")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    load_parser = subparsers.add_parser('load', help='Load knowledge from directory into knowledge base')
    load_parser.add_argument('--knowledge-dir', default='guides', help='Directory containing knowledge files (default: guides)')

    rebuild_parser = subparsers.add_parser('rebuild', help='Rebuild knowledge base from scratch')
    rebuild_parser.add_argument('--knowledge-dir', default='guides', help='Directory containing knowledge files (default: guides)')

    search_parser = subparsers.add_parser('search', help='Search all knowledge bases')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--top-k', type=int, default=3, help='Number of results to return')

    list_parser = subparsers.add_parser('list', help='List all indexed content from a knowledge base')
    list_parser.add_argument('--knowledge-dir', default='guides', help='Directory to list (default: guides)')

    clear_parser = subparsers.add_parser('clear', help='Clear a knowledge base')
    clear_parser.add_argument('--knowledge-dir', default='guides', help='Directory to clear (default: guides)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'load': load_command,
        'rebuild': rebuild_command,
        'search': search_command,
        'list': list_command,
        'clear': clear_command
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
