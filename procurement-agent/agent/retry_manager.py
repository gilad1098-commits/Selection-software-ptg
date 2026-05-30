from __future__ import annotations

import logging

from agent.approval_manager import ApprovalManager
from agent.models import ApprovalStatus

logger = logging.getLogger(__name__)


class RetryManager:
    """Handles approvals that were never actioned within the 48-hour window.

    Called by the daily_scan function. Finds expired pending approvals,
    marks them as expired, and re-queues the follow-up action so a fresh
    draft is created in the next cycle.
    """

    def __init__(self):
        self._approval_manager = ApprovalManager()

    async def process_expired_approvals(self) -> None:
        """Find all pending approvals past their expiry and re-queue them.

        For each expired approval we:
        1. Mark the ApprovalRecord status = EXPIRED.
        2. Log the event so ops can audit it.

        The next daily_scan run will re-evaluate the parent RFQ via decide_action()
        and generate a fresh draft because followup_count has not been incremented
        (the email was never sent), so the threshold check will fire again.
        """
        expired = await self._approval_manager.get_expired_pending()

        if not expired:
            logger.info("RetryManager: no expired approvals found")
            return

        logger.info("RetryManager: processing %d expired approval(s)", len(expired))

        for record in expired:
            try:
                await self._approval_manager.mark_expired(record.approval_id)
                logger.warning(
                    "Approval %s expired without action — RFQ %s follow-up #%d "
                    "will be re-queued on next scan cycle.",
                    record.approval_id,
                    record.rfq_id,
                    record.followup_number,
                )
            except Exception:
                logger.exception(
                    "Failed to mark approval %s as expired", record.approval_id
                )
