"""RabbitMQ PoC — Validate messaging topology for Mythline v2.

Tests the knowledge.topic exchange, agent queues, user.decisions queue,
and publish/subscribe patterns using aio-pika.

Requires RabbitMQ running on localhost:5672.
Start via: docker compose up -d
"""

import asyncio
import json

import aio_pika
import pytest

RABBITMQ_URL = "amqp://mythline:mythline@localhost:5672/"

EXCHANGE_NAME = "knowledge.topic"
RESEARCHER_QUEUE = "agent.world_lore_researcher"
VALIDATOR_QUEUE = "agent.world_lore_validator"
USER_QUEUE = "user.decisions"


@pytest.fixture
async def connection():
    """Create a RabbitMQ connection for each test."""
    conn = await aio_pika.connect_robust(RABBITMQ_URL)
    yield conn
    await conn.close()


@pytest.fixture
async def channel(connection):
    """Create a channel from the connection."""
    channel = await connection.channel()
    yield channel


@pytest.fixture
async def exchange(channel):
    """Declare the knowledge.topic exchange."""
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )
    yield exchange
    await channel.exchange_delete(EXCHANGE_NAME)


@pytest.fixture
async def queues(channel, exchange):
    """Declare all queues and bind them to the exchange."""
    researcher_q = await channel.declare_queue(RESEARCHER_QUEUE, durable=True)
    validator_q = await channel.declare_queue(VALIDATOR_QUEUE, durable=True)
    user_q = await channel.declare_queue(USER_QUEUE, durable=True)

    await researcher_q.bind(exchange, routing_key=RESEARCHER_QUEUE)
    await validator_q.bind(exchange, routing_key=VALIDATOR_QUEUE)
    await user_q.bind(exchange, routing_key=USER_QUEUE)

    yield {
        "researcher": researcher_q,
        "validator": validator_q,
        "user": user_q,
    }

    await researcher_q.purge()
    await validator_q.purge()
    await user_q.purge()
    await researcher_q.delete()
    await validator_q.delete()
    await user_q.delete()


class TestConnection:
    async def test_connect(self, connection):
        """Should connect to RabbitMQ successfully."""
        assert not connection.is_closed

    async def test_channel(self, channel):
        """Should create a channel."""
        assert not channel.is_closed


class TestExchange:
    async def test_declare_topic_exchange(self, exchange):
        """Should declare a topic exchange."""
        assert exchange.name == EXCHANGE_NAME

    async def test_exchange_is_durable(self, exchange):
        """Exchange should be durable (survives broker restart)."""
        assert exchange.durable


class TestQueues:
    async def test_all_queues_declared(self, queues):
        """All three queues should be declared."""
        assert queues["researcher"].name == RESEARCHER_QUEUE
        assert queues["validator"].name == VALIDATOR_QUEUE
        assert queues["user"].name == USER_QUEUE


class TestPublishSubscribe:
    async def test_publish_to_researcher(self, exchange, queues):
        """Publish a validation result to the researcher queue."""
        message = {
            "message_type": "validation_result",
            "source_agent": "world_lore_validator",
            "target_agent": "world_lore_researcher",
            "payload": {
                "zone_name": "Elwynn Forest",
                "accepted": True,
                "feedback": [],
                "iteration": 1,
            },
        }

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=RESEARCHER_QUEUE,
        )

        incoming = await queues["researcher"].get(timeout=5)
        assert incoming is not None
        body = json.loads(incoming.body.decode())
        assert body["message_type"] == "validation_result"
        assert body["payload"]["zone_name"] == "Elwynn Forest"
        assert body["payload"]["accepted"] is True
        await incoming.ack()

    async def test_publish_to_validator(self, exchange, queues):
        """Publish a research package to the validator queue."""
        message = {
            "message_type": "research_package",
            "source_agent": "world_lore_researcher",
            "target_agent": "world_lore_validator",
            "payload": {
                "zone_name": "Westfall",
                "npcs": ["gryan_stoutmantle", "sentinel_hill_guard"],
                "confidence": 0.85,
            },
        }

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=VALIDATOR_QUEUE,
        )

        incoming = await queues["validator"].get(timeout=5)
        body = json.loads(incoming.body.decode())
        assert body["message_type"] == "research_package"
        assert body["payload"]["zone_name"] == "Westfall"
        await incoming.ack()

    async def test_publish_user_decision(self, exchange, queues):
        """Publish a user decision request to the user queue."""
        message = {
            "message_type": "user_decision_required",
            "source_agent": "world_lore_researcher",
            "payload": {
                "question": "Which zone should we research next?",
                "options": ["Westfall", "Loch Modan", "Darkshore"],
                "context": "Fork detected from Elwynn Forest research",
                "decision_id": "dec-001",
            },
        }

        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(message).encode(),
                content_type="application/json",
            ),
            routing_key=USER_QUEUE,
        )

        incoming = await queues["user"].get(timeout=5)
        body = json.loads(incoming.body.decode())
        assert body["message_type"] == "user_decision_required"
        assert body["payload"]["decision_id"] == "dec-001"
        assert "Westfall" in body["payload"]["options"]
        await incoming.ack()

    async def test_routing_isolation(self, exchange, queues):
        """Messages should only go to their targeted queue."""
        await exchange.publish(
            aio_pika.Message(body=b"for validator only"),
            routing_key=VALIDATOR_QUEUE,
        )

        with pytest.raises(aio_pika.exceptions.QueueEmpty):
            await queues["researcher"].get(timeout=1, fail=True)

        incoming = await queues["validator"].get(timeout=5)
        assert incoming.body == b"for validator only"
        await incoming.ack()

    async def test_message_persistence(self, exchange, queues):
        """Persistent messages should survive queue inspection."""
        await exchange.publish(
            aio_pika.Message(
                body=b"persistent message",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=RESEARCHER_QUEUE,
        )

        incoming = await queues["researcher"].get(timeout=5)
        assert incoming.body == b"persistent message"
        assert incoming.delivery_mode == aio_pika.DeliveryMode.PERSISTENT
        await incoming.ack()


class TestConsumerPattern:
    async def test_async_consumer(self, connection):
        """Test the async consumer pattern used by agents."""
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True,
        )
        queue = await channel.declare_queue("test.consumer", auto_delete=True)
        await queue.bind(exchange, routing_key="test.consumer")

        received_messages = []

        async def on_message(message: aio_pika.IncomingMessage):
            async with message.process():
                body = json.loads(message.body.decode())
                received_messages.append(body)

        consumer_tag = await queue.consume(on_message)

        for i in range(3):
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps({"seq": i, "type": "test"}).encode(),
                ),
                routing_key="test.consumer",
            )

        await asyncio.sleep(0.5)

        assert len(received_messages) == 3
        assert received_messages[0]["seq"] == 0
        assert received_messages[2]["seq"] == 2

        await queue.cancel(consumer_tag)
