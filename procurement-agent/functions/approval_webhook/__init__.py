from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import azure.functions as func

from agent.approval_manager import ApprovalManager
from agent.state_manager import StateManager
from config.settings import settings
from integrations.graph_client import GraphClient

logger = logging.getLogger(__name__)


def _verify_hmac_signature(req: func.HttpRequest) -> bool:
    """Validate the X-PTG-Signature HMAC-SHA256 header against the raw request body."""
    secret = settings.WEBHOOK_SECRET
    if not secret:
        logger.warning("WEBHOOK_SECRET is not configured; skipping signature check")
        return True

    signature_header = req.headers.get("X-PTG-Signature", "")
    if not signature_header:
        logger.warning("Missing X-PTG-Signature header")
        return False

    # Accept "sha256=<hex>" or plain hex
    if signature_header.startswith("sha256="):
        provided_sig = signature_header[len("sha256="):]
    else:
        provided_sig = signature_header

    body_bytes = req.get_body()
    expected_sig = hmac.new(
        secret.encode("utf-8"), body_bytes, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, provided_sig)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    # --- HMAC validation ---
    if not _verify_hmac_signature(req):
        return func.HttpResponse(
            json.dumps({"error": "Invalid signature"}),
            status_code=401,
            mimetype="application/json",
        )

    # --- Parse body ---
    try:
        data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    action = data.get("action")
    approval_id = data.get("approval_id")
    rfq_id = data.get("rfq_id")

    if not action:
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: action"}),
            status_code=400,
            mimetype="application/json",
        )

    approval_manager = ApprovalManager()
    state_manager = StateManager()

    # --- "send" ---
    if action == "send":
        if not approval_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required field: approval_id"}),
                status_code=400,
                mimetype="application/json",
            )

        approval = await approval_manager.get_pending(approval_id)
        if approval is None:
            return func.HttpResponse(
                json.dumps({"error": f"Approval {approval_id} not found"}),
                status_code=404,
                mimetype="application/json",
            )

        rfq = await state_manager.get(approval.rfq_id)
        if rfq is None:
            return func.HttpResponse(
                json.dumps({"error": f"RFQ {approval.rfq_id} not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Send the Outlook draft
        graph = GraphClient()
        await graph.send_draft(approval.draft_id)

        # Update ApprovalRecord
        await approval_manager.mark_actioned(approval_id, "sent")

        # Update RFQRecord
        rfq.followup_count += 1
        rfq.last_followup_sent = datetime.now(timezone.utc)
        await state_manager.upsert(rfq)

        logger.info(
            "Approval %s: draft %s sent for RFQ %s (follow-up #%d)",
            approval_id,
            approval.draft_id,
            rfq.rfq_id,
            rfq.followup_count,
        )
        return func.HttpResponse(
            json.dumps({"status": "sent", "approval_id": approval_id}),
            status_code=200,
            mimetype="application/json",
        )

    # --- "dismiss" ---
    elif action == "dismiss":
        if not approval_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required field: approval_id"}),
                status_code=400,
                mimetype="application/json",
            )

        approval = await approval_manager.get_pending(approval_id)
        if approval is None:
            return func.HttpResponse(
                json.dumps({"error": f"Approval {approval_id} not found"}),
                status_code=404,
                mimetype="application/json",
            )

        rfq = await state_manager.get(approval.rfq_id)
        if rfq is None:
            return func.HttpResponse(
                json.dumps({"error": f"RFQ {approval.rfq_id} not found"}),
                status_code=404,
                mimetype="application/json",
            )

        await approval_manager.mark_actioned(approval_id, "dismissed")

        # Add a note to the RFQ
        note = f"[{datetime.now(timezone.utc).isoformat()}] Follow-up #{approval.followup_number} draft dismissed."
        rfq.notes = (rfq.notes + "\n" + note).strip()
        await state_manager.upsert(rfq)

        logger.info(
            "Approval %s dismissed for RFQ %s (follow-up #%d)",
            approval_id,
            rfq.rfq_id,
            approval.followup_number,
        )
        return func.HttpResponse(
            json.dumps({"status": "dismissed", "approval_id": approval_id}),
            status_code=200,
            mimetype="application/json",
        )

    # --- "expired" (internal signal from daily_scan / retry_manager) ---
    elif action == "expired":
        if not approval_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required field: approval_id"}),
                status_code=400,
                mimetype="application/json",
            )

        await approval_manager.mark_expired(approval_id)
        logger.info("Approval %s marked as expired", approval_id)
        return func.HttpResponse(
            json.dumps({"status": "expired", "approval_id": approval_id}),
            status_code=200,
            mimetype="application/json",
        )

    # --- Unknown action ---
    return func.HttpResponse(
        json.dumps({"error": f"Unknown action: {action}"}),
        status_code=400,
        mimetype="application/json",
    )
