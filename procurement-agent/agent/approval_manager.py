from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables.aio import TableServiceClient

from agent.models import ApprovalRecord, ApprovalStatus, RFQRecord
from config.settings import settings

logger = logging.getLogger(__name__)

_PARTITION_KEY = "approval"
_TABLE_NAME = "approvals"
_APPROVAL_TTL_HOURS = 48


def _to_entity(record: ApprovalRecord) -> dict:
    data = record.model_dump()
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif value is None:
            data[key] = ""
    data["PartitionKey"] = _PARTITION_KEY
    data["RowKey"] = record.approval_id
    return data


def _from_entity(entity: dict) -> ApprovalRecord:
    data = dict(entity)
    data.pop("PartitionKey", None)
    data.pop("RowKey", None)

    for field in ("created_at", "expires_at", "actioned_at"):
        raw = data.get(field)
        if raw:
            data[field] = datetime.fromisoformat(raw)
        else:
            data[field] = None

    return ApprovalRecord(**data)


class ApprovalManager:
    def __init__(self):
        self._conn = settings.AZURE_STORAGE_CONNECTION_STRING

    async def _get_client(self):
        service = TableServiceClient.from_connection_string(self._conn)
        return service.get_table_client(_TABLE_NAME)

    async def create_pending_approval(
        self, rfq: RFQRecord, draft_id: str, draft_body: str
    ) -> ApprovalRecord:
        now = datetime.now(timezone.utc)
        record = ApprovalRecord(
            approval_id=str(uuid.uuid4()),
            rfq_id=rfq.rfq_id,
            draft_id=draft_id,
            draft_body=draft_body,
            followup_number=rfq.followup_count + 1,
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=_APPROVAL_TTL_HOURS),
        )
        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(record))
        logger.debug(
            "Created pending approval %s for RFQ %s (follow-up #%d)",
            record.approval_id,
            rfq.rfq_id,
            record.followup_number,
        )
        return record

    async def get_pending(self, approval_id: str) -> Optional[ApprovalRecord]:
        client = await self._get_client()
        async with client:
            try:
                entity = await client.get_entity(_PARTITION_KEY, approval_id)
                return _from_entity(entity)
            except ResourceNotFoundError:
                return None

    async def mark_actioned(self, approval_id: str, action: str) -> None:
        """Mark an approval record as actioned.

        action must be one of: "sent" | "dismissed" | "edited"
        """
        status_map = {
            "sent": ApprovalStatus.SENT,
            "dismissed": ApprovalStatus.DISMISSED,
            "edited": ApprovalStatus.SENT,  # edited + sent counts as sent
        }
        new_status = status_map.get(action)
        if new_status is None:
            raise ValueError(f"Unknown action '{action}'. Must be: sent, dismissed, edited")

        record = await self.get_pending(approval_id)
        if record is None:
            logger.warning("Approval %s not found; cannot mark as %s", approval_id, action)
            return

        record.status = new_status
        record.actioned_at = datetime.now(timezone.utc)

        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(record))
        logger.debug("Approval %s marked as %s", approval_id, new_status)

    async def get_expired_pending(self) -> list[ApprovalRecord]:
        """Return all approval records that are still PENDING but past their expires_at."""
        now = datetime.now(timezone.utc)
        client = await self._get_client()
        expired: list[ApprovalRecord] = []
        async with client:
            async for entity in client.query_entities(
                f"PartitionKey eq '{_PARTITION_KEY}' and status eq 'pending'"
            ):
                record = _from_entity(entity)
                if record.expires_at and record.expires_at < now:
                    expired.append(record)
        logger.debug("Found %d expired pending approvals", len(expired))
        return expired

    async def mark_expired(self, approval_id: str) -> None:
        record = await self.get_pending(approval_id)
        if record is None:
            return
        record.status = ApprovalStatus.EXPIRED
        record.actioned_at = datetime.now(timezone.utc)
        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(record))
        logger.debug("Approval %s marked as expired", approval_id)
