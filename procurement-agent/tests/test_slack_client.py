"""Unit tests for integrations.slack_client.SlackClient.

AsyncWebClient is fully mocked — no real Slack credentials required.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.models import EngineerAction
from integrations.slack_client import SlackClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(post_return: dict | None = None, update_return: dict | None = None):
    """Build a SlackClient whose underlying AsyncWebClient is mocked."""
    mock_web = MagicMock()
    mock_web.chat_postMessage = AsyncMock(
        return_value=post_return or {"ok": True, "ts": "123.456"}
    )
    mock_web.chat_update = AsyncMock(
        return_value=update_return or {"ok": True}
    )

    with patch("integrations.slack_client.AsyncWebClient", return_value=mock_web):
        client = SlackClient()

    # Expose the mock so tests can inspect calls
    client._client = mock_web
    return client


def _get_actions_block(blocks: list) -> dict:
    """Return the 'actions' block from a list of blocks."""
    for block in blocks:
        if block.get("type") == "actions":
            return block
    raise AssertionError("No 'actions' block found in blocks")


def _get_buttons(blocks: list) -> list:
    return _get_actions_block(blocks)["elements"]


# ---------------------------------------------------------------------------
# Tests: send_engineer_notification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_engineer_notification_returns_ts():
    client = _make_client(post_return={"ok": True, "ts": "123.456"})

    ts = await client.send_engineer_notification(
        engineer_slack_id="U012AB345",
        rfq_id="rfq-001",
        response_id="resp-uuid-1",
        supplier_name="AcmeCorp",
        summary="Supplier asked about specs.",
        requires_action="Review and confirm",
    )

    assert ts == "123.456"
    client._client.chat_postMessage.assert_called_once()


@pytest.mark.asyncio
async def test_send_engineer_notification_blocks_contain_buttons():
    client = _make_client()

    await client.send_engineer_notification(
        engineer_slack_id="U012AB345",
        rfq_id="rfq-001",
        response_id="resp-uuid-1",
        supplier_name="AcmeCorp",
        summary="Supplier asked about specs.",
        requires_action="Review and confirm",
    )

    call_kwargs = client._client.chat_postMessage.call_args
    blocks = call_kwargs.kwargs.get("blocks") or call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs["blocks"]
    # chat_postMessage is called with keyword args
    blocks = client._client.chat_postMessage.call_args.kwargs["blocks"]

    buttons = _get_buttons(blocks)
    assert len(buttons) == 3, f"Expected 3 buttons, got {len(buttons)}"


@pytest.mark.asyncio
async def test_send_engineer_notification_button_values_are_valid_json():
    client = _make_client()

    rfq_id = "rfq-042"
    response_id = "resp-uuid-42"

    await client.send_engineer_notification(
        engineer_slack_id="U012AB345",
        rfq_id=rfq_id,
        response_id=response_id,
        supplier_name="AcmeCorp",
        summary="Supplier asked about specs.",
        requires_action="Review and confirm",
    )

    blocks = client._client.chat_postMessage.call_args.kwargs["blocks"]
    buttons = _get_buttons(blocks)

    for btn in buttons:
        value_str = btn["value"]
        parsed = json.loads(value_str)  # must not raise
        assert parsed["rfq_id"] == rfq_id
        assert parsed["response_id"] == response_id
        assert parsed["action"] in (
            EngineerAction.APPROVED,
            EngineerAction.NEEDS_INFO,
            EngineerAction.REJECTED,
        )


@pytest.mark.asyncio
async def test_send_engineer_notification_button_styles():
    """approved → primary, rejected → danger, needs_info → no style key."""
    client = _make_client()

    await client.send_engineer_notification(
        engineer_slack_id="U012AB345",
        rfq_id="rfq-001",
        response_id="resp-uuid-1",
        supplier_name="AcmeCorp",
        summary="Summary text.",
        requires_action="Do something",
    )

    blocks = client._client.chat_postMessage.call_args.kwargs["blocks"]
    buttons = _get_buttons(blocks)

    # Map action → button
    by_action: dict[str, dict] = {}
    for btn in buttons:
        parsed = json.loads(btn["value"])
        by_action[parsed["action"]] = btn

    assert by_action[EngineerAction.APPROVED]["style"] == "primary"
    assert by_action[EngineerAction.REJECTED]["style"] == "danger"
    # needs_info should not have a danger or primary style
    assert by_action[EngineerAction.NEEDS_INFO].get("style") not in ("primary", "danger")


# ---------------------------------------------------------------------------
# Tests: update_message_after_action
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_message_after_action_approved():
    client = _make_client()

    await client.update_message_after_action(
        channel="C01ABC",
        message_ts="123.456",
        engineer_name="Denis",
        action=EngineerAction.APPROVED,
    )

    client._client.chat_update.assert_called_once()
    call_kwargs = client._client.chat_update.call_args.kwargs
    assert call_kwargs["channel"] == "C01ABC"
    assert call_kwargs["ts"] == "123.456"
    # Must have replaced the buttons (no 'actions' block in the updated message)
    for block in call_kwargs["blocks"]:
        assert block.get("type") != "actions"
    # Confirmation text must be present
    text_parts = " ".join(
        block.get("text", {}).get("text", "")
        for block in call_kwargs["blocks"]
        if block.get("type") == "section"
    )
    assert "Denis" in text_parts or "Denis" in call_kwargs.get("text", "")


@pytest.mark.asyncio
async def test_update_message_after_action_rejected():
    client = _make_client()

    await client.update_message_after_action(
        channel="C01ABC",
        message_ts="789.012",
        engineer_name="Dmitri",
        action=EngineerAction.REJECTED,
    )

    client._client.chat_update.assert_called_once()
    call_kwargs = client._client.chat_update.call_args.kwargs
    assert call_kwargs["ts"] == "789.012"
    for block in call_kwargs["blocks"]:
        assert block.get("type") != "actions"


@pytest.mark.asyncio
async def test_update_message_after_action_needs_info():
    client = _make_client()

    await client.update_message_after_action(
        channel="C02XYZ",
        message_ts="555.666",
        engineer_name="Denis",
        action=EngineerAction.NEEDS_INFO,
    )

    client._client.chat_update.assert_called_once()
    call_kwargs = client._client.chat_update.call_args.kwargs
    assert call_kwargs["ts"] == "555.666"


@pytest.mark.asyncio
async def test_update_message_after_action_accepts_string_action():
    """update_message_after_action should also accept plain string action values."""
    client = _make_client()

    # Pass a plain string instead of the enum
    await client.update_message_after_action(
        channel="C01ABC",
        message_ts="123.456",
        engineer_name="Denis",
        action="approved",  # type: ignore[arg-type]
    )

    client._client.chat_update.assert_called_once()
