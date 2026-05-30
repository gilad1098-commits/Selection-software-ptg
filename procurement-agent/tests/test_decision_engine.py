"""Unit tests for agent.decision_engine.decide_action.

No network I/O. All time is controlled via freezegun or manual offsets.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from agent.decision_engine import decide_action
from agent.models import Action, ActionType, RFQRecord, RFQStatus
from config.rules import (
    ENGINEER_NO_REPLY_DAYS,
    MAX_FOLLOWUPS,
    SUPPLIER_NO_REPLY_DAYS,
    SUPPLIER_SECOND_FOLLOWUP_DAYS,
)


def _base_rfq(**overrides) -> RFQRecord:
    """Factory for a minimal valid RFQRecord."""
    now = datetime.now(timezone.utc)
    defaults = dict(
        rfq_id="rfq-001",
        supplier_name="ACME",
        supplier_email="acme@example.com",
        subject="RFQ-001",
        thread_id="thread-001",
        status=RFQStatus.AWAITING_REPLY,
        sent_at=now,
        followup_count=0,
        priority_updated=False,
    )
    defaults.update(overrides)
    return RFQRecord(**defaults)


# ---------------------------------------------------------------------------
# Rule 1 — supplier follow-up
# ---------------------------------------------------------------------------

def test_awaiting_reply_4_days_triggers_followup():
    """RFQ awaiting reply for 4 days (≥ SUPPLIER_NO_REPLY_DAYS=3) → DRAFT_SUPPLIER_FOLLOWUP."""
    sent_at = datetime.now(timezone.utc) - timedelta(days=4)
    rfq = _base_rfq(status=RFQStatus.AWAITING_REPLY, sent_at=sent_at)

    actions = decide_action(rfq)

    assert len(actions) == 1
    assert actions[0].type == ActionType.DRAFT_SUPPLIER_FOLLOWUP
    assert actions[0].requires_approval is True
    assert actions[0].metadata["followup_number"] == 1


def test_awaiting_reply_1_day_no_action():
    """RFQ awaiting reply for only 1 day → no action (below threshold)."""
    sent_at = datetime.now(timezone.utc) - timedelta(days=1)
    rfq = _base_rfq(status=RFQStatus.AWAITING_REPLY, sent_at=sent_at)

    actions = decide_action(rfq)

    assert actions == []


def test_awaiting_reply_max_followups_no_action():
    """followup_count at MAX_FOLLOWUPS → no follow-up drafted even if threshold exceeded."""
    sent_at = datetime.now(timezone.utc) - timedelta(days=10)
    rfq = _base_rfq(
        status=RFQStatus.AWAITING_REPLY,
        sent_at=sent_at,
        followup_count=MAX_FOLLOWUPS,
    )

    actions = decide_action(rfq)

    followup_actions = [a for a in actions if a.type == ActionType.DRAFT_SUPPLIER_FOLLOWUP]
    assert followup_actions == []


def test_awaiting_reply_uses_last_followup_date_for_threshold():
    """After a first follow-up, threshold resets to SUPPLIER_SECOND_FOLLOWUP_DAYS."""
    now = datetime.now(timezone.utc)
    # Sent long ago, but last follow-up was only 1 day ago
    sent_at = now - timedelta(days=10)
    last_followup_sent = now - timedelta(days=1)
    rfq = _base_rfq(
        status=RFQStatus.AWAITING_REPLY,
        sent_at=sent_at,
        followup_count=1,
        last_followup_sent=last_followup_sent,
    )

    actions = decide_action(rfq)

    followup_actions = [a for a in actions if a.type == ActionType.DRAFT_SUPPLIER_FOLLOWUP]
    assert followup_actions == [], "Should not draft when last followup was too recent"


def test_awaiting_reply_second_followup_threshold_met():
    """After first follow-up, SUPPLIER_SECOND_FOLLOWUP_DAYS days later → follow-up #2."""
    now = datetime.now(timezone.utc)
    sent_at = now - timedelta(days=10)
    last_followup_sent = now - timedelta(days=SUPPLIER_SECOND_FOLLOWUP_DAYS + 1)
    rfq = _base_rfq(
        status=RFQStatus.AWAITING_REPLY,
        sent_at=sent_at,
        followup_count=1,
        last_followup_sent=last_followup_sent,
    )

    actions = decide_action(rfq)

    followup_actions = [a for a in actions if a.type == ActionType.DRAFT_SUPPLIER_FOLLOWUP]
    assert len(followup_actions) == 1
    assert followup_actions[0].metadata["followup_number"] == 2


# ---------------------------------------------------------------------------
# Rule 2 — notify engineer
# ---------------------------------------------------------------------------

def test_supplier_replied_no_engineer_assigned_triggers_notify():
    """Supplier replied, no engineer assigned → NOTIFY_ENGINEER."""
    rfq = _base_rfq(
        status=RFQStatus.SUPPLIER_REPLIED,
        sent_at=datetime.now(timezone.utc) - timedelta(days=5),
        engineer_assigned=None,
    )

    actions = decide_action(rfq)

    assert any(a.type == ActionType.NOTIFY_ENGINEER for a in actions)


def test_supplier_replied_engineer_already_assigned_no_notify():
    """Supplier replied, engineer already assigned → no NOTIFY_ENGINEER."""
    rfq = _base_rfq(
        status=RFQStatus.SUPPLIER_REPLIED,
        sent_at=datetime.now(timezone.utc) - timedelta(days=5),
        engineer_assigned="Denis",
    )

    actions = decide_action(rfq)

    assert not any(a.type == ActionType.NOTIFY_ENGINEER for a in actions)


# ---------------------------------------------------------------------------
# Rule 3 — engineer reminder
# ---------------------------------------------------------------------------

def test_engineer_review_3_days_no_reply_triggers_reminder():
    """Engineer notified 3 days ago (≥ ENGINEER_NO_REPLY_DAYS=2) → ENGINEER_REMINDER."""
    now = datetime.now(timezone.utc)
    rfq = _base_rfq(
        status=RFQStatus.ENGINEER_REVIEW,
        sent_at=now - timedelta(days=10),
        engineer_assigned="Denis",
        engineer_notified_at=now - timedelta(days=3),
    )

    actions = decide_action(rfq)

    assert any(a.type == ActionType.ENGINEER_REMINDER for a in actions)


def test_engineer_review_1_day_no_reminder():
    """Engineer notified only 1 day ago → no reminder yet."""
    now = datetime.now(timezone.utc)
    rfq = _base_rfq(
        status=RFQStatus.ENGINEER_REVIEW,
        sent_at=now - timedelta(days=10),
        engineer_assigned="Denis",
        engineer_notified_at=now - timedelta(days=1),
    )

    actions = decide_action(rfq)

    assert not any(a.type == ActionType.ENGINEER_REMINDER for a in actions)


# ---------------------------------------------------------------------------
# Rule 4 — update Priority due date
# ---------------------------------------------------------------------------

def test_delivery_date_set_priority_not_updated_triggers_update():
    """Delivery date confirmed, priority_updated = False → UPDATE_PRIORITY_DUE_DATE."""
    rfq = _base_rfq(
        status=RFQStatus.DELIVERY_CONFIRMED,
        sent_at=datetime.now(timezone.utc) - timedelta(days=5),
        delivery_date=date(2026, 7, 1),
        priority_updated=False,
    )

    actions = decide_action(rfq)

    assert any(a.type == ActionType.UPDATE_PRIORITY_DUE_DATE for a in actions)


def test_delivery_date_set_priority_already_updated_no_action():
    """priority_updated = True → no UPDATE_PRIORITY_DUE_DATE."""
    rfq = _base_rfq(
        status=RFQStatus.DELIVERY_CONFIRMED,
        sent_at=datetime.now(timezone.utc) - timedelta(days=5),
        delivery_date=date(2026, 7, 1),
        priority_updated=True,
    )

    actions = decide_action(rfq)

    assert not any(a.type == ActionType.UPDATE_PRIORITY_DUE_DATE for a in actions)


# ---------------------------------------------------------------------------
# Multiple rules at once
# ---------------------------------------------------------------------------

def test_multiple_rules_fire_simultaneously():
    """An RFQ in ENGINEER_REVIEW with delivery date can fire both
    ENGINEER_REMINDER and UPDATE_PRIORITY_DUE_DATE in the same scan."""
    now = datetime.now(timezone.utc)
    rfq = _base_rfq(
        status=RFQStatus.ENGINEER_REVIEW,
        sent_at=now - timedelta(days=15),
        engineer_assigned="Dmitri",
        engineer_notified_at=now - timedelta(days=ENGINEER_NO_REPLY_DAYS + 1),
        delivery_date=date(2026, 8, 15),
        priority_updated=False,
    )

    actions = decide_action(rfq)

    action_types = {a.type for a in actions}
    assert ActionType.ENGINEER_REMINDER in action_types
    assert ActionType.UPDATE_PRIORITY_DUE_DATE in action_types


def test_no_actions_for_fresh_awaiting_rfq():
    """Newly sent RFQ with no elapsed time → empty action list."""
    rfq = _base_rfq(
        status=RFQStatus.AWAITING_REPLY,
        sent_at=datetime.now(timezone.utc),
    )

    actions = decide_action(rfq)

    assert actions == []
