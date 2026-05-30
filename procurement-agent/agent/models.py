from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RFQStatus(str, Enum):
    SENT = "sent"
    AWAITING_REPLY = "awaiting_reply"
    TECHNICAL_DISCUSSION = "technical_discussion"   # Active back-and-forth with supplier
    AWAITING_QUOTE = "awaiting_quote"               # Tech resolved, waiting for price
    SUPPLIER_REPLIED = "supplier_replied"
    ENGINEER_REVIEW = "engineer_review"
    APPROVED = "approved"
    PO_ISSUED = "po_issued"
    DELIVERY_CONFIRMED = "delivery_confirmed"
    CLOSED = "closed"


class ActionType(str, Enum):
    DRAFT_SUPPLIER_FOLLOWUP = "draft_supplier_followup"
    NOTIFY_ENGINEER = "notify_engineer"
    ENGINEER_REMINDER = "engineer_reminder"
    UPDATE_PRIORITY_DUE_DATE = "update_priority_due_date"


class Action(BaseModel):
    type: ActionType
    rfq_id: str
    requires_approval: bool = False
    metadata: dict = Field(default_factory=dict)


class RFQRecord(BaseModel):
    rfq_id: str
    supplier_name: str
    supplier_email: str
    subject: str
    thread_id: str
    status: RFQStatus = RFQStatus.AWAITING_REPLY
    sent_at: datetime
    last_supplier_reply: Optional[datetime] = None
    last_followup_sent: Optional[datetime] = None
    followup_count: int = 0
    engineer_assigned: Optional[str] = None
    engineer_notified_at: Optional[datetime] = None
    engineer_responded_at: Optional[datetime] = None
    priority_updated: bool = False
    delivery_date: Optional[date] = None
    po_number: Optional[str] = None
    notes: str = ""
    last_activity_at: Optional[datetime] = None   # Last any email in thread (either direction)
    discussion_message_count: int = 0             # Count of back-and-forth messages in current discussion
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"use_enum_values": True}


class EmailClassification(BaseModel):
    classification: str
    supplier_name: Optional[str] = None
    delivery_date: Optional[str] = None
    requires_engineer: bool = False
    summary: str = ""


class EngineerAction(str, Enum):
    APPROVED = "approved"
    NEEDS_INFO = "needs_info"
    REJECTED = "rejected"


class EngineerResponse(BaseModel):
    response_id: str
    rfq_id: str
    engineer_name: str
    action: Optional[EngineerAction] = None
    slack_message_ts: str
    responded_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""

    model_config = {"use_enum_values": True}


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ApprovalRecord(BaseModel):
    approval_id: str
    rfq_id: str
    draft_id: str
    draft_body: str
    followup_number: int
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime
    actioned_at: Optional[datetime] = None

    model_config = {"use_enum_values": True}
