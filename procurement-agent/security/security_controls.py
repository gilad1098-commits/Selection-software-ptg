"""
PTG Procurement Agent — Security Controls
==========================================
Implements defensive controls identified in security/threat_model.md.
All functions use stdlib only (hmac, hashlib, re, logging, time, asyncio).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import re
import time
from collections import defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Control 1: HMAC Webhook Signature Validation
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validates X-PTG-Signature header using HMAC-SHA256.

    The expected signature format is: ``sha256=<hex_digest>``

    Args:
        payload:   Raw request body bytes.
        signature: Value of the ``X-PTG-Signature`` header from the request.
        secret:    Shared HMAC secret (from Azure Key Vault / env var).

    Returns:
        True if the signature is valid, False otherwise.
    """
    if not signature or not secret:
        logger.warning("verify_webhook_signature: missing signature or secret")
        return False

    # Accept both "sha256=<hex>" and bare hex for flexibility
    if signature.startswith("sha256="):
        provided_hex = signature[len("sha256="):]
    else:
        provided_hex = signature

    expected_mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    valid = hmac.compare_digest(expected_mac, provided_hex)
    if not valid:
        logger.warning("Webhook signature mismatch — possible tampering or wrong secret")
    return valid


# ---------------------------------------------------------------------------
# Control 2: Prompt Injection Guard
# ---------------------------------------------------------------------------

# Patterns that indicate attempted prompt injection.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(system|assistant|human)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"<\s*/?instructions?\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[\/INST\]", re.IGNORECASE),
    re.compile(r"###\s*(instruction|prompt|system)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"print\s+(your\s+)?(system\s+)?prompt", re.IGNORECASE),
]


def sanitize_email_for_prompt(body: str, max_length: int = 3000) -> str:
    """Strips prompt injection attempts from email body before sending to Claude.

    Removes lines or fragments matching known injection patterns:
      - Lines starting with ``System:``, ``Assistant:``, ``Human:``
      - Phrases like "Ignore previous instructions"
      - Jailbreak markers such as ``[INST]``, ``<instructions>``, ``###System``

    The result is truncated to *max_length* characters.

    Args:
        body:       Raw email body text.
        max_length: Maximum number of characters to pass to the LLM.

    Returns:
        Sanitised, truncated body string.
    """
    if not body:
        return ""

    sanitized = body

    # Remove entire lines that begin with role-like prefixes
    sanitized = re.sub(
        r"^\s*(system|assistant|human)\s*:.*$",
        "[REDACTED]",
        sanitized,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # Replace inline injection attempts with a placeholder
    for pattern in _INJECTION_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)

    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "\n[... truncated for security ...]"

    return sanitized


# ---------------------------------------------------------------------------
# Control 3: Rate Limiter for Claude API Calls
# ---------------------------------------------------------------------------

class RateLimiter:
    """Prevents runaway API usage. Tracks call counts per key in a sliding window.

    Usage::

        limiter = RateLimiter(max_calls=100, window_seconds=3600)
        allowed = await limiter.check("classify_email")
        if not allowed:
            raise RuntimeError("Rate limit exceeded")

    The implementation is in-process only (suitable for single-instance Azure Functions).
    For multi-instance deployments, replace the in-memory store with Azure Cache for Redis.
    """

    def __init__(self, max_calls: int = 100, window_seconds: int = 3600) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        # key -> list of call timestamps (epoch float)
        self._calls: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        """Return False (and log a warning) if the rate limit for *key* is exceeded.

        Calling this method also records the current call timestamp so repeated
        calls accumulate toward the limit.

        Args:
            key: Logical identifier for the operation, e.g. ``"classify_email"``.

        Returns:
            True  — call is allowed.
            False — rate limit exceeded; the caller should abort.
        """
        now = time.monotonic()
        window_start = now - self.window_seconds

        async with self._lock:
            # Evict timestamps outside the window
            self._calls[key] = [t for t in self._calls[key] if t >= window_start]

            if len(self._calls[key]) >= self.max_calls:
                logger.warning(
                    "RateLimiter: key=%r exceeded %d calls / %ds window",
                    key,
                    self.max_calls,
                    self.window_seconds,
                )
                return False

            self._calls[key].append(now)
            return True

    def reset(self, key: Optional[str] = None) -> None:
        """Reset counters — useful in tests.

        Args:
            key: If given, reset only that key; otherwise reset all counters.
        """
        if key is not None:
            self._calls.pop(key, None)
        else:
            self._calls.clear()


# ---------------------------------------------------------------------------
# Control 4: Audit Logger
# ---------------------------------------------------------------------------

class AuditLogger:
    """Logs every agent action to Azure Table Storage (table: ``audit_log``).

    Each row records who did what, to which RFQ, whether it succeeded, and any
    error message.  The ``PartitionKey`` is the date (``YYYY-MM-DD``) and the
    ``RowKey`` is ``<rfq_id>:<timestamp_us>``.

    In tests or environments without Azure credentials, pass
    ``connection_string=None`` to fall back to Python's standard logging only.
    """

    def __init__(self, connection_string: Optional[str] = None, table_name: str = "auditlog") -> None:
        self._conn = connection_string
        self._table_name = table_name

    async def log(
        self,
        action_type: str,
        rfq_id: str,
        actor: str,
        details: dict,
        success: bool,
        error_msg: str = "",
    ) -> None:
        """Persist an audit record.

        Args:
            action_type: Symbolic name, e.g. ``"DRAFT_CREATED"``, ``"EMAIL_SENT"``.
            rfq_id:      Identifier of the RFQ being acted upon.
            actor:       ``"agent"`` or the email address of the human who triggered the action.
            details:     Arbitrary dict with context (e.g. draft_id, supplier_email).
            success:     Whether the action completed successfully.
            error_msg:   Exception message or empty string on success.
        """
        import json
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        log_entry = {
            "action_type": action_type,
            "rfq_id": rfq_id,
            "actor": actor,
            "details": json.dumps(details),
            "success": success,
            "error_msg": mask_sensitive_data(error_msg),
            "timestamp": now.isoformat(),
        }

        # Always emit to Python logger so Application Insights picks it up
        level = logging.INFO if success else logging.ERROR
        logger.log(
            level,
            "AUDIT | action=%s rfq=%s actor=%s success=%s error=%s details=%s",
            action_type,
            rfq_id,
            actor,
            success,
            log_entry["error_msg"],
            log_entry["details"],
        )

        if not self._conn:
            return  # No Azure storage configured — log-only mode

        try:
            from azure.data.tables.aio import TableServiceClient

            partition_key = now.strftime("%Y-%m-%d")
            row_key = f"{rfq_id}:{int(now.timestamp() * 1_000_000)}"

            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                **log_entry,
            }

            service = TableServiceClient.from_connection_string(self._conn)
            async with service.get_table_client(self._table_name) as table:
                await table.create_entity(entity)

        except Exception as exc:  # noqa: BLE001
            # Audit logging must never crash the main flow
            logger.error("AuditLogger: failed to write to Azure Table: %s", exc)


# ---------------------------------------------------------------------------
# Control 5: Supplier Email Allowlist Checker
# ---------------------------------------------------------------------------

def is_known_supplier_domain(email: str, known_domains: list[str]) -> bool:
    """Return True only if the sender's domain matches a known supplier domain.

    Comparison is case-insensitive.  Subdomains are *not* accepted by default
    (``mail.supplier.com`` does not match ``supplier.com``) to prevent bypass
    via crafted subdomains.

    Args:
        email:         Full sender email address, e.g. ``"sales@acme.com"``.
        known_domains: List of approved supplier domains, e.g. ``["acme.com", "globex.co.il"]``.

    Returns:
        True if the domain matches exactly, False otherwise.
    """
    if not email or not known_domains:
        return False

    # Extract domain part after the last '@'
    parts = email.rsplit("@", 1)
    if len(parts) != 2:
        logger.warning("is_known_supplier_domain: malformed email address %r", email)
        return False

    sender_domain = parts[1].strip().lower()
    normalised_domains = {d.strip().lower() for d in known_domains}

    result = sender_domain in normalised_domains
    if not result:
        logger.info(
            "is_known_supplier_domain: domain %r not in allowlist (%d entries)",
            sender_domain,
            len(normalised_domains),
        )
    return result


# ---------------------------------------------------------------------------
# Control 6: Secret Masker for Logs
# ---------------------------------------------------------------------------

# Compiled patterns for known secret formats
_SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Anthropic API key: sk-ant-api03-...  or  sk-ant-...
    (re.compile(r"sk-ant-[A-Za-z0-9\-_]{8,}"), "sk-ant-***REDACTED***"),
    # Azure Storage connection string
    (
        re.compile(r"DefaultEndpointsProtocol=[^;]+;[^\s\"']+", re.IGNORECASE),
        "DefaultEndpointsProtocol=***REDACTED***",
    ),
    # Slack bot / user tokens
    (re.compile(r"xox[bpsa]-[A-Za-z0-9\-]{10,}"), "xox*-***REDACTED***"),
    # Passwords in URLs (http://user:password@host)
    (re.compile(r"(https?://[^:@\s]+:)[^@\s]+(@)", re.IGNORECASE), r"\1***REDACTED***\2"),
    # Generic "password=<value>" patterns in query strings / config lines
    (re.compile(r"(password\s*[=:]\s*)[^\s&\"';,]+", re.IGNORECASE), r"\1***REDACTED***"),
    # Azure SAS tokens
    (re.compile(r"sig=[A-Za-z0-9%+/=]{20,}", re.IGNORECASE), "sig=***REDACTED***"),
    # Azure client secrets (GUIDs or long strings after "secret")
    (re.compile(r"(client.?secret\s*[=:]\s*)[^\s\"',;]+", re.IGNORECASE), r"\1***REDACTED***"),
]


def mask_sensitive_data(text: str) -> str:
    """Replace API keys, connection strings, and passwords in log output.

    This function is intended to be applied to any string before it is written
    to a log, included in an error message, or persisted to storage.

    Patterns replaced:
      - Anthropic API keys (``sk-ant-*``)
      - Azure Storage connection strings (``DefaultEndpointsProtocol=*``)
      - Slack tokens (``xox*``)
      - Passwords embedded in URLs
      - Generic ``password=<value>`` key-value pairs
      - Azure SAS ``sig=`` parameters
      - Azure client secret patterns

    Args:
        text: String that may contain sensitive data.

    Returns:
        String with sensitive values replaced by ``***REDACTED***``.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result
