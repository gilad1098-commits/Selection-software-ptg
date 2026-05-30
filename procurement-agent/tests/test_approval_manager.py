"""Unit tests for agent.approval_manager.ApprovalManager.

Azure Table Storage is fully mocked — no real credentials required.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.approval_manager import ApprovalManager, _PARTITION_KEY
from agent.models import ApprovalRecord, ApprovalStatus, RFQRecord, RFQStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rfq(**overrides) -> RFQRecord:
    now = datetime.now(timezone.utc)
    defaults = dict(
        rfq_id="rfq-test-001",
        supplier_name="TestCo",
        supplier_email="test@testco.com",
        subject="RFQ-TEST",
        thread_id="thread-001",
        status=RFQStatus.AWAITING_REPLY,
        sent_at=now - timedelta(days=5),
        followup_count=0,
    )
    defaults.update(overrides)
    return RFQRecord(**defaults)


def _make_approval_entity(
    approval_id: str,
    rfq_id: str,
    status: str = "pending",
    created_offset_hours: int = 0,
) -> dict:
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(hours=created_offset_hours)
    expires_at = created_at + timedelta(hours=48)
    return {
        "PartitionKey": _PARTITION_KEY,
        "RowKey": approval_id,
        "approval_id": approval_id,
        "rfq_id": rfq_id,
        "draft_id": "draft-abc",
        "draft_body": "Dear supplier…",
        "followup_number": 1,
        "status": status,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "actioned_at": "",
    }


def _async_iter(items):
    """Return an async iterable from a plain list."""
    async def _gen():
        for item in items:
            yield item
    return _gen()


@asynccontextmanager
async def _mock_table_client(table_client_mock):
    """Context manager that yields the mock table client (mirrors 'async with client:')."""
    yield table_client_mock


def _build_manager_with_mock_client(table_client_mock):
    """Patch TableServiceClient so ApprovalManager uses our mock.

    ApprovalManager._get_client() does:
        service = TableServiceClient.from_connection_string(...)
        return service.get_table_client(table_name)
    Then the caller does `async with client: ...`.
    We replace the entire TableServiceClient class in agent.approval_manager
    with a MagicMock whose .from_connection_string() chain ends at table_client_mock.
    """
    manager = ApprovalManager()

    # Make the context manager work: `async with table_client_mock:` → yields itself
    table_client_mock.__aenter__ = AsyncMock(return_value=table_client_mock)
    table_client_mock.__aexit__ = AsyncMock(return_value=False)

    service_mock = MagicMock()
    service_mock.get_table_client.return_value = table_client_mock

    tsc_mock = MagicMock()
    tsc_mock.from_connection_string = MagicMock(return_value=service_mock)

    patcher = patch("agent.approval_manager.TableServiceClient", tsc_mock)
    return manager, patcher


# ---------------------------------------------------------------------------
# Tests: create_pending_approval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_pending_approval_returns_record():
    rfq = _make_rfq()
    table_mock = MagicMock()
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        record = await manager.create_pending_approval(rfq, "draft-111", "Dear supplier…")

    assert isinstance(record, ApprovalRecord)
    assert record.rfq_id == rfq.rfq_id
    assert record.draft_id == "draft-111"
    assert record.draft_body == "Dear supplier…"
    assert record.followup_number == 1  # rfq.followup_count(0) + 1
    assert record.status == ApprovalStatus.PENDING
    assert record.expires_at > record.created_at


@pytest.mark.asyncio
async def test_create_pending_approval_calls_upsert():
    rfq = _make_rfq(followup_count=2)
    table_mock = MagicMock()
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        record = await manager.create_pending_approval(rfq, "draft-222", "Body text")

    table_mock.upsert_entity.assert_called_once()
    call_args = table_mock.upsert_entity.call_args[0][0]
    assert call_args["PartitionKey"] == _PARTITION_KEY
    assert call_args["approval_id"] == record.approval_id
    assert call_args["followup_number"] == 3  # followup_count(2) + 1


@pytest.mark.asyncio
async def test_create_pending_approval_expires_48h_later():
    rfq = _make_rfq()
    table_mock = MagicMock()
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        record = await manager.create_pending_approval(rfq, "draft-333", "Body")

    delta = record.expires_at - record.created_at
    assert delta == timedelta(hours=48)


# ---------------------------------------------------------------------------
# Tests: get_pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pending_returns_record():
    approval_id = str(uuid.uuid4())
    entity = _make_approval_entity(approval_id, "rfq-001")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        result = await manager.get_pending(approval_id)

    assert result is not None
    assert result.approval_id == approval_id
    assert result.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_get_pending_returns_none_when_not_found():
    from azure.core.exceptions import ResourceNotFoundError

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(side_effect=ResourceNotFoundError())

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        result = await manager.get_pending("non-existent-id")

    assert result is None


# ---------------------------------------------------------------------------
# Tests: mark_actioned
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_actioned_sent_updates_status():
    approval_id = str(uuid.uuid4())
    entity = _make_approval_entity(approval_id, "rfq-001")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        await manager.mark_actioned(approval_id, "sent")

    table_mock.upsert_entity.assert_called_once()
    saved = table_mock.upsert_entity.call_args[0][0]
    assert saved["status"] == "sent"
    assert saved["actioned_at"] != ""


@pytest.mark.asyncio
async def test_mark_actioned_dismissed_updates_status():
    approval_id = str(uuid.uuid4())
    entity = _make_approval_entity(approval_id, "rfq-001")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        await manager.mark_actioned(approval_id, "dismissed")

    saved = table_mock.upsert_entity.call_args[0][0]
    assert saved["status"] == "dismissed"


@pytest.mark.asyncio
async def test_mark_actioned_invalid_action_raises():
    approval_id = str(uuid.uuid4())
    entity = _make_approval_entity(approval_id, "rfq-001")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        with pytest.raises(ValueError, match="Unknown action"):
            await manager.mark_actioned(approval_id, "bogus")


@pytest.mark.asyncio
async def test_mark_actioned_noop_when_not_found():
    """Should not raise if the approval doesn't exist — just logs a warning."""
    from azure.core.exceptions import ResourceNotFoundError

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(side_effect=ResourceNotFoundError())
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        await manager.mark_actioned("ghost-id", "sent")  # should not raise

    table_mock.upsert_entity.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: get_expired_pending
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_expired_pending_returns_only_past_expiry():
    now = datetime.now(timezone.utc)

    # Expired: created 72h ago → expires_at is 24h ago
    expired_id = str(uuid.uuid4())
    expired_entity = _make_approval_entity(expired_id, "rfq-002", created_offset_hours=72)

    # Not expired: created 10h ago → expires_at is 38h in the future
    fresh_id = str(uuid.uuid4())
    fresh_entity = _make_approval_entity(fresh_id, "rfq-003", created_offset_hours=10)

    table_mock = MagicMock()
    table_mock.query_entities = MagicMock(
        return_value=_async_iter([expired_entity, fresh_entity])
    )

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        results = await manager.get_expired_pending()

    assert len(results) == 1
    assert results[0].approval_id == expired_id


@pytest.mark.asyncio
async def test_get_expired_pending_empty_when_none_expired():
    fresh_id = str(uuid.uuid4())
    fresh_entity = _make_approval_entity(fresh_id, "rfq-003", created_offset_hours=1)

    table_mock = MagicMock()
    table_mock.query_entities = MagicMock(return_value=_async_iter([fresh_entity]))

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        results = await manager.get_expired_pending()

    assert results == []


# ---------------------------------------------------------------------------
# Tests: mark_expired
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_expired_sets_status_to_expired():
    approval_id = str(uuid.uuid4())
    entity = _make_approval_entity(approval_id, "rfq-001")

    table_mock = MagicMock()
    table_mock.get_entity = AsyncMock(return_value=entity)
    table_mock.upsert_entity = AsyncMock()

    manager, patcher = _build_manager_with_mock_client(table_mock)
    with patcher:
        await manager.mark_expired(approval_id)

    saved = table_mock.upsert_entity.call_args[0][0]
    assert saved["status"] == "expired"
