from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from azure.data.tables.aio import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError

from agent.models import EmailClassification, RFQRecord, RFQStatus
from config.settings import settings
from config.rules import OPEN_STATUSES

logger = logging.getLogger(__name__)

_PARTITION_KEY = "rfq"


def _to_entity(rfq: RFQRecord) -> dict:
    data = rfq.model_dump()
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif hasattr(value, "isoformat"):  # date
            data[key] = value.isoformat()
        elif value is None:
            data[key] = ""
    data["PartitionKey"] = _PARTITION_KEY
    data["RowKey"] = rfq.rfq_id
    return data


def _from_entity(entity: dict) -> RFQRecord:
    data = dict(entity)
    data.pop("PartitionKey", None)
    data.pop("RowKey", None)

    for field in ("sent_at", "last_supplier_reply", "last_followup_sent",
                  "engineer_notified_at", "engineer_responded_at",
                  "created_at", "updated_at"):
        raw = data.get(field)
        if raw:
            data[field] = datetime.fromisoformat(raw)
        else:
            data[field] = None

    for field in ("delivery_date",):
        raw = data.get(field)
        if raw:
            from datetime import date
            data[field] = date.fromisoformat(raw)
        else:
            data[field] = None

    for field in ("supplier_name", "supplier_email", "subject", "thread_id",
                  "engineer_assigned", "po_number", "notes"):
        if data.get(field) == "":
            data[field] = None if field in ("engineer_assigned", "po_number") else data[field]

    data.setdefault("followup_count", 0)
    data.setdefault("priority_updated", False)
    return RFQRecord(**data)


class StateManager:
    def __init__(self):
        self._conn = settings.AZURE_STORAGE_CONNECTION_STRING
        self._table = settings.AZURE_TABLE_NAME

    async def _get_client(self):
        service = TableServiceClient.from_connection_string(self._conn)
        return service.get_table_client(self._table)

    async def get(self, rfq_id: str) -> Optional[RFQRecord]:
        client = await self._get_client()
        async with client:
            try:
                entity = await client.get_entity(_PARTITION_KEY, rfq_id)
                return _from_entity(entity)
            except ResourceNotFoundError:
                return None

    async def get_or_create(self, thread_id: str, email_data: dict) -> RFQRecord:
        # Try to find by thread_id first
        existing = await self._find_by_thread(thread_id)
        if existing:
            return existing

        rfq = RFQRecord(
            rfq_id=thread_id,
            supplier_name=email_data.get("supplier_name", "Unknown"),
            supplier_email=email_data.get("sender", ""),
            subject=email_data.get("subject", ""),
            thread_id=thread_id,
            status=RFQStatus.AWAITING_REPLY,
            sent_at=datetime.now(timezone.utc),
        )
        await self.upsert(rfq)
        return rfq

    async def _find_by_thread(self, thread_id: str) -> Optional[RFQRecord]:
        client = await self._get_client()
        async with client:
            try:
                entity = await client.get_entity(_PARTITION_KEY, thread_id)
                return _from_entity(entity)
            except ResourceNotFoundError:
                return None

    async def upsert(self, rfq: RFQRecord) -> None:
        rfq.updated_at = datetime.now(timezone.utc)
        client = await self._get_client()
        async with client:
            await client.upsert_entity(_to_entity(rfq))
        logger.debug("Upserted RFQ %s (status=%s)", rfq.rfq_id, rfq.status)

    async def update_from_classification(
        self, rfq: RFQRecord, classification: EmailClassification
    ) -> None:
        cls = classification.classification

        if cls == "supplier_quote_received":
            rfq.status = RFQStatus.SUPPLIER_REPLIED
            rfq.last_supplier_reply = datetime.now(timezone.utc)
            if classification.supplier_name:
                rfq.supplier_name = classification.supplier_name

        elif cls == "supplier_question":
            rfq.status = RFQStatus.SUPPLIER_REPLIED
            rfq.last_supplier_reply = datetime.now(timezone.utc)

        elif cls == "supplier_delivery_confirmed":
            rfq.status = RFQStatus.DELIVERY_CONFIRMED
            rfq.last_supplier_reply = datetime.now(timezone.utc)
            if classification.delivery_date:
                from datetime import date
                rfq.delivery_date = date.fromisoformat(classification.delivery_date)

        elif cls == "supplier_acknowledgment":
            rfq.last_supplier_reply = datetime.now(timezone.utc)

        elif cls == "engineer_response":
            rfq.status = RFQStatus.APPROVED
            rfq.engineer_responded_at = datetime.now(timezone.utc)

        await self.upsert(rfq)

    async def get_all_open(self) -> list[RFQRecord]:
        client = await self._get_client()
        filter_parts = " or ".join(f"status eq '{s}'" for s in OPEN_STATUSES)
        records = []
        async with client:
            async for entity in client.query_entities(
                f"PartitionKey eq '{_PARTITION_KEY}' and ({filter_parts})"
            ):
                records.append(_from_entity(entity))
        return records
