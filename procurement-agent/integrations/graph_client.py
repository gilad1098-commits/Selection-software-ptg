from __future__ import annotations

import logging
from typing import Any

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody,
)

from config.settings import settings

logger = logging.getLogger(__name__)


class GraphClient:
    def __init__(self):
        self._credential = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET,
        )
        self._client = GraphServiceClient(
            self._credential,
            scopes=["https://graph.microsoft.com/.default"],
        )

    async def get_unread_rfq_emails(self, folder_id: str) -> list[Message]:
        result = await (
            self._client.users[settings.USER_EMAIL]
            .mail_folders[folder_id]
            .messages.get()
        )
        return [m for m in (result.value or []) if not m.is_read]

    async def create_draft(self, to: str, subject: str, body: str) -> str:
        draft = Message(
            subject=subject,
            body=ItemBody(content=body, content_type=BodyType.Text),
            to_recipients=[
                Recipient(email_address=EmailAddress(address=to))
            ],
        )
        result = await self._client.users[settings.USER_EMAIL].messages.post(draft)
        return result.id

    async def send_draft(self, draft_id: str) -> None:
        await (
            self._client.users[settings.USER_EMAIL]
            .messages[draft_id]
            .send.post()
        )
        logger.info("Draft %s sent", draft_id)

    async def send_internal_email(self, to: str, subject: str, body: str) -> None:
        message = Message(
            subject=subject,
            body=ItemBody(content=body, content_type=BodyType.Text),
            to_recipients=[
                Recipient(email_address=EmailAddress(address=to))
            ],
        )
        await self._client.users[settings.USER_EMAIL].send_mail.post(
            SendMailPostRequestBody(message=message, save_to_sent_items=True)
        )
        logger.info("Internal email sent to %s: %s", to, subject)
