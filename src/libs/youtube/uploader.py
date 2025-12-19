from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from src.libs.youtube.auth import YouTubeAuth


SUPPORTED_FORMATS = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".wmv": "video/x-ms-wmv",
    ".flv": "video/x-flv",
    ".webm": "video/webm"
}

SUPPORTED_THUMBNAILS = {".jpg", ".jpeg", ".png"}


@dataclass
class VideoMetadata:
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: str = "22"
    privacy_status: str = "private"
    publish_at: datetime | None = None
    made_for_kids: bool = False
    language: str = "en"


class YouTubeUploader:

    def __init__(self, client_secrets_path: str | None = None):
        self._auth = YouTubeAuth(client_secrets_path)
        self._service = None

    def connect(self) -> tuple[bool, str]:
        credentials, error = self._auth.get_credentials()
        if not credentials:
            return False, error

        try:
            self._service = build("youtube", "v3", credentials=credentials)
            return True, ""
        except Exception as e:
            return False, str(e)

    def disconnect(self) -> None:
        self._service = None

    def is_connected(self) -> bool:
        return self._service is not None

    def upload(
        self,
        video_path: Path,
        metadata: VideoMetadata,
        progress_callback: Callable[[float], None] | None = None
    ) -> tuple[bool, str, str]:
        if not self._service:
            return False, "", "Not connected"

        video_path = Path(video_path)
        if not video_path.exists():
            return False, "", f"Video file not found: {video_path}"

        suffix = video_path.suffix.lower()
        if suffix not in SUPPORTED_FORMATS:
            return False, "", f"Unsupported format: {suffix}"

        body = self._build_request_body(metadata)

        media = MediaFileUpload(
            str(video_path),
            mimetype=SUPPORTED_FORMATS[suffix],
            resumable=True,
            chunksize=1024 * 1024
        )

        try:
            request = self._service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status and progress_callback:
                    progress_callback(status.progress())

            if progress_callback:
                progress_callback(1.0)

            return True, response["id"], ""

        except HttpError as e:
            error_message = self._parse_http_error(e)
            return False, "", error_message
        except Exception as e:
            return False, "", str(e)

    def _build_request_body(self, metadata: VideoMetadata) -> dict:
        body = {
            "snippet": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "categoryId": metadata.category_id,
                "defaultLanguage": metadata.language
            },
            "status": {
                "privacyStatus": metadata.privacy_status,
                "selfDeclaredMadeForKids": metadata.made_for_kids
            }
        }

        if metadata.publish_at:
            body["status"]["publishAt"] = metadata.publish_at.isoformat()
            body["status"]["privacyStatus"] = "private"

        return body

    def _parse_http_error(self, error: HttpError) -> str:
        try:
            import json
            error_content = json.loads(error.content.decode())
            reason = error_content["error"]["errors"][0]["reason"]

            error_messages = {
                "quotaExceeded": "Daily upload quota exceeded. Try again tomorrow.",
                "uploadLimitExceeded": "Upload limit reached for this video.",
                "invalidMetadata": "Invalid video metadata. Check title/description.",
                "forbidden": "Account not authorized for uploads.",
                "notFound": "Resource not found.",
                "videoNotFound": "Video not found.",
                "playlistNotFound": "Playlist not found."
            }

            return error_messages.get(reason, str(error))
        except Exception:
            return str(error)

    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> tuple[bool, str]:
        if not self._service:
            return False, "Not connected"

        thumbnail_path = Path(thumbnail_path)
        if not thumbnail_path.exists():
            return False, f"Thumbnail file not found: {thumbnail_path}"

        suffix = thumbnail_path.suffix.lower()
        if suffix not in SUPPORTED_THUMBNAILS:
            return False, f"Unsupported thumbnail format: {suffix}. Use JPG or PNG."

        try:
            media = MediaFileUpload(str(thumbnail_path), mimetype=f"image/{suffix.lstrip('.')}")
            self._service.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            return True, ""
        except HttpError as e:
            return False, self._parse_http_error(e)
        except Exception as e:
            return False, str(e)

    def add_to_playlist(self, video_id: str, playlist_id: str) -> tuple[bool, str]:
        if not self._service:
            return False, "Not connected"

        try:
            self._service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            ).execute()
            return True, ""
        except HttpError as e:
            return False, self._parse_http_error(e)
        except Exception as e:
            return False, str(e)

    def get_playlist_id(self, playlist_name: str) -> str | None:
        playlists = self.list_playlists()
        for playlist in playlists:
            if playlist["title"].lower() == playlist_name.lower():
                return playlist["id"]
        return None

    def list_playlists(self) -> list[dict]:
        if not self._service:
            return []

        try:
            response = self._service.playlists().list(
                part="snippet",
                mine=True,
                maxResults=50
            ).execute()

            return [
                {
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"].get("description", "")
                }
                for item in response.get("items", [])
            ]
        except Exception:
            return []

    def list_categories(self, region_code: str = "US") -> list[dict]:
        if not self._service:
            return []

        try:
            response = self._service.videoCategories().list(
                part="snippet",
                regionCode=region_code
            ).execute()

            return [
                {
                    "id": item["id"],
                    "title": item["snippet"]["title"]
                }
                for item in response.get("items", [])
                if item["snippet"].get("assignable", False)
            ]
        except Exception:
            return []

    def clear_credentials(self) -> bool:
        return self._auth.clear_credentials()
