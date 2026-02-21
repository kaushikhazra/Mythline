"""Tests for the LLM-powered research agent — extraction and cross-reference."""

import os
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.agent import ZoneExtraction, CrossReferenceResult, _load_system_prompt
from src.models import (
    ZoneData,
    NPCData,
    FactionData,
    LoreData,
    NarrativeItemData,
    SourceReference,
    SourceTier,
    Conflict,
)


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-for-tests")


def _make_researcher():
    from src.agent import LoreResearcher
    return LoreResearcher()


class TestLoadSystemPrompt:
    def test_loads_prompt_file(self):
        prompt = _load_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestZoneExtraction:
    def test_minimal_extraction(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest"),
        )
        assert extraction.zone.name == "Elwynn Forest"
        assert extraction.npcs == []
        assert extraction.factions == []

    def test_full_extraction(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest", narrative_arc="Peaceful beginnings"),
            npcs=[NPCData(name="Marshal Dughan")],
            factions=[FactionData(name="Stormwind Guard")],
            lore=[LoreData(title="History of Elwynn")],
            narrative_items=[NarrativeItemData(name="Hogger's Claw")],
        )
        assert len(extraction.npcs) == 1
        assert len(extraction.factions) == 1
        assert len(extraction.lore) == 1
        assert len(extraction.narrative_items) == 1

    def test_serialization_roundtrip(self):
        extraction = ZoneExtraction(
            zone=ZoneData(name="Westfall"),
            npcs=[NPCData(name="Gryan Stoutmantle")],
        )
        json_str = extraction.model_dump_json()
        restored = ZoneExtraction.model_validate_json(json_str)
        assert restored.zone.name == "Westfall"
        assert restored.npcs[0].name == "Gryan Stoutmantle"


class TestCrossReferenceResult:
    def test_consistent_result(self):
        result = CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.9, "npcs": 0.85},
        )
        assert result.is_consistent is True
        assert result.confidence["zone"] == 0.9

    def test_inconsistent_result(self):
        result = CrossReferenceResult(
            is_consistent=False,
            conflicts=[
                Conflict(
                    data_point="NPC faction",
                    source_a=SourceReference(url="https://a.com", domain="a.com", tier=SourceTier.PRIMARY),
                    claim_a="Alliance",
                    source_b=SourceReference(url="https://b.com", domain="b.com", tier=SourceTier.TERTIARY),
                    claim_b="Neutral",
                )
            ],
        )
        assert result.is_consistent is False
        assert len(result.conflicts) == 1


class TestLoreResearcherInit:
    def test_creates_agents(self):
        researcher = _make_researcher()
        assert researcher._extraction_agent is not None
        assert researcher._cross_ref_agent is not None
        assert researcher._research_agent is not None

    def test_cross_reference_prompt(self):
        from src.agent import LoreResearcher
        prompt = LoreResearcher._cross_reference_prompt()
        assert "consistency" in prompt.lower()
        assert "confidence" in prompt.lower()


class TestExtractZoneData:
    @pytest.mark.asyncio
    async def test_extract_zone_data_calls_agent(self):
        researcher = _make_researcher()

        mock_extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest", narrative_arc="Starting zone"),
            npcs=[NPCData(name="Marshal Dughan")],
        )

        mock_result = MagicMock()
        mock_result.output = mock_extraction

        researcher._extraction_agent = MagicMock()
        researcher._extraction_agent.run = AsyncMock(return_value=mock_result)

        sources = [
            SourceReference(url="https://wowpedia.fandom.com/wiki/Elwynn", domain="wowpedia.fandom.com", tier=SourceTier.OFFICIAL),
        ]

        result = await researcher.extract_zone_data(
            zone_name="elwynn_forest",
            raw_content=["# Elwynn Forest\nA peaceful forest..."],
            sources=sources,
        )

        assert result.zone.name == "Elwynn Forest"
        assert len(result.npcs) == 1
        researcher._extraction_agent.run.assert_called_once()


class TestCrossReference:
    @pytest.mark.asyncio
    async def test_cross_reference_calls_agent(self):
        researcher = _make_researcher()

        mock_cr_result = CrossReferenceResult(
            is_consistent=True,
            confidence={"zone": 0.95, "npcs": 0.9},
        )

        mock_result = MagicMock()
        mock_result.output = mock_cr_result

        researcher._cross_ref_agent = MagicMock()
        researcher._cross_ref_agent.run = AsyncMock(return_value=mock_result)

        extraction = ZoneExtraction(
            zone=ZoneData(name="Elwynn Forest"),
            npcs=[NPCData(name="Marshal Dughan")],
        )

        result = await researcher.cross_reference(extraction)

        assert result.is_consistent is True
        assert result.confidence["zone"] == 0.95
        researcher._cross_ref_agent.run.assert_called_once()
