"""Unit tests for agent.engineer_response_manager.EngineerResponseManager.

Azure Table Storage is fully mocked — no real credentials required.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.engineer_response_manager import EngineerResponseManager, _PARTITION_KEY
from agent.models import EngineerAction, EngineerResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    response_id: str,
    rfq_id: str,
    engineer_name: str = "Denis",
    action: str = "",
    responded_at: str = "",
    created_offset_hours: int = 0,
) -> dict:
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=created_offset_hours)
    return {
        "PartitionKey": _PARTITION_KEY,
        "RowKey": response_id,
        "response_id": response_id,
        "rfq_id": rfq_id,
        "engineer_name": engineer_name,
        "action": action,
        "slack_message_ts": "ts-001",
        "responded_at": responded_at,
        "created_at": created_at.isoformat(),
        "notes": "",
    }


def _async_iter(items):
    async def _gen():
        for item in items:
            yield item
    return _gen()


def _build_manager_with_mock_client(table_client_mock):
    """Patch TableServiceClient so EngineerResponseManager uses our mock."""
    manager = EngineerResponseManager()

    table_client_mock.__aenter__ = AsyncMock(return_value=table_client_mock)
    table_client_mock.__aexit__ = AsyncMock(return_value=False)

    service_mock = MagicMock()
    service_mock.get_table_client.return_value = table_client_mock

    tsc_mock = MagicMock()
    tsc_mock.from_connection_string = MagicMock(return_value=service_mock)

    patcher = patch("agent.engineer_response_manager.TableServiceClient", tsc_mock)
    return manager, patcher


# ---------------------------------------------------------------------------
# Tests: create_pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_pending_returns_record():
    table_mock = MagicMock()
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        record = await manager.create_pending(
            rfq_id="rfq-001",
            engineer_name="Denis",
            slack_message_ts="ts-abc",
        )

    assert isinstance(record, EngineerResponse)
    assert record.rfq_id == "rfq-001"
    assert record.engineer_name == "Denis"
    assert record.slack_message_ts == "ts-abc"
    assert record.action is None
    assert record.responded_at is None
    assert record.response_id  # non-empty uuid


@pytest.mark.asyncio
async def test_create_pending_calls_upsert():
    table_mock = MagicMock()
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        record = await manager.create_pending(
            rfq_id="rfq-002",
            engineer_name="Dmitri",
            slack_message_ts="ts-xyz",
        )

    table_mock.upsert_entity.assert_called_once()
    saved = table_mock.upsert_entity.call_args[0][0]
    assert saved["PartitionKey"] == _PARTITION_KEY
    assert saved["response_id"] == record.response_id
    assert saved["rfq_id"] == "rfq-002"


@pytest.mark.asyncio
async def test_create_pending_response_id_is_uuid():
    table_mock = MagicMock()
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        record = await manager.create_pending(
            rfq_id="rfq-003",
            engineer_name="Denis",
            slack_message_ts="",
        )

    # Must be a valid UUID
    uuid.UUID(record.response_id)


# ---------------------------------------------------------------------------
# Tests: mark_responded
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_responded_updates_action():
    response_id = str(uuid.uuid4())
    entity = _make_entity(response_id, "rfq-001")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        updated = await manager.mark_responded(response_id, EngineerAction.APPROVED)

    assert updated.action == EngineerAction.APPROVED
    assert updated.responded_at is not None

    table_mock.upsert_entity.assert_called_once()
    saved = table_mock.upsert_entity.call_args[0][0]
    assert saved["action"] == EngineerAction.APPROVED


@pytest.mark.asyncio
async def test_mark_responded_rejected():
    response_id = str(uuid.uuid4())
    entity = _make_entity(response_id, "rfq-002")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        updated = await manager.mark_responded(
            response_id, EngineerAction.REJECTED, notes="Specs mismatch"
        )

    assert updated.action == EngineerAction.REJECTED
    assert updated.notes == "Specs mismatch"


@pytest.mark.asyncio
async def test_mark_responded_raises_when_not_found():
    from azure.core.exceptions import ResourceNotFoundError

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(side_effect=ResourceNotFoundError())

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        with pytest.raises(ValueError, match="not found"):
            await manager.mark_responded("ghost-id", EngineerAction.APPROVED)


# ---------------------------------------------------------------------------
# Tests: get_unanswered_older_than
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_unanswered_older_than_filters_correctly():
    old_id = str(uuid.uuid4())
    recent_id = str(uuid.uuid4())
    responded_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc)

    # Old + unanswered → should be returned
    old_entity = _make_entity(old_id, "rfq-010", created_offset_hours=50)

    # Recent + unanswered → should NOT be returned (only 5h old, threshold is 48h)
    recent_entity = _make_entity(recent_id, "rfq-011", created_offset_hours=5)

    # Old but already responded → should NOT be returned
    responded_entity = _make_entity(
        responded_id, "rfq-012", created_offset_hours=72,
        action=EngineerAction.APPROVED,
        responded_at=now.isoformat(),
    )

    table_mock = MagicMock()
    table_mock.query_entities = MagicMock(
        return_value=_async_iter([old_entity, recent_entity, responded_entity])
    )

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        results = await manager.get_unanswered_older_than(hours=48)

    ids = [r.response_id for r in results]
    assert old_id in ids
    assert recent_id not in ids
    assert responded_id not in ids


@pytest.mark.asyncio
async def test_get_unanswered_older_than_empty_when_all_recent():
    recent_id = str(uuid.uuid4())
    recent_entity = _make_entity(recent_id, "rfq-020", created_offset_hours=1)

    table_mock = MagicMock()
    table_mock.query_entities = MagicMock(return_value=_async_iter([recent_entity]))

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        results = await manager.get_unanswered_older_than(hours=48)

    assert results == []


@pytest.mark.asyncio
async def test_get_unanswered_older_than_empty_list():
    table_mock = MagicMock()
    table_mock.query_entities = MagicMock(return_value=_async_iter([]))

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        results = await manager.get_unanswered_older_than(hours=24)

    assert results == []


# ---------------------------------------------------------------------------
# Tests: get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_returns_record():
    response_id = str(uuid.uuid4())
    entity = _make_entity(response_id, "rfq-030")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        result = await manager.get(response_id)

    assert result is not None
    assert result.response_id == response_id
    assert result.rfq_id == "rfq-030"


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found():
    from azure.core.exceptions import ResourceNotFoundError

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(side_effect=ResourceNotFoundError())

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        result = await manager.get("non-existent-id")

    assert result is None
