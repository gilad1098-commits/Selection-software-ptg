from __future__ import annotations

import json
import logging

from slack_sdk.web.async_client import AsyncWebClient

from agent.models import EngineerAction
from config.settings import settings

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self):
        self._client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)

    async def send_engineer_notification(
        self,
        engineer_slack_id: str,
        rfq_id: str,
        response_id: str,
        supplier_name: str,
        summary: str,
        requires_action: str,
    ) -> str:
        """Sends the interactive message. Returns the Slack message timestamp (ts)."""

        def _btn_value(action: str) -> str:
            return json.dumps(
                {"response_id": response_id, "rfq_id": rfq_id, "action": action}
            )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"RFQ Review Required — {supplier_name}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Action needed:* {requires_action}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approved", "emoji": True},
                        "style": "primary",
                        "value": _btn_value(EngineerAction.APPROVED),
                        "action_id": "engineer_approved",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Needs Info", "emoji": True},
                        "value": _btn_value(EngineerAction.NEEDS_INFO),
                        "action_id": "engineer_needs_info",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Rejected", "emoji": True},
                        "style": "danger",
                        "value": _btn_value(EngineerAction.REJECTED),
                        "action_id": "engineer_rejected",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"RFQ ID: `{rfq_id}`",
                    }
                ],
            },
        ]

        response = await self._client.chat_postMessage(
            channel=engineer_slack_id, blocks=blocks
        )
        ts: str = response["ts"]
        logger.info(
            "Slack interactive notification sent to %s for RFQ %s (ts=%s)",
            engineer_slack_id,
            rfq_id,
            ts,
        )
        return ts

    async def update_message_after_action(
        self,
        channel: str,
        message_ts: str,
        engineer_name: str,
        action: EngineerAction,
    ) -> None:
        """Replaces the buttons with a confirmation after engineer clicks."""
        action_labels = {
            EngineerAction.APPROVED: "✅ אישרת — טיוטה נשלחה ל-Becky",
            EngineerAction.NEEDS_INFO: "❓ ביקשת מידע נוסף מ-Becky",
            EngineerAction.REJECTED: "❌ דחית את הבקשה",
        }
        # Normalise: EngineerAction enum members or plain string values both work
        if isinstance(action, str):
            action = EngineerAction(action)

        label = action_labels.get(action, str(action))

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{engineer_name}* responded:\n{label}",
                },
            }
        ]

        await self._client.chat_update(
            channel=channel,
            ts=message_ts,
            blocks=blocks,
            text=f"{engineer_name}: {label}",
        )
        logger.info(
            "Slack message %s in %s updated after action %s by %s",
            message_ts,
            channel,
            action,
            engineer_name,
        )

    # ------------------------------------------------------------------
    # Legacy helper kept for backwards-compat with existing reminder code
    # ------------------------------------------------------------------

    async def send_engineer_dm(
        self,
        engineer_slack_id: str,
        rfq_id: str,
        supplier_name: str,
        summary: str,
        requires_action: str,
    ) -> None:
        """Simple DM without interactive buttons (used for reminders)."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*RFQ Follow-up Required* — {supplier_name}\n\n{summary}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Action needed:* {requires_action}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View thread"},
                        "url": f"{settings.SHAREPOINT_BASE_URL}/rfq/{rfq_id}",
                    }
                ],
            },
        ]
        await self._client.chat_postMessage(channel=engineer_slack_id, blocks=blocks)
        logger.info("Slack DM sent to %s for RFQ %s", engineer_slack_id, rfq_id)
