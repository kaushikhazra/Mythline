"""Integration tests — require Docker services running.

Run with: pytest tests/test_integration.py -m integration
Skip by default in CI/local without services.
"""

from __future__ import annotations

import os

import httpx
import pytest

from src.config import MCP_STORAGE_URL, MCP_WEB_SEARCH_URL, MCP_WEB_CRAWLER_URL, RABBITMQ_URL

SERVICES_AVAILABLE = os.getenv("INTEGRATION_TESTS", "").lower() == "true"
skip_unless_services = pytest.mark.skipif(
    not SERVICES_AVAILABLE,
    reason="Set INTEGRATION_TESTS=true with Docker services running",
)


async def _mcp_health(url: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                timeout=5.0,
            )
            return response.status_code == 200
    except Exception:
        return False


@skip_unless_services
class TestStorageMCPIntegration:
    @pytest.mark.asyncio
    async def test_storage_reachable(self):
        assert await _mcp_health(MCP_STORAGE_URL)

    @pytest.mark.asyncio
    async def test_checkpoint_save_load_cycle(self):
        from src.checkpoint import save_checkpoint, load_checkpoint, delete_checkpoint
        from src.models import ResearchCheckpoint

        cp = ResearchCheckpoint(zone_name="integration_test_zone", current_step=3)
        await save_checkpoint(cp)

        loaded = await load_checkpoint()
        assert loaded is not None
        assert loaded.zone_name == "integration_test_zone"
        assert loaded.current_step == 3

        await delete_checkpoint()


@skip_unless_services
class TestWebSearchMCPIntegration:
    @pytest.mark.asyncio
    async def test_search_reachable(self):
        assert await _mcp_health(MCP_WEB_SEARCH_URL)

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        from src.mcp_client import web_search

        results = await web_search("Elwynn Forest World of Warcraft", max_results=3)
        assert isinstance(results, list)
        assert len(results) > 0
        assert "url" in results[0]


@skip_unless_services
class TestWebCrawlerMCPIntegration:
    @pytest.mark.asyncio
    async def test_crawler_reachable(self):
        assert await _mcp_health(MCP_WEB_CRAWLER_URL)

    @pytest.mark.asyncio
    async def test_crawl_returns_content(self):
        from src.mcp_client import crawl_url

        result = await crawl_url("https://wowpedia.fandom.com/wiki/Elwynn_Forest")
        assert isinstance(result, dict)
        assert result.get("content") is not None or result.get("error") is not None


@skip_unless_services
class TestRabbitMQIntegration:
    @pytest.mark.asyncio
    async def test_rabbitmq_connect(self):
        import aio_pika

        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()
        assert channel is not None
        await channel.close()
        await connection.close()

    @pytest.mark.asyncio
    async def test_publish_consume(self):
        import aio_pika

        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()

        queue = await channel.declare_queue("test_integration", auto_delete=True)
        await channel.default_exchange.publish(
            aio_pika.Message(body=b'{"test": true}'),
            routing_key="test_integration",
        )

        message = await queue.get(timeout=5)
        assert message is not None
        assert b"test" in message.body

        await channel.close()
        await connection.close()
