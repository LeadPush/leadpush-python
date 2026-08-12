from __future__ import annotations

import httpx
import pytest

from leadpush import (
    API_VERSION,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    SDK_VERSION,
    ApiError,
    AsyncLeadpush,
    ForbiddenError,
    Leadpush,
    NotFoundError,
    TimeoutError,
    UnauthorizedError,
    ValidationError,
)

from .support import TEST_BASE_URL, assert_headers, async_client, request_json, sync_client


def test_client_defaults_and_resource_caching() -> None:
    client = Leadpush("test-key")

    assert client.key == "test-key"
    assert client.version == SDK_VERSION
    assert client.options.base_url == DEFAULT_BASE_URL
    assert client.options.timeout == DEFAULT_TIMEOUT
    assert client.options.headers == {}
    assert client.options.user_agent == DEFAULT_USER_AGENT
    assert client.contacts is client.contacts
    assert client.domains is client.domains
    client.close()


def test_low_level_requests_encode_paths_queries_bodies_and_headers() -> None:
    client, recorder, transport = sync_client(
        [{"ok": True}, {"created": True}, None],
        headers={"X-App-Name": "tests", "User-Agent": "header-agent"},
        user_agent="test-agent",
    )

    assert client.get(["contacts", "team/a@example.com", "events"], {"force": True, "filters": [{"id": "x"}]}) == {
        "ok": True
    }
    assert client.post("contacts/contact-id/subscribe", {"subscribed": True}) == {"created": True}
    assert client.delete(["contacts", "contact-id"]) is None

    get_request, post_request, delete_request = recorder.requests
    assert str(get_request.url) == (
        f"{TEST_BASE_URL}/contacts/team%2Fa%40example.com/events?force=true&filters=%5B%7B%22id%22%3A%22x%22%7D%5D"
    )
    assert_headers(get_request, **{"x-app-name": "tests", "user-agent": "test-agent"})
    assert post_request.method == "POST"
    assert request_json(post_request) == {"subscribed": True}
    assert post_request.headers["content-type"] == "application/json"
    assert delete_request.method == "DELETE"
    transport.close()


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, UnauthorizedError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (422, ValidationError),
        (500, ApiError),
    ],
)
def test_http_status_errors(status: int, error_type: type[ApiError]) -> None:
    payload = {"message": "failed"}
    client, _, transport = sync_client([httpx.Response(status, json=payload)])

    with pytest.raises(error_type) as raised:
        client.get("contacts")

    assert raised.value.status == status
    assert raised.value.response == payload
    transport.close()


def test_plain_text_and_empty_responses() -> None:
    client, _, transport = sync_client([httpx.Response(200, text="plain"), None])
    assert client.get("plain") == "plain"
    assert client.delete("empty") is None
    transport.close()


def test_timeout_is_mapped_and_other_transport_errors_propagate() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    timeout_transport = httpx.Client(transport=httpx.MockTransport(timeout_handler))
    client = Leadpush("test-key", base_url=TEST_BASE_URL, timeout=1.5, http_client=timeout_transport)

    with pytest.raises(TimeoutError, match=r"1\.5s"):
        client.get("contacts")

    timeout_transport.close()

    def connection_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    connection_transport = httpx.Client(transport=httpx.MockTransport(connection_handler))
    client = Leadpush("test-key", base_url=TEST_BASE_URL, http_client=connection_transport)

    with pytest.raises(httpx.ConnectError):
        client.get("contacts")

    connection_transport.close()


def test_injected_sync_client_remains_caller_owned() -> None:
    client, _, transport = sync_client([{"ok": True}])
    client.close()
    assert not transport.is_closed
    assert client.get("health") == {"ok": True}
    transport.close()


@pytest.mark.asyncio
async def test_async_low_level_client_and_caller_ownership() -> None:
    client, recorder, transport = async_client([{"ok": True}], headers={"X-App": "async"})

    async with client:
        assert await client.get("health", {"version": API_VERSION}) == {"ok": True}

    assert not transport.is_closed
    assert str(recorder.requests[0].url) == f"{TEST_BASE_URL}/health?version=v1"
    assert_headers(recorder.requests[0], **{"x-app": "async"})
    await transport.aclose()


@pytest.mark.asyncio
async def test_async_timeout_mapping() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.WriteTimeout("slow", request=request)

    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = AsyncLeadpush("test-key", base_url=TEST_BASE_URL, timeout=2, http_client=transport)

    with pytest.raises(TimeoutError, match="2s"):
        await client.post("contacts", {"value": True})

    await transport.aclose()


def test_default_context_manager_closes_owned_client() -> None:
    client = Leadpush("test-key")
    with client as entered:
        assert entered is client

    with pytest.raises(RuntimeError, match="client has been closed"):
        client.get("health")


@pytest.mark.asyncio
async def test_default_async_context_manager_closes_owned_client() -> None:
    client = AsyncLeadpush("test-key")
    async with client as entered:
        assert entered is client

    with pytest.raises(RuntimeError, match="client has been closed"):
        await client.get("health")


def test_public_version_matches_distribution_metadata() -> None:
    assert isinstance(SDK_VERSION, str)
    assert SDK_VERSION
