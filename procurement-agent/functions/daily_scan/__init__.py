import logging
import azure.functions as func
from agent.state_manager import StateManager
from agent.decision_engine import decide_action
from agent.action_executor import ActionExecutor
from agent.retry_manager import RetryManager

logger = logging.getLogger(__name__)


async def main(timer: func.TimerRequest):
    if timer.past_due:
        logger.warning("Daily scan timer is past due")

    state_manager = StateManager()
    open_rfqs = await state_manager.get_all_open()

    logger.info("Daily scan: processing %d open RFQs", len(open_rfqs))

    executor = ActionExecutor()
    for rfq in open_rfqs:
        actions = decide_action(rfq)
        if actions:
            await executor.execute(actions, rfq)

    # Process any approvals that expired without being actioned
    retry_manager = RetryManager()
    await retry_manager.process_expired_approvals()
