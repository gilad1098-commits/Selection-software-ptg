"""Claude API integration for email classification and draft generation."""

import json
import os
from typing import Optional

import anthropic

# User explicitly requested this model for the pilot
MODEL = "claude-sonnet-4-20250514"

_client: Optional[anthropic.AsyncAnthropic] = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


async def classify_email(subject: str, body: str, sender: str) -> dict:
    """
    Classify an incoming supplier email.

    Returns a dict with:
      - classification: str
      - supplier_name: str | None
      - delivery_date: str | None  (ISO date)
      - requires_engineer: bool
      - summary: str
    """
    client = get_client()

    prompt = f"""You are analyzing an incoming supplier email for PTG USA procurement.

Sender: {sender}
Subject: {subject}
Body:
{body}

Classify this email and extract key information. Respond with ONLY valid JSON, no markdown fences:
{{
  "classification": "<one of: supplier_quote_received | supplier_question | supplier_delivery_confirmed | supplier_acknowledgment | other>",
  "supplier_name": "<extracted supplier company name or null>",
  "delivery_date": "<ISO date string YYYY-MM-DD if mentioned, otherwise null>",
  "requires_engineer": <true if the email contains a technical question needing engineering input, otherwise false>,
  "summary": "<2 sentences max summarizing the email>"
}}"""

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()

    result = json.loads(text)
    return result


async def generate_draft(
    rfq_dict: Optional[dict],
    email_subject: str,
    email_body: str,
    classification: str,
    requires_engineer: bool = False,
    supplier_name: str = "",
) -> str:
    """
    Generate a draft reply in Becky's writing style.

    Returns the email body only (no subject line).
    """
    client = get_client()

    # Determine the writing style instructions based on classification
    if classification == "supplier_question" and requires_engineer:
        style_hint = (
            "Write a brief reply saying you are checking with the engineering team. "
            "Use this exact structure: "
            "Thank them for their question, say you are checking with the engineering team "
            "and will get back to them shortly."
        )
    elif classification == "supplier_acknowledgment":
        style_hint = (
            "Write a brief acknowledgment reply thanking them and confirming you will "
            "follow up if anything else is needed."
        )
    elif classification == "supplier_quote_received":
        style_hint = (
            "Write a reply thanking them for their quote, and say that PTG USA will "
            "review the quote and get back to them with our decision."
        )
    else:
        style_hint = (
            "Write a professional follow-up email asking for an update on the quoted items."
        )

    rfq_context = ""
    if rfq_dict:
        rfq_context = f"""
RFQ Context:
- RFQ ID: {rfq_dict.get('rfq_id', 'N/A')}
- Subject: {rfq_dict.get('subject', 'N/A')}
- Follow-up count: {rfq_dict.get('followup_count', 0)}
"""

    name_to_use = supplier_name or (rfq_dict.get("supplier_name") if rfq_dict else "") or "there"

    prompt = f"""You are writing an email on behalf of Becky Amato, Procurement Specialist at PTG USA.

ORIGINAL EMAIL:
Subject: {email_subject}
Body:
{email_body}

{rfq_context}

BECKY'S WRITING STYLE RULES:
1. Opens with: "Hi [Name], I hope you've been well."
2. Body: Direct, professional, friendly, concise.
3. For follow-ups: "I'm just following up on [subject]. Can you please let me know [specific ask]?"
4. Always closes with exactly:
   With Best Regards,

   Becky Amato
   Procurement Specialist
   Mobile: (937) 608-7188
   PTG USA, Inc.
   becky@pachtaas.com | www.pachtaas.com

TASK: {style_hint}

The supplier's first name or company name to address is: {name_to_use}

Write ONLY the email body. Do not include a subject line. Do not include any preamble or explanation."""

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()
