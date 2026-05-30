from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables.aio import TableServiceClient

from agent.models import EngineerAction, EngineerResponse
from config.settings import settings

logger = logging.getLogger(__name__)

_PARTITION_KEY = "engineer_response"
_TABLE_NAME = "engineer_responses"


def _to_entity(record: EngineerResponse) -> dict:
    data = record.model_dump()
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif value is None:
            data[key] = ""
    data["PartitionKey"] = _PARTITION_KEY
    data["RowKey"] = record.response_id
    return data


def _from_entity(entity: dict) -> EngineerResponse:
    data = dict(entity)
    data.pop("PartitionKey", None)
    data.pop("RowKey", None)

    for field in ("responded_at", "created_at"):
        raw = data.get(field)
        if raw:
            data[field] = datetime.fromisoformat(raw)
        else:
            data[field] = None

    # Empty string → None for optional fields
    for field in ("action", "notes"):
        if data.get(field) == "":
            data[field] = None if field == "action" else ""

    return EngineerResponse(**data)


class EngineerResponseManager:
    """Stores pending engineer responses in Azure Table Storage (table: engineer_responses)."""

    def __init__(self):
        self._conn = settings.AZURE_STORAGE_CONNECTION_STRING

    async def _get_client(self):
        service = TableServiceClient.from_connection_string(self._conn)
        return service.get_table_client(_TABLE_NAME)

    async def create_pending(
        self,
        rfq_id: str,
        engineer_name: str,
        slack_message_ts: str,
    ) -> EngineerResponse:
        """Creates a pending EngineerResponse record. response_id = uuid4."""
        record = EngineerResponse(
            response_id=str(uuid.uuid4()),
            rfq_id=rfq_id,
            engineer_name=engineer_name,
            slack_message_ts=slack_message_ts,
            action=None,
            responded_at=None,
            created_at=datetime.now(timezone.utc),
        )
        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(record))
        logger.debug(
            "Created pending engineer response %s for RFQ %s (engineer=%s)",
            record.response_id,
            rfq_id,
            engineer_name,
        )
        return record

    async def get(self, response_id: str) -> Optional[EngineerResponse]:
        client = await self._get_client()
        async with client:
            try:
                entity = await client.get_entity(_PARTITION_KEY, response_id)
                return _from_entity(entity)
            except ResourceNotFoundError:
                return None

    async def mark_responded(
        self,
        response_id: str,
        action: EngineerAction,
        notes: str = "",
    ) -> EngineerResponse:
        record = await self.get(response_id)
        if record is None:
            raise ValueError(f"EngineerResponse {response_id} not found")

        record.action = action
        record.responded_at = datetime.now(timezone.utc)
        record.notes = notes

        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(record))
        logger.debug(
            "Marked engineer response %s as %s", response_id, action
        )
        return record

    async def update_slack_ts(self, response_id: str, slack_message_ts: str) -> None:
        """Updates the slack_message_ts field on an existing record."""
        record = await self.get(response_id)
        if record is None:
            logger.warning("EngineerResponse %s not found; cannot update slack ts", response_id)
            return
        record.slack_message_ts = slack_message_ts
        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(record))
        logger.debug("Updated slack_message_ts for response %s to %s", response_id, slack_message_ts)

    async def get_unanswered_older_than(self, hours: int) -> list[EngineerResponse]:
        """Returns pending responses where responded_at is None and
        created more than `hours` ago. Used for reminders."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        client = await self._get_client()
        results: list[EngineerResponse] = []
        async with client:
            async for entity in client.query_entities(
                f"PartitionKey eq '{_PARTITION_KEY}'"
            ):
                record = _from_entity(entity)
                if record.responded_at is None and record.created_at <= cutoff:
                    results.append(record)
        logger.debug(
            "Found %d unanswered engineer responses older than %d hours",
            len(results),
            hours,
        )
        return results
