from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from ._http import AsyncHttpClient, SyncHttpClient
from ._types import RequestParams, RequestPath
from ._version import API_VERSION, DEFAULT_BASE_URL, DEFAULT_TIMEOUT, DEFAULT_USER_AGENT, SDK_NAME, SDK_VERSION
from .resources import (
    AsyncContacts,
    AsyncDomains,
    AsyncEmails,
    AsyncFields,
    AsyncSuppressions,
    Contacts,
    Domains,
    Emails,
    Fields,
    Suppressions,
)


@dataclass(frozen=True, slots=True)
class ClientOptions:
    """Resolved options used by a Leadpush client."""

    base_url: str
    timeout: float | None
    headers: dict[str, str]
    user_agent: str


class Leadpush:
    """Synchronous Leadpush API client."""

    def __init__(
        self,
        key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.key = key
        self.version = SDK_VERSION
        self.options = ClientOptions(
            base_url=base_url,
            timeout=timeout,
            headers=dict(headers or {}),
            user_agent=user_agent,
        )
        self._http = SyncHttpClient(
            api_key=key,
            api_version=API_VERSION,
            base_url=base_url,
            headers=self.options.headers,
            sdk_name=SDK_NAME,
            sdk_version=SDK_VERSION,
            timeout=timeout,
            user_agent=user_agent,
            client=http_client,
        )
        self.contacts = Contacts(self)
        self.domains = Domains(self)
        self.emails = Emails(self)
        self.fields = Fields(self)
        self.suppressions = Suppressions(self)

    def get(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        """Make a GET request to an API path relative to the configured base URL."""
        return self._http.get(path, params)

    def post(
        self,
        path: RequestPath,
        data: Mapping[str, Any] | None = None,
        params: RequestParams | None = None,
    ) -> Any:
        """Make a POST request to an API path relative to the configured base URL."""
        return self._http.post(path, data, params)

    def delete(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        """Make a DELETE request to an API path relative to the configured base URL."""
        return self._http.delete(path, params)

    def close(self) -> None:
        """Close the internally created HTTP transport, if any."""
        self._http.close()

    def __enter__(self) -> Leadpush:
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()


class AsyncLeadpush:
    """Asynchronous Leadpush API client."""

    def __init__(
        self,
        key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.key = key
        self.version = SDK_VERSION
        self.options = ClientOptions(
            base_url=base_url,
            timeout=timeout,
            headers=dict(headers or {}),
            user_agent=user_agent,
        )
        self._http = AsyncHttpClient(
            api_key=key,
            api_version=API_VERSION,
            base_url=base_url,
            headers=self.options.headers,
            sdk_name=SDK_NAME,
            sdk_version=SDK_VERSION,
            timeout=timeout,
            user_agent=user_agent,
            client=http_client,
        )
        self.contacts = AsyncContacts(self)
        self.domains = AsyncDomains(self)
        self.emails = AsyncEmails(self)
        self.fields = AsyncFields(self)
        self.suppressions = AsyncSuppressions(self)

    async def get(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        """Make an asynchronous GET request relative to the configured base URL."""
        return await self._http.get(path, params)

    async def post(
        self,
        path: RequestPath,
        data: Mapping[str, Any] | None = None,
        params: RequestParams | None = None,
    ) -> Any:
        """Make an asynchronous POST request relative to the configured base URL."""
        return await self._http.post(path, data, params)

    async def delete(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        """Make an asynchronous DELETE request relative to the configured base URL."""
        return await self._http.delete(path, params)

    async def aclose(self) -> None:
        """Close the internally created HTTP transport, if any."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncLeadpush:
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.aclose()
