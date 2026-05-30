from __future__ import annotations

import logging
from datetime import datetime, timezone

from agent.draft_generator import generate_engineer_report, generate_followup_draft
from agent.models import Action, ActionType, RFQRecord
from agent.state_manager import StateManager
from config.settings import settings
from integrations.graph_client import GraphClient
from integrations.priority_client import PriorityClient
from integrations.slack_client import SlackClient

logger = logging.getLogger(__name__)


class ActionExecutor:
    def __init__(self):
        self._graph = GraphClient()
        self._slack = SlackClient()
        self._priority = PriorityClient()
        self._state = StateManager()

    async def execute(self, actions: list[Action], rfq: RFQRecord) -> None:
        for action in actions:
            try:
                await self._dispatch(action, rfq)
            except Exception:
                logger.exception("Failed to execute action %s for RFQ %s", action.type, rfq.rfq_id)

    async def _dispatch(self, action: Action, rfq: RFQRecord) -> None:
        if action.type == ActionType.DRAFT_SUPPLIER_FOLLOWUP:
            await self._draft_supplier_followup(action, rfq)

        elif action.type == ActionType.NOTIFY_ENGINEER:
            await self._notify_engineer(action, rfq)

        elif action.type == ActionType.ENGINEER_REMINDER:
            await self._engineer_reminder(action, rfq)

        elif action.type == ActionType.UPDATE_PRIORITY_DUE_DATE:
            await self._update_priority(action, rfq)

    async def _draft_supplier_followup(self, action: Action, rfq: RFQRecord) -> None:
        followup_number = action.metadata.get("followup_number", rfq.followup_count + 1)
        body = await generate_followup_draft(rfq, followup_number)
        subject = f"Re: {rfq.subject}"

        draft_id = await self._graph.create_draft(rfq.supplier_email, subject, body)

        # Notify the procurement user internally — no approval required for this message
        approval_link = f"{settings.SHAREPOINT_BASE_URL}/rfq/{rfq.rfq_id}"
        notification_body = (
            f"Follow-up draft ready for RFQ #{rfq.rfq_id} with {rfq.supplier_name}.\n\n"
            f"Preview:\n{body}\n\n"
            f"[View & Send] {approval_link}?action=send&draft_id={draft_id}\n"
            f"[Dismiss] {approval_link}?action=dismiss&draft_id={draft_id}"
        )
        await self._graph.send_internal_email(
            to=settings.USER_EMAIL,
            subject=f"[Approval Required] Follow-up #{followup_number} for {rfq.supplier_name}",
            body=notification_body,
        )
        logger.info("Draft %s created for RFQ %s follow-up #%d", draft_id, rfq.rfq_id, followup_number)

    async def _notify_engineer(self, action: Action, rfq: RFQRecord) -> None:
        # Pick the first available engineer; a real implementation would use routing logic
        engineer_map = settings.engineer_email_map
        slack_map = settings.engineer_slack_map
        if not engineer_map:
            logger.warning("No engineer email map configured")
            return

        engineer_name = next(iter(engineer_map))
        engineer_email = engineer_map[engineer_name]
        engineer_slack_id = slack_map.get(engineer_name)

        # Fetch thread for summary (empty list is safe — generator handles it)
        summary = await generate_engineer_report(rfq, [])

        if engineer_slack_id:
            await self._slack.send_engineer_dm(
                engineer_slack_id=engineer_slack_id,
                rfq_id=rfq.rfq_id,
                supplier_name=rfq.supplier_name,
                summary=summary,
                requires_action="Review supplier response and confirm technical specs",
            )

        await self._graph.send_internal_email(
            to=engineer_email,
            subject=f"[RFQ Review Needed] {rfq.subject} — {rfq.supplier_name}",
            body=summary,
        )

        rfq.engineer_assigned = engineer_name
        rfq.engineer_notified_at = datetime.now(timezone.utc)
        from agent.models import RFQStatus
        rfq.status = RFQStatus.ENGINEER_REVIEW
        await self._state.upsert(rfq)
        logger.info("Engineer %s notified for RFQ %s", engineer_name, rfq.rfq_id)

    async def _engineer_reminder(self, action: Action, rfq: RFQRecord) -> None:
        engineer_map = settings.engineer_email_map
        slack_map = settings.engineer_slack_map
        engineer_email = engineer_map.get(rfq.engineer_assigned or "")
        engineer_slack_id = slack_map.get(rfq.engineer_assigned or "")

        if engineer_slack_id:
            await self._slack.send_engineer_dm(
                engineer_slack_id=engineer_slack_id,
                rfq_id=rfq.rfq_id,
                supplier_name=rfq.supplier_name,
                summary=f"Reminder: RFQ #{rfq.rfq_id} from {rfq.supplier_name} is still awaiting your review.",
                requires_action="Please review and respond at your earliest convenience",
            )

        if engineer_email:
            await self._graph.send_internal_email(
                to=engineer_email,
                subject=f"[Reminder] RFQ Review Pending — {rfq.subject}",
                body=f"This is a reminder that RFQ #{rfq.rfq_id} from {rfq.supplier_name} is still awaiting your review.",
            )
        logger.info("Engineer reminder sent for RFQ %s", rfq.rfq_id)

    async def _update_priority(self, action: Action, rfq: RFQRecord) -> None:
        if not rfq.po_number or not rfq.delivery_date:
            logger.warning("Cannot update Priority for RFQ %s — missing PO number or delivery date", rfq.rfq_id)
            return

        success = await self._priority.update_due_date(rfq.po_number, rfq.delivery_date)
        if success:
            rfq.priority_updated = True
            await self._state.upsert(rfq)
            logger.info("Priority updated for RFQ %s PO %s", rfq.rfq_id, rfq.po_number)
        else:
            logger.error("Failed to update Priority for RFQ %s", rfq.rfq_id)
