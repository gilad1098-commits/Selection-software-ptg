import json
import logging
import azure.functions as func
from integrations.graph_client import GraphClient
from agent.state_manager import StateManager
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    action = data.get("action")
    rfq_id = data.get("rfq_id")
    draft_id = data.get("draft_id")

    if not all([action, rfq_id, draft_id]):
        return func.HttpResponse("Missing required fields: action, rfq_id, draft_id", status_code=400)

    state_manager = StateManager()
    rfq = await state_manager.get(rfq_id)
    if rfq is None:
        return func.HttpResponse(f"RFQ {rfq_id} not found", status_code=404)

    if action == "send":
        graph = GraphClient()
        await graph.send_draft(draft_id)

        rfq.followup_count += 1
        rfq.last_followup_sent = datetime.now(timezone.utc)
        rfq.updated_at = datetime.now(timezone.utc)
        await state_manager.upsert(rfq)

        logger.info("Draft %s sent for RFQ %s (follow-up #%d)", draft_id, rfq_id, rfq.followup_count)
        return func.HttpResponse(json.dumps({"status": "sent"}), mimetype="application/json")

    elif action == "dismiss":
        logger.info("Draft %s dismissed for RFQ %s", draft_id, rfq_id)
        return func.HttpResponse(json.dumps({"status": "dismissed"}), mimetype="application/json")

    return func.HttpResponse(f"Unknown action: {action}", status_code=400)
