from __future__ import annotations

import logging

from slack_sdk.web.async_client import AsyncWebClient

from config.settings import settings

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self):
        self._client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)

    async def send_engineer_dm(
        self,
        engineer_slack_id: str,
        rfq_id: str,
        supplier_name: str,
        summary: str,
        requires_action: str,
    ) -> None:
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
