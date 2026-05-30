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


async def generate_followup_draft(
    rfq: RFQRecord,
    followup_number: int,
    followup_type: str = "standard",  # "standard" | "discussion_checkin" | "quote_reminder"
) -> str:
    if followup_type == "discussion_checkin":
        prompt = f"""You are a professional procurement assistant.
Write a polite check-in email to a supplier after a technical discussion has gone quiet.

RFQ Details:
- Supplier: {rfq.supplier_name}
- Subject: {rfq.subject}
- Follow-up number: {followup_number}

We've been having a productive technical discussion about {rfq.subject}. \
Just checking in to see if you need any further information from our side, \
or if you have an update on timing for the quote.

Rules:
- Professional but friendly tone
- Reference the ongoing technical discussion
- Keep it under 5 sentences
- Sign as "{settings.PROCUREMENT_NAME}"

Return only the email body text, no subject line."""

    elif followup_type == "quote_reminder":
        prompt = f"""You are a professional procurement assistant.
Write a polite follow-up email reminding a supplier to send a quote after a technical discussion.

RFQ Details:
- Supplier: {rfq.supplier_name}
- Subject: {rfq.subject}
- Follow-up number: {followup_number}

Following our recent technical discussion about {rfq.subject}, we wanted to follow up on the quote. \
Could you please let us know when we can expect to receive it?

Rules:
- Professional but friendly tone
- Reference the concluded technical discussion
- Keep it under 5 sentences
- Sign as "{settings.PROCUREMENT_NAME}"

Return only the email body text, no subject line."""

    else:
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
- Sign as "{settings.PROCUREMENT_NAME}"

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
