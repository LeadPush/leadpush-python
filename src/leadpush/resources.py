from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator, Mapping, Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

from ._types import UNSET, _UnsetType, without_none, without_unset
from .errors import UnsupportedEndpointError
from .models import (
    AsyncContact,
    AsyncDomain,
    AsyncDomainAddress,
    AsyncModelContext,
    AttributeValue,
    Contact,
    ContactEvent,
    ContactEventAttributes,
    ContactIdentifier,
    Domain,
    DomainAddress,
    DomainTrackingMode,
    EmailSend,
    Field,
    FieldFormat,
    FieldType,
    FieldTypeFilter,
    Model,
    Suppression,
    SuppressionType,
    SuppressionTypeFilter,
    SyncModelContext,
)
from .pagination import PaginatedResponse, PaginationMeta

if TYPE_CHECKING:
    from .client import AsyncLeadpush, Leadpush

ModelT = TypeVar("ModelT", bound=Model)


class SyncResource(Generic[ModelT]):
    endpoint: Sequence[str]
    model_class: type[ModelT]

    def __init__(self, client: Leadpush) -> None:
        self.client = client

    def _make_model(self, data: Mapping[str, Any]) -> ModelT:
        return self.model_class(data)

    def _get(self, path: Sequence[str] = (), params: Mapping[str, Any] | None = None) -> Any:
        return self.client.get([*self.endpoint, *path], params=params)

    def _post(
        self,
        path: Sequence[str] = (),
        data: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return self.client.post([*self.endpoint, *path], data=data, params=params)

    def _delete(self, path: Sequence[str] = (), params: Mapping[str, Any] | None = None) -> Any:
        return self.client.delete([*self.endpoint, *path], params=params)

    def _list(self, params: Mapping[str, Any]) -> PaginatedResponse[ModelT]:
        payload = cast(dict[str, Any], self._get(params=params))
        return PaginatedResponse(
            data=[self._make_model(item) for item in payload.get("data", [])],
            meta=PaginationMeta.from_dict(payload.get("meta", {})),
        )


class AsyncResource(Generic[ModelT]):
    endpoint: Sequence[str]
    model_class: type[ModelT]

    def __init__(self, client: AsyncLeadpush) -> None:
        self.client = client

    def _make_model(self, data: Mapping[str, Any]) -> ModelT:
        return self.model_class(data)

    async def _get(self, path: Sequence[str] = (), params: Mapping[str, Any] | None = None) -> Any:
        return await self.client.get([*self.endpoint, *path], params=params)

    async def _post(
        self,
        path: Sequence[str] = (),
        data: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self.client.post([*self.endpoint, *path], data=data, params=params)

    async def _delete(self, path: Sequence[str] = (), params: Mapping[str, Any] | None = None) -> Any:
        return await self.client.delete([*self.endpoint, *path], params=params)

    async def _list(self, params: Mapping[str, Any]) -> PaginatedResponse[ModelT]:
        payload = cast(dict[str, Any], await self._get(params=params))
        return PaginatedResponse(
            data=[self._make_model(item) for item in payload.get("data", [])],
            meta=PaginationMeta.from_dict(payload.get("meta", {})),
        )


def _sync_cursor(
    resource: Any,
    params: Mapping[str, Any],
) -> Iterator[PaginatedResponse[Any]]:
    page = int(params.get("page") or 1)

    while True:
        result = resource.list(**{**params, "page": page})
        yield result

        if not result.meta.has_next:
            return

        page = result.meta.current_page + 1


async def _async_cursor(
    resource: Any,
    params: Mapping[str, Any],
) -> AsyncIterator[PaginatedResponse[Any]]:
    page = int(params.get("page") or 1)

    while True:
        result = await resource.list(**{**params, "page": page})
        yield result

        if not result.meta.has_next:
            return

        page = result.meta.current_page + 1


class Contacts(SyncResource[Contact]):
    endpoint = ("contacts",)
    model_class = Contact

    def _make_model(self, data: Mapping[str, Any]) -> Contact:
        context = SyncModelContext(
            client=self.client,
            get=self._get,
            post=self._post,
            delete=self._delete,
            update=lambda identifier, values: self.update(identifier, **values),
        )
        return Contact(data, context)

    def list(self, *, page: int | None = None, per_page: int | None = None) -> PaginatedResponse[Contact]:
        return self._list(without_none({"page": page, "per_page": per_page}))

    def cursor(self, *, page: int | None = None, per_page: int | None = None) -> Iterator[PaginatedResponse[Contact]]:
        return cast(
            Iterator[PaginatedResponse[Contact]], _sync_cursor(self, without_none({"page": page, "per_page": per_page}))
        )

    def list_all(self, *, page: int | None = None, per_page: int | None = None) -> Iterator[Contact]:
        for result in self.cursor(page=page, per_page=per_page):
            yield from result.data

    def get(self, identifier: ContactIdentifier) -> Contact:
        payload = cast(dict[str, Any], self._get([identifier]))
        return self._make_model(payload["data"])

    def create(self, *, attributes: Mapping[str, AttributeValue], subscribed: bool | _UnsetType = UNSET) -> Contact:
        data = without_unset({"attributes": dict(attributes), "subscribed": subscribed})
        payload = cast(dict[str, Any], self._post(data=data))
        return self._make_model(payload["data"])

    def update(
        self,
        identifier: ContactIdentifier,
        *,
        attributes: Mapping[str, AttributeValue] | _UnsetType = UNSET,
        subscribed: bool | _UnsetType = UNSET,
    ) -> Contact:
        data = without_unset(
            {
                "attributes": dict(attributes) if not isinstance(attributes, _UnsetType) else UNSET,
                "subscribed": subscribed,
            }
        )
        payload = cast(dict[str, Any], self._post([identifier], data=data))
        return self._make_model(payload["data"])

    def subscribe(self, identifier: ContactIdentifier) -> Contact:
        payload = cast(dict[str, Any], self._post([identifier, "subscribe"]))
        return self._make_model(payload["data"])

    def unsubscribe(self, identifier: ContactIdentifier) -> Contact:
        payload = cast(dict[str, Any], self._post([identifier, "unsubscribe"]))
        return self._make_model(payload["data"])

    def events(self, identifier: ContactIdentifier) -> ContactEvents:
        return ContactEvents(self.client, identifier)


class AsyncContacts(AsyncResource[AsyncContact]):
    endpoint = ("contacts",)
    model_class = AsyncContact

    def _make_model(self, data: Mapping[str, Any]) -> AsyncContact:
        context = AsyncModelContext(
            client=self.client,
            get=self._get,
            post=self._post,
            delete=self._delete,
            update=lambda identifier, values: self.update(identifier, **values),
        )
        return AsyncContact(data, context)

    async def list(self, *, page: int | None = None, per_page: int | None = None) -> PaginatedResponse[AsyncContact]:
        return await self._list(without_none({"page": page, "per_page": per_page}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None
    ) -> AsyncIterator[PaginatedResponse[AsyncContact]]:
        return cast(
            AsyncIterator[PaginatedResponse[AsyncContact]],
            _async_cursor(self, without_none({"page": page, "per_page": per_page})),
        )

    async def list_all(self, *, page: int | None = None, per_page: int | None = None) -> AsyncIterator[AsyncContact]:
        async for result in self.cursor(page=page, per_page=per_page):
            for item in result.data:
                yield item

    async def get(self, identifier: ContactIdentifier) -> AsyncContact:
        payload = cast(dict[str, Any], await self._get([identifier]))
        return self._make_model(payload["data"])

    async def create(
        self, *, attributes: Mapping[str, AttributeValue], subscribed: bool | _UnsetType = UNSET
    ) -> AsyncContact:
        data = without_unset({"attributes": dict(attributes), "subscribed": subscribed})
        payload = cast(dict[str, Any], await self._post(data=data))
        return self._make_model(payload["data"])

    async def update(
        self,
        identifier: ContactIdentifier,
        *,
        attributes: Mapping[str, AttributeValue] | _UnsetType = UNSET,
        subscribed: bool | _UnsetType = UNSET,
    ) -> AsyncContact:
        data = without_unset(
            {
                "attributes": dict(attributes) if not isinstance(attributes, _UnsetType) else UNSET,
                "subscribed": subscribed,
            }
        )
        payload = cast(dict[str, Any], await self._post([identifier], data=data))
        return self._make_model(payload["data"])

    async def subscribe(self, identifier: ContactIdentifier) -> AsyncContact:
        payload = cast(dict[str, Any], await self._post([identifier, "subscribe"]))
        return self._make_model(payload["data"])

    async def unsubscribe(self, identifier: ContactIdentifier) -> AsyncContact:
        payload = cast(dict[str, Any], await self._post([identifier, "unsubscribe"]))
        return self._make_model(payload["data"])

    def events(self, identifier: ContactIdentifier) -> AsyncContactEvents:
        return AsyncContactEvents(self.client, identifier)


class ContactEvents(SyncResource[ContactEvent]):
    model_class = ContactEvent

    def __init__(self, client: Leadpush, contact_identifier: ContactIdentifier) -> None:
        super().__init__(client)
        self.contact_identifier = contact_identifier
        self.endpoint = ("contacts", contact_identifier, "events")

    def list(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> PaginatedResponse[ContactEvent]:
        return self._list(without_none({"page": page, "per_page": per_page, "search": search}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> Iterator[PaginatedResponse[ContactEvent]]:
        return cast(
            Iterator[PaginatedResponse[ContactEvent]],
            _sync_cursor(self, without_none({"page": page, "per_page": per_page, "search": search})),
        )

    def list_all(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> Iterator[ContactEvent]:
        for result in self.cursor(page=page, per_page=per_page, search=search):
            yield from result.data

    def create(self, *, event_name: str, attributes: ContactEventAttributes | _UnsetType = UNSET) -> None:
        data = without_unset(
            {
                "event_name": event_name,
                "attributes": json.dumps(attributes, separators=(",", ":"))
                if not isinstance(attributes, _UnsetType)
                else UNSET,
            }
        )
        self._post(data=data)


class AsyncContactEvents(AsyncResource[ContactEvent]):
    model_class = ContactEvent

    def __init__(self, client: AsyncLeadpush, contact_identifier: ContactIdentifier) -> None:
        super().__init__(client)
        self.contact_identifier = contact_identifier
        self.endpoint = ("contacts", contact_identifier, "events")

    async def list(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> PaginatedResponse[ContactEvent]:
        return await self._list(without_none({"page": page, "per_page": per_page, "search": search}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> AsyncIterator[PaginatedResponse[ContactEvent]]:
        return cast(
            AsyncIterator[PaginatedResponse[ContactEvent]],
            _async_cursor(self, without_none({"page": page, "per_page": per_page, "search": search})),
        )

    async def list_all(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> AsyncIterator[ContactEvent]:
        async for result in self.cursor(page=page, per_page=per_page, search=search):
            for item in result.data:
                yield item

    async def create(self, *, event_name: str, attributes: ContactEventAttributes | _UnsetType = UNSET) -> None:
        data = without_unset(
            {
                "event_name": event_name,
                "attributes": json.dumps(attributes, separators=(",", ":"))
                if not isinstance(attributes, _UnsetType)
                else UNSET,
            }
        )
        await self._post(data=data)


class Domains(SyncResource[Domain]):
    endpoint = ("domains",)
    model_class = Domain

    def _make_model(self, data: Mapping[str, Any]) -> Domain:
        context = SyncModelContext(
            client=self.client,
            get=self._get,
            post=self._post,
            delete=self._delete,
            update=lambda _identifier, _values: (_ for _ in ()).throw(
                UnsupportedEndpointError("This resource does not support model updates.")
            ),
        )
        return Domain(data, context)

    def list(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> PaginatedResponse[Domain]:
        return self._list(without_none({"page": page, "per_page": per_page, "search": search}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> Iterator[PaginatedResponse[Domain]]:
        return cast(
            Iterator[PaginatedResponse[Domain]],
            _sync_cursor(self, without_none({"page": page, "per_page": per_page, "search": search})),
        )

    def list_all(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> Iterator[Domain]:
        for result in self.cursor(page=page, per_page=per_page, search=search):
            yield from result.data

    def get(self, uuid: str) -> Domain:
        payload = cast(dict[str, Any], self._get([uuid]))
        return self._make_model(payload["data"])

    def create(
        self,
        *,
        name: str,
        dkim_selectors: Sequence[str] | _UnsetType | None = UNSET,
        tracking_subdomain: str | _UnsetType | None = UNSET,
        tracking_mode: DomainTrackingMode | _UnsetType | None = UNSET,
    ) -> Domain:
        data = without_unset(
            {
                "name": name,
                "dkim_selectors": list(dkim_selectors)
                if not isinstance(dkim_selectors, _UnsetType) and dkim_selectors is not None
                else dkim_selectors,
                "tracking_subdomain": tracking_subdomain,
                "tracking_mode": tracking_mode,
            }
        )
        payload = cast(dict[str, Any], self._post(data=data))
        return self._make_model(payload["data"])

    def verify(self, uuid: str) -> Domain:
        payload = cast(dict[str, Any], self._post([uuid, "verification"]))
        return self._make_model(payload["data"])

    def delete(self, uuid: str) -> None:
        self._delete([uuid])

    def addresses(self, uuid: str) -> DomainAddresses:
        return DomainAddresses(self.client, uuid)


class AsyncDomains(AsyncResource[AsyncDomain]):
    endpoint = ("domains",)
    model_class = AsyncDomain

    def _make_model(self, data: Mapping[str, Any]) -> AsyncDomain:
        context = AsyncModelContext(
            client=self.client,
            get=self._get,
            post=self._post,
            delete=self._delete,
            update=self._unsupported_update,
        )
        return AsyncDomain(data, context)

    async def _unsupported_update(self, _identifier: str, _values: Mapping[str, Any]) -> Any:
        raise UnsupportedEndpointError("This resource does not support model updates.")

    async def list(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> PaginatedResponse[AsyncDomain]:
        return await self._list(without_none({"page": page, "per_page": per_page, "search": search}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> AsyncIterator[PaginatedResponse[AsyncDomain]]:
        return cast(
            AsyncIterator[PaginatedResponse[AsyncDomain]],
            _async_cursor(self, without_none({"page": page, "per_page": per_page, "search": search})),
        )

    async def list_all(
        self, *, page: int | None = None, per_page: int | None = None, search: str | None = None
    ) -> AsyncIterator[AsyncDomain]:
        async for result in self.cursor(page=page, per_page=per_page, search=search):
            for item in result.data:
                yield item

    async def get(self, uuid: str) -> AsyncDomain:
        payload = cast(dict[str, Any], await self._get([uuid]))
        return self._make_model(payload["data"])

    async def create(
        self,
        *,
        name: str,
        dkim_selectors: Sequence[str] | _UnsetType | None = UNSET,
        tracking_subdomain: str | _UnsetType | None = UNSET,
        tracking_mode: DomainTrackingMode | _UnsetType | None = UNSET,
    ) -> AsyncDomain:
        data = without_unset(
            {
                "name": name,
                "dkim_selectors": list(dkim_selectors)
                if not isinstance(dkim_selectors, _UnsetType) and dkim_selectors is not None
                else dkim_selectors,
                "tracking_subdomain": tracking_subdomain,
                "tracking_mode": tracking_mode,
            }
        )
        payload = cast(dict[str, Any], await self._post(data=data))
        return self._make_model(payload["data"])

    async def verify(self, uuid: str) -> AsyncDomain:
        payload = cast(dict[str, Any], await self._post([uuid, "verification"]))
        return self._make_model(payload["data"])

    async def delete(self, uuid: str) -> None:
        await self._delete([uuid])

    def addresses(self, uuid: str) -> AsyncDomainAddresses:
        return AsyncDomainAddresses(self.client, uuid)


class DomainAddresses(SyncResource[DomainAddress]):
    model_class = DomainAddress

    def __init__(self, client: Leadpush, domain_uuid: str) -> None:
        super().__init__(client)
        self.domain_uuid = domain_uuid
        self.endpoint = ("domains", domain_uuid, "addresses")

    def _make_model(self, data: Mapping[str, Any]) -> DomainAddress:
        context = SyncModelContext(
            client=self.client,
            get=self._get,
            post=self._post,
            delete=self._delete,
            update=lambda _identifier, _values: (_ for _ in ()).throw(
                UnsupportedEndpointError("This resource does not support model updates.")
            ),
        )
        return DomainAddress(data, context)

    def list(self, *, page: int | None = None, per_page: int | None = None) -> PaginatedResponse[DomainAddress]:
        return self._list(without_none({"page": page, "per_page": per_page}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None
    ) -> Iterator[PaginatedResponse[DomainAddress]]:
        return cast(
            Iterator[PaginatedResponse[DomainAddress]],
            _sync_cursor(self, without_none({"page": page, "per_page": per_page})),
        )

    def list_all(self, *, page: int | None = None, per_page: int | None = None) -> Iterator[DomainAddress]:
        for result in self.cursor(page=page, per_page=per_page):
            yield from result.data

    def get(self, uuid: str) -> DomainAddress:
        payload = cast(dict[str, Any], self._get([uuid]))
        return self._make_model(payload["data"])

    def create(
        self,
        *,
        address: str,
        display_name: str,
        reply_to: str,
        company_address: str,
        company_city: str,
        company_state: str,
        company_zip: str,
        company_country: str,
        company_address_2: str | _UnsetType | None = UNSET,
    ) -> DomainAddress:
        data = without_unset(
            {
                "address": address,
                "display_name": display_name,
                "reply_to": reply_to,
                "company_address": company_address,
                "company_address_2": company_address_2,
                "company_city": company_city,
                "company_state": company_state,
                "company_zip": company_zip,
                "company_country": company_country,
            }
        )
        payload = cast(dict[str, Any], self._post(data=data))
        return self._make_model(payload["data"])

    def delete(self, uuid: str) -> None:
        self._delete([uuid])


class AsyncDomainAddresses(AsyncResource[AsyncDomainAddress]):
    model_class = AsyncDomainAddress

    def __init__(self, client: AsyncLeadpush, domain_uuid: str) -> None:
        super().__init__(client)
        self.domain_uuid = domain_uuid
        self.endpoint = ("domains", domain_uuid, "addresses")

    def _make_model(self, data: Mapping[str, Any]) -> AsyncDomainAddress:
        context = AsyncModelContext(
            client=self.client,
            get=self._get,
            post=self._post,
            delete=self._delete,
            update=self._unsupported_update,
        )
        return AsyncDomainAddress(data, context)

    async def _unsupported_update(self, _identifier: str, _values: Mapping[str, Any]) -> Any:
        raise UnsupportedEndpointError("This resource does not support model updates.")

    async def list(
        self, *, page: int | None = None, per_page: int | None = None
    ) -> PaginatedResponse[AsyncDomainAddress]:
        return await self._list(without_none({"page": page, "per_page": per_page}))

    def cursor(
        self, *, page: int | None = None, per_page: int | None = None
    ) -> AsyncIterator[PaginatedResponse[AsyncDomainAddress]]:
        return cast(
            AsyncIterator[PaginatedResponse[AsyncDomainAddress]],
            _async_cursor(self, without_none({"page": page, "per_page": per_page})),
        )

    async def list_all(
        self, *, page: int | None = None, per_page: int | None = None
    ) -> AsyncIterator[AsyncDomainAddress]:
        async for result in self.cursor(page=page, per_page=per_page):
            for item in result.data:
                yield item

    async def get(self, uuid: str) -> AsyncDomainAddress:
        payload = cast(dict[str, Any], await self._get([uuid]))
        return self._make_model(payload["data"])

    async def create(
        self,
        *,
        address: str,
        display_name: str,
        reply_to: str,
        company_address: str,
        company_city: str,
        company_state: str,
        company_zip: str,
        company_country: str,
        company_address_2: str | _UnsetType | None = UNSET,
    ) -> AsyncDomainAddress:
        data = without_unset(
            {
                "address": address,
                "display_name": display_name,
                "reply_to": reply_to,
                "company_address": company_address,
                "company_address_2": company_address_2,
                "company_city": company_city,
                "company_state": company_state,
                "company_zip": company_zip,
                "company_country": company_country,
            }
        )
        payload = cast(dict[str, Any], await self._post(data=data))
        return self._make_model(payload["data"])

    async def delete(self, uuid: str) -> None:
        await self._delete([uuid])


class Emails(SyncResource[EmailSend]):
    endpoint = ("emails",)
    model_class = EmailSend

    def send(
        self,
        *,
        from_address: str,
        subject: str,
        html: str | _UnsetType = UNSET,
        text: str | _UnsetType = UNSET,
        to: Sequence[str] | _UnsetType = UNSET,
        bcc: Sequence[str] | _UnsetType = UNSET,
        reply_to: str | _UnsetType = UNSET,
        headers: Mapping[str, str] | _UnsetType = UNSET,
    ) -> EmailSend:
        data = without_unset(
            {
                "from": from_address,
                "subject": subject,
                "html": html,
                "text": text,
                "to": list(to) if not isinstance(to, _UnsetType) else UNSET,
                "bcc": list(bcc) if not isinstance(bcc, _UnsetType) else UNSET,
                "reply_to": reply_to,
                "headers": dict(headers) if not isinstance(headers, _UnsetType) else UNSET,
            }
        )
        payload = cast(dict[str, Any], self._post(data=data))
        return self._make_model(payload["data"])


class AsyncEmails(AsyncResource[EmailSend]):
    endpoint = ("emails",)
    model_class = EmailSend

    async def send(
        self,
        *,
        from_address: str,
        subject: str,
        html: str | _UnsetType = UNSET,
        text: str | _UnsetType = UNSET,
        to: Sequence[str] | _UnsetType = UNSET,
        bcc: Sequence[str] | _UnsetType = UNSET,
        reply_to: str | _UnsetType = UNSET,
        headers: Mapping[str, str] | _UnsetType = UNSET,
    ) -> EmailSend:
        data = without_unset(
            {
                "from": from_address,
                "subject": subject,
                "html": html,
                "text": text,
                "to": list(to) if not isinstance(to, _UnsetType) else UNSET,
                "bcc": list(bcc) if not isinstance(bcc, _UnsetType) else UNSET,
                "reply_to": reply_to,
                "headers": dict(headers) if not isinstance(headers, _UnsetType) else UNSET,
            }
        )
        payload = cast(dict[str, Any], await self._post(data=data))
        return self._make_model(payload["data"])


class Fields(SyncResource[Field]):
    endpoint = ("fields",)
    model_class = Field

    def list(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[FieldTypeFilter] | None = None,
    ) -> PaginatedResponse[Field]:
        return self._list(without_none({"page": page, "per_page": per_page, "search": search, "filters": filters}))

    def cursor(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[FieldTypeFilter] | None = None,
    ) -> Iterator[PaginatedResponse[Field]]:
        params = without_none({"page": page, "per_page": per_page, "search": search, "filters": filters})
        return cast(Iterator[PaginatedResponse[Field]], _sync_cursor(self, params))

    def list_all(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[FieldTypeFilter] | None = None,
    ) -> Iterator[Field]:
        for result in self.cursor(page=page, per_page=per_page, search=search, filters=filters):
            yield from result.data

    def get(self, uuid: str) -> Field:
        payload = cast(dict[str, Any], self._get([uuid]))
        return self._make_model(payload["data"])

    def create(
        self,
        *,
        name: str,
        type: FieldType,
        format: Mapping[str, Any] | FieldFormat | _UnsetType | None = UNSET,
    ) -> Field:
        data = without_unset({"name": name, "type": type, "format": _mapping_value(format)})
        payload = cast(dict[str, Any], self._post(data=data))
        return self._make_model(payload["data"])

    def update(
        self,
        uuid: str,
        *,
        name: str | _UnsetType = UNSET,
        type: FieldType | _UnsetType = UNSET,
        format: Mapping[str, Any] | FieldFormat | _UnsetType | None = UNSET,
    ) -> Field:
        data = without_unset({"name": name, "type": type, "format": _mapping_value(format)})
        payload = cast(dict[str, Any], self._post([uuid], data=data))
        return self._make_model(payload["data"])


class AsyncFields(AsyncResource[Field]):
    endpoint = ("fields",)
    model_class = Field

    async def list(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[FieldTypeFilter] | None = None,
    ) -> PaginatedResponse[Field]:
        return await self._list(
            without_none({"page": page, "per_page": per_page, "search": search, "filters": filters})
        )

    def cursor(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[FieldTypeFilter] | None = None,
    ) -> AsyncIterator[PaginatedResponse[Field]]:
        params = without_none({"page": page, "per_page": per_page, "search": search, "filters": filters})
        return cast(AsyncIterator[PaginatedResponse[Field]], _async_cursor(self, params))

    async def list_all(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[FieldTypeFilter] | None = None,
    ) -> AsyncIterator[Field]:
        async for result in self.cursor(page=page, per_page=per_page, search=search, filters=filters):
            for item in result.data:
                yield item

    async def get(self, uuid: str) -> Field:
        payload = cast(dict[str, Any], await self._get([uuid]))
        return self._make_model(payload["data"])

    async def create(
        self,
        *,
        name: str,
        type: FieldType,
        format: Mapping[str, Any] | FieldFormat | _UnsetType | None = UNSET,
    ) -> Field:
        data = without_unset({"name": name, "type": type, "format": _mapping_value(format)})
        payload = cast(dict[str, Any], await self._post(data=data))
        return self._make_model(payload["data"])

    async def update(
        self,
        uuid: str,
        *,
        name: str | _UnsetType = UNSET,
        type: FieldType | _UnsetType = UNSET,
        format: Mapping[str, Any] | FieldFormat | _UnsetType | None = UNSET,
    ) -> Field:
        data = without_unset({"name": name, "type": type, "format": _mapping_value(format)})
        payload = cast(dict[str, Any], await self._post([uuid], data=data))
        return self._make_model(payload["data"])


class Suppressions(SyncResource[Suppression]):
    endpoint = ("suppressions",)
    model_class = Suppression

    def list(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[SuppressionTypeFilter] | None = None,
    ) -> PaginatedResponse[Suppression]:
        return self._list(without_none({"page": page, "per_page": per_page, "search": search, "filters": filters}))

    def cursor(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[SuppressionTypeFilter] | None = None,
    ) -> Iterator[PaginatedResponse[Suppression]]:
        params = without_none({"page": page, "per_page": per_page, "search": search, "filters": filters})
        return cast(Iterator[PaginatedResponse[Suppression]], _sync_cursor(self, params))

    def list_all(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[SuppressionTypeFilter] | None = None,
    ) -> Iterator[Suppression]:
        for result in self.cursor(page=page, per_page=per_page, search=search, filters=filters):
            yield from result.data

    def get(self, uuid: str) -> Suppression:
        payload = cast(dict[str, Any], self._get([uuid]))
        return self._make_model(payload["data"])

    def create(self, *, email: str, type: SuppressionType | _UnsetType = UNSET) -> Suppression:
        payload = cast(dict[str, Any], self._post(data=without_unset({"email": email, "type": type})))
        return self._make_model(payload["data"])

    def update(self, uuid: str, **data: Any) -> Suppression:
        del uuid, data
        raise UnsupportedEndpointError("The suppressions update endpoint is not supported.")


class AsyncSuppressions(AsyncResource[Suppression]):
    endpoint = ("suppressions",)
    model_class = Suppression

    async def list(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[SuppressionTypeFilter] | None = None,
    ) -> PaginatedResponse[Suppression]:
        return await self._list(
            without_none({"page": page, "per_page": per_page, "search": search, "filters": filters})
        )

    def cursor(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[SuppressionTypeFilter] | None = None,
    ) -> AsyncIterator[PaginatedResponse[Suppression]]:
        params = without_none({"page": page, "per_page": per_page, "search": search, "filters": filters})
        return cast(AsyncIterator[PaginatedResponse[Suppression]], _async_cursor(self, params))

    async def list_all(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
        search: str | None = None,
        filters: Sequence[SuppressionTypeFilter] | None = None,
    ) -> AsyncIterator[Suppression]:
        async for result in self.cursor(page=page, per_page=per_page, search=search, filters=filters):
            for item in result.data:
                yield item

    async def get(self, uuid: str) -> Suppression:
        payload = cast(dict[str, Any], await self._get([uuid]))
        return self._make_model(payload["data"])

    async def create(self, *, email: str, type: SuppressionType | _UnsetType = UNSET) -> Suppression:
        payload = cast(dict[str, Any], await self._post(data=without_unset({"email": email, "type": type})))
        return self._make_model(payload["data"])

    async def update(self, uuid: str, **data: Any) -> Suppression:
        del uuid, data
        raise UnsupportedEndpointError("The suppressions update endpoint is not supported.")


def _mapping_value(value: Mapping[str, Any] | Model | _UnsetType | None) -> Mapping[str, Any] | _UnsetType | None:
    if isinstance(value, Model):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    return value
