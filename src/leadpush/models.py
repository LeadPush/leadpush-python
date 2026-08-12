from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal, TypedDict, cast

from .errors import DetachedModelError

if TYPE_CHECKING:
    from .client import AsyncLeadpush, Leadpush
    from .resources import AsyncContactEvents, AsyncDomainAddresses, ContactEvents, DomainAddresses

AttributeValue = str | int | float | bool | None
Attributes = Mapping[str, AttributeValue]
ContactIdentifier = str
ContactEventAttributes = Mapping[str, Any]

DomainProvider = Literal["aws", "leadpush"]
DomainStatus = Literal["pending"]
DomainVerification = Literal["pending", "completed", "failed"]
DomainTrackingMode = Literal["direct", "cloudflare"]

EmailRecipientType = Literal["to", "bcc"]

FieldType = Literal["integer", "text", "date", "datetime", "boolean"]
FieldTextFormat = Literal["email", "phone", "uuid", "url", "regex"]

SuppressionType = Literal["bounce", "complaint", "manual"]


class FieldTypeFilter(TypedDict):
    id: Literal["type"]
    value: Sequence[FieldType]


class SuppressionTypeFilter(TypedDict):
    id: Literal["type"]
    value: Sequence[SuppressionType]


@dataclass(frozen=True)
class SyncModelContext:
    client: Leadpush
    get: Callable[..., Any]
    post: Callable[..., Any]
    delete: Callable[..., Any]
    update: Callable[[str, Mapping[str, Any]], Any]


@dataclass(frozen=True)
class AsyncModelContext:
    client: AsyncLeadpush
    get: Callable[..., Awaitable[Any]]
    post: Callable[..., Awaitable[Any]]
    delete: Callable[..., Awaitable[Any]]
    update: Callable[[str, Mapping[str, Any]], Awaitable[Any]]


class Model:
    """Base class for Leadpush API response models."""

    def __init__(self, data: Mapping[str, Any]) -> None:
        self._data = deepcopy(dict(data))
        self._dirty: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """Return a detached copy of the raw API-shaped data."""
        return deepcopy(self._data)

    def _clear_dirty(self) -> None:
        self._dirty = {}

    def _get_dirty(self) -> dict[str, Any]:
        return deepcopy(self._dirty)

    def _is_dirty(self) -> bool:
        return bool(self._dirty)

    def _replace_data(self, data: Mapping[str, Any]) -> None:
        self._data = deepcopy(dict(data))

    def _set_dirty(self, key: str, value: Any) -> None:
        self._dirty[key] = deepcopy(value)


class ContactBase(Model):
    """Shared data view for synchronous and asynchronous contacts."""

    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def subscribed(self) -> bool:
        return bool(self._data["subscribed"])

    @subscribed.setter
    def subscribed(self, value: bool) -> None:
        self._data["subscribed"] = value
        self._set_dirty("subscribed", value)

    @property
    def attributes(self) -> dict[str, AttributeValue]:
        return deepcopy(cast(dict[str, AttributeValue], self._data.get("attributes", {})))

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        attributes = self.attributes
        attributes[key] = value
        self._data["attributes"] = attributes

        dirty_attributes = cast(dict[str, AttributeValue], self._dirty.get("attributes", {})).copy()
        dirty_attributes[key] = value
        self._set_dirty("attributes", dirty_attributes)

    @property
    def provider(self) -> str | None:
        value = self._data.get("provider")
        return None if value is None else str(value)

    @property
    def created_at(self) -> datetime:
        return _datetime(self._data["created_at"])

    @property
    def updated_at(self) -> datetime:
        return _datetime(self._data["updated_at"])


class Contact(ContactBase):
    """Contact returned by the synchronous Leadpush client."""

    def __init__(self, data: Mapping[str, Any], context: SyncModelContext | None = None) -> None:
        super().__init__(data)
        self._context = context

    def update(self) -> Contact:
        if not self._is_dirty():
            return self

        updated = self._require_context().update(self.uuid, self._get_dirty())
        self._replace_data(cast(Contact, updated).to_dict())
        self._clear_dirty()
        return self

    def subscribe(self) -> Contact:
        payload = self._require_context().post([self.uuid, "subscribe"])
        self._replace_data(cast(dict[str, Any], payload)["data"])
        self._clear_dirty()
        return self

    def unsubscribe(self) -> Contact:
        payload = self._require_context().post([self.uuid, "unsubscribe"])
        self._replace_data(cast(dict[str, Any], payload)["data"])
        self._clear_dirty()
        return self

    @property
    def events(self) -> ContactEvents:
        from .resources import ContactEvents

        return ContactEvents(self._require_context().client, self.uuid)

    def _require_context(self) -> SyncModelContext:
        if self._context is None:
            raise DetachedModelError
        return self._context


class AsyncContact(ContactBase):
    """Contact returned by the asynchronous Leadpush client."""

    def __init__(self, data: Mapping[str, Any], context: AsyncModelContext | None = None) -> None:
        super().__init__(data)
        self._context = context

    async def update(self) -> AsyncContact:
        if not self._is_dirty():
            return self

        updated = await self._require_context().update(self.uuid, self._get_dirty())
        self._replace_data(cast(AsyncContact, updated).to_dict())
        self._clear_dirty()
        return self

    async def subscribe(self) -> AsyncContact:
        payload = await self._require_context().post([self.uuid, "subscribe"])
        self._replace_data(cast(dict[str, Any], payload)["data"])
        self._clear_dirty()
        return self

    async def unsubscribe(self) -> AsyncContact:
        payload = await self._require_context().post([self.uuid, "unsubscribe"])
        self._replace_data(cast(dict[str, Any], payload)["data"])
        self._clear_dirty()
        return self

    @property
    def events(self) -> AsyncContactEvents:
        from .resources import AsyncContactEvents

        return AsyncContactEvents(self._require_context().client, self.uuid)

    def _require_context(self) -> AsyncModelContext:
        if self._context is None:
            raise DetachedModelError
        return self._context


class ContactEvent(Model):
    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def event_name(self) -> str:
        return str(self._data["event_name"])

    @property
    def type(self) -> str:
        """Deprecated alias for :attr:`event_name`."""
        return self.event_name

    @property
    def attributes(self) -> dict[str, Any] | None:
        value = self._data.get("attributes")
        return None if value is None else deepcopy(cast(dict[str, Any], value))

    @property
    def created_at(self) -> datetime:
        return _datetime(self._data["created_at"])


class DomainDnsRecord(Model):
    @property
    def type(self) -> str:
        return str(self._data["type"])

    @property
    def name(self) -> str:
        return str(self._data["name"])

    @property
    def value(self) -> str:
        return str(self._data["value"])

    @property
    def is_valid(self) -> bool:
        return bool(self._data["is_valid"])


class DomainBase(Model):
    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def name(self) -> str:
        return str(self._data["name"])

    @property
    def domain(self) -> str:
        return str(self._data["domain"])

    @property
    def verified(self) -> bool:
        return bool(self._data["verified"])

    @property
    def provider(self) -> DomainProvider:
        return cast(DomainProvider, self._data["provider"])

    @property
    def status(self) -> DomainStatus:
        return cast(DomainStatus, self._data["status"])

    @property
    def verification(self) -> DomainVerification:
        return cast(DomainVerification, self._data["verification"])

    @property
    def mail_from_domain(self) -> str:
        return str(self._data["mail_from_domain"])

    @property
    def mail_from_verified(self) -> bool:
        return bool(self._data["mail_from_verified"])

    @property
    def dns(self) -> list[DomainDnsRecord]:
        return [DomainDnsRecord(item) for item in cast(list[dict[str, Any]], self._data.get("dns", []))]

    @property
    def created_at(self) -> datetime:
        return _datetime(self._data["created_at"])

    @property
    def updated_at(self) -> datetime:
        return _datetime(self._data["updated_at"])


class Domain(DomainBase):
    def __init__(self, data: Mapping[str, Any], context: SyncModelContext | None = None) -> None:
        super().__init__(data)
        self._context = context

    def verify(self) -> Domain:
        payload = self._require_context().post([self.uuid, "verification"])
        self._replace_data(cast(dict[str, Any], payload)["data"])
        self._clear_dirty()
        return self

    def delete(self) -> None:
        self._require_context().delete([self.uuid])

    @property
    def addresses(self) -> DomainAddresses:
        from .resources import DomainAddresses

        return DomainAddresses(self._require_context().client, self.uuid)

    def _require_context(self) -> SyncModelContext:
        if self._context is None:
            raise DetachedModelError
        return self._context


class AsyncDomain(DomainBase):
    def __init__(self, data: Mapping[str, Any], context: AsyncModelContext | None = None) -> None:
        super().__init__(data)
        self._context = context

    async def verify(self) -> AsyncDomain:
        payload = await self._require_context().post([self.uuid, "verification"])
        self._replace_data(cast(dict[str, Any], payload)["data"])
        self._clear_dirty()
        return self

    async def delete(self) -> None:
        await self._require_context().delete([self.uuid])

    @property
    def addresses(self) -> AsyncDomainAddresses:
        from .resources import AsyncDomainAddresses

        return AsyncDomainAddresses(self._require_context().client, self.uuid)

    def _require_context(self) -> AsyncModelContext:
        if self._context is None:
            raise DetachedModelError
        return self._context


class DomainAddressBase(Model):
    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def domain_uuid(self) -> str:
        return str(self._data["domain_uuid"])

    @property
    def address(self) -> str:
        return str(self._data["address"])

    @property
    def full_address(self) -> str:
        return str(self._data["full_address"])

    @property
    def provider(self) -> DomainProvider | None:
        return cast(DomainProvider | None, self._data.get("provider"))

    @property
    def display_name(self) -> str:
        return str(self._data["display_name"])

    @property
    def verification(self) -> DomainVerification:
        return cast(DomainVerification, self._data["verification"])

    @property
    def created_at(self) -> datetime:
        return _datetime(self._data["created_at"])

    @property
    def updated_at(self) -> datetime:
        return _datetime(self._data["updated_at"])


class DomainAddress(DomainAddressBase):
    def __init__(self, data: Mapping[str, Any], context: SyncModelContext | None = None) -> None:
        super().__init__(data)
        self._context = context

    def delete(self) -> None:
        self._require_context().delete([self.uuid])

    def _require_context(self) -> SyncModelContext:
        if self._context is None:
            raise DetachedModelError
        return self._context


class AsyncDomainAddress(DomainAddressBase):
    def __init__(self, data: Mapping[str, Any], context: AsyncModelContext | None = None) -> None:
        super().__init__(data)
        self._context = context

    async def delete(self) -> None:
        await self._require_context().delete([self.uuid])

    def _require_context(self) -> AsyncModelContext:
        if self._context is None:
            raise DetachedModelError
        return self._context


class FieldFormat(Model):
    @property
    def text(self) -> FieldTextFormat | None:
        return cast(FieldTextFormat | None, self._data.get("text"))

    @property
    def pattern(self) -> str | None:
        value = self._data.get("pattern")
        return None if value is None else str(value)

    @property
    def iso_format(self) -> str | None:
        value = self._data.get("iso_format")
        return None if value is None else str(value)


class Field(Model):
    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def name(self) -> str:
        return str(self._data["name"])

    @property
    def type(self) -> FieldType:
        return cast(FieldType, self._data["type"])

    @property
    def format(self) -> FieldFormat | None:
        value = self._data.get("format")
        return None if value is None else FieldFormat(cast(dict[str, Any], value))

    @property
    def created_at(self) -> datetime:
        return _datetime(self._data["created_at"])


class Suppression(Model):
    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def email(self) -> str:
        return str(self._data["email"])

    @property
    def type(self) -> SuppressionType:
        return cast(SuppressionType, self._data["type"])

    @property
    def created_at(self) -> datetime:
        return _datetime(self._data["created_at"])


class EmailSendMessage(Model):
    @property
    def uuid(self) -> str:
        return str(self._data["uuid"])

    @property
    def recipient(self) -> str:
        return str(self._data["recipient"])

    @property
    def type(self) -> EmailRecipientType:
        return cast(EmailRecipientType, self._data["type"])

    @property
    def from_address(self) -> str:
        return str(self._data["from"])

    @property
    def status(self) -> str:
        return str(self._data["status"])


class EmailSend(Model):
    @property
    def accepted(self) -> bool:
        return bool(self._data["accepted"])

    @property
    def message_count(self) -> int:
        return int(self._data["message_count"])

    @property
    def messages(self) -> list[EmailSendMessage]:
        return [EmailSendMessage(item) for item in cast(list[dict[str, Any]], self._data.get("messages", []))]


def _datetime(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
