"""Unit tests for the email classifier.

Each test mocks the Anthropic API so no real credentials are needed.
Run with: pytest tests/test_classifier.py -v
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.classifier import classify_email
from agent.models import EmailClassification


def _mock_response(payload: dict) -> MagicMock:
    """Build a fake Anthropic messages.create response."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [content_block]
    return response


# ---------------------------------------------------------------------------
# Sample 1: Supplier sends a price quote
# ---------------------------------------------------------------------------

QUOTE_EMAIL = {
    "subject": "Re: RFQ-2024-0042 — Hydraulic Pump Assembly",
    "sender": "sales@acme-hydraulics.com",
    "body": (
        "Dear Procurement Team,\n\n"
        "Thank you for your inquiry. We are pleased to offer the following:\n"
        "- Part #HPA-900: $1,250 per unit (MOQ 5)\n"
        "- Lead time: 6 weeks from confirmed PO\n"
        "- Delivery: DDP your warehouse\n\n"
        "Please let us know if you have any questions.\n\n"
        "Best regards,\nJohn Smith, ACME Hydraulics"
    ),
}

QUOTE_EXPECTED = {
    "classification": "supplier_quote_received",
    "supplier_name": "ACME Hydraulics",
    "delivery_date": None,
    "requires_engineer": False,
    "summary": "Supplier provided a price quote for Part #HPA-900 at $1,250/unit with 6-week lead time.",
}


# ---------------------------------------------------------------------------
# Sample 2: Supplier asks a technical question
# ---------------------------------------------------------------------------

QUESTION_EMAIL = {
    "subject": "Re: RFQ-2024-0043 — Control Valve Assembly",
    "sender": "engineering@valvetek.com",
    "body": (
        "Hello,\n\n"
        "We received your RFQ for the control valve assembly. Before we can provide a quote,\n"
        "could you confirm the operating pressure range and the fluid media?\n"
        "Our standard valve handles up to 150 PSI with water/oil. If higher pressure is required,\n"
        "we would need to spec a custom unit.\n\n"
        "Regards,\nValveTek Engineering"
    ),
}

QUESTION_EXPECTED = {
    "classification": "supplier_question",
    "supplier_name": "ValveTek",
    "delivery_date": None,
    "requires_engineer": True,
    "summary": "Supplier is asking for the operating pressure range and fluid media before they can quote.",
}


# ---------------------------------------------------------------------------
# Sample 3: Supplier confirms a delivery date
# ---------------------------------------------------------------------------

DELIVERY_EMAIL = {
    "subject": "Re: PO-5501 — Delivery Confirmation",
    "sender": "orders@precision-parts.co",
    "body": (
        "Hi,\n\n"
        "This is to confirm that your order (PO-5501) will be shipped on 2024-07-15.\n"
        "Expected delivery to your site: 2024-07-18.\n\n"
        "Tracking number will be provided upon dispatch.\n\n"
        "Thanks,\nPrecision Parts"
    ),
}

DELIVERY_EXPECTED = {
    "classification": "supplier_delivery_confirmed",
    "supplier_name": "Precision Parts",
    "delivery_date": "2024-07-18",
    "requires_engineer": False,
    "summary": "Supplier confirmed delivery of PO-5501 on 2024-07-18.",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_classify_supplier_quote():
    with patch("agent.classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_response(QUOTE_EXPECTED))
        mock_get_client.return_value = mock_client

        result = await classify_email(**QUOTE_EMAIL)

    assert isinstance(result, EmailClassification)
    assert result.classification == "supplier_quote_received"
    assert result.supplier_name == "ACME Hydraulics"
    assert result.delivery_date is None
    assert result.requires_engineer is False
    assert "quote" in result.summary.lower() or "price" in result.summary.lower()


@pytest.mark.asyncio
async def test_classify_supplier_question():
    with patch("agent.classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_response(QUESTION_EXPECTED))
        mock_get_client.return_value = mock_client

        result = await classify_email(**QUESTION_EMAIL)

    assert isinstance(result, EmailClassification)
    assert result.classification == "supplier_question"
    assert result.requires_engineer is True
    assert result.supplier_name == "ValveTek"


@pytest.mark.asyncio
async def test_classify_delivery_confirmed():
    with patch("agent.classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=_mock_response(DELIVERY_EXPECTED))
        mock_get_client.return_value = mock_client

        result = await classify_email(**DELIVERY_EMAIL)

    assert isinstance(result, EmailClassification)
    assert result.classification == "supplier_delivery_confirmed"
    assert result.delivery_date == "2024-07-18"
    assert result.supplier_name == "Precision Parts"


@pytest.mark.asyncio
async def test_classify_raises_on_invalid_json():
    with patch("agent.classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        bad_response = MagicMock()
        bad_response.content = [MagicMock(text="not json at all")]
        mock_client.messages.create = AsyncMock(return_value=bad_response)
        mock_get_client.return_value = mock_client

        with pytest.raises(ValueError, match="non-JSON"):
            await classify_email(
                subject="test", body="test body", sender="x@example.com"
            )
