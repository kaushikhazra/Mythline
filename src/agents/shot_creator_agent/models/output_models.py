from enum import Enum
from pydantic import BaseModel


class CameraZoom(str, Enum):
    wide = "wide"
    medium = "medium"
    close = "close"


class CameraAngle(str, Enum):
    front = "front"
    front_left = "front_left"
    left = "left"
    back_left = "back_left"
    back = "back"
    back_right = "back_right"
    right = "right"
    front_right = "front_right"


class Shot(BaseModel):
    shot_number: int
    actor: str
    temperature: float
    language: str
    exaggeration: float
    cfg_weight: float
    text: str
    reference: str
    camera_zoom: CameraZoom
    camera_angle: CameraAngle
    player_actions: str
    backdrop: str
    duration_seconds: float
