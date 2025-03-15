from __future__ import annotations

import asyncio
import json
from typing import Any, Iterator
from urllib.parse import parse_qs

import attrs


@attrs.define
class Request:
    """
    A class representing an HTTP request.

    Attributes:
        headers (RequestHeader): HTTP headers.
        body (bytes): Request body.
        _parsed_body (dict | None): Parsed body cache.
        _parsed_query (dict | None): Parsed query cache.
    """

    headers: RequestHeader = attrs.field()
    body: bytes = attrs.field(default=b"")
    _parsed_body: dict | None = attrs.field(default=None, init=False)
    _parsed_query: dict | None = attrs.field(default=None, init=False)

    @classmethod
    def from_scope_and_body(cls, scope: dict[str, Any], body: bytes) -> Request:
        """
        Create a Request object from ASGI scope and body.

        :param scope: ASGI scope dictionary.
        :param body: Request body as bytes.
        :return: Request object.
        """
        headers = RequestHeader()
        headers._method = scope.get("method", "")
        headers._path = scope.get("path", "")
        headers._http_version = f"HTTP/{scope.get('http_version', '1.1')}"

        for name, value in scope.get("headers", []):
            headers[name.decode("latin1")] = value.decode("latin1")

        return cls(headers=headers, body=body)

    @classmethod
    def from_raw_data(cls, header_data: bytes, body: bytes) -> Request:
        """
        Create a Request object from raw header data and body.

        :param header_data: Raw header data as bytes.
        :param body: Request body as bytes.
        :return: Request object.
        """
        headers = RequestHeader.from_raw_headers(header_data)
        return cls(headers=headers, body=body)

    @property
    def method(self) -> str:
        """
        Get the HTTP method.

        :return: HTTP method as a string.
        """
        return self.headers.method

    @property
    def path(self) -> str:
        """
        Get the request path.

        :return: Request path as a string.
        """
        return self.headers.path

    @property
    def http_version(self) -> str:
        """
        Get the HTTP version.

        :return: HTTP version as a string.
        """
        return self.headers.http_version

    @property
    def content_type(self) -> str | None:
        """
        Get the Content-Type header.

        :return: Content-Type as a string or None.
        """
        return self.headers.content_type

    @property
    def content_length(self) -> int | None:
        """
        Get the Content-Length header.

        :return: Content-Length as an integer or None.
        """
        return self.headers.content_length

    @property
    def host(self) -> str | None:
        """
        Get the Host header.

        :return: Host as a string or None.
        """
        return self.headers.host

    @property
    def is_json(self) -> bool:
        """
        Check if the request is JSON.

        :return: True if Content-Type is application/json, else False.
        """
        return self.headers.is_json

    @property
    def is_form_data(self) -> bool:
        """
        Check if the request is form data.

        :return: True if Content-Type is application/x-www-form-urlencoded, else False.
        """
        return self.headers.is_form_data

    @property
    def query_string(self) -> str:
        """
        Get the query string from the request path.

        :return: Query string as a string.
        """
        if "?" in self.path:
            return self.path.split("?", 1)[1]
        return ""

    @property
    def path_without_query(self) -> str:
        """
        Get the request path without the query string.

        :return: Path without query string as a string.
        """
        if "?" in self.path:
            return self.path.split("?", 1)[0]
        return self.path

    @property
    def query(self) -> dict[str, str | list[str]]:
        """
        Get the parsed query parameters.

        :return: Parsed query parameters as a dictionary.
        """
        if self._parsed_query is None:
            query_string = self.query_string
            if query_string:
                parsed = parse_qs(query_string)
                self._parsed_query = {
                    k: v[0] if len(v) == 1 else v for k, v in parsed.items()
                }
            else:
                self._parsed_query = {}
        return self._parsed_query

    async def json(self) -> Any:
        """
        Parse and return the request body as JSON.

        :return: Parsed JSON data.
        :raises ValueError: If Content-Type is not application/json.
        """
        if not self.is_json:
            raise ValueError("Request Content-Type is not application/json")

        if self._parsed_body is None:
            if not self.body:
                return None
            loop = asyncio.get_event_loop()
            self._parsed_body = await loop.run_in_executor(
                None, lambda: json.loads(self.body.decode("utf-8"))
            )

        return self._parsed_body

    async def form(self) -> dict[str, str | list[str]]:
        """
        Parse and return the request body as form data.

        :return: Parsed form data as a dictionary.
        :raises ValueError: If Content-Type is not application/x-www-form-urlencoded.
        """
        if not self.is_form_data:
            raise ValueError(
                "Request Content-Type is not application/x-www-form-urlencoded"
            )

        if self._parsed_body is None:
            if not self.body:
                return {}
            loop = asyncio.get_event_loop()
            form_data = await loop.run_in_executor(
                None, lambda: parse_qs(self.body.decode("utf-8"))
            )
            self._parsed_body = {
                k: v[0] if len(v) == 1 else v for k, v in form_data.items()
            }

        return self._parsed_body

    async def text(self) -> str:
        """
        Return the request body as text.

        :return: Request body as a string.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.body.decode("utf-8", errors="replace")
        )

    def raw(self) -> bytes:
        """
        Return the raw request body.

        :return: Request body as bytes.
        """
        return self.body

    def __str__(self) -> str:
        parts = [str(self.headers)]
        if self.body:
            parts.append("")
            parts.append(self.body.decode("utf-8", errors="replace"))
        return "\n".join(parts)


@attrs.define
class RequestHeader:
    """
    A class representing HTTP request headers.

    Attributes:
        _headers (dict[str, str]): Dictionary of headers.
        _method (str): HTTP method.
        _path (str): Request path.
        _http_version (str): HTTP version.
    """

    _headers: dict[str, str] = attrs.field(factory=dict)
    _method: str = attrs.field(default="")
    _path: str = attrs.field(default="")
    _http_version: str = attrs.field(default="")

    @classmethod
    def from_raw_headers(cls, header_data: bytes) -> RequestHeader:
        """
        Create a RequestHeader object from raw header data.

        :param header_data: Raw header data as bytes.
        :return: RequestHeader object.
        """
        header_obj = cls()
        lines = header_data.decode("utf-8", errors="replace").split("\r\n")

        if lines and " " in lines[0]:
            request_parts = lines[0].split(" ")
            if len(request_parts) >= 3:
                header_obj._method = request_parts[0]
                header_obj._path = request_parts[1]
                header_obj._http_version = request_parts[2]
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                header_obj[key.strip()] = value.strip()

        return header_obj

    @classmethod
    def from_lines(cls, lines: list[str]) -> RequestHeader:
        """
        Create a RequestHeader object from header lines.

        :param lines: List of header lines as strings.
        :return: RequestHeader object.
        """
        header_obj = cls()
        if lines and " " in lines[0]:
            request_parts = lines[0].split(" ")
            if len(request_parts) >= 3:
                header_obj._method = request_parts[0]
                header_obj._path = request_parts[1]
                header_obj._http_version = request_parts[2]
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                header_obj[key.strip()] = value.strip()

        return header_obj

    def __getitem__(self, key: str) -> str:
        return self._headers[key.lower()]

    def __setitem__(self, key: str, value: str) -> None:
        self._headers[key.lower()] = str(value)

    def __contains__(self, key: str) -> bool:
        return key.lower() in self._headers

    def get(self, key: str, default: Any = None) -> str:
        """
        Get a header value by key with a default.

        :param key: Header name.
        :param default: Default value if header does not exist.
        :return: Header value as a string or default.
        """
        return self._headers.get(key.lower(), default)

    def items(self) -> Iterator[tuple[str, str]]:
        """
        Get an iterator of header items.

        :return: Iterator of header items as (key, value) tuples.
        """
        return self._headers.items()

    @property
    def method(self) -> str:
        """
        Get the HTTP method.

        :return: HTTP method as a string.
        """
        return self._method

    @property
    def path(self) -> str:
        """
        Get the request path.

        :return: Request path as a string.
        """
        return self._path

    @property
    def http_version(self) -> str:
        """
        Get the HTTP version.

        :return: HTTP version as a string.
        """
        return self._http_version

    @property
    def content_type(self) -> str | None:
        """
        Get the Content-Type header.

        :return: Content-Type as a string or None.
        """
        return self.get("content-type")

    @property
    def content_length(self) -> int | None:
        """
        Get the Content-Length header.

        :return: Content-Length as an integer or None.
        """
        length = self.get("content-length")
        if length is not None:
            try:
                return int(length)
            except ValueError:
                pass
        return None

    @property
    def host(self) -> str | None:
        """
        Get the Host header.

        :return: Host as a string or None.
        """
        return self.get("host")

    @property
    def user_agent(self) -> str | None:
        """
        Get the User-Agent header.

        :return: User-Agent as a string or None.
        """
        return self.get("user-agent")

    @property
    def is_json(self) -> bool:
        """
        Check if the request is JSON.

        :return: True if Content-Type is application/json, else False.
        """
        content_type = self.content_type
        return content_type is not None and "application/json" in content_type.lower()

    @property
    def is_form_data(self) -> bool:
        """
        Check if the request is form data.

        :return: True if Content-Type is application/x-www-form-urlencoded, else False.
        """
        content_type = self.content_type
        return (
            content_type is not None
            and "application/x-www-form-urlencoded" in content_type.lower()
        )

    def __str__(self) -> str:
        parts = []
        if self._method and self._path and self._http_version:
            parts.append(f"{self._method} {self._path} {self._http_version}")
        if self._headers:
            max_key_length = max((len(key) for key in self._headers.keys()), default=0)
            priority_headers = ["host", "content-type", "content-length", "user-agent"]
            for priority_key in priority_headers:
                if priority_key in self._headers:
                    key_display = priority_key.title()
                    value = self._headers[priority_key]
                    parts.append(f"{key_display:<{max_key_length + 2}}: {value}")
            for key, value in sorted(self._headers.items()):
                if key not in priority_headers:
                    key_display = key.title()
                    parts.append(f"{key_display:<{max_key_length + 2}}: {value}")

        return "\n".join(parts)
