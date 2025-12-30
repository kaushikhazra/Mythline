import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from src.libs.youtube import YouTubeUploader, VideoMetadata
from src.agents.youtube_metadata_agent import YouTubeMetadataAgent


console = Console()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload videos to YouTube with auto-generated metadata from story"
    )

    parser.add_argument(
        "--subject",
        type=str,
        help="Subject name (loads video from output/{subject}/video/upload/{subject}.mp4)"
    )
    parser.add_argument(
        "--privacy", "-p",
        type=str,
        choices=["public", "private", "unlisted"],
        default="private",
        help="Privacy setting (default: private)"
    )
    parser.add_argument(
        "--thumbnail",
        type=str,
        help="Path to thumbnail image (JPG or PNG)"
    )
    parser.add_argument(
        "--publish-at",
        type=str,
        help="Schedule publish time (ISO format: 2024-12-25T10:00:00)"
    )
    parser.add_argument(
        "--category", "-c",
        type=str,
        default="20",
        help="Category ID or name (default: 20 - Gaming)"
    )
    parser.add_argument(
        "--playlist",
        type=str,
        help="Playlist name or ID to add video to"
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available video categories"
    )
    parser.add_argument(
        "--list-playlists",
        action="store_true",
        help="List your playlists"
    )
    parser.add_argument(
        "--logout",
        action="store_true",
        help="Clear stored credentials"
    )

    return parser.parse_args()


def validate_subject(subject: str) -> tuple[Path, Path] | None:
    subject_dir = Path(f"output/{subject}")
    if not subject_dir.exists():
        console.print(f"[red]Error: Subject directory not found: {subject_dir}[/red]")
        return None

    story_file = subject_dir / "story.json"
    if not story_file.exists():
        console.print(f"[red]Error: Story file not found: {story_file}[/red]")
        return None

    video_file = subject_dir / "video" / "upload" / f"{subject}.mov"
    if not video_file.exists():
        console.print(f"[red]Error: Video file not found: {video_file}[/red]")
        return None

    return video_file, story_file


def validate_thumbnail(thumbnail_path: str) -> Path | None:
    path = Path(thumbnail_path)
    if not path.exists():
        console.print(f"[red]Error: Thumbnail file not found: {thumbnail_path}[/red]")
        return None

    valid_extensions = {".jpg", ".jpeg", ".png"}
    if path.suffix.lower() not in valid_extensions:
        console.print(f"[red]Error: Thumbnail must be JPG or PNG[/red]")
        return None

    return path


def parse_publish_at(publish_at_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(publish_at_str)
    except ValueError:
        console.print(f"[red]Error: Invalid datetime format: {publish_at_str}[/red]")
        console.print("Use ISO format: 2024-12-25T10:00:00")
        return None


def resolve_category(uploader: YouTubeUploader, category: str) -> str:
    if category.isdigit():
        return category

    categories = uploader.list_categories()
    for cat in categories:
        if cat["title"].lower() == category.lower():
            return cat["id"]

    console.print(f"[yellow]Warning: Category '{category}' not found, using default (20)[/yellow]")
    return "20"


def display_categories(uploader: YouTubeUploader) -> None:
    categories = uploader.list_categories()

    if not categories:
        console.print("[yellow]No categories available[/yellow]")
        return

    table = Table(title="YouTube Video Categories")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")

    for cat in categories:
        table.add_row(cat["id"], cat["title"])

    console.print(table)


def display_playlists(uploader: YouTubeUploader) -> None:
    playlists = uploader.list_playlists()

    if not playlists:
        console.print("[yellow]No playlists found[/yellow]")
        return

    table = Table(title="Your Playlists")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Description", style="dim")

    for playlist in playlists:
        desc = playlist["description"][:50] + "..." if len(playlist["description"]) > 50 else playlist["description"]
        table.add_row(playlist["id"], playlist["title"], desc)

    console.print(table)


async def generate_metadata(story_file: Path) -> tuple[str, str, list[str]]:
    with open(story_file, "r", encoding="utf-8") as f:
        story_data = json.load(f)

    story_json = json.dumps(story_data, indent=2)

    agent = YouTubeMetadataAgent()
    result = await agent.run(story_json)

    return result.output.title, result.output.description, result.output.tags


def handle_upload(uploader: YouTubeUploader, args: argparse.Namespace) -> None:
    paths = validate_subject(args.subject)
    if not paths:
        sys.exit(1)

    video_path, story_file = paths

    thumbnail_path = None
    if args.thumbnail:
        thumbnail_path = validate_thumbnail(args.thumbnail)
        if not thumbnail_path:
            sys.exit(1)

    publish_at = None
    if args.publish_at:
        publish_at = parse_publish_at(args.publish_at)
        if not publish_at:
            sys.exit(1)

    category_id = resolve_category(uploader, args.category)

    console.print()
    with console.status("[cyan]Generating YouTube metadata from story..."):
        title, description, tags = asyncio.run(generate_metadata(story_file))

    console.print(f"[bold]Title:[/bold] {title}")
    console.print(f"[bold]Description:[/bold] {description[:100]}...")
    console.print(f"[bold]Tags:[/bold] {', '.join(tags[:5])}...")
    console.print()

    metadata = VideoMetadata(
        title=title,
        description=description,
        tags=tags,
        category_id=category_id,
        privacy_status=args.privacy,
        publish_at=publish_at
    )

    console.print(f"[bold]Uploading:[/bold] {video_path.name}")
    console.print(f"[bold]Privacy:[/bold] {metadata.privacy_status}")
    if publish_at:
        console.print(f"[bold]Scheduled:[/bold] {publish_at.isoformat()}")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Uploading...", total=100)

        def update_progress(pct: float):
            progress.update(task, completed=pct * 100)

        success, video_id, error = uploader.upload(video_path, metadata, update_progress)

    if not success:
        console.print(f"\n[red]Upload failed: {error}[/red]")
        sys.exit(1)

    console.print()
    console.print("[green]Upload complete![/green]")
    console.print(f"[bold]Video ID:[/bold] {video_id}")
    console.print(f"[bold]URL:[/bold] https://youtube.com/watch?v={video_id}")

    if thumbnail_path:
        console.print()
        with console.status("[cyan]Setting thumbnail..."):
            success, error = uploader.set_thumbnail(video_id, thumbnail_path)

        if success:
            console.print("[green]Thumbnail set successfully[/green]")
        else:
            console.print(f"[yellow]Failed to set thumbnail: {error}[/yellow]")

    if args.playlist:
        console.print()
        playlist_id = args.playlist

        if not playlist_id.startswith("PL"):
            with console.status("[cyan]Finding playlist..."):
                found_id = uploader.get_playlist_id(args.playlist)

            if found_id:
                playlist_id = found_id
            else:
                console.print(f"[yellow]Playlist '{args.playlist}' not found[/yellow]")
                return

        with console.status(f"[cyan]Adding to playlist..."):
            success, error = uploader.add_to_playlist(video_id, playlist_id)

        if success:
            console.print(f"[green]Added to playlist[/green]")
        else:
            console.print(f"[yellow]Failed to add to playlist: {error}[/yellow]")


def main():
    args = parse_arguments()

    if args.logout:
        uploader = YouTubeUploader()
        if uploader.clear_credentials():
            console.print("[green]Credentials cleared successfully[/green]")
        else:
            console.print("[yellow]No credentials to clear[/yellow]")
        return

    if not args.list_categories and not args.list_playlists and not args.subject:
        console.print("[red]Error: --subject is required[/red]")
        console.print("Usage: python -m src.ui.cli.upload_youtube --subject <subject_name>")
        sys.exit(1)

    uploader = YouTubeUploader()

    with console.status("[cyan]Authenticating with YouTube..."):
        success, error = uploader.connect()

    if not success:
        console.print(f"[red]Authentication failed: {error}[/red]")
        if "client_secrets" in error.lower():
            console.print()
            console.print("[yellow]Setup instructions:[/yellow]")
            console.print("1. Go to https://console.cloud.google.com")
            console.print("2. Create a project and enable YouTube Data API v3")
            console.print("3. Create OAuth 2.0 credentials (Desktop application)")
            console.print("4. Download and save as 'client_secrets.json' in project root")
        sys.exit(1)

    console.print("[green]Authenticated[/green]")

    if args.list_categories:
        display_categories(uploader)
        return

    if args.list_playlists:
        display_playlists(uploader)
        return

    handle_upload(uploader, args)


if __name__ == "__main__":
    main()
