import json
import logging
import azure.functions as func
from agent.classifier import classify_email
from agent.state_manager import StateManager
from agent.decision_engine import decide_action
from agent.action_executor import ActionExecutor

logger = logging.getLogger(__name__)


async def main(msg: func.ServiceBusMessage):
    email_data = json.loads(msg.get_body().decode())

    classification = await classify_email(
        subject=email_data["subject"],
        body=email_data["body"],
        sender=email_data["sender"],
    )

    state_manager = StateManager()
    rfq = await state_manager.get_or_create(email_data["thread_id"], email_data)
    await state_manager.update_from_classification(rfq, classification)

    actions = decide_action(rfq)
    executor = ActionExecutor()
    await executor.execute(actions, rfq)

    logger.info("Processed email for thread %s — %d actions", email_data["thread_id"], len(actions))
