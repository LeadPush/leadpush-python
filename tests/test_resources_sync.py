from __future__ import annotations

import json

import pytest

from leadpush import (
    Contact,
    ContactEvent,
    DetachedModelError,
    Domain,
    DomainAddress,
    EmailSend,
    Field,
    Suppression,
    UnsupportedEndpointError,
)

from .support import (
    ADDRESS,
    CONTACT,
    DOMAIN,
    EMAIL_SEND,
    EVENT,
    FIELD,
    SUPPRESSION,
    VERIFIED_DOMAIN,
    page,
    request_json,
    sync_client,
)


def test_contacts_crud_identity_actions_and_attached_update() -> None:
    updated = {**CONTACT, "subscribed": False, "attributes": {**CONTACT["attributes"], "first_name": "Updated"}}
    client, recorder, transport = sync_client(
        [
            {"data": CONTACT},
            {"data": updated},
            {"data": CONTACT},
            {"data": updated},
            {"data": CONTACT},
            {"data": updated},
        ]
    )

    contact = client.contacts.get("person@example.test")
    assert isinstance(contact, Contact)
    assert contact.uuid == CONTACT["uuid"]
    assert contact.provider == "leadpush"
    assert contact.attributes["email"] == "person@example.test"
    assert str(recorder.requests[0].url).endswith("/contacts/person%40example.test")

    contact.subscribed = False
    contact.set_attribute("first_name", "Updated")
    assert contact.update() is contact
    assert request_json(recorder.requests[1]) == {
        "subscribed": False,
        "attributes": {"first_name": "Updated"},
    }
    assert contact.subscribed is False

    request_count = len(recorder.requests)
    assert contact.update() is contact
    assert len(recorder.requests) == request_count

    assert client.contacts.create(attributes={"email": "person@example.test"}).uuid == CONTACT["uuid"]
    assert request_json(recorder.requests[2]) == {"attributes": {"email": "person@example.test"}}

    assert client.contacts.update("contact-uuid", subscribed=False).subscribed is False
    assert client.contacts.subscribe("person@example.test").subscribed is True
    assert client.contacts.unsubscribe("person@example.test").subscribed is False
    transport.close()


def test_attached_contact_subscribe_unsubscribe_and_events() -> None:
    unsubscribed = {**CONTACT, "subscribed": False}
    client, recorder, transport = sync_client(
        [
            {"data": CONTACT},
            {"data": unsubscribed},
            {"data": CONTACT},
            page([EVENT]),
        ]
    )
    contact = client.contacts.get("contact-uuid")

    assert contact.unsubscribe() is contact
    assert contact.subscribed is False
    assert contact.subscribe() is contact
    assert contact.subscribed is True

    events = contact.events.list(search="purchase")
    assert isinstance(events.data[0], ContactEvent)
    assert events.data[0].event_name == "purchase"
    assert recorder.requests[3].url.path.endswith("/contacts/contact-uuid/events")
    transport.close()


def test_contact_events_create_serializes_attributes_and_omits_them_when_unspecified() -> None:
    client, recorder, transport = sync_client([None, None])
    events = client.contacts.events("team/a@example.test")

    events.create(event_name="purchase", attributes={"plan": "enterprise"})
    events.create(event_name="login")

    assert str(recorder.requests[0].url).endswith("/contacts/team%2Fa%40example.test/events")
    assert request_json(recorder.requests[0]) == {
        "event_name": "purchase",
        "attributes": json.dumps({"plan": "enterprise"}, separators=(",", ":")),
    }
    assert request_json(recorder.requests[1]) == {"event_name": "login"}
    transport.close()


def test_sync_pagination_cursor_and_list_all_honor_starting_page() -> None:
    second_contact = {**CONTACT, "uuid": "contact-2"}
    client, recorder, transport = sync_client(
        [page([CONTACT], current=2, has_next=True), page([second_contact], current=3)]
    )

    contacts = list(client.contacts.list_all(page=2, per_page=1))

    assert [contact.uuid for contact in contacts] == ["contact-uuid", "contact-2"]
    assert recorder.requests[0].url.query == b"page=2&per_page=1"
    assert recorder.requests[1].url.query == b"page=3&per_page=1"
    transport.close()


def test_domains_and_attached_domain_actions() -> None:
    client, recorder, transport = sync_client(
        [
            page([DOMAIN]),
            {"data": DOMAIN},
            {"data": DOMAIN},
            {"data": VERIFIED_DOMAIN},
            {"data": VERIFIED_DOMAIN},
            None,
            None,
        ]
    )

    domains = client.domains.list(page=2, per_page=1, search="example")
    domain = domains.data[0]
    assert isinstance(domain, Domain)
    assert domain.dns[0].is_valid is False
    assert domain.created_at.tzinfo is not None
    assert "search=example" in str(recorder.requests[0].url)

    assert client.domains.get("domain-uuid").uuid == "domain-uuid"
    created = client.domains.create(
        name="example.test",
        dkim_selectors=["default"],
        tracking_subdomain=None,
        tracking_mode="cloudflare",
    )
    assert created.name == "example.test"
    assert request_json(recorder.requests[2]) == {
        "name": "example.test",
        "dkim_selectors": ["default"],
        "tracking_subdomain": None,
        "tracking_mode": "cloudflare",
    }

    assert client.domains.verify("domain-uuid").verified is True
    assert domain.verify() is domain
    assert domain.verified is True
    domain.delete()
    client.domains.delete("domain-uuid")
    transport.close()


def test_domain_addresses_nested_and_attached_actions() -> None:
    client, recorder, transport = sync_client([page([ADDRESS]), {"data": ADDRESS}, {"data": ADDRESS}, None, None])
    addresses = client.domains.addresses("domain-uuid")

    page_result = addresses.list(page=1, per_page=10)
    address = page_result.data[0]
    assert isinstance(address, DomainAddress)
    assert address.full_address == "sender@example.test"
    assert address.updated_at.tzinfo is not None

    assert addresses.get("address-uuid").uuid == "address-uuid"
    created = addresses.create(
        address="sender",
        display_name="Sender",
        reply_to="reply@example.test",
        company_address="123 Main St",
        company_address_2=None,
        company_city="New York",
        company_state="NY",
        company_zip="10001",
        company_country="US",
    )
    assert created.uuid == "address-uuid"
    assert request_json(recorder.requests[2])["company_address_2"] is None
    address.delete()
    addresses.delete("address-uuid")
    transport.close()


def test_email_send_and_message_models() -> None:
    client, recorder, transport = sync_client([{"data": EMAIL_SEND}])

    send = client.emails.send(
        from_address="sender@example.test",
        subject="Hello",
        html="<p>Hello</p>",
        to=["person@example.test"],
        bcc=["audit@example.test"],
        headers={"X-Correlation-ID": "abc"},
    )

    assert isinstance(send, EmailSend)
    assert send.accepted is True
    assert send.message_count == 2
    assert send.messages[0].from_address == "sender@example.test"
    assert send.messages[1].type == "bcc"
    assert request_json(recorder.requests[0])["from"] == "sender@example.test"
    transport.close()


def test_fields_crud_filters_and_models() -> None:
    client, recorder, transport = sync_client([page([FIELD]), {"data": FIELD}, {"data": FIELD}, {"data": FIELD}])
    fields = client.fields.list(search="company", filters=[{"id": "type", "value": ["text"]}])

    field = fields.data[0]
    assert isinstance(field, Field)
    assert field.type == "text"
    assert field.format is not None
    assert field.format.text == "url"
    assert "%22text%22" in str(recorder.requests[0].url)

    assert client.fields.get("field-uuid").uuid == "field-uuid"
    assert client.fields.create(name="company", type="text", format={"text": "url"}).name == "company"
    assert client.fields.update("field-uuid", name="company_url").uuid == "field-uuid"
    assert request_json(recorder.requests[3]) == {"name": "company_url"}
    transport.close()


def test_suppressions_crud_filters_and_unsupported_update() -> None:
    client, recorder, transport = sync_client([page([SUPPRESSION]), {"data": SUPPRESSION}, {"data": SUPPRESSION}])
    suppressions = client.suppressions.list(
        search="blocked@example.test",
        filters=[{"id": "type", "value": ["manual"]}],
    )
    assert isinstance(suppressions.data[0], Suppression)
    assert suppressions.data[0].type == "manual"
    assert client.suppressions.get("suppression-uuid").uuid == "suppression-uuid"
    assert client.suppressions.create(email="blocked@example.test").email == "blocked@example.test"
    assert request_json(recorder.requests[2]) == {"email": "blocked@example.test"}

    with pytest.raises(UnsupportedEndpointError):
        client.suppressions.update("suppression-uuid", email="new@example.test")

    transport.close()


def test_models_preserve_unknown_data_deep_copy_and_detached_failures() -> None:
    detached = Contact(CONTACT)
    raw = detached.to_dict()
    raw["attributes"]["first_name"] = "Changed"

    assert detached.attributes["first_name"] == "Person"
    assert detached.to_dict()["future_field"] == "preserved"
    assert detached.created_at.tzinfo is not None

    with pytest.raises(DetachedModelError):
        detached.subscribe()
