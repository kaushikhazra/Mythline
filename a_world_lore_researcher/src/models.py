"""Pydantic models for the World Lore Researcher agent.

All BaseModel subclasses and enums live here. No business logic.

Sections:
  1. Enums
  2. Sub-models (shared building blocks)
  3. Domain models (World Lore schema)
  4. Message models (RabbitMQ communication + job queue)
  5. Checkpoint
  6. Agent output models (LLM structured output)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now()


# ---------------------------------------------------------------------------
# 1. Enums
# ---------------------------------------------------------------------------


class SourceTier(str, Enum):
    OFFICIAL = "official"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"


class FactionStance(str, Enum):
    ALLIED = "allied"
    HOSTILE = "hostile"
    NEUTRAL = "neutral"


class LoreCategory(str, Enum):
    HISTORY = "history"
    MYTHOLOGY = "mythology"
    COSMOLOGY = "cosmology"
    POWER_SOURCE = "power_source"


class ItemSignificance(str, Enum):
    LEGENDARY = "legendary"
    EPIC = "epic"
    QUEST = "quest"
    NOTABLE = "notable"


class MessageType(str, Enum):
    RESEARCH_PACKAGE = "research_package"
    RESEARCH_JOB = "research_job"
    JOB_STATUS_UPDATE = "job_status_update"
    VALIDATION_RESULT = "validation_result"
    USER_DECISION_REQUIRED = "user_decision_required"
    USER_DECISION_RESPONSE = "user_decision_response"


class JobStatus(str, Enum):
    ACCEPTED = "accepted"
    ZONE_STARTED = "zone_started"
    STEP_PROGRESS = "step_progress"
    ZONE_COMPLETED = "zone_completed"
    JOB_COMPLETED = "job_completed"
    JOB_PARTIAL_COMPLETED = "job_partial_completed"
    JOB_FAILED = "job_failed"


# ---------------------------------------------------------------------------
# 2. Sub-models
# ---------------------------------------------------------------------------


class SourceReference(BaseModel):
    url: str
    domain: str
    tier: SourceTier
    accessed_at: datetime = Field(default_factory=_now)


class PhaseState(BaseModel):
    phase_name: str
    description: str
    trigger: str = ""


class NPCRelationship(BaseModel):
    npc_id: str
    relationship_type: str
    description: str = ""


class FactionRelation(BaseModel):
    faction_id: str
    stance: FactionStance
    description: str = ""


class Conflict(BaseModel):
    data_point: str
    source_a: SourceReference
    claim_a: str
    source_b: SourceReference
    claim_b: str
    resolution: str = ""


class ValidationFeedback(BaseModel):
    field: str
    issue: str
    suggestion: str = ""


# ---------------------------------------------------------------------------
# 3. Domain models
# ---------------------------------------------------------------------------


class ZoneData(BaseModel):
    name: str
    game: str = "wow"
    level_range: dict[str, int] = Field(default_factory=lambda: {"min": 0, "max": 0})
    narrative_arc: str = ""
    political_climate: str = ""
    access_gating: list[str] = Field(default_factory=list)
    phase_states: list[PhaseState] = Field(default_factory=list)
    connected_zones: list[str] = Field(default_factory=list)
    era: str = ""
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float = 0.0


class NPCData(BaseModel):
    name: str
    zone_id: str = ""
    faction_ids: list[str] = Field(default_factory=list)
    personality: str = ""
    motivations: list[str] = Field(default_factory=list)
    relationships: list[NPCRelationship] = Field(default_factory=list)
    quest_threads: list[str] = Field(default_factory=list)
    phased_state: str = ""
    role: str = ""
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float = 0.0


class FactionData(BaseModel):
    name: str
    parent_faction_id: str = ""
    level: str = ""
    inter_faction: list[FactionRelation] = Field(default_factory=list)
    exclusive_with: list[str] = Field(default_factory=list)
    ideology: str = ""
    goals: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float = 0.0


class LoreData(BaseModel):
    zone_id: str = ""
    title: str = ""
    category: LoreCategory = LoreCategory.HISTORY
    content: str = ""
    era: str = ""
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float = 0.0


class NarrativeItemData(BaseModel):
    name: str
    zone_id: str = ""
    story_arc: str = ""
    wielder_lineage: list[str] = Field(default_factory=list)
    power_description: str = ""
    significance: ItemSignificance = ItemSignificance.NOTABLE
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# 4. Message models (RabbitMQ communication + job queue)
# ---------------------------------------------------------------------------


class ResearchJob(BaseModel):
    job_id: str
    zone_name: str = Field(min_length=1)
    depth: int = Field(default=0, ge=0, le=5)
    game: str = "wow"
    requested_by: str = ""
    requested_at: datetime = Field(default_factory=_now)


class ZoneFailure(BaseModel):
    zone_name: str
    error: str


class JobStatusUpdate(BaseModel):
    job_id: str
    status: JobStatus
    zone_name: str = ""
    step_name: str = ""
    step_number: int = 0
    total_steps: int = 0
    zones_completed: int = 0
    zones_total: int = 0
    zones_failed: list[ZoneFailure] = Field(default_factory=list)
    error: str = ""
    timestamp: datetime = Field(default_factory=_now)


class BudgetState(BaseModel):
    daily_tokens_used: int = 0
    last_reset_date: str = ""


class MessageEnvelope(BaseModel):
    message_id: str = Field(default_factory=_uuid)
    source_agent: str
    target_agent: str
    message_type: MessageType
    timestamp: datetime = Field(default_factory=_now)
    correlation_id: str = Field(default_factory=_uuid)
    payload: dict = Field(default_factory=dict)


class ResearchPackage(BaseModel):
    zone_name: str
    zone_data: ZoneData
    npcs: list[NPCData] = Field(default_factory=list)
    factions: list[FactionData] = Field(default_factory=list)
    lore: list[LoreData] = Field(default_factory=list)
    narrative_items: list[NarrativeItemData] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    conflicts: list[Conflict] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    zone_name: str
    accepted: bool
    feedback: list[ValidationFeedback] = Field(default_factory=list)
    iteration: int = 1


class UserDecisionRequired(BaseModel):
    question: str
    options: list[str]
    context: str = ""
    decision_id: str = Field(default_factory=_uuid)


class UserDecisionResponse(BaseModel):
    decision_id: str
    choice: str


# ---------------------------------------------------------------------------
# 5. Checkpoint
# ---------------------------------------------------------------------------


class ResearchCheckpoint(BaseModel):
    job_id: str
    zone_name: str
    current_step: int = 0
    wave_depth: int = 0
    step_data: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 6. Agent output models (LLM structured output)
# ---------------------------------------------------------------------------


class ZoneExtraction(BaseModel):
    zone: ZoneData
    npcs: list[NPCData] = Field(default_factory=list)
    factions: list[FactionData] = Field(default_factory=list)
    lore: list[LoreData] = Field(default_factory=list)
    narrative_items: list[NarrativeItemData] = Field(default_factory=list)


class NPCExtractionResult(BaseModel):
    npcs: list[NPCData] = Field(default_factory=list)


class FactionExtractionResult(BaseModel):
    factions: list[FactionData] = Field(default_factory=list)


class LoreExtractionResult(BaseModel):
    lore: list[LoreData] = Field(default_factory=list)


class NarrativeItemExtractionResult(BaseModel):
    narrative_items: list[NarrativeItemData] = Field(default_factory=list)


class CrossReferenceResult(BaseModel):
    is_consistent: bool = True
    conflicts: list[Conflict] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class ResearchResult(BaseModel):
    """Returned by research_zone() — raw crawled content + source references."""
    raw_content: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    summary: str = ""


class ConnectedZonesResult(BaseModel):
    """Returned by _zone_discovery_agent — slugified zone names."""
    zone_slugs: list[str] = Field(default_factory=list)
