# YouTube Uploader Implementation Plan

## Overview

CLI tool for uploading videos to YouTube with full metadata support, OAuth authentication with token storage, following existing Mythline patterns.

## Files to Create

| File | Purpose |
|------|---------|
| `src/libs/youtube/__init__.py` | Export YouTubeUploader, YouTubeAuth |
| `src/libs/youtube/auth.py` | OAuth 2.0 authentication with token storage |
| `src/libs/youtube/uploader.py` | YouTubeUploader class (follows OBSController pattern) |
| `src/ui/cli/upload_youtube.py` | CLI entry point with argparse |
| `start_youtube_upload.bat` | Windows launcher |

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add Google API dependencies |

## Dependencies to Add

```
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
```

## Implementation Details

### 1. OAuth Authentication (`src/libs/youtube/auth.py`)

**Token Storage:** `.mythline/youtube/credentials.json`

**Class: YouTubeAuth**
- `get_credentials()` - Load/refresh/create credentials
- `_load_credentials()` - Load from JSON
- `_save_credentials()` - Save to JSON
- `_refresh_credentials()` - Refresh expired tokens
- `_run_oauth_flow()` - Browser-based consent
- `clear_credentials()` - Delete stored tokens

**Scopes:**
- `youtube.upload` - Upload videos
- `youtube` - Manage playlists/thumbnails

### 2. YouTube Uploader (`src/libs/youtube/uploader.py`)

**Pattern:** Follow `src/libs/obs/controller.py`

**Class: YouTubeUploader**
- `connect() -> tuple[bool, str]` - Authenticate and build service
- `disconnect()` - Clear service
- `is_connected() -> bool` - Check connection
- `upload(video_path, metadata) -> tuple[bool, str, str]` - Upload video
- `set_thumbnail(video_id, path) -> tuple[bool, str]` - Set thumbnail
- `add_to_playlist(video_id, playlist_id) -> tuple[bool, str]` - Add to playlist
- `get_playlist_id(name) -> str | None` - Find playlist by name
- `list_playlists() -> list[dict]` - Get user playlists
- `list_categories() -> list[dict]` - Get categories

**VideoMetadata Dataclass:**
```python
@dataclass
class VideoMetadata:
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: str = "22"  # People & Blogs
    privacy_status: str = "private"
    publish_at: datetime = None
    made_for_kids: bool = False
```

**Supported Formats:** .mp4, .mov, .avi, .mkv, .wmv, .webm

### 3. CLI Tool (`src/ui/cli/upload_youtube.py`)

**Arguments:**

| Argument | Flag | Required | Description |
|----------|------|----------|-------------|
| video | positional | Yes | Path to video file |
| --title | -t | Yes | Video title |
| --description | -d | No | Description |
| --tags | | No | Comma-separated tags |
| --privacy | -p | No | public/private/unlisted |
| --thumbnail | | No | Thumbnail image path |
| --publish-at | | No | Schedule (ISO format) |
| --category | -c | No | Category ID or name |
| --playlist | | No | Playlist name or ID |
| --list-categories | | No | List categories |
| --list-playlists | | No | List playlists |
| --logout | | No | Clear credentials |

**CLI Flow:**
1. Pre-flight validation (video exists, thumbnail format)
2. Connect (OAuth if needed)
3. Handle utility commands (list/logout)
4. Upload with Rich progress bar
5. Post-upload: set thumbnail, add to playlist
6. Display video URL

## Usage Examples

```bash
# Basic upload
python -m src.ui.cli.upload_youtube video.mp4 -t "My Video"

# Full metadata
python -m src.ui.cli.upload_youtube video.mp4 \
    -t "Epic Gaming Moment" \
    -d "Watch this amazing play!" \
    --tags "gaming,wow,epic" \
    -p public \
    --thumbnail thumb.jpg \
    --category "Gaming" \
    --playlist "My Gaming Videos"

# Scheduled publish
python -m src.ui.cli.upload_youtube video.mp4 \
    -t "Upcoming Video" \
    --publish-at "2024-12-25T10:00:00"

# Utility commands
python -m src.ui.cli.upload_youtube --list-categories
python -m src.ui.cli.upload_youtube --list-playlists
python -m src.ui.cli.upload_youtube --logout
```

## Setup Requirements

1. Create project at console.cloud.google.com
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app)
4. Download `client_secrets.json` to project root
5. First upload triggers browser OAuth consent
6. Credentials stored for future uploads

## Implementation Order

1. `src/libs/youtube/__init__.py`
2. `src/libs/youtube/auth.py`
3. `src/libs/youtube/uploader.py`
4. `src/ui/cli/upload_youtube.py`
5. `requirements.txt` (add dependencies)
6. `start_youtube_upload.bat`

## Reference Files

- `src/libs/obs/controller.py` - Service controller pattern
- `src/ui/cli/create_audio.py` - CLI with argparse pattern
- `src/libs/agent_memory/context_memory.py` - .mythline/ storage pattern
