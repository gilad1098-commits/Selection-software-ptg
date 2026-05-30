from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from datetime import datetime, timezone

import azure.functions as func

from agent.engineer_response_manager import EngineerResponseManager
from agent.models import EngineerAction, RFQStatus
from agent.state_manager import StateManager
from config.settings import settings
from integrations.graph_client import GraphClient
from integrations.slack_client import SlackClient

logger = logging.getLogger(__name__)

_SLACK_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


def _verify_slack_signature(req: func.HttpRequest) -> bool:
    """Verify Slack request via HMAC-SHA256.

    Slack signs requests as:
        v0=HMAC_SHA256(signing_secret, "v0:{timestamp}:{raw_body}")

    The header X-Slack-Signature contains "v0=<hex>".
    """
    signing_secret = settings.SLACK_SIGNING_SECRET
    if not signing_secret:
        logger.warning("SLACK_SIGNING_SECRET not configured; skipping signature check")
        return True

    slack_signature = req.headers.get("X-Slack-Signature", "")
    slack_timestamp = req.headers.get("X-Slack-Request-Timestamp", "")

    if not slack_signature or not slack_timestamp:
        logger.warning("Missing Slack signature headers")
        return False

    # Guard against replay attacks
    try:
        ts_int = int(slack_timestamp)
    except ValueError:
        logger.warning("Invalid X-Slack-Request-Timestamp: %s", slack_timestamp)
        return False

    if abs(time.time() - ts_int) > _SLACK_TIMESTAMP_TOLERANCE_SECONDS:
        logger.warning("Slack request timestamp too old: %s", slack_timestamp)
        return False

    body_bytes = req.get_body()
    sig_base = f"v0:{slack_timestamp}:{body_bytes.decode('utf-8')}".encode("utf-8")
    computed = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"), sig_base, hashlib.sha256
        ).hexdigest()
    )
    return hmac.compare_digest(computed, slack_signature)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    # 1. Verify Slack request signature
    if not _verify_slack_signature(req):
        return func.HttpResponse(
            json.dumps({"error": "Invalid Slack signature"}),
            status_code=401,
            mimetype="application/json",
        )

    # 2. Parse the payload — Slack sends as form field "payload" containing JSON
    try:
        body_str = req.get_body().decode("utf-8")
        parsed = urllib.parse.parse_qs(body_str)
        payload_str = parsed.get("payload", [None])[0]
        if payload_str is None:
            raise ValueError("Missing 'payload' field")
        payload = json.loads(payload_str)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse Slack payload: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": "Invalid payload"}),
            status_code=400,
            mimetype="application/json",
        )

    # 3. Extract fields
    try:
        actions_list = payload.get("actions", [])
        if not actions_list:
            return func.HttpResponse(
                json.dumps({"error": "No actions in payload"}),
                status_code=400,
                mimetype="application/json",
            )

        raw_action = actions_list[0]
        action_value = json.loads(raw_action["value"])
        response_id: str = action_value["response_id"]
        rfq_id: str = action_value["rfq_id"]
        action_str: str = action_value["action"]

        user_name: str = payload.get("user", {}).get("name", "unknown")
        message_ts: str = payload.get("message", {}).get("ts", "")
        channel_id: str = payload.get("channel", {}).get("id", "")
    except (KeyError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Malformed Slack action payload: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": "Malformed action payload"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        engineer_action = EngineerAction(action_str)
    except ValueError:
        logger.warning("Unknown engineer action: %s", action_str)
        return func.HttpResponse(
            json.dumps({"error": f"Unknown action: {action_str}"}),
            status_code=400,
            mimetype="application/json",
        )

    response_manager = EngineerResponseManager()
    state_manager = StateManager()
    slack_client = SlackClient()
    graph_client = GraphClient()

    # 4. Look up the EngineerResponse record
    eng_response = await response_manager.get(response_id)
    if eng_response is None:
        logger.warning("EngineerResponse %s not found", response_id)
        return func.HttpResponse(
            json.dumps({"error": f"Response {response_id} not found"}),
            status_code=404,
            mimetype="application/json",
        )

    # 5. Mark it as responded
    eng_response = await response_manager.mark_responded(response_id, engineer_action)

    # 6. Update RFQ status and notify Becky
    rfq = await state_manager.get(rfq_id)
    if rfq is None:
        logger.warning("RFQ %s not found", rfq_id)
        return func.HttpResponse(
            json.dumps({"error": f"RFQ {rfq_id} not found"}),
            status_code=404,
            mimetype="application/json",
        )

    engineer_name = eng_response.engineer_name

    if engineer_action == EngineerAction.APPROVED:
        rfq.status = RFQStatus.APPROVED
        rfq.engineer_responded_at = datetime.now(timezone.utc)
        await state_manager.upsert(rfq)

        # Notify Becky via email with draft info
        subject = f"[Engineer Approved] RFQ #{rfq_id} — {rfq.supplier_name}"
        body = (
            f"Engineer {engineer_name} has approved the supplier response for RFQ #{rfq_id}.\n\n"
            f"Supplier: {rfq.supplier_name}\n"
            f"Subject: {rfq.subject}\n\n"
            f"A reply draft is being prepared. You will receive it shortly for review."
        )
        await graph_client.send_internal_email(
            to=settings.USER_EMAIL,
            subject=subject,
            body=body,
        )
        logger.info("RFQ %s approved by %s; Becky notified", rfq_id, engineer_name)

    elif engineer_action == EngineerAction.NEEDS_INFO:
        # RFQ stays in ENGINEER_REVIEW; ask Becky for more info
        rfq.engineer_responded_at = datetime.now(timezone.utc)
        await state_manager.upsert(rfq)

        subject = f"[Info Needed] RFQ #{rfq_id} — {rfq.supplier_name}"
        body = (
            f"Engineer {engineer_name} needs additional information from you regarding "
            f"RFQ #{rfq_id} with {rfq.supplier_name}.\n\n"
            f"Subject: {rfq.subject}\n\n"
            f"Please provide the required technical details so {engineer_name} can complete "
            f"their review."
        )
        await graph_client.send_internal_email(
            to=settings.USER_EMAIL,
            subject=subject,
            body=body,
        )
        logger.info(
            "RFQ %s: engineer %s requested more info; Becky notified", rfq_id, engineer_name
        )

    elif engineer_action == EngineerAction.REJECTED:
        rfq.status = RFQStatus.CLOSED
        rfq.engineer_responded_at = datetime.now(timezone.utc)
        await state_manager.upsert(rfq)

        subject = f"[Rejected] RFQ #{rfq_id} — {rfq.supplier_name}"
        body = (
            f"Engineer {engineer_name} has rejected the request for RFQ #{rfq_id}.\n\n"
            f"Supplier: {rfq.supplier_name}\n"
            f"Subject: {rfq.subject}\n\n"
            f"The RFQ has been closed. No further action is required unless you wish to "
            f"escalate or seek an alternative supplier."
        )
        await graph_client.send_internal_email(
            to=settings.USER_EMAIL,
            subject=subject,
            body=body,
        )
        logger.info("RFQ %s rejected by %s; Becky notified", rfq_id, engineer_name)

    # 7. Update the Slack message — replace buttons with confirmation
    if channel_id and message_ts:
        await slack_client.update_message_after_action(
            channel=channel_id,
            message_ts=message_ts,
            engineer_name=engineer_name,
            action=engineer_action,
        )

    # 8. Return HTTP 200 immediately (Slack requires fast response)
    return func.HttpResponse(
        json.dumps({"status": "ok"}),
        status_code=200,
        mimetype="application/json",
    )
