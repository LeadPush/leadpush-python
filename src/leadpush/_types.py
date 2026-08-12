from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

RequestPath: TypeAlias = str | Sequence[str]
RequestParams: TypeAlias = Mapping[str, Any]
ResponseData: TypeAlias = dict[str, Any]


class _UnsetType:
    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


UNSET = _UnsetType()


def without_unset(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not UNSET}


def without_none(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
