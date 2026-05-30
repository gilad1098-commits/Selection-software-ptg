from __future__ import annotations

import json
import logging

from anthropic import AsyncAnthropic

from agent.models import EmailClassification
from config.settings import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """
You are a procurement email classifier. Analyze the email and return JSON only.

Classify into one of:
- rfq_sent: We sent an RFQ to a supplier
- supplier_quote_received: Supplier sent back a quote or price
- supplier_question: Supplier is asking ONE isolated question with no prior technical back-and-forth context
- technical_discussion: This message is part of an ongoing technical back-and-forth — both sides have been going back and forth, the supplier is answering a question or asking a follow-up technical question. Key signals: references to previous messages, technical specs being refined, "as we discussed", "to clarify", "following up on your question about X"
- discussion_concluded: Supplier signals the technical discussion is done and a price/quote is coming soon — e.g. "we have all the info we need, quote will follow", "I'll prepare the pricing now", "technically we can do this, sending quote shortly"
- supplier_delivery_confirmed: Supplier confirmed a delivery date
- supplier_acknowledgment: Supplier just confirmed receipt
- engineer_response: An engineer replied about a technical query
- other: None of the above

Also extract:
- supplier_name (string or null)
- delivery_date (ISO date string or null)
- requires_engineer (boolean — does this need technical review?)
- summary (max 2 sentences)

Return ONLY valid JSON, no explanation.
""".strip()

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def classify_email(subject: str, body: str, sender: str) -> EmailClassification:
    prompt = f"Subject: {subject}\nFrom: {sender}\n\nBody:\n{body[:3000]}"

    response = await _get_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=CLASSIFICATION_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse classifier response: %s", raw)
        raise ValueError(f"Classifier returned non-JSON: {raw!r}") from exc

    return EmailClassification(**data)
