SUPPLIER_NO_REPLY_DAYS = 3
SUPPLIER_SECOND_FOLLOWUP_DAYS = 2
MAX_FOLLOWUPS = 3
ENGINEER_NO_REPLY_DAYS = 2
ENGINEER_REMINDER_HOURS = 48  # Hours before sending reminder if no button clicked
DISCUSSION_SILENCE_DAYS = 5   # Days of silence in a technical discussion before checking in

OPEN_STATUSES = {
    "sent",
    "awaiting_reply",
    "technical_discussion",
    "awaiting_quote",
    "supplier_replied",
    "engineer_review",
    "approved",
    "po_issued",
}
