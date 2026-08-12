from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PaginationMeta:
    """Pagination metadata returned by the Leadpush API."""

    current_page: int
    per_page: int
    total: int
    last_page: int
    has_next: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaginationMeta:
        return cls(
            current_page=int(data.get("current_page", 1)),
            per_page=int(data.get("per_page", 0)),
            total=int(data.get("total", 0)),
            last_page=int(data.get("last_page", 1)),
            has_next=bool(data.get("has_next", False)),
        )

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "current_page": self.current_page,
            "per_page": self.per_page,
            "total": self.total,
            "last_page": self.last_page,
            "has_next": self.has_next,
        }


@dataclass(frozen=True, slots=True)
class PaginatedResponse(Generic[T]):
    """One page of models returned by a list operation."""

    data: list[T]
    meta: PaginationMeta

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": [item.to_dict() if hasattr(item, "to_dict") else item for item in self.data],
            "meta": self.meta.to_dict(),
        }
