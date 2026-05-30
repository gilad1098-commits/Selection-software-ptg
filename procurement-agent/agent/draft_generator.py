from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from agent.models import RFQRecord
from config.settings import settings

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def generate_followup_draft(rfq: RFQRecord, followup_number: int) -> str:
    prompt = f"""You are a professional procurement assistant.
Write a polite follow-up email to a supplier who has not responded to our RFQ.

RFQ Details:
- Supplier: {rfq.supplier_name}
- Original subject: {rfq.subject}
- Sent: {rfq.sent_at.strftime('%B %d, %Y')}
- Follow-up number: {followup_number}

Rules:
- Professional but friendly tone
- Reference the original RFQ subject
- Ask for confirmation of receipt OR a timeline for their quote
- Keep it under 5 sentences
- Do NOT mention urgency aggressively on first follow-up
- Sign as "Procurement Team"

Return only the email body text, no subject line."""

    response = await _get_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def generate_engineer_report(rfq: RFQRecord, email_thread: list[dict]) -> str:
    thread_text = "\n---\n".join(
        f"From: {e['sender']}\nDate: {e['date']}\n{e['body'][:1000]}"
        for e in email_thread
    )

    prompt = f"""You are a procurement assistant summarizing an RFQ thread for an engineer.

Supplier: {rfq.supplier_name}
Subject: {rfq.subject}

Email thread:
{thread_text}

Write a concise summary report (max 150 words) that includes:
1. What the supplier sent/asked
2. Specific technical items the engineer needs to review or approve
3. Any delivery dates or lead times mentioned

Format as plain text, no bullet points."""

    response = await _get_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
