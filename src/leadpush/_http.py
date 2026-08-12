from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

import httpx

from ._types import RequestParams, RequestPath
from .errors import ApiError, ForbiddenError, NotFoundError, TimeoutError, UnauthorizedError, ValidationError


class SyncHttpClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_version: str,
        base_url: str,
        headers: Mapping[str, str],
        sdk_name: str,
        sdk_version: str,
        timeout: float | None,
        user_agent: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_version = api_version
        self._base_url = base_url
        self._headers = dict(headers)
        self._sdk_name = sdk_name
        self._sdk_version = sdk_version
        self._timeout = timeout
        self._user_agent = user_agent
        self._owns_client = client is None
        self._client = client or httpx.Client()

    def get(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(
        self, path: RequestPath, data: Mapping[str, Any] | None = None, params: RequestParams | None = None
    ) -> Any:
        return self.request("POST", path, data=data, params=params)

    def delete(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        return self.request("DELETE", path, params=params)

    def request(
        self,
        method: str,
        path: RequestPath,
        *,
        data: Mapping[str, Any] | None = None,
        params: RequestParams | None = None,
    ) -> Any:
        content = None if data is None else json.dumps(data, separators=(",", ":"))

        try:
            response = self._client.request(
                method,
                self._url(path, params or {}),
                headers=self._request_headers(has_body=data is not None),
                content=content,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as error:
            raise TimeoutError(self._timeout) from error

        return _parse_response(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _url(self, path: RequestPath, params: RequestParams) -> str:
        segments = _path_segments(path)
        suffix = "/".join(quote(segment, safe="") for segment in segments)
        url = self._base_url.rstrip("/")

        if suffix:
            url = f"{url}/{suffix}"

        query = _query_string(params)
        return url if not query else f"{url}?{query}"

    def _request_headers(self, *, has_body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "X-Leadpush-API-Version": self._api_version,
            "X-Leadpush-SDK": self._sdk_name,
            "X-Leadpush-SDK-Version": self._sdk_version,
            **self._headers,
            "User-Agent": self._user_agent,
        }

        if has_body:
            headers["Content-Type"] = "application/json"

        return headers


class AsyncHttpClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_version: str,
        base_url: str,
        headers: Mapping[str, str],
        sdk_name: str,
        sdk_version: str,
        timeout: float | None,
        user_agent: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_version = api_version
        self._base_url = base_url
        self._headers = dict(headers)
        self._sdk_name = sdk_name
        self._sdk_version = sdk_version
        self._timeout = timeout
        self._user_agent = user_agent
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient()

    async def get(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(
        self,
        path: RequestPath,
        data: Mapping[str, Any] | None = None,
        params: RequestParams | None = None,
    ) -> Any:
        return await self.request("POST", path, data=data, params=params)

    async def delete(self, path: RequestPath, params: RequestParams | None = None) -> Any:
        return await self.request("DELETE", path, params=params)

    async def request(
        self,
        method: str,
        path: RequestPath,
        *,
        data: Mapping[str, Any] | None = None,
        params: RequestParams | None = None,
    ) -> Any:
        content = None if data is None else json.dumps(data, separators=(",", ":"))

        try:
            response = await self._client.request(
                method,
                self._url(path, params or {}),
                headers=self._request_headers(has_body=data is not None),
                content=content,
                timeout=self._timeout,
            )
        except httpx.TimeoutException as error:
            raise TimeoutError(self._timeout) from error

        return _parse_response(response)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _url(self, path: RequestPath, params: RequestParams) -> str:
        segments = _path_segments(path)
        suffix = "/".join(quote(segment, safe="") for segment in segments)
        url = self._base_url.rstrip("/")

        if suffix:
            url = f"{url}/{suffix}"

        query = _query_string(params)
        return url if not query else f"{url}?{query}"

    def _request_headers(self, *, has_body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "X-Leadpush-API-Version": self._api_version,
            "X-Leadpush-SDK": self._sdk_name,
            "X-Leadpush-SDK-Version": self._sdk_version,
            **self._headers,
            "User-Agent": self._user_agent,
        }

        if has_body:
            headers["Content-Type"] = "application/json"

        return headers


def _path_segments(path: RequestPath) -> list[str]:
    if isinstance(path, str):
        return [segment for segment in path.split("/") if segment]

    return [str(segment) for segment in path if str(segment)]


def _query_string(params: RequestParams) -> str:
    pairs: list[str] = []

    for key, value in params.items():
        if value is None:
            continue

        serialized = _query_value(value)
        pairs.append(f"{quote(str(key), safe='')}={quote(serialized, safe='')}")

    return "&".join(pairs)


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
        return json.dumps(value, separators=(",", ":"))

    return str(value)


def _parse_response(response: httpx.Response) -> Any:
    payload = _parse_response_body(response)

    if 200 <= response.status_code < 300:
        return payload

    if response.status_code == 401:
        raise UnauthorizedError(payload)
    if response.status_code == 403:
        raise ForbiddenError(payload)
    if response.status_code == 404:
        raise NotFoundError(payload)
    if response.status_code == 422:
        raise ValidationError(payload)

    raise ApiError(response.status_code, payload)


def _parse_response_body(response: httpx.Response) -> Any:
    if not response.content:
        return None

    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text
