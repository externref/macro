from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

import attrs


@attrs.define
class Response:
    """
    A class representing an HTTP response.

    Attributes:
        status (int): HTTP status code.
        headers (dict[str, str]): HTTP headers.
        body (bytes): Response body.
        _sent (bool): Flag indicating if the response has been sent.
    """

    status: int = attrs.field(default=200)
    headers: dict[str, str] = attrs.field(factory=dict)
    body: bytes = attrs.field(default=b"")
    _sent: bool = attrs.field(default=False, init=False)

    @classmethod
    def html(cls, content: str, status: int = 200) -> Response:
        """
        Create an HTML response.

        :param content: HTML content as a string.
        :param status: HTTP status code.
        :return: Response object.
        """
        response = cls(
            status=status,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=content.encode("utf-8"),
        )
        return response

    @classmethod
    def json(cls, data: Any, status: int = 200) -> Response:
        """
        Create a JSON response.

        :param data: Data to be serialized to JSON.
        :param status: HTTP status code.
        :return: Response object.
        """
        response = cls(
            status=status,
            headers={"Content-Type": "application/json"},
            body=json.dumps(data).encode("utf-8"),
        )
        return response

    @classmethod
    def text(cls, text: str, status: int = 200) -> Response:
        """
        Create a plain text response.

        :param text: Text content.
        :param status: HTTP status code.
        :return: Response object.
        """
        response = cls(
            status=status,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=text.encode("utf-8"),
        )
        return response

    @classmethod
    def redirect(cls, location: str, status: int = 302) -> Response:
        """
        Create a redirect response.

        :param location: URL to redirect to.
        :param status: HTTP status code.
        :return: Response object.
        """
        response = cls(
            status=status,
            headers={"Location": location},
            body=f"Redirecting to {location}".encode("utf-8"),
        )
        return response

    @classmethod
    def error(
        cls, message: str = "Internal Server Error", status: int = 500
    ) -> Response:
        """
        Create an error response.

        :param message: Error message.
        :param status: HTTP status code.
        :return: Response object.
        """
        response = cls(
            status=status,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=message.encode("utf-8"),
        )
        return response

    def set_header(self, key: str, value: str) -> Response:
        """
        Set a header for the response.

        :param key: Header name.
        :param value: Header value.
        :return: Response object.
        """
        self.headers[key] = value
        return self

    def set_content_type(self, content_type: str) -> Response:
        """
        Set the Content-Type header for the response.

        :param content_type: Content-Type value.
        :return: Response object.
        """
        self.headers["Content-Type"] = content_type
        return self

    def set_cookie(
        self,
        name: str,
        value: str,
        max_age: int = None,
        expires: str = None,
        path: str = "/",
        domain: str = None,
        secure: bool = False,
        http_only: bool = False,
        same_site: str = None,
    ) -> Response:
        """
        Set a cookie for the response.

        :param name: Cookie name.
        :param value: Cookie value.
        :param max_age: Max-Age attribute.
        :param expires: Expires attribute.
        :param path: Path attribute.
        :param domain: Domain attribute.
        :param secure: Secure attribute.
        :param http_only: HttpOnly attribute.
        :param same_site: SameSite attribute.
        :return: Response object.
        """
        cookie_parts = [f"{name}={value}"]

        if max_age is not None:
            cookie_parts.append(f"Max-Age={max_age}")
        if expires is not None:
            cookie_parts.append(f"Expires={expires}")
        if path:
            cookie_parts.append(f"Path={path}")
        if domain:
            cookie_parts.append(f"Domain={domain}")
        if secure:
            cookie_parts.append("Secure")
        if http_only:
            cookie_parts.append("HttpOnly")
        if same_site:
            cookie_parts.append(f"SameSite={same_site}")

        cookie_header = "; ".join(cookie_parts)

        if "Set-Cookie" in self.headers:
            self.headers["Set-Cookie"] = (
                self.headers["Set-Cookie"] + "\n" + cookie_header
            )
        else:
            self.headers["Set-Cookie"] = cookie_header

        return self

    def prepare_headers(self) -> list[tuple[bytes, bytes]]:
        """
        Prepare headers for the response.

        :return: List of headers as tuples of bytes.
        """
        final_headers = dict(self.headers)

        if "Content-Length" not in final_headers:
            final_headers["Content-Length"] = str(len(self.body))

        return [
            (key.lower().encode("latin1"), value.encode("latin1"))
            for key, value in final_headers.items()
        ]

    async def send(self, send_func: Callable[[dict], Awaitable[None]]) -> None:
        """
        Send the response using the provided send function.

        :param send_func: Callable to send the response.
        """
        if self._sent:
            raise RuntimeError("Response has already been sent")

        await send_func(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": self.prepare_headers(),
            }
        )

        await send_func(
            {"type": "http.response.body", "body": self.body, "more_body": False}
        )

        self._sent = True

    def __str__(self) -> str:
        status_line = f"HTTP/1.1 {self.status} {self._status_phrase()}"
        headers = "\n".join([f"{key}: {value}" for key, value in self.headers.items()])
        body_preview = self.body[:100].decode("utf-8", errors="replace")
        if len(self.body) > 100:
            body_preview += "..."

        return f"{status_line}\n{headers}\n\n{body_preview}"

    def _status_phrase(self) -> str:
        phrases = {
            200: "OK",
            201: "Created",
            204: "No Content",
            301: "Moved Permanently",
            302: "Found",
            304: "Not Modified",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }
        return phrases.get(self.status, "Unknown")


class JSONResponse(Response):
    """
    A class representing a JSON response.

    Inherits from Response.

    Attributes:
        data (Any): Data to be serialized to JSON.
        status (int): HTTP status code.
    """

    def __init__(self, data: Any, status: int = 200):
        super().__init__(
            status=status,
            headers={"Content-Type": "application/json"},
            body=json.dumps(data).encode("utf-8"),
        )


class HTMLResponse(Response):
    """
    A class representing an HTML response.

    Inherits from Response.

    Attributes:
        content (str): HTML content as a string.
        status (int): HTTP status code.
    """

    def __init__(self, content: str, status: int = 200):
        super().__init__(
            status=status,
            headers={"Content-Type": "text/html; charset=utf-8"},
            body=content.encode("utf-8"),
        )


class PlainTextResponse(Response):
    """
    A class representing a plain text response.

    Inherits from Response.

    Attributes:
        text (str): Text content.
        status (int): HTTP status code.
    """

    def __init__(self, text: str, status: int = 200):
        super().__init__(
            status=status,
            headers={"Content-Type": "text/plain; charset=utf-8"},
            body=text.encode("utf-8"),
        )


class RedirectResponse(Response):
    """
    A class representing a redirect response.

    Inherits from Response.

    Attributes:
        location (str): URL to redirect to.
        status (int): HTTP status code.
    """

    def __init__(self, location: str, status: int = 302):
        super().__init__(
            status=status,
            headers={"Location": location},
            body=f"Redirecting to {location}".encode("utf-8"),
        )


class StreamingResponse(Response):
    """
    A class representing a streaming response.

    Inherits from Response.

    Attributes:
        content (list[bytes] | iter[bytes]): Content to stream.
        status (int): HTTP status code.
        headers (dict[str, str]): Additional headers.
    """

    def __init__(
        self,
        content: list[bytes] | iter[bytes],
        status: int = 200,
        headers: dict[str, str] = None,
    ):
        super().__init__(status=status, headers=headers or {}, body=b"")
        self.content = content

        if "Content-Length" in self.headers:
            del self.headers["Content-Length"]

    async def send(self, send_func: Callable[[dict], Awaitable[None]]) -> None:
        """
        Send the streaming response using the provided send function.

        :param send_func: Callable to send the response.
        """
        if self._sent:
            raise RuntimeError("Response has already been sent")

        await send_func(
            {
                "type": "http.response.start",
                "status": self.status,
                "headers": self.prepare_headers(),
            }
        )

        is_iterable = hasattr(self.content, "__iter__") and not isinstance(
            self.content, (bytes, str)
        )

        if is_iterable:
            for i, chunk in enumerate(self.content):
                if not isinstance(chunk, bytes):
                    chunk = str(chunk).encode("utf-8")

                await send_func(
                    {"type": "http.response.body", "body": chunk, "more_body": True}
                )

            await send_func(
                {"type": "http.response.body", "body": b"", "more_body": False}
            )
        else:
            content = self.content
            if not isinstance(content, bytes):
                content = str(content).encode("utf-8")

            await send_func(
                {"type": "http.response.body", "body": content, "more_body": False}
            )

        self._sent = True
