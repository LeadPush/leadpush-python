# leadpush

Official synchronous and asynchronous Python SDK for the Leadpush API.

Create a Leadpush account at [leadpush.io](https://leadpush.io).

## Installation

```sh
pip install leadpush
```

Requirements:

- Python 3.10 or newer
- A Leadpush API key

## Quick start

```python
import os

from leadpush import Leadpush

with Leadpush(os.environ["LEADPUSH_API_KEY"]) as client:
    contacts = client.contacts.list(page=1, per_page=10)
    print(contacts.data)
```

Use `AsyncLeadpush` in asynchronous applications:

```python
import os

from leadpush import AsyncLeadpush


async def main() -> None:
    async with AsyncLeadpush(os.environ["LEADPUSH_API_KEY"]) as client:
        contacts = await client.contacts.list(page=1, per_page=10)
        print(contacts.data)
```

The synchronous and asynchronous clients expose the same resources. Async network operations require `await`, and
`cursor()` and `list_all()` are asynchronous iterators on `AsyncLeadpush`.

## Configuration

```python
from leadpush import Leadpush

client = Leadpush(
    "leadpush_api_key",
    base_url="https://api.leadpush.io/v1",
    timeout=30.0,
    headers={"X-App-Name": "my-app"},
    user_agent="my-app/1.0",
)
```

Defaults:

- `base_url`: `https://api.leadpush.io/v1`
- `timeout`: `30.0` seconds; pass `None` to disable timeouts
- `headers`: `{}`
- `user_agent`: `leadpush/<installed version> (api=v1)`

Pass an `httpx.Client` or `httpx.AsyncClient` with `http_client=` to customize the transport or mock requests. Injected
clients remain caller-owned and are not closed by Leadpush.

## Contacts

Contact identifiers may be a contact UUID or the workspace identity field value, such as an email address.

```python
contact = client.contacts.get("person@example.com")

created = client.contacts.create(
    subscribed=True,
    attributes={
        "email": "person@example.com",
        "first_name": "Person",
    },
)

updated = client.contacts.update(
    contact.uuid,
    subscribed=False,
    attributes={"first_name": "Updated"},
)

client.contacts.subscribe("person@example.com")
client.contacts.unsubscribe("person@example.com")
```

Models returned by the client are attached to it. Contacts track local changes until `update()`:

```python
contact.subscribed = False
contact.set_attribute("first_name", "Updated")
contact.update()

contact.subscribe()
contact.unsubscribe()
```

The async equivalents are `await contact.update()`, `await contact.subscribe()`, and `await contact.unsubscribe()`.

### Contact events

```python
events = client.contacts.events("person@example.com").list(search="purchase")

client.contacts.events(contact.uuid).create(
    event_name="purchase",
    attributes={"plan": "enterprise"},
)

# An attached contact exposes the same nested resource.
events = contact.events.list()
```

Event creation returns `None` when the API accepts the event.

## Pagination

List methods return `PaginatedResponse` with `data` and `meta` properties:

```python
page = client.contacts.list(page=1, per_page=25)
print(page.meta.has_next)
```

Iterate models or complete pages without managing page numbers:

```python
for contact in client.contacts.list_all(per_page=100):
    print(contact.uuid)

for page in client.contacts.cursor(per_page=100):
    print(page.meta.current_page, len(page.data))
```

With `AsyncLeadpush`, use `async for` for both iterators.

## Domains

```python
domains = client.domains.list(search="example", page=1, per_page=10)

domain = client.domains.create(
    name="example.com",
    dkim_selectors=["default"],
    tracking_subdomain="click",
    tracking_mode="cloudflare",
)

verified = client.domains.verify(domain.uuid)
client.domains.delete(domain.uuid)
```

Attached domains support `verify()`, `delete()`, and the `addresses` nested resource:

```python
domain.verify()

addresses = domain.addresses.list()
address = domain.addresses.create(
    address="sender",
    display_name="Sender Name",
    reply_to="reply@example.com",
    company_address="123 Main St",
    company_city="New York",
    company_state="NY",
    company_zip="10001",
    company_country="US",
)

address.delete()
```

## Emails

```python
send = client.emails.send(
    from_address="sender@example.com",
    subject="Developer API email",
    html="<p>Hello world</p>",
    text="Hello world",
    to=["known@example.com", "other@example.com"],
    bcc=["audit@example.com"],
    reply_to="reply@example.com",
    headers={"X-Correlation-ID": "abc-123"},
)

print(send.accepted)
print(send.message_count)
print(send.messages[0].uuid)
```

The `from_address` must be a verified sendable address in the API key workspace. Provide `html`, `text`, or both, and
at least one recipient across `to` and `bcc`.

## Fields and suppressions

```python
fields = client.fields.list(
    search="company",
    filters=[{"id": "type", "value": ["text"]}],
)

field = client.fields.create(
    name="company_name",
    type="text",
    format={"text": "url"},
)

suppressions = client.suppressions.list(
    search="blocked@example.com",
    filters=[{"id": "type", "value": ["manual"]}],
)

suppression = client.suppressions.create(email="blocked@example.com", type="manual")
```

Suppressions do not support updates. Calling `client.suppressions.update(...)` raises `UnsupportedEndpointError`.

## Models

Response models expose snake_case properties and timezone-aware `datetime` values. `to_dict()` returns a deep-copied,
API-shaped dictionary and preserves response fields unknown to this SDK version.

Standalone models can be created from API-shaped dictionaries, but attached operations on them raise
`DetachedModelError` because no client is available.

## Low-level requests

Use `get`, `post`, or `delete` for endpoints without a resource yet:

```python
response = client.get("contacts/contact_uuid/events")
response = client.post("contacts/contact_uuid/subscribe")
client.delete(["contacts", "contact_uuid"])
```

Sequence paths preserve every item as one path segment. This is useful for identity values containing `/` or `@`.

## Errors

```python
from leadpush import UnauthorizedError, ValidationError

try:
    client.contacts.list()
except UnauthorizedError:
    print("Invalid API key")
except ValidationError as error:
    print(error.response)
```

Available SDK exceptions:

- `ApiError`
- `UnauthorizedError`
- `ForbiddenError`
- `NotFoundError`
- `ValidationError`
- `TimeoutError`
- `UnsupportedEndpointError`
- `DetachedModelError`

Other `httpx` transport errors propagate unchanged.

## Development

```sh
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv build
uv run twine check dist/*
```

## Releasing

Update the version in `pyproject.toml` and changelog, merge the change to `main`, then dispatch the Release workflow
with the exact version. The workflow verifies the source, publishes the distributions to PyPI through trusted
publishing, creates `v<version>`, and creates a GitHub release.

Configure a PyPI trusted publisher for:

- project: `leadpush`
- repository: `LeadPush/leadpush-python`
- workflow: `release.yml`
- environment: none

## License

MIT

