from __future__ import annotations

import logging
from datetime import date

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


class PriorityClient:
    """Priority ERP REST API — updates Due Date on purchase orders."""

    @property
    def _auth(self) -> tuple[str, str]:
        return (settings.PRIORITY_USER, settings.PRIORITY_PASSWORD)

    async def update_due_date(self, po_number: str, due_date: date) -> bool:
        url = f"{settings.PRIORITY_BASE_URL}/PORDERS('{po_number}')"
        payload = {"DUEDATE": due_date.strftime("%Y-%m-%dT00:00:00+02:00")}

        async with httpx.AsyncClient() as client:
            response = await client.patch(
                url,
                json=payload,
                auth=self._auth,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code != 200:
            logger.error(
                "Priority update_due_date failed: status=%d body=%s",
                response.status_code,
                response.text[:500],
            )
        return response.status_code == 200

    async def get_open_orders_report(self) -> list[dict]:
        url = (
            f"{settings.PRIORITY_BASE_URL}/PORDERS"
            "?$filter=STATDES eq 'Open'"
            "&$select=PORDER,SUPNAME,DUEDATE,PARTNAME"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url, auth=self._auth)
            response.raise_for_status()
        return response.json().get("value", [])
