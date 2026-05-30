"""Pytest configuration: stub missing Azure SDK packages so unit tests can
run without installing the full Azure SDK.

The stubs expose just enough surface (TableServiceClient, ResourceNotFoundError,
ServiceBusClient, etc.) for import-time resolution. The actual calls are mocked
per-test with unittest.mock.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import AsyncMock, MagicMock


def _make_azure_stubs() -> None:
    """Insert lightweight azure stub modules into sys.modules."""

    def _mod(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    # azure
    azure = _mod("azure")

    # azure.core
    core = _mod("azure.core")
    azure.core = core

    # azure.core.exceptions
    core_exc = _mod("azure.core.exceptions")
    core.exceptions = core_exc  # type: ignore[attr-defined]

    class ResourceNotFoundError(Exception):
        pass

    core_exc.ResourceNotFoundError = ResourceNotFoundError  # type: ignore[attr-defined]

    # azure.data
    data = _mod("azure.data")
    azure.data = data  # type: ignore[attr-defined]

    # azure.data.tables
    tables = _mod("azure.data.tables")
    data.tables = tables  # type: ignore[attr-defined]

    # azure.data.tables.aio
    tables_aio = _mod("azure.data.tables.aio")
    tables.aio = tables_aio  # type: ignore[attr-defined]
    tables_aio.TableServiceClient = MagicMock  # replaced per-test as needed

    # azure.identity
    identity = _mod("azure.identity")
    azure.identity = identity  # type: ignore[attr-defined]
    identity.ClientSecretCredential = MagicMock  # type: ignore[attr-defined]

    # azure.identity.aio
    identity_aio = _mod("azure.identity.aio")
    identity.aio = identity_aio  # type: ignore[attr-defined]
    identity_aio.ClientSecretCredential = MagicMock  # type: ignore[attr-defined]

    # azure.functions (used by function entry-points)
    functions = _mod("azure.functions")
    azure.functions = functions  # type: ignore[attr-defined]
    functions.ServiceBusMessage = MagicMock  # type: ignore[attr-defined]
    functions.TimerRequest = MagicMock  # type: ignore[attr-defined]
    functions.HttpRequest = MagicMock  # type: ignore[attr-defined]
    functions.HttpResponse = MagicMock  # type: ignore[attr-defined]


def _make_slack_stubs() -> None:
    """Insert lightweight slack_sdk stub modules into sys.modules."""

    def _mod(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        sys.modules[name] = m
        return m

    slack_sdk = _mod("slack_sdk")
    web = _mod("slack_sdk.web")
    slack_sdk.web = web  # type: ignore[attr-defined]
    async_client = _mod("slack_sdk.web.async_client")
    web.async_client = async_client  # type: ignore[attr-defined]
    async_client.AsyncWebClient = MagicMock  # replaced per-test as needed


# Only stub when the real packages are absent
if "azure" not in sys.modules:
    _make_azure_stubs()

if "slack_sdk" not in sys.modules:
    _make_slack_stubs()
