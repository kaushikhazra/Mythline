import obsws_python as obs
from obsws_python.error import OBSSDKError


class OBSController:

    def __init__(self, host: str = "localhost", port: int = 4455, password: str = ""):
        self._host = host
        self._port = port
        self._password = password
        self._client = None

    def connect(self) -> bool:
        try:
            self._client = obs.ReqClient(
                host=self._host,
                port=self._port,
                password=self._password
            )
            return True
        except ConnectionRefusedError:
            return False
        except Exception:
            return False

    def disconnect(self):
        if self._client:
            self._client.disconnect()
            self._client = None

    def is_connected(self) -> bool:
        return self._client is not None

    def start_recording(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.start_record()
            return True
        except OBSSDKError:
            return False

    def pause_recording(self) -> tuple[bool, str]:
        if not self._client:
            return False, "Not connected"
        try:
            self._client.pause_record()
            return True, ""
        except OBSSDKError as e:
            return False, str(e)

    def resume_recording(self) -> tuple[bool, str]:
        if not self._client:
            return False, "Not connected"
        try:
            self._client.resume_record()
            return True, ""
        except OBSSDKError as e:
            return False, str(e)

    def stop_recording(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.stop_record()
            return True
        except OBSSDKError:
            return False

    def get_record_status(self) -> dict | None:
        if not self._client:
            return None
        try:
            status = self._client.get_record_status()
            return {
                "active": status.output_active,
                "paused": status.output_paused,
                "timecode": status.output_timecode,
                "bytes": status.output_bytes,
            }
        except OBSSDKError:
            return None
