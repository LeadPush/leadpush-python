from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from leadpush import API_VERSION, SDK_NAME, SDK_VERSION, AsyncLeadpush, Leadpush

TEST_BASE_URL = "https://api.leadpush.test/v1"

CONTACT: dict[str, Any] = {
    "uuid": "contact-uuid",
    "subscribed": True,
    "attributes": {"email": "person@example.test", "first_name": "Person"},
    "provider": "leadpush",
    "created_at": "2026-01-01T12:00:00Z",
    "updated_at": "2026-01-02T12:00:00Z",
    "future_field": "preserved",
}

EVENT: dict[str, Any] = {
    "uuid": "event-uuid",
    "event_name": "purchase",
    "attributes": {"plan": "enterprise"},
    "created_at": "2026-01-03T12:00:00Z",
}

DOMAIN: dict[str, Any] = {
    "uuid": "domain-uuid",
    "name": "example.test",
    "domain": "example.test",
    "verified": False,
    "provider": "leadpush",
    "status": "pending",
    "verification": "pending",
    "mail_from_domain": "mail.example.test",
    "mail_from_verified": False,
    "dns": [{"type": "TXT", "name": "example.test", "value": "value", "is_valid": False}],
    "created_at": "2026-01-01T12:00:00Z",
    "updated_at": "2026-01-02T12:00:00Z",
}

VERIFIED_DOMAIN: dict[str, Any] = {
    **DOMAIN,
    "verified": True,
    "verification": "completed",
    "mail_from_verified": True,
}

ADDRESS: dict[str, Any] = {
    "uuid": "address-uuid",
    "domain_uuid": "domain-uuid",
    "address": "sender",
    "full_address": "sender@example.test",
    "provider": "leadpush",
    "display_name": "Sender",
    "verification": "completed",
    "created_at": "2026-01-01T12:00:00Z",
    "updated_at": "2026-01-02T12:00:00Z",
}

FIELD: dict[str, Any] = {
    "uuid": "field-uuid",
    "name": "company",
    "type": "text",
    "format": {"text": "url", "pattern": None, "iso_format": None},
    "created_at": "2026-01-01T12:00:00Z",
}

SUPPRESSION: dict[str, Any] = {
    "uuid": "suppression-uuid",
    "email": "blocked@example.test",
    "type": "manual",
    "created_at": "2026-01-01T12:00:00Z",
}

EMAIL_SEND: dict[str, Any] = {
    "accepted": True,
    "message_count": 2,
    "messages": [
        {
            "uuid": "message-1",
            "recipient": "person@example.test",
            "type": "to",
            "from": "sender@example.test",
            "status": "pending",
        },
        {
            "uuid": "message-2",
            "recipient": "audit@example.test",
            "type": "bcc",
            "from": "sender@example.test",
            "status": "pending",
        },
    ],
}


def page(data: Sequence[Mapping[str, Any]], *, current: int = 1, has_next: bool = False) -> dict[str, Any]:
    return {
        "data": list(data),
        "meta": {
            "current_page": current,
            "per_page": len(data),
            "total": 2 if has_next else len(data),
            "last_page": 2 if has_next else current,
            "has_next": has_next,
        },
    }


class Recorder:
    def __init__(self, responses: Sequence[httpx.Response | Mapping[str, Any] | None]) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self.responses.pop(0)

        if isinstance(response, httpx.Response):
            return response
        if response is None:
            return httpx.Response(204)
        return httpx.Response(200, json=response)


def sync_client(
    responses: Sequence[httpx.Response | Mapping[str, Any] | None],
    **options: Any,
) -> tuple[Leadpush, Recorder, httpx.Client]:
    recorder = Recorder(responses)
    transport_client = httpx.Client(transport=httpx.MockTransport(recorder))
    client = Leadpush("test-key", base_url=TEST_BASE_URL, timeout=None, http_client=transport_client, **options)
    return client, recorder, transport_client


def async_client(
    responses: Sequence[httpx.Response | Mapping[str, Any] | None],
    **options: Any,
) -> tuple[AsyncLeadpush, Recorder, httpx.AsyncClient]:
    recorder = Recorder(responses)
    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    client = AsyncLeadpush("test-key", base_url=TEST_BASE_URL, timeout=None, http_client=transport_client, **options)
    return client, recorder, transport_client


def assert_headers(request: httpx.Request, **extra: str) -> None:
    assert request.headers["accept"] == "application/json"
    assert request.headers["authorization"] == "Bearer test-key"
    assert request.headers["x-leadpush-api-version"] == API_VERSION
    assert request.headers["x-leadpush-sdk"] == SDK_NAME
    assert request.headers["x-leadpush-sdk-version"] == SDK_VERSION

    for name, value in extra.items():
        assert request.headers[name] == value


def request_json(request: httpx.Request) -> Any:
    return json.loads(request.content)
