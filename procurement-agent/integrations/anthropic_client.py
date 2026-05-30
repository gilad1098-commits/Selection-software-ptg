from __future__ import annotations

from anthropic import AsyncAnthropic
from config.settings import settings

# Shared async client instance — import this rather than constructing directly
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
