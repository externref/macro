from __future__ import annotations

import re
import typing
from inspect import Parameter, signature

from macro.request import Request, RequestHeader
from macro.response import Response

if typing.TYPE_CHECKING:
    import asgiref.typing as asgiref_typing

ResponseT: typing.TypeAlias = typing.Type[Response]
RouteT: typing.TypeAlias = typing.Callable[
    [Request, ResponseT], typing.Awaitable[Response]
]


class Macro:
    """
    A simple web framework for handling HTTP requests with support for dynamic paths and type casting.
    """

    def __init__(self):
        self.routes: dict[str, dict[str, RouteT]] = {}

    async def __call__(self, scope: asgiref_typing.Scope, receive, send) -> None:
        if scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        else:
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Only HTTP requests are supported",
                }
            )

    async def handle_http(self, scope: asgiref_typing.HTTPScope, receive, send) -> None:
        """
        Handle HTTP requests.

        :param scope: The scope of the request.
        :param receive: The receive channel to get request data.
        :param send: The send channel to send response data.
        """
        headers, body = await self._parse(scope, receive)
        path = scope["path"]
        method = scope["method"]
        fn, path_vars = self._find_route(path, method)
        if fn is None:
            response = Response(status=404, body=b"Not Found")
        else:
            try:
                path_vars = self._cast_path_vars(fn, path_vars)
            except ValueError:
                response = Response(status=404, body=b"Not Found")
            else:
                request = Request(headers=headers, body=body)
                response = await fn(request, Response, **path_vars)
            await response.send(send)

    def _find_route(
        self, path: str, method: str
    ) -> typing.Tuple[typing.Optional[RouteT], dict]:
        for route_path, methods in self.routes.items():
            match = re.fullmatch(route_path, path)
            if match and method in methods:
                return methods[method], match.groupdict()
        return None, {}

    def _cast_path_vars(self, fn: RouteT, path_vars: dict) -> dict:
        sig = signature(fn)
        for name, param in sig.parameters.items():
            if name in path_vars and param.annotation != Parameter.empty:
                try:
                    path_vars[name] = param.annotation(path_vars[name])
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid type for path variable '{name}'")
        return path_vars

    async def _parse(
        self, scope: asgiref_typing.HTTPScope, receive
    ) -> tuple[RequestHeader, bytes]:
        headers = RequestHeader()
        headers._method = scope.get("method", "")
        headers._path = scope.get("path", "")
        headers._http_version = f"HTTP/{scope.get('http_version', '1.1')}"

        for name, value in scope.get("headers", []):
            headers[name.decode("latin1")] = value.decode("latin1")

        body = b""
        more_body = True

        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

        return headers, body

    def route(
        self, path: str, method: str = "GET"
    ) -> typing.Callable[[RouteT], RouteT]:
        """
        Decorator to register a route handler for a specific path and method.

        :param path: The route path, which can include dynamic segments.
        :param method: The HTTP method (default is "GET").
        :return: The decorator function.
        """

        def decorator(func: RouteT) -> RouteT:
            # Convert dynamic path to regex with named groups
            path_regex = re.sub(r"{([^/]+)}", r"(?P<\1>[^/]+)", path)
            if path_regex not in self.routes:
                self.routes[path_regex] = {}

            self.routes[path_regex][method] = func
            return func

        return decorator
