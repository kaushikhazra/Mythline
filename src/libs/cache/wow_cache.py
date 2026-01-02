import json
from pathlib import Path
from datetime import datetime, timezone

from src.graphs.story_research_graph.models.research_models import NPC, Location, Area


CACHE_DIR = Path(".mythline/wow_cache")
NPC_CACHE_FILE = CACHE_DIR / "npcs.json"
LOCATION_CACHE_FILE = CACHE_DIR / "locations.json"


def _normalize_key(name: str) -> str:
    return name.lower().strip()


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_npc_cache() -> dict:
    if not NPC_CACHE_FILE.exists():
        return {}
    return json.loads(NPC_CACHE_FILE.read_text(encoding="utf-8"))


def _save_npc_cache(cache: dict):
    _ensure_cache_dir()
    NPC_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _load_location_cache() -> dict:
    if not LOCATION_CACHE_FILE.exists():
        return {}
    return json.loads(LOCATION_CACHE_FILE.read_text(encoding="utf-8"))


def _save_location_cache(cache: dict):
    _ensure_cache_dir()
    LOCATION_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def get_npc(name: str) -> NPC | None:
    cache = _load_npc_cache()
    key = _normalize_key(name)

    if key not in cache:
        return None

    entry = cache[key]
    loc_data = entry.get("location", {})
    area_data = loc_data.get("area", {})

    return NPC(
        name=entry.get("name", ""),
        title=entry.get("title", ""),
        personality=entry.get("personality", ""),
        lore=entry.get("lore", ""),
        location=Location(
            area=Area(
                name=area_data.get("name", ""),
                x=area_data.get("x"),
                y=area_data.get("y")
            ),
            position=loc_data.get("position", ""),
            visual=loc_data.get("visual", ""),
            landmarks=loc_data.get("landmarks", "")
        )
    )


def set_npc(npc: NPC):
    cache = _load_npc_cache()
    key = _normalize_key(npc.name)

    cache[key] = {
        "name": npc.name,
        "title": npc.title,
        "personality": npc.personality,
        "lore": npc.lore,
        "location": {
            "area": {
                "name": npc.location.area.name,
                "x": npc.location.area.x,
                "y": npc.location.area.y
            },
            "position": npc.location.position,
            "visual": npc.location.visual,
            "landmarks": npc.location.landmarks
        },
        "cached_at": datetime.now(timezone.utc).isoformat()
    }

    _save_npc_cache(cache)


def get_location(name: str) -> dict | None:
    cache = _load_location_cache()
    key = _normalize_key(name)

    if key not in cache:
        return None

    entry = cache[key]
    return {
        "url": entry.get("url", ""),
        "content": entry.get("content", "")
    }


def set_location(name: str, url: str, content: str):
    cache = _load_location_cache()
    key = _normalize_key(name)

    cache[key] = {
        "url": url,
        "content": content,
        "cached_at": datetime.now(timezone.utc).isoformat()
    }

    _save_location_cache(cache)
