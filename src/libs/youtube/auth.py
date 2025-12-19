import json
from pathlib import Path
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


CREDENTIALS_DIR = Path(".mythline/youtube")
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
CLIENT_SECRETS_FILE = Path("client_secrets.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


class YouTubeAuth:

    def __init__(self, client_secrets_path: str | None = None):
        self._client_secrets_path = Path(client_secrets_path) if client_secrets_path else CLIENT_SECRETS_FILE
        self._credentials_dir = CREDENTIALS_DIR
        self._credentials_file = CREDENTIALS_FILE

    def get_credentials(self) -> tuple[Credentials | None, str]:
        credentials = self._load_credentials()

        if credentials and credentials.valid:
            return credentials, ""

        if credentials and credentials.expired and credentials.refresh_token:
            refreshed = self._refresh_credentials(credentials)
            if refreshed:
                return refreshed, ""

        if not self._client_secrets_path.exists():
            return None, f"Client secrets file not found: {self._client_secrets_path}"

        try:
            credentials = self._run_oauth_flow()
            return credentials, ""
        except Exception as e:
            return None, str(e)

    def _load_credentials(self) -> Credentials | None:
        if not self._credentials_file.exists():
            return None

        try:
            with open(self._credentials_file, "r") as f:
                creds_data = json.load(f)

            return Credentials(
                token=creds_data.get("token"),
                refresh_token=creds_data.get("refresh_token"),
                token_uri=creds_data.get("token_uri"),
                client_id=creds_data.get("client_id"),
                client_secret=creds_data.get("client_secret"),
                scopes=creds_data.get("scopes")
            )
        except Exception:
            return None

    def _save_credentials(self, credentials: Credentials) -> None:
        self._credentials_dir.mkdir(parents=True, exist_ok=True)

        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }

        with open(self._credentials_file, "w") as f:
            json.dump(creds_data, f, indent=2)

    def _refresh_credentials(self, credentials: Credentials) -> Credentials | None:
        try:
            credentials.refresh(Request())
            self._save_credentials(credentials)
            return credentials
        except Exception:
            return None

    def _run_oauth_flow(self) -> Credentials:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self._client_secrets_path),
            scopes=SCOPES
        )
        credentials = flow.run_local_server(port=0)
        self._save_credentials(credentials)
        return credentials

    def clear_credentials(self) -> bool:
        if self._credentials_file.exists():
            self._credentials_file.unlink()
            return True
        return False
