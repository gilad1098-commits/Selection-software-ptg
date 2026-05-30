from __future__ import annotations

from datetime import datetime, timezone

from agent.models import Action, ActionType, RFQRecord, RFQStatus
from config.rules import (
    ENGINEER_NO_REPLY_DAYS,
    MAX_FOLLOWUPS,
    SUPPLIER_NO_REPLY_DAYS,
    SUPPLIER_SECOND_FOLLOWUP_DAYS,
)


def decide_action(rfq: RFQRecord) -> list[Action]:
    actions: list[Action] = []
    now = datetime.now(timezone.utc)

    # Rule 1: No supplier reply → draft follow-up (requires human approval)
    if rfq.status == RFQStatus.AWAITING_REPLY:
        days_since_sent = (now - rfq.sent_at).days
        days_since_last_followup = (
            (now - rfq.last_followup_sent).days
            if rfq.last_followup_sent
            else days_since_sent
        )
        threshold = (
            SUPPLIER_NO_REPLY_DAYS if rfq.followup_count == 0
            else SUPPLIER_SECOND_FOLLOWUP_DAYS
        )
        if days_since_last_followup >= threshold and rfq.followup_count < MAX_FOLLOWUPS:
            actions.append(Action(
                type=ActionType.DRAFT_SUPPLIER_FOLLOWUP,
                rfq_id=rfq.rfq_id,
                requires_approval=True,
                metadata={"followup_number": rfq.followup_count + 1},
            ))

    # Rule 2: Supplier replied → notify engineer (auto-send)
    if rfq.status == RFQStatus.SUPPLIER_REPLIED and not rfq.engineer_assigned:
        actions.append(Action(
            type=ActionType.NOTIFY_ENGINEER,
            rfq_id=rfq.rfq_id,
            requires_approval=False,
        ))

    # Rule 3: Engineer not responding → reminder (auto-send)
    if rfq.status == RFQStatus.ENGINEER_REVIEW and rfq.engineer_notified_at:
        days_waiting = (now - rfq.engineer_notified_at).days
        if days_waiting >= ENGINEER_NO_REPLY_DAYS:
            actions.append(Action(
                type=ActionType.ENGINEER_REMINDER,
                rfq_id=rfq.rfq_id,
                requires_approval=False,
            ))

    # Rule 4: Delivery date received → update Priority (auto)
    if rfq.delivery_date and not rfq.priority_updated:
        actions.append(Action(
            type=ActionType.UPDATE_PRIORITY_DUE_DATE,
            rfq_id=rfq.rfq_id,
            requires_approval=False,
        ))

    return actions
