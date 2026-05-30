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


# ---------------------------------------------------------------------------
# Sample 4: Technical discussion — ongoing back-and-forth
# ---------------------------------------------------------------------------

TECH_DISCUSSION_EMAIL = {
    "subject": "Re: RFQ-2024-0044 — Custom Bearing Assembly",
    "sender": "tech@bearing-specialists.com",
    "body": (
        "Hi,\n\n"
        "Following up on your question about the load rating — as we discussed, "
        "the standard grade handles up to 12 kN radial load. "
        "To clarify from our last exchange, the temperature range you specified (up to 180°C) "
        "will require the ceramic variant we mentioned. "
        "Could you confirm whether the shaft diameter we discussed (42mm) is still the target?\n\n"
        "Best,\nBearing Specialists Tech Team"
    ),
}

TECH_DISCUSSION_EXPECTED = {
    "classification": "technical_discussion",
    "supplier_name": "Bearing Specialists",
    "delivery_date": None,
    "requires_engineer": True,
    "summary": "Supplier is continuing the technical discussion, confirming specs and asking a follow-up question about shaft diameter.",
}


# ---------------------------------------------------------------------------
# Sample 5: Discussion concluded — supplier says quote is coming
# ---------------------------------------------------------------------------

DISCUSSION_CONCLUDED_EMAIL = {
    "subject": "Re: RFQ-2024-0044 — Custom Bearing Assembly",
    "sender": "tech@bearing-specialists.com",
    "body": (
        "Hi,\n\n"
        "We now have all the technical information we need from your side. "
        "Technically we can meet your requirements with the ceramic variant. "
        "I'll prepare the pricing now and send the formal quote by end of week.\n\n"
        "Best,\nBearing Specialists"
    ),
}

DISCUSSION_CONCLUDED_EXPECTED = {
    "classification": "discussion_concluded",
    "supplier_name": "Bearing Specialists",
    "delivery_date": None,
    "requires_engineer": False,
    "summary": "Supplier has all needed info and will send the quote by end of week.",
}


# ---------------------------------------------------------------------------
# New classification tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_classify_technical_discussion():
    """Email referencing prior specs exchange is classified as technical_discussion."""
    with patch("agent.classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(TECH_DISCUSSION_EXPECTED)
        )
        mock_get_client.return_value = mock_client

        result = await classify_email(**TECH_DISCUSSION_EMAIL)

    assert isinstance(result, EmailClassification)
    assert result.classification == "technical_discussion"
    assert result.requires_engineer is True
    assert result.supplier_name == "Bearing Specialists"


@pytest.mark.asyncio
async def test_classify_discussion_concluded():
    """Email saying 'quote coming shortly' is classified as discussion_concluded."""
    with patch("agent.classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(DISCUSSION_CONCLUDED_EXPECTED)
        )
        mock_get_client.return_value = mock_client

        result = await classify_email(**DISCUSSION_CONCLUDED_EMAIL)

    assert isinstance(result, EmailClassification)
    assert result.classification == "discussion_concluded"
    assert result.supplier_name == "Bearing Specialists"
    assert result.delivery_date is None
