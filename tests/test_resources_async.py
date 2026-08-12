from __future__ import annotations

import pytest

from leadpush import AsyncContact, AsyncDomain, AsyncDomainAddress, UnsupportedEndpointError

from .support import (
    ADDRESS,
    CONTACT,
    DOMAIN,
    EMAIL_SEND,
    EVENT,
    FIELD,
    SUPPRESSION,
    VERIFIED_DOMAIN,
    async_client,
    page,
    request_json,
)


@pytest.mark.asyncio
async def test_async_contacts_attached_actions_events_and_pagination() -> None:
    updated = {**CONTACT, "subscribed": False}
    second_contact = {**CONTACT, "uuid": "contact-2"}
    client, recorder, transport = async_client(
        [
            {"data": CONTACT},
            {"data": updated},
            {"data": CONTACT},
            {"data": updated},
            page([EVENT]),
            None,
            page([CONTACT], current=2, has_next=True),
            page([second_contact], current=3),
        ]
    )

    contact = await client.contacts.get("person@example.test")
    assert isinstance(contact, AsyncContact)
    contact.subscribed = False
    assert await contact.update() is contact
    assert contact.subscribed is False
    assert await contact.subscribe() is contact
    assert await contact.unsubscribe() is contact

    events = await contact.events.list(search="purchase")
    assert events.data[0].event_name == "purchase"
    await client.contacts.events("person@example.test").create(event_name="login")

    contacts = [item async for item in client.contacts.list_all(page=2, per_page=1)]
    assert [item.uuid for item in contacts] == ["contact-uuid", "contact-2"]
    assert recorder.requests[-2].url.query == b"page=2&per_page=1"
    assert recorder.requests[-1].url.query == b"page=3&per_page=1"
    await transport.aclose()


@pytest.mark.asyncio
async def test_async_contact_resource_crud_and_actions() -> None:
    updated = {**CONTACT, "subscribed": False}
    client, recorder, transport = async_client(
        [{"data": CONTACT}, {"data": updated}, {"data": CONTACT}, {"data": updated}]
    )

    assert (await client.contacts.create(attributes={"email": "person@example.test"})).uuid == "contact-uuid"
    assert (await client.contacts.update("contact-uuid", subscribed=False)).subscribed is False
    assert (await client.contacts.subscribe("person@example.test")).subscribed is True
    assert (await client.contacts.unsubscribe("person@example.test")).subscribed is False
    assert request_json(recorder.requests[0]) == {"attributes": {"email": "person@example.test"}}
    await transport.aclose()


@pytest.mark.asyncio
async def test_async_domains_addresses_and_attached_actions() -> None:
    client, _, transport = async_client(
        [
            page([DOMAIN]),
            {"data": DOMAIN},
            {"data": DOMAIN},
            {"data": VERIFIED_DOMAIN},
            {"data": VERIFIED_DOMAIN},
            None,
            None,
            page([ADDRESS]),
            {"data": ADDRESS},
            {"data": ADDRESS},
            None,
            None,
        ]
    )

    listed = await client.domains.list(search="example")
    domain = listed.data[0]
    assert isinstance(domain, AsyncDomain)
    assert (await client.domains.get("domain-uuid")).uuid == "domain-uuid"
    assert (await client.domains.create(name="example.test")).name == "example.test"
    assert (await client.domains.verify("domain-uuid")).verified is True
    assert await domain.verify() is domain
    await domain.delete()
    await client.domains.delete("domain-uuid")

    addresses = client.domains.addresses("domain-uuid")
    address = (await addresses.list()).data[0]
    assert isinstance(address, AsyncDomainAddress)
    assert (await addresses.get("address-uuid")).uuid == "address-uuid"
    created = await addresses.create(
        address="sender",
        display_name="Sender",
        reply_to="reply@example.test",
        company_address="123 Main St",
        company_city="New York",
        company_state="NY",
        company_zip="10001",
        company_country="US",
    )
    assert created.full_address == "sender@example.test"
    await address.delete()
    await addresses.delete("address-uuid")
    await transport.aclose()


@pytest.mark.asyncio
async def test_async_email_fields_and_suppressions() -> None:
    client, recorder, transport = async_client(
        [
            {"data": EMAIL_SEND},
            page([FIELD]),
            {"data": FIELD},
            {"data": FIELD},
            {"data": FIELD},
            page([SUPPRESSION]),
            {"data": SUPPRESSION},
            {"data": SUPPRESSION},
        ]
    )

    send = await client.emails.send(
        from_address="sender@example.test",
        subject="Hello",
        text="Hello",
        to=["person@example.test"],
    )
    assert send.message_count == 2
    assert request_json(recorder.requests[0])["from"] == "sender@example.test"

    assert (await client.fields.list(filters=[{"id": "type", "value": ["text"]}])).data[0].name == "company"
    assert (await client.fields.get("field-uuid")).uuid == "field-uuid"
    assert (await client.fields.create(name="company", type="text")).name == "company"
    assert (await client.fields.update("field-uuid", format=None)).uuid == "field-uuid"

    suppressions = await client.suppressions.list(filters=[{"id": "type", "value": ["manual"]}])
    assert suppressions.data[0].email == "blocked@example.test"
    assert (await client.suppressions.get("suppression-uuid")).uuid == "suppression-uuid"
    assert (await client.suppressions.create(email="blocked@example.test", type="manual")).type == "manual"

    with pytest.raises(UnsupportedEndpointError):
        await client.suppressions.update("suppression-uuid", email="new@example.test")

    await transport.aclose()


@pytest.mark.asyncio
async def test_async_nested_resource_from_attached_domain() -> None:
    client, recorder, transport = async_client([{"data": DOMAIN}, page([ADDRESS])])
    domain = await client.domains.get("domain-uuid")
    addresses = await domain.addresses.list()

    assert addresses.data[0].uuid == "address-uuid"
    assert recorder.requests[1].url.path.endswith("/domains/domain-uuid/addresses")
    await transport.aclose()
